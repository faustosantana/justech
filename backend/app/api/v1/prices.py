"""API — Price Intelligence Engine v2."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.prices import (
    OdooProductMatchResponse,
    PriceCompareResponse,
    PriceProductDetailResponse,
    PriceQuoteDraftCreate,
    PriceQuoteDraftListResponse,
    PriceQuoteDraftResponse,
    PriceSearchResponse,
    PriceSyncResponse,
)
from app.services.price_intelligence_service import PriceIntelligenceService, PriceSearchFilters
from app.services.price_list_indexer import PriceListIndexer
from app.services.price_quote_draft_service import PriceQuoteDraftService
from app.schemas.bulk_actions import BulkActionResult, DraftBulkRequest
from app.services.bulk_actions_service import BulkActionsService

router = APIRouter(prefix="/prices", tags=["Inteligencia de Precios"])


def _svc(db) -> PriceIntelligenceService:
    ctx = require_tenant_context()
    return PriceIntelligenceService(db, ctx.tenant_id)


def _filters_from_query(
    *,
    q: str | None = None,
    marca: str | None = None,
    proveedor: str | None = None,
    fabricante: str | None = None,
    categoria: str | None = None,
    tipo_producto: str | None = None,
    ram_gb: int | None = None,
    almacenamiento_gb: int | None = None,
    procesador: str | None = None,
    pantalla: str | None = None,
    sistema_operativo: str | None = None,
    precio_min: Decimal | None = None,
    precio_max: Decimal | None = None,
    moneda: str | None = None,
    stock_min: int | None = None,
    stock_disponible: bool | None = None,
    solo_disponibles: bool | None = None,
    fecha_lista_desde: datetime | None = None,
    fecha_lista_hasta: datetime | None = None,
    limit: int = 50,
) -> PriceSearchFilters:
    return PriceSearchFilters(
        q=q,
        brand=marca,
        supplier=proveedor,
        manufacturer=fabricante,
        category=categoria,
        product_type=tipo_producto,
        ram_gb=ram_gb,
        storage_gb=almacenamiento_gb,
        processor=procesador,
        display=pantalla,
        operating_system=sistema_operativo,
        price_min=precio_min,
        price_max=precio_max,
        currency=moneda,
        stock_min=stock_min,
        stock_disponible=solo_disponibles if solo_disponibles is not None else stock_disponible,
        list_date_from=fecha_lista_desde,
        list_date_to=fecha_lista_hasta,
        limit=limit,
    )


@router.get("/search", response_model=PriceSearchResponse)
async def search_prices(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: str | None = None,
    marca: str | None = None,
    proveedor: str | None = None,
    fabricante: str | None = None,
    categoria: str | None = None,
    tipo_producto: str | None = None,
    ram_gb: int | None = None,
    almacenamiento_gb: int | None = None,
    procesador: str | None = None,
    pantalla: str | None = None,
    sistema_operativo: str | None = None,
    precio_min: Decimal | None = None,
    precio_max: Decimal | None = None,
    moneda: str | None = None,
    stock_min: int | None = None,
    stock_disponible: bool | None = None,
    solo_disponibles: bool | None = None,
    fecha_lista_desde: datetime | None = None,
    fecha_lista_hasta: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> PriceSearchResponse:
    filters = _filters_from_query(
        q=q, marca=marca, proveedor=proveedor, fabricante=fabricante, categoria=categoria,
        tipo_producto=tipo_producto, ram_gb=ram_gb, almacenamiento_gb=almacenamiento_gb,
        procesador=procesador, pantalla=pantalla, sistema_operativo=sistema_operativo,
        precio_min=precio_min, precio_max=precio_max, moneda=moneda, stock_min=stock_min,
        stock_disponible=stock_disponible, solo_disponibles=solo_disponibles,
        fecha_lista_desde=fecha_lista_desde, fecha_lista_hasta=fecha_lista_hasta, limit=limit,
    )
    return await _svc(db).search(filters)


@router.get("/products/{product_id}", response_model=PriceProductDetailResponse)
async def get_price_product(
    product_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> PriceProductDetailResponse:
    product = await _svc(db).get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@router.get("/compare", response_model=PriceCompareResponse)
async def compare_prices(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: str | None = None,
    marca: str | None = None,
    proveedor: str | None = None,
    fabricante: str | None = None,
    categoria: str | None = None,
    tipo_producto: str | None = None,
    ram_gb: int | None = None,
    almacenamiento_gb: int | None = None,
    procesador: str | None = None,
    precio_min: Decimal | None = None,
    precio_max: Decimal | None = None,
    moneda: str | None = None,
    solo_disponibles: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> PriceCompareResponse:
    filters = _filters_from_query(
        q=q, marca=marca, proveedor=proveedor, fabricante=fabricante, categoria=categoria,
        tipo_producto=tipo_producto, ram_gb=ram_gb, almacenamiento_gb=almacenamiento_gb,
        procesador=procesador, precio_min=precio_min, precio_max=precio_max, moneda=moneda,
        solo_disponibles=solo_disponibles, limit=limit,
    )
    question = q or f"Comparar {categoria or tipo_producto or 'productos'}"
    if ram_gb:
        question += f" {ram_gb}GB RAM"
    if almacenamiento_gb:
        question += f" {almacenamiento_gb}GB"
    return await _svc(db).compare(filters, question=question)


@router.post("/quote-drafts", response_model=PriceQuoteDraftResponse)
async def create_quote_draft(
    payload: PriceQuoteDraftCreate,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> PriceQuoteDraftResponse:
    ctx = require_tenant_context()
    try:
        return await PriceQuoteDraftService(db, ctx.tenant_id, user.id).create_draft(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/quote-drafts", response_model=PriceQuoteDraftListResponse)
async def list_quote_drafts(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> PriceQuoteDraftListResponse:
    ctx = require_tenant_context()
    return await PriceQuoteDraftService(db, ctx.tenant_id, user.id).list_drafts(limit=limit, offset=offset)


@router.get("/products/{product_id}/odoo-match", response_model=OdooProductMatchResponse)
async def odoo_match_product(
    product_id: UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> OdooProductMatchResponse:
    ctx = require_tenant_context()
    return await PriceQuoteDraftService(db, ctx.tenant_id, user.id).odoo_match(product_id)


@router.post("/quote-drafts/bulk", response_model=BulkActionResult)
async def quote_drafts_bulk(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    payload: DraftBulkRequest,
) -> BulkActionResult:
    ctx = require_tenant_context()
    return await BulkActionsService(db, ctx.tenant_id, user.id).drafts_bulk(
        payload.ids,
        payload.action,
        status=payload.status,
        assigned_user_id=payload.assigned_user_id,
    )


@router.post("/sync", response_model=PriceSyncResponse)
async def sync_price_lists(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> PriceSyncResponse:
    ctx = require_tenant_context()
    report = await PriceListIndexer(db, ctx.tenant_id).sync()
    return PriceSyncResponse(
        files_detected=report.files_detected,
        files_new=report.files_new,
        files_unchanged=report.files_unchanged,
        files_updated=report.files_updated,
        records_created=report.records_created,
        duration_ms=report.duration_ms,
        errors=report.errors,
    )
