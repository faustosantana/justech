"""API — Enterprise Knowledge Engine (Fase 4) + búsqueda global."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.search import (
    AssistantKnowledgeSearchRequest,
    AssistantKnowledgeSearchResponse,
    EnterpriseSearchResponse,
    KnowledgeEngineResponse,
    ResolvedEntitySchema,
    SearchAnalyticsResponse,
    SpeechSearchPlaceholder,
)
from app.services.knowledge_engine_service import KnowledgeEngineService
from app.services.search_analytics_service import SearchAnalyticsService

router = APIRouter(prefix="/search", tags=["Enterprise Search"])


def _engine(db, user) -> KnowledgeEngineService:
    ctx = require_tenant_context()
    return KnowledgeEngineService(db, ctx.tenant_id, user.id)


async def _global_search(
    db,
    user,
    q: str,
    *,
    source: str | None = None,
    type: str | None = None,
    company: str | None = None,
    limit: int = 8,
    channel: str = "api",
) -> KnowledgeEngineResponse:
    return await _engine(db, user).search_global(
        q,
        source_filter=source,
        type_filter=type,
        company_filter=company,
        limit_per_group=limit,
        channel=channel,
    )


@router.get("", response_model=KnowledgeEngineResponse)
async def enterprise_search(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query(min_length=0, description="Término o pregunta de búsqueda")],
    source: Annotated[str | None, Query(description="Filtrar por fuente: odoo, dgcp, jaios")] = None,
    type: Annotated[str | None, Query(description="Filtrar por tipo de grupo")] = None,
    company: Annotated[str | None, Query(description="Filtrar por empresa")] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> KnowledgeEngineResponse:
    return await _global_search(db, user, q, source=source, type=type, company=company, limit=limit)


@router.get("/global", response_model=KnowledgeEngineResponse)
async def global_search(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query(min_length=0)],
    source: Annotated[str | None, Query()] = None,
    type: Annotated[str | None, Query()] = None,
    company: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> KnowledgeEngineResponse:
    return await _global_search(db, user, q, source=source, type=type, company=company, limit=limit)


@router.get("/entities", response_model=list[ResolvedEntitySchema])
async def search_entities(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> list[ResolvedEntitySchema]:
    return await _engine(db, user).search_entities(q, limit=limit)


@router.get("/products", response_model=KnowledgeEngineResponse)
async def search_products(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query(min_length=2)],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> KnowledgeEngineResponse:
    return await _engine(db, user).search_by_type(q, "products", limit=limit)


@router.get("/customers", response_model=KnowledgeEngineResponse)
async def search_customers(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query(min_length=2)],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> KnowledgeEngineResponse:
    return await _engine(db, user).search_by_type(q, "customers", limit=limit)


@router.get("/documents", response_model=KnowledgeEngineResponse)
async def search_documents_knowledge(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query(min_length=2)],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> KnowledgeEngineResponse:
    return await _engine(db, user).search_by_type(q, "documents", limit=limit)


@router.get("/dgcp", response_model=KnowledgeEngineResponse)
async def search_dgcp_knowledge(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query(min_length=2)],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> KnowledgeEngineResponse:
    return await _engine(db, user).search_by_type(q, "dgcp", limit=limit)


@router.get("/providers", response_model=KnowledgeEngineResponse)
async def search_providers(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: Annotated[str, Query(min_length=2)],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> KnowledgeEngineResponse:
    return await _engine(db, user).search_by_type(q, "vendors", limit=limit)


@router.post("/assistant", response_model=AssistantKnowledgeSearchResponse)
async def search_assistant_knowledge(
    data: AssistantKnowledgeSearchRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> AssistantKnowledgeSearchResponse:
    engine = _engine(db, user)
    result = await engine.search_global(
        data.question,
        company_filter=data.company_filter,
        channel="assistant",
    )
    focus = result.resolved_entities[0] if result.resolved_entities else None
    summary_parts = []
    if focus:
        summary_parts.append(f"Entidad: **{focus.canonical_name}** ({focus.entity_type})")
    for gtype, label in (
        ("customers", "Clientes"),
        ("invoices", "Facturas"),
        ("quotations", "Cotizaciones"),
        ("dgcp", "Licitaciones"),
        ("documents", "Documentos"),
        ("tasks", "Tareas"),
    ):
        count = result.knowledge_graph.get("summary", {}).get(gtype, 0) if isinstance(result.knowledge_graph, dict) else 0
        if not count:
            for g in result.groups:
                if g.type == gtype:
                    count = g.count
                    break
        if count:
            summary_parts.append(f"{label}: {count}")
    answer = " · ".join(summary_parts) if summary_parts else f"{result.total} resultados para «{data.question}»"
    return AssistantKnowledgeSearchResponse(
        question=data.question,
        answer=answer,
        search=result,
        entity_focus=focus,
    )


@router.get("/speech", response_model=SpeechSearchPlaceholder)
async def speech_search_placeholder(
    _: CurrentUser,
    __: TenantCtx,
) -> SpeechSearchPlaceholder:
    return SpeechSearchPlaceholder()


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
