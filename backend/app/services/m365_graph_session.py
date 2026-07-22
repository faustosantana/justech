"""Sesión Graph por cuenta M365 — tokens, errores reales, multi-cuenta."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.m365_account import M365UserAccount
from app.services.m365_config_resolver import resolve_m365_config
from app.services.m365_oauth_service import M365OAuthService
from integrations.microsoft365.client import M365Client
from integrations.microsoft365.errors import GraphError
from integrations.microsoft365.schemas import M365OAuthTokens


@dataclass
class M365GraphSession:
    account: M365UserAccount
    client: M365Client
    email: str | None


class M365GraphSessionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, actor_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self._oauth = M365OAuthService(db, tenant_id, actor_id)

    async def list_accounts(self, *, oauth_only: bool = True) -> list[M365UserAccount]:
        q = select(M365UserAccount).where(
            M365UserAccount.tenant_id == self.tenant_id,
            M365UserAccount.jaios_user_id == self.actor_id,
            M365UserAccount.is_active.is_(True),
        )
        if oauth_only:
            q = q.where(M365UserAccount.connection_mode == "oauth")
        result = await self.db.execute(q.order_by(M365UserAccount.email.asc()))
        return list(result.scalars().all())

    async def get_account(self, account_id: uuid.UUID) -> M365UserAccount | None:
        result = await self.db.execute(
            select(M365UserAccount).where(
                M365UserAccount.id == account_id,
                M365UserAccount.tenant_id == self.tenant_id,
                M365UserAccount.jaios_user_id == self.actor_id,
                M365UserAccount.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _mark_token_error(self, acc: M365UserAccount, error: str) -> None:
        acc.connection_status = "expired"
        acc.last_graph_error = error[:500]
        acc.token_status = "error"
        await self.db.flush()

    async def session_for_account(self, account_id: uuid.UUID | None = None) -> M365GraphSession:
        accounts = await self.list_accounts()
        if not accounts:
            raise GraphError(401, "Sin cuenta Microsoft 365 conectada — use OAuth en Cuentas M365")

        acc = None
        if account_id:
            acc = await self.get_account(account_id)
            if not acc:
                raise GraphError(404, "Cuenta no encontrada o sin acceso")
        if not acc:
            acc = next((a for a in accounts if a.connection_status == "connected"), accounts[0])

        if acc.connection_mode != "oauth":
            raise GraphError(400, "Esta cuenta usa IMAP — use OAuth para Graph API")

        cfg, _ = await resolve_m365_config(self.db, self.tenant_id)
        token = await self._oauth.get_valid_access_token(acc.jaios_user_id, acc.id)
        if not token:
            await self._mark_token_error(acc, "No se pudo renovar el token OAuth")
            raise GraphError(401, "Token OAuth expirado — reconecte la cuenta", error_code="token_expired")

        client = M365Client(cfg, tokens=M365OAuthTokens(access_token=token))
        try:
            me = await client.graph().get_me()
            acc.email = me.get("mail") or me.get("userPrincipalName") or acc.email
            acc.display_name = me.get("displayName") or acc.display_name
            acc.microsoft_user_id = me.get("id")
            acc.connection_status = "connected"
            acc.token_status = "valid"
            acc.last_graph_error = None
            acc.last_sync_at = datetime.now(UTC)
            await self.db.flush()
        except GraphError as exc:
            await self._mark_token_error(acc, exc.message)
            raise
        except Exception as exc:
            await self._mark_token_error(acc, str(exc))
            raise GraphError(502, f"Graph no respondió: {exc}") from exc

        return M365GraphSession(account=acc, client=client, email=acc.email)

    async def verify_all_accounts(self) -> list[dict]:
        out = []
        for acc in await self.list_accounts():
            try:
                await self.session_for_account(acc.id)
                out.append({"id": str(acc.id), "email": acc.email, "status": "connected"})
            except GraphError as exc:
                out.append({
                    "id": str(acc.id),
                    "email": acc.email,
                    "status": "error",
                    "error": exc.message,
                    "permission_hint": exc.permission_hint,
                })
        return out
