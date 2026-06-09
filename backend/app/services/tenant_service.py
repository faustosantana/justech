from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TenantNotFoundError
from app.models.tenant import Tenant, TenantMembership
from app.models.user import User
from app.schemas.tenant import TenantCreate


class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant(self, data: TenantCreate, owner: User) -> Tenant:
        existing = await self.db.execute(select(Tenant).where(Tenant.slug == data.slug))
        if existing.scalar_one_or_none():
            raise TenantNotFoundError(f"Tenant slug '{data.slug}' already exists")

        tenant = Tenant(
            slug=data.slug,
            name=data.name,
            legal_name=data.legal_name,
            tax_id=data.tax_id,
        )
        self.db.add(tenant)
        await self.db.flush()

        membership = TenantMembership(
            tenant_id=tenant.id,
            user_id=owner.id,
            role="owner",
            is_default=True,
        )
        self.db.add(membership)
        await self.db.flush()
        return tenant

    async def get_by_id(self, tenant_id) -> Tenant:
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise TenantNotFoundError("Tenant not found")
        return tenant

    async def get_by_slug(self, slug: str) -> Tenant:
        result = await self.db.execute(select(Tenant).where(Tenant.slug == slug))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise TenantNotFoundError("Tenant not found")
        return tenant
