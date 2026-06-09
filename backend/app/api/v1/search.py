"""API — Búsqueda empresarial global."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.search import EnterpriseSearchResponse, SearchAnalyticsResponse
from app.services.enterprise_search_service import EnterpriseSearchService
from app.services.search_analytics_service import SearchAnalyticsService

router = APIRouter(prefix="/search", tags=["Enterprise Search"])


@router.get("", response_model=EnterpriseSearchResponse)
async def enterprise_search(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query(min_length=0, description="Término de búsqueda")],
    source: Annotated[str | None, Query(description="Filtrar por fuente: odoo, dgcp, jaios")] = None,
    type: Annotated[str | None, Query(description="Filtrar por tipo de grupo")] = None,
    company: Annotated[str | None, Query(description="Filtrar por empresa")] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> EnterpriseSearchResponse:
    ctx = require_tenant_context()
    service = EnterpriseSearchService(db, ctx.tenant_id, user.id)
    return await service.search(
        q,
        source_filter=source,
        type_filter=type,
        company_filter=company,
        limit_per_group=limit,
        channel="api",
    )


@router.get("/analytics", response_model=SearchAnalyticsResponse)
async def search_analytics(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> SearchAnalyticsResponse:
    ctx = require_tenant_context()
    service = SearchAnalyticsService(db, ctx.tenant_id)
    return await service.get_analytics(days=days)
