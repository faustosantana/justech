"""OAuth Microsoft 365 por usuario JAIOS."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.m365_account import M365UserAccount
from app.models.user import User
from app.schemas.m365_account import M365AccountResponse
from app.services.audit_service import AuditService
from app.services.credential_vault import decrypt_secret, encrypt_secret
from app.services.m365_account_service import M365AccountService
from app.services.m365_config_resolver import resolve_m365_config
from integrations.microsoft365.config import DEFAULT_READ_SCOPES, M365Config
from integrations.microsoft365.oauth import M365OAuthError, authorization_url, exchange_code, refresh_tokens


class M365OAuthService:
    STATE_PURPOSE = "m365_oauth"
    STATE_TTL_MINUTES = 15

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, actor_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self.audit = AuditService(db)
        self.accounts = M365AccountService(db, tenant_id, actor_id=actor_id)

    async def _config_async(self) -> M365Config:
        cfg, _ = await resolve_m365_config(self.db, self.tenant_id)
        return cfg

    def _encode_state(self) -> str:
        payload = {
            "sub": str(self.actor_id),
            "tenant_id": str(self.tenant_id),
            "purpose": self.STATE_PURPOSE,
            "exp": datetime.now(UTC).timestamp() + self.STATE_TTL_MINUTES * 60,
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def _decode_state(self, state: str) -> tuple[uuid.UUID, uuid.UUID]:
        try:
            payload = jwt.decode(state, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        except JWTError as exc:
            raise M365OAuthError("State OAuth inválido o expirado") from exc
        if payload.get("purpose") != self.STATE_PURPOSE:
            raise M365OAuthError("State OAuth inválido")
        return uuid.UUID(payload["tenant_id"]), uuid.UUID(payload["sub"])

    async def build_authorize_url(self) -> str:
        cfg = await self._config_async()
        if not cfg.is_configured():
            raise M365OAuthError("Microsoft 365 no configurado — complete variables de entorno")
        return authorization_url(cfg, state=self._encode_state())

    async def handle_callback(self, code: str, state: str) -> M365AccountResponse:
        tenant_id, user_id = self._decode_state(state)
        if tenant_id != self.tenant_id:
            raise M365OAuthError("Tenant no coincide")
        cfg = await self._config_async()
        tokens = await exchange_code(cfg, code)

        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise M365OAuthError("Usuario no encontrado")

        from integrations.microsoft365.graph_client import GraphClient
        from integrations.microsoft365.schemas import M365OAuthTokens

        graph = GraphClient(cfg, tokens=M365OAuthTokens(access_token=tokens.access_token))
        try:
            me = await graph.get_me()
            ms_email = me.get("mail") or me.get("userPrincipalName") or user.email
            ms_name = me.get("displayName") or user.full_name
            ms_id = me.get("id")
        except Exception:
            ms_email = user.email
            ms_name = user.full_name
            ms_id = None

        existing = await self.db.execute(
            select(M365UserAccount).where(
                M365UserAccount.tenant_id == self.tenant_id,
                M365UserAccount.jaios_user_id == user_id,
                M365UserAccount.email == ms_email,
            )
        )
        acc = existing.scalar_one_or_none()
        if not acc:
            acc = M365UserAccount(
                tenant_id=self.tenant_id,
                jaios_user_id=user_id,
                email=ms_email,
                is_active=True,
            )
            self.db.add(acc)

        acc.connection_mode = "oauth"
        acc.connection_status = "connected"
        acc.token_status = "valid"
        acc.last_graph_error = None
        acc.access_token_encrypted = encrypt_secret(tokens.access_token)
        acc.refresh_token_encrypted = encrypt_secret(tokens.refresh_token) if tokens.refresh_token else None
        acc.token_expires_at = tokens.expires_at
        acc.scopes_granted = tokens.scopes or list(DEFAULT_READ_SCOPES)
        acc.imap_password_encrypted = None
        acc.imap_host = None
        acc.email = ms_email
        acc.microsoft_user_id = ms_id
        acc.display_name = ms_name
        acc.last_sync_at = datetime.now(UTC)

        await self.audit.log(
            action="m365.oauth_connected",
            tenant_id=self.tenant_id,
            user_id=user_id,
            resource_type="m365_account",
            resource_id=acc.id if acc.id else None,
            details={"scopes": acc.scopes_granted},
        )
        await self.db.flush()
        return self.accounts._to_response(acc, user)

    async def _oauth_account(
        self, user_id: uuid.UUID, account_id: uuid.UUID | None = None
    ) -> M365UserAccount | None:
        q = select(M365UserAccount).where(
            M365UserAccount.tenant_id == self.tenant_id,
            M365UserAccount.jaios_user_id == user_id,
            M365UserAccount.connection_mode == "oauth",
            M365UserAccount.is_active.is_(True),
        )
        if account_id:
            q = q.where(M365UserAccount.id == account_id)
        result = await self.db.execute(q.order_by(M365UserAccount.email.asc()))
        return result.scalars().first()

    async def refresh_account_tokens(
        self, user_id: uuid.UUID, account_id: uuid.UUID | None = None
    ) -> M365UserAccount | None:
        acc = await self._oauth_account(user_id, account_id)
        if not acc or not acc.refresh_token_encrypted:
            if acc:
                acc.connection_status = "expired"
                acc.token_status = "error"
                await self.db.flush()
            return None
        refresh = decrypt_secret(acc.refresh_token_encrypted)
        cfg = await self._config_async()
        try:
            tokens = await refresh_tokens(cfg, refresh)
        except M365OAuthError:
            acc.connection_status = "expired"
            acc.token_status = "error"
            acc.last_graph_error = "No se pudo renovar el refresh token"
            await self.db.flush()
            return None
        acc.access_token_encrypted = encrypt_secret(tokens.access_token)
        if tokens.refresh_token:
            acc.refresh_token_encrypted = encrypt_secret(tokens.refresh_token)
        acc.token_expires_at = tokens.expires_at
        acc.connection_status = "connected"
        acc.token_status = "valid"
        acc.last_graph_error = None
        await self.db.flush()
        return acc

    async def get_valid_access_token(
        self, user_id: uuid.UUID, account_id: uuid.UUID | None = None
    ) -> str | None:
        acc = await self._oauth_account(user_id, account_id)
        if not acc or not acc.access_token_encrypted:
            return None
        if acc.connection_status not in ("connected", "expired"):
            return None
        if acc.token_expires_at and acc.token_expires_at <= datetime.now(UTC):
            acc = await self.refresh_account_tokens(user_id, acc.id)
            if not acc or not acc.access_token_encrypted:
                return None
        return decrypt_secret(acc.access_token_encrypted)
