"""API — dashboards Licitador (legales, plantillas, precios)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import AdminViewer, CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.licitador import (
    DgcpTemplatesDashboardResponse,
    LegalDocumentsDashboardResponse,
    PriceIntelligenceDashboardResponse,
)
from app.schemas.supplier import SupplierTenderSuggestionRequest, SupplierTenderSuggestionResponse
from app.services.company_missing_info_email_service import CompanyMissingInfoEmailService
from app.services.licitador_dashboard_service import LicitadorDashboardService
from app.services.m365_template_service import M365TemplateService
from app.services.supplier_service import SupplierService

router = APIRouter(prefix="/licitador", tags=["Licitador"])


def _dash(db, user) -> LicitadorDashboardService:
    ctx = require_tenant_context()
    return LicitadorDashboardService(db, ctx.tenant_id, user_id=user.id)


@router.get("/documentos-legales", response_model=LegalDocumentsDashboardResponse)
async def legal_documents_dashboard(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> LegalDocumentsDashboardResponse:
    return await _dash(db, user).legal_documents()


@router.get("/plantillas", response_model=DgcpTemplatesDashboardResponse)
async def dgcp_templates_dashboard(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> DgcpTemplatesDashboardResponse:
    return await _dash(db, user).dgcp_templates()


@router.get("/precios", response_model=PriceIntelligenceDashboardResponse)
async def price_intelligence_dashboard(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> PriceIntelligenceDashboardResponse:
    return await _dash(db, user).price_intelligence()


@router.post("/proveedores-sugeridos", response_model=SupplierTenderSuggestionResponse)
async def suggest_suppliers_for_tender(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: SupplierTenderSuggestionRequest
) -> SupplierTenderSuggestionResponse:
    ctx = require_tenant_context()
    svc = SupplierService(db, ctx.tenant_id, user_id=user.id)
    await svc.ensure_base_categories()
    return await svc.suggest_for_tender(payload)


@router.post("/documentos-legales/{company_key}/solicitar-actualizacion")
async def request_legal_update_email(
    company_key: str, db: DbSession, user: AdminViewer, _: TenantCtx
) -> dict:
    ctx = require_tenant_context()
    extra = ["certificacion_dgii", "certificacion_tss", "certificacion_mipyme", "certificacion_proveedor_estado"]
    return await CompanyMissingInfoEmailService(db, ctx.tenant_id).draft_email(company_key, extra_missing=extra)


@router.post("/plantillas/preview")
async def preview_template(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    template_type: str = Query(...),
    company_key: str = Query("justech"),
):
    ctx = require_tenant_context()
    return await M365TemplateService(db, ctx.tenant_id).preview(
        template_type=template_type, company_key=company_key
    )
