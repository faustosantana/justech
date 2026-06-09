"""Servicio — Empresas y proveedores."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_company import BusinessCompany
from app.schemas.business_company import (
    BusinessCompanyCreate,
    BusinessCompanyListResponse,
    BusinessCompanyResponse,
    BusinessCompanyUpdate,
)


class BusinessCompanyService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def list_companies(
        self,
        *,
        company_type: str | None = None,
        status: str | None = None,
        search: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> BusinessCompanyListResponse:
        stmt = select(BusinessCompany).where(BusinessCompany.tenant_id == self.tenant_id)
        count_stmt = select(func.count(BusinessCompany.id)).where(
            BusinessCompany.tenant_id == self.tenant_id
        )
        if company_type:
            stmt = stmt.where(BusinessCompany.company_type == company_type)
            count_stmt = count_stmt.where(BusinessCompany.company_type == company_type)
        if status:
            stmt = stmt.where(BusinessCompany.status == status)
            count_stmt = count_stmt.where(BusinessCompany.status == status)
        if search.strip():
            pattern = f"%{search.strip()}%"
            filt = or_(
                BusinessCompany.name.ilike(pattern),
                BusinessCompany.tax_id.ilike(pattern),
                BusinessCompany.email.ilike(pattern),
                BusinessCompany.primary_contact.ilike(pattern),
                BusinessCompany.category.ilike(pattern),
            )
            stmt = stmt.where(filt)
            count_stmt = count_stmt.where(filt)

        total = int((await self.db.execute(count_stmt)).scalar() or 0)
        result = await self.db.execute(
            stmt.order_by(BusinessCompany.name.asc()).limit(limit).offset(offset)
        )
        items = [
            BusinessCompanyResponse.model_validate(row)
            for row in result.scalars().all()
        ]
        return BusinessCompanyListResponse(items=items, total=total)

    async def get(self, company_id: uuid.UUID) -> BusinessCompanyResponse | None:
        result = await self.db.execute(
            select(BusinessCompany).where(
                BusinessCompany.tenant_id == self.tenant_id,
                BusinessCompany.id == company_id,
            )
        )
        row = result.scalar_one_or_none()
        return BusinessCompanyResponse.model_validate(row) if row else None

    async def create(self, payload: BusinessCompanyCreate) -> BusinessCompanyResponse:
        row = BusinessCompany(tenant_id=self.tenant_id, **payload.model_dump())
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return BusinessCompanyResponse.model_validate(row)

    async def update(
        self, company_id: uuid.UUID, payload: BusinessCompanyUpdate
    ) -> BusinessCompanyResponse | None:
        result = await self.db.execute(
            select(BusinessCompany).where(
                BusinessCompany.tenant_id == self.tenant_id,
                BusinessCompany.id == company_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, key, value)
        await self.db.commit()
        await self.db.refresh(row)
        return BusinessCompanyResponse.model_validate(row)

    async def deactivate(self, company_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(BusinessCompany).where(
                BusinessCompany.tenant_id == self.tenant_id,
                BusinessCompany.id == company_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        row.status = "inactivo"
        await self.db.commit()
        return True
