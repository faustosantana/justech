import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.business_company import (
    BusinessCompanyCreate,
    BusinessCompanyListResponse,
    BusinessCompanyResponse,
    BusinessCompanyUpdate,
)
from app.services.business_company_service import BusinessCompanyService

router = APIRouter(prefix="/companies", tags=["Empresas y proveedores"])


def _svc(db: DbSession) -> BusinessCompanyService:
    ctx = require_tenant_context()
    return BusinessCompanyService(db, ctx.tenant_id)


@router.get("", response_model=BusinessCompanyListResponse)
async def list_companies(
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
    company_type: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BusinessCompanyListResponse:
    return await _svc(db).list_companies(
        company_type=company_type,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=BusinessCompanyResponse, status_code=201)
async def create_company(
    db: DbSession, _: CurrentUser, __: TenantCtx, payload: BusinessCompanyCreate
) -> BusinessCompanyResponse:
    return await _svc(db).create(payload)


@router.get("/{company_id}", response_model=BusinessCompanyResponse)
async def get_company(
    db: DbSession, _: CurrentUser, __: TenantCtx, company_id: uuid.UUID
) -> BusinessCompanyResponse:
    row = await _svc(db).get(company_id)
    if not row:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return row


@router.put("/{company_id}", response_model=BusinessCompanyResponse)
async def update_company(
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
    company_id: uuid.UUID,
    payload: BusinessCompanyUpdate,
) -> BusinessCompanyResponse:
    row = await _svc(db).update(company_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return row


@router.post("/{company_id}/deactivate", response_model=BusinessCompanyResponse)
async def deactivate_company(
    db: DbSession, _: CurrentUser, __: TenantCtx, company_id: uuid.UUID
) -> BusinessCompanyResponse:
    if not await _svc(db).deactivate(company_id):
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    row = await _svc(db).get(company_id)
    assert row
    return row
