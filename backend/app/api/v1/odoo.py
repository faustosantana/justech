from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.odoo import (
    OdooCompaniesResponse,
    OdooCompanyContextResponse,
    OdooCompanyContextUpdate,
    OdooCustomerDetailResponse,
    OdooHealthResponse,
    OdooInvoiceDetailResponse,
    OdooLastPriceResponse,
    OdooLinkUserRequest,
    OdooListResponse,
    OdooMeResponse,
    OdooProductDetailResponse,
    OdooQueryResponse,
    OdooQuotationDetailResponse,
    OdooQuotationSearchParams,
    OdooSummaryResponse,
    OdooUserMappingResponse,
    OdooVendorDetailResponse,
)
from app.services.odoo_detail_service import OdooDetailService
from app.services.odoo_query_service import OdooQueryService
from app.services.odoo_quotation_service import OdooQuotationService
from app.services.odoo_service import OdooService
from integrations.odoo.exceptions import OdooConnectionError, OdooNotConfiguredError

router = APIRouter(prefix="/odoo", tags=["Odoo Intelligence"])


def _service(db: DbSession, user: CurrentUser) -> OdooService:
    ctx = require_tenant_context()
    return OdooService(db, ctx.tenant_id, user_id=user.id)


@router.get("/health", response_model=OdooHealthResponse)
async def odoo_health(db: DbSession, user: CurrentUser, _: TenantCtx) -> OdooHealthResponse:
    return await _service(db, user).health()


@router.get("/summary", response_model=OdooSummaryResponse)
async def odoo_summary(db: DbSession, user: CurrentUser, _: TenantCtx) -> OdooSummaryResponse:
    return await _service(db, user).summary()


@router.get("/companies", response_model=OdooCompaniesResponse)
async def odoo_companies(db: DbSession, user: CurrentUser, _: TenantCtx) -> OdooCompaniesResponse:
    svc = _service(db, user)
    return await svc.company_context_service().list_companies()


@router.get("/company-context", response_model=OdooCompanyContextResponse)
async def get_odoo_company_context(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> OdooCompanyContextResponse:
    svc = _service(db, user)
    return await svc.company_context_service().get_context_response()


@router.put("/company-context", response_model=OdooCompanyContextResponse)
async def set_odoo_company_context(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    payload: OdooCompanyContextUpdate,
) -> OdooCompanyContextResponse:
    svc = _service(db, user)
    return await svc.company_context_service().set_context(payload)


@router.get("/me", response_model=OdooMeResponse)
async def odoo_me(db: DbSession, user: CurrentUser, _: TenantCtx) -> OdooMeResponse:
    svc = _service(db, user)
    return await svc.company_context_service().get_me(
        jaios_email=user.email,
        jaios_name=user.full_name,
    )


@router.post("/link-user", response_model=OdooUserMappingResponse)
async def odoo_link_user(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    payload: OdooLinkUserRequest,
) -> OdooUserMappingResponse:
    svc = _service(db, user)
    return await svc.company_context_service().link_user(payload)


@router.delete("/link-user", status_code=204)
async def odoo_unlink_user(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> None:
    svc = _service(db, user)
    await svc.company_context_service().unlink_user()


@router.get("/users/mapping", response_model=list[OdooUserMappingResponse])
async def odoo_user_mappings(
    db: DbSession, user: CurrentUser, _: TenantCtx
) -> list[OdooUserMappingResponse]:
    svc = _service(db, user)
    return await svc.company_context_service().list_mappings()


@router.get("/customers", response_model=OdooListResponse)
async def odoo_customers(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).list_customers(search=search, limit=limit)


@router.get("/customers/{partner_id}", response_model=OdooCustomerDetailResponse)
async def odoo_customer_detail(
    partner_id: int,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> OdooCustomerDetailResponse:
    svc = _service(db, user)
    return await OdooDetailService(svc).get_customer_detail(partner_id)


@router.get("/products", response_model=OdooListResponse)
async def odoo_products(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).list_products(search=search, limit=limit)


@router.get("/products/{product_id}", response_model=OdooProductDetailResponse)
async def odoo_product_detail(
    product_id: int,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> OdooProductDetailResponse:
    svc = _service(db, user)
    return await OdooDetailService(svc).get_product_detail(product_id)


@router.get("/sales/history", response_model=OdooListResponse)
async def odoo_sales_history(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    partner_id: Annotated[int | None, Query()] = None,
    product_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).sales_history(
        partner_id=partner_id, product_id=product_id, limit=limit
    )


@router.get("/sales/last-price", response_model=OdooLastPriceResponse)
async def odoo_last_price(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    partner_id: Annotated[int | None, Query()] = None,
    product_id: Annotated[int | None, Query()] = None,
    partner_name: Annotated[str | None, Query()] = None,
    product_name: Annotated[str | None, Query()] = None,
) -> OdooLastPriceResponse:
    return await _service(db, user).last_price(
        partner_id=partner_id,
        product_id=product_id,
        partner_name=partner_name,
        product_name=product_name,
    )


@router.get("/invoices/open", response_model=OdooListResponse)
async def odoo_open_invoices(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    partner_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).open_invoices(partner_id=partner_id, limit=limit)


@router.get("/invoices/overdue", response_model=OdooListResponse)
async def odoo_overdue_invoices(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    partner_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).overdue_invoices(partner_id=partner_id, limit=limit)


@router.get("/invoices/{invoice_id}", response_model=OdooInvoiceDetailResponse)
async def odoo_invoice_detail(
    invoice_id: int,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> OdooInvoiceDetailResponse:
    svc = _service(db, user)
    return await OdooDetailService(svc).get_invoice_detail(invoice_id)


@router.get("/quotations/search", response_model=OdooListResponse)
async def odoo_quotations_search(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str | None, Query()] = None,
    quotation_number: Annotated[str | None, Query()] = None,
    customer: Annotated[str | None, Query()] = None,
    salesperson: Annotated[str | None, Query()] = None,
    product: Annotated[str | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    amount_min: Annotated[Decimal | None, Query()] = None,
    amount_max: Annotated[Decimal | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    company_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    svc = _service(db, user)
    params = OdooQuotationSearchParams(
        q=q,
        quotation_number=quotation_number,
        customer=customer,
        salesperson=salesperson,
        product=product,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        state=state,
        company_id=company_id,
        limit=limit,
    )
    result = await OdooQuotationService(svc).search(params)
    query_label = q or quotation_number or customer or salesperson or product or ""
    if query_label:
        from app.services.audit_service import AuditService

        ctx = require_tenant_context()
        await AuditService(db).log(
            action="odoo.quotation.search",
            tenant_id=ctx.tenant_id,
            user_id=user.id,
            resource_type="odoo_quotation",
            details={"query": query_label, "result_count": result.total},
        )
        await db.commit()
    return result


@router.get("/quotations/{quotation_id}", response_model=OdooQuotationDetailResponse)
async def odoo_quotation_detail(
    quotation_id: int,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> OdooQuotationDetailResponse:
    svc = _service(db, user)
    try:
        return await OdooQuotationService(svc).get_detail(quotation_id)
    except OdooConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except OdooNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/quotations/{quotation_id}/pdf")
async def odoo_quotation_pdf(
    quotation_id: int,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> Response:
    svc = _service(db, user)
    try:
        pdf_bytes, filename = await OdooQuotationService(svc).download_pdf(quotation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OdooConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except OdooNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/quotations", response_model=OdooListResponse)
async def odoo_quotations(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    partner_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).list_quotations(partner_id=partner_id, limit=limit)


@router.get("/opportunities", response_model=OdooListResponse)
async def odoo_opportunities(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    partner_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).list_opportunities(partner_id=partner_id, limit=limit)


@router.get("/projects", response_model=OdooListResponse)
async def odoo_projects(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    partner_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).list_projects(partner_id=partner_id, limit=limit)


@router.get("/purchases/history", response_model=OdooListResponse)
async def odoo_purchase_history(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    partner_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).purchase_history(partner_id=partner_id, limit=limit)


@router.get("/tickets", response_model=OdooListResponse)
async def odoo_tickets(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    partner_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).list_tickets(partner_id=partner_id, limit=limit)


@router.get("/query", response_model=OdooQueryResponse)
async def odoo_intelligent_query(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query(min_length=1)],
) -> OdooQueryResponse:
    ctx = require_tenant_context()
    return await OdooQueryService(db, ctx.tenant_id, user_id=user.id).answer(q)


@router.get("/vendors", response_model=OdooListResponse)
async def odoo_vendors(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> OdooListResponse:
    return await _service(db, user).list_vendors(search=search, limit=limit)


@router.get("/vendors/{vendor_id}", response_model=OdooVendorDetailResponse)
async def odoo_vendor_detail(
    vendor_id: int,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> OdooVendorDetailResponse:
    svc = _service(db, user)
    return await OdooDetailService(svc).get_vendor_detail(vendor_id)
