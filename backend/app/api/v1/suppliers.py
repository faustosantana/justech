"""API — Directorio inteligente de proveedores."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.supplier import (
    SupplierCategoryCreate,
    SupplierCategoryListResponse,
    SupplierCategoryResponse,
    SupplierCategoryUpdate,
    SupplierCreate,
    SupplierDashboardStats,
    SupplierImportRequest,
    SupplierImportResponse,
    SupplierInteractionResponse,
    SupplierListResponse,
    SupplierPriceListSummary,
    SupplierQuoteRequest,
    SupplierQuoteResponse,
    SupplierResponse,
    SupplierSearchRequest,
    SupplierSearchResponse,
    SupplierTenderSuggestionRequest,
    SupplierTenderSuggestionResponse,
    SupplierUpdate,
)
from app.services.supplier_service import SupplierService

router = APIRouter(prefix="/suppliers", tags=["Directorio de proveedores"])


def _svc(db: DbSession, user: CurrentUser) -> SupplierService:
    ctx = require_tenant_context()
    return SupplierService(db, ctx.tenant_id, user_id=user.id)


@router.get("/dashboard", response_model=SupplierDashboardStats)
async def supplier_dashboard(db: DbSession, user: CurrentUser, _: TenantCtx) -> SupplierDashboardStats:
    await _svc(db, user).ensure_base_categories()
    return await _svc(db, user).dashboard_stats()


@router.get("/categories/list", response_model=SupplierCategoryListResponse)
async def list_supplier_categories(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> SupplierCategoryListResponse:
    svc = _svc(db, user)
    await svc.ensure_base_categories()
    return await svc.list_categories()


@router.post("/categories", response_model=SupplierCategoryResponse, status_code=201)
async def create_supplier_category(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: SupplierCategoryCreate
) -> SupplierCategoryResponse:
    return await _svc(db, user).create_category(payload)


@router.put("/categories/{category_id}", response_model=SupplierCategoryResponse)
async def update_supplier_category(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    category_id: uuid.UUID,
    payload: SupplierCategoryUpdate,
) -> SupplierCategoryResponse:
    row = await _svc(db, user).update_category(category_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return row


@router.post("/search", response_model=SupplierSearchResponse)
async def search_suppliers(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: SupplierSearchRequest
) -> SupplierSearchResponse:
    svc = _svc(db, user)
    await svc.ensure_base_categories()
    return await svc.search(payload)


@router.post("/import", response_model=SupplierImportResponse)
async def import_suppliers(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: SupplierImportRequest
) -> SupplierImportResponse:
    return await _svc(db, user).import_suppliers(payload)


@router.post("/tender-suggestions", response_model=SupplierTenderSuggestionResponse)
async def suggest_suppliers_for_tender(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: SupplierTenderSuggestionRequest
) -> SupplierTenderSuggestionResponse:
    svc = _svc(db, user)
    await svc.ensure_base_categories()
    return await svc.suggest_for_tender(payload)


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    company_type: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
    brand: Annotated[str | None, Query()] = None,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SupplierListResponse:
    svc = _svc(db, user)
    await svc.ensure_base_categories()
    return await svc.list_suppliers(
        company_type=company_type,
        status=status,
        category_id=category_id,
        brand=brand,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: SupplierCreate
) -> SupplierResponse:
    return await _svc(db, user).create_supplier(payload)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    db: DbSession, user: CurrentUser, _: TenantCtx, supplier_id: uuid.UUID
) -> SupplierResponse:
    row = await _svc(db, user).get_supplier(supplier_id)
    if not row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return row


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
) -> SupplierResponse:
    row = await _svc(db, user).update_supplier(supplier_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return row


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(
    db: DbSession, user: CurrentUser, _: TenantCtx, supplier_id: uuid.UUID
) -> None:
    if not await _svc(db, user).delete_supplier(supplier_id):
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")


@router.post("/{supplier_id}/prefer", response_model=SupplierResponse)
async def mark_supplier_preferred(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    supplier_id: uuid.UUID,
    preferred: Annotated[bool, Query()] = True,
) -> SupplierResponse:
    row = await _svc(db, user).mark_preferred(supplier_id, preferred)
    if not row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return row


@router.post("/{supplier_id}/request-quote", response_model=SupplierQuoteResponse)
async def request_supplier_quote(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    supplier_id: uuid.UUID,
    payload: SupplierQuoteRequest,
) -> SupplierQuoteResponse:
    row = await _svc(db, user).request_quote(supplier_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return row


@router.get("/{supplier_id}/price-lists", response_model=list[SupplierPriceListSummary])
async def get_supplier_price_lists(
    db: DbSession, user: CurrentUser, _: TenantCtx, supplier_id: uuid.UUID
) -> list[SupplierPriceListSummary]:
    if not await _svc(db, user).get_supplier(supplier_id):
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return await _svc(db, user).list_price_lists(supplier_id)


@router.get("/{supplier_id}/interactions", response_model=list[SupplierInteractionResponse])
async def get_supplier_interactions(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    supplier_id: uuid.UUID,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[SupplierInteractionResponse]:
    if not await _svc(db, user).get_supplier(supplier_id):
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return await _svc(db, user).list_interactions(supplier_id, limit=limit)
