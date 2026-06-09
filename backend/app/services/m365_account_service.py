"""Cuentas Microsoft 365 por usuario — preparación sin Graph real."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.m365_account import M365UserAccount
from app.models.user import User
from app.schemas.m365_account import (
    M365AccountListResponse,
    M365AccountPrepareRequest,
    M365AccountResponse,
)
from app.services.audit_service import AuditService

REQUIRED_SCOPES = [
    "Mail.Read",
    "Mail.Send",
    "Mail.ReadWrite",
    "User.Read",
    "offline_access",
]

STATUS_LABELS = {
    "not_connected": "No conectado",
    "connected": "Conectado",
    "expired": "Expirado",
    "prepared": "Preparado",
}


class M365AccountService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, actor_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self.audit = AuditService(db)

    def _to_response(self, acc: M365UserAccount, user: User | None = None) -> M365AccountResponse:
        return M365AccountResponse(
            id=acc.id,
            jaios_user_id=acc.jaios_user_id,
            jaios_user_name=user.full_name if user else None,
            jaios_user_email=user.email if user else None,
            email=acc.email,
            microsoft_user_id=acc.microsoft_user_id,
            display_name=acc.display_name,
            connection_status=acc.connection_status,
            scopes_granted=acc.scopes_granted or [],
            token_expires_at=acc.token_expires_at,
            last_sync_at=acc.last_sync_at,
            is_active=acc.is_active,
            can_connect=acc.connection_status in ("not_connected", "prepared", "expired"),
            required_scopes=REQUIRED_SCOPES,
        )

    async def list_accounts(self) -> M365AccountListResponse:
        result = await self.db.execute(
            select(M365UserAccount, User)
            .join(User, User.id == M365UserAccount.jaios_user_id)
            .where(M365UserAccount.tenant_id == self.tenant_id)
            .order_by(User.full_name.asc())
        )
        items = [self._to_response(acc, user) for acc, user in result.all()]
        return M365AccountListResponse(items=items, total=len(items))

    async def get_my_account(self, user_id: uuid.UUID) -> M365AccountResponse | None:
        result = await self.db.execute(
            select(M365UserAccount, User)
            .join(User, User.id == M365UserAccount.jaios_user_id)
            .where(
                M365UserAccount.tenant_id == self.tenant_id,
                M365UserAccount.jaios_user_id == user_id,
            )
        )
        row = result.first()
        if not row:
            return None
        acc, user = row
        return self._to_response(acc, user)

    async def prepare_account(
        self, payload: M365AccountPrepareRequest, *, actor_id: uuid.UUID
    ) -> M365AccountResponse:
        target_user_id = payload.jaios_user_id or actor_id
        user_result = await self.db.execute(select(User).where(User.id == target_user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("Usuario no encontrado")

        existing = await self.db.execute(
            select(M365UserAccount).where(
                M365UserAccount.tenant_id == self.tenant_id,
                M365UserAccount.jaios_user_id == target_user_id,
            )
        )
        acc = existing.scalar_one_or_none()
        if not acc:
            acc = M365UserAccount(
                tenant_id=self.tenant_id,
                jaios_user_id=target_user_id,
                email=payload.email or user.email,
                display_name=user.full_name,
                connection_status="prepared",
                scopes_granted=[],
                is_active=True,
            )
            self.db.add(acc)
        else:
            acc.email = payload.email or acc.email or user.email
            acc.display_name = user.full_name
            acc.connection_status = "prepared"
            acc.is_active = True

        await self.audit.log(
            action="m365.account_prepared",
            tenant_id=self.tenant_id,
            user_id=actor_id,
            resource_type="m365_account",
            resource_id=acc.id if acc.id else None,
            details={"jaios_user_id": str(target_user_id), "email": acc.email},
        )
        await self.db.flush()
        return self._to_response(acc, user)

    async def delete_account(self, account_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(M365UserAccount).where(
                M365UserAccount.id == account_id,
                M365UserAccount.tenant_id == self.tenant_id,
            )
        )
        acc = result.scalar_one_or_none()
        if not acc:
            return False
        acc.is_active = False
        acc.connection_status = "not_connected"
        acc.access_token_encrypted = None
        acc.refresh_token_encrypted = None
        await self.db.flush()
        return True
