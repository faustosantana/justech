"""Servicio de usuarios por tenant."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import TenantMembership
from app.models.user import User
from app.schemas.users import TenantUserListResponse, TenantUserResponse


class UserService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def list_tenant_users(
        self,
        *,
        search: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> TenantUserListResponse:
        q = (
            select(User, TenantMembership.role)
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .where(
                TenantMembership.tenant_id == self.tenant_id,
                User.is_active.is_(True),
            )
        )
        if search:
            pattern = f"%{search}%"
            q = q.where(
                (User.full_name.ilike(pattern)) | (User.email.ilike(pattern))
            )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(User.full_name.asc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        items = [
            TenantUserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=role,
                is_active=user.is_active,
            )
            for user, role in result.all()
        ]
        return TenantUserListResponse(items=items, total=total)

    async def get_user_in_tenant(self, user_id: uuid.UUID) -> TenantUserResponse | None:
        result = await self.db.execute(
            select(User, TenantMembership.role)
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .where(
                TenantMembership.tenant_id == self.tenant_id,
                User.id == user_id,
                User.is_active.is_(True),
            )
            .limit(1)
        )
        row = result.first()
        if not row:
            return None
        user, role = row
        return TenantUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=role,
            is_active=user.is_active,
        )
