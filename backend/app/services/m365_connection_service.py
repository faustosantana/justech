"""Estado de conexión Microsoft 365 — Azure vs cuenta OAuth verificada."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.m365_account import M365UserAccount
from app.schemas.m365 import M365AccountSummary, M365ConnectionState
from app.services.m365_config_resolver import resolve_m365_config
from app.services.m365_graph_session import M365GraphSessionService
from integrations.microsoft365.errors import GraphError


class M365ConnectionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def _accounts_query(self):
        q = select(M365UserAccount).where(
            M365UserAccount.tenant_id == self.tenant_id,
            M365UserAccount.is_active.is_(True),
            M365UserAccount.connection_mode == "oauth",
        )
        if self.user_id:
            q = q.where(M365UserAccount.jaios_user_id == self.user_id)
        return q.order_by(M365UserAccount.email.asc())

    async def list_oauth_accounts(self) -> list[M365UserAccount]:
        result = await self.db.execute(await self._accounts_query())
        return list(result.scalars().all())

    async def list_verified_accounts(self) -> list[M365AccountSummary]:
        if not self.user_id:
            return []
        session_svc = M365GraphSessionService(self.db, self.tenant_id, self.user_id)
        summaries: list[M365AccountSummary] = []
        for acc in await self.list_oauth_accounts():
            summary = M365AccountSummary(
                id=acc.id,
                email=acc.email,
                display_name=acc.display_name,
                connection_mode=acc.connection_mode or "oauth",
                connection_status=acc.connection_status,
                microsoft_user_id=acc.microsoft_user_id,
                token_expires_at=acc.token_expires_at,
                last_sync_at=acc.last_sync_at,
                is_active=acc.is_active,
                jaios_user_id=acc.jaios_user_id,
            )
            try:
                await session_svc.session_for_account(acc.id)
                summary.connection_status = "connected"
                summaries.append(summary)
            except GraphError:
                summary.connection_status = acc.connection_status or "expired"
                if acc.last_graph_error:
                    summary.display_name = f"{acc.display_name or acc.email} (error)"
                summaries.append(summary)
        return summaries

    async def connection_state(self, *, verify_graph: bool = True) -> M365ConnectionState:
        cfg, _ = await resolve_m365_config(self.db, self.tenant_id)
        azure_configured = cfg.is_configured()
        raw_accounts = await self.list_oauth_accounts()

        summaries: list[M365AccountSummary] = []
        verified_count = 0
        last_error: str | None = None

        if verify_graph and self.user_id and raw_accounts:
            session_svc = M365GraphSessionService(self.db, self.tenant_id, self.user_id)
            for acc in raw_accounts:
                summary = M365AccountSummary(
                    id=acc.id,
                    email=acc.email,
                    display_name=acc.display_name,
                    connection_mode="oauth",
                    connection_status=acc.connection_status,
                    microsoft_user_id=acc.microsoft_user_id,
                    token_expires_at=acc.token_expires_at,
                    last_sync_at=acc.last_sync_at,
                    is_active=acc.is_active,
                    jaios_user_id=acc.jaios_user_id,
                    token_status=getattr(acc, "token_status", None),
                    last_graph_error=getattr(acc, "last_graph_error", None),
                )
                try:
                    sess = await session_svc.session_for_account(acc.id)
                    summary.connection_status = "connected"
                    summary.email = sess.email
                    summary.token_status = "valid"
                    summary.last_graph_error = None
                    verified_count += 1
                except GraphError as exc:
                    summary.connection_status = "expired" if exc.status_code == 401 else "error"
                    summary.token_status = "error"
                    summary.last_graph_error = exc.message
                    last_error = exc.message
                summaries.append(summary)
        else:
            for acc in raw_accounts:
                if acc.connection_mode == "oauth" and acc.access_token_encrypted and acc.connection_status == "connected":
                    summaries.append(
                        M365AccountSummary(
                            id=acc.id,
                            email=acc.email,
                            display_name=acc.display_name,
                            connection_mode="oauth",
                            connection_status=acc.connection_status,
                            microsoft_user_id=acc.microsoft_user_id,
                            token_expires_at=acc.token_expires_at,
                            last_sync_at=acc.last_sync_at,
                            is_active=acc.is_active,
                            jaios_user_id=acc.jaios_user_id,
                        )
                    )
                    verified_count += 1

        account_connected = verified_count > 0
        primary = summaries[0] if summaries and summaries[0].connection_status == "connected" else None

        if account_connected and primary:
            msg = f"Conectado — {primary.email or primary.display_name or 'cuenta M365'}"
        elif raw_accounts and last_error:
            msg = f"Cuenta registrada pero Graph falló: {last_error}"
        elif azure_configured:
            msg = "Azure configurado — conecte una cuenta Microsoft 365 con OAuth"
        else:
            msg = "Microsoft 365 no conectado"

        return M365ConnectionState(
            connected=account_connected,
            account_connected=account_connected,
            azure_configured=azure_configured,
            oauth_ready=azure_configured,
            read_only=settings.m365_read_only,
            message=msg,
            tenant_id=cfg.tenant_id or None,
            client_id=cfg.client_id or None,
            redirect_uri=cfg.redirect_uri,
            webhook_url=settings.m365_webhook_url or None,
            connected_accounts=summaries,
            active_account=primary,
        )
