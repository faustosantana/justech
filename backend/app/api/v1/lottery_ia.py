"""Lottery IA Dashboard + Motor v1.0 freeze + Discovery + Knowledge Engine."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.config import settings
from app.core.admin_permissions import role_has_permission
from app.core.exceptions import forbidden
from app.core.tenant import get_current_role
from app.lottery.ai.analyst.discovery_engine import DiscoveryRequest, get_discovery_engine
from app.lottery.ai.analyst.knowledge_engine import (
    KnowledgeSaveRequest,
    KnowledgeSearchQuery,
    get_knowledge_engine,
)
from app.lottery.numeric_relations.analysis_engine.ia_dashboard import build_ia_dashboard
from app.lottery.numeric_relations.analysis_engine.motor_v1_freeze import (
    motor_v1_freeze_manifest,
    persist_freeze_artifact,
)

router = APIRouter(prefix="/lottery/ia", tags=["lottery-ia"])


def require_lottery_permission(*permissions: str):
    async def _dep(user: CurrentUser, _: TenantCtx) -> None:
        if not settings.lottery_module_enabled:
            raise forbidden("Módulo Resultados de Loterías deshabilitado")
        role = get_current_role()
        if user.is_superadmin:
            return
        if not any(role_has_permission(role, p) for p in permissions):
            raise forbidden(f"Permiso requerido: {' o '.join(permissions)}")

    return Depends(_dep)


class DiscoveryRunBody(BaseModel):
    kind: str = "auto_discovery"
    context: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSaveBody(BaseModel):
    title: str | None = None
    original_question: str = ""
    executive_summary: str = ""
    full_investigation: str = ""
    evidences: list[dict[str, Any]] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    evidence_level: str | None = None
    confidence: str | None = None
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
    cited_ids: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)
    pairs: list[list[str]] = Field(default_factory=list)
    years: list[int] = Field(default_factory=list)
    period: str | None = None
    motor_version: str | None = None
    historical_version: str | None = None
    finished_ok: bool = True
    discarded: bool = False
    has_errors: bool = False


class KnowledgeSearchBody(BaseModel):
    number: str | None = None
    pair: list[str] | None = None
    group: str | None = None
    table1: str | None = None
    table2: str | None = None
    lottery: str | None = None
    position: str | None = None
    year: int | None = None
    period: str | None = None
    keyword: str | None = None
    tags: list[str] | None = None
    collection: str | None = None
    favorite_only: bool = False
    pinned_only: bool = False
    include_archived: bool = False
    include_obsolete: bool = True
    motor_version: str | None = None
    historical_version: str | None = None
    limit: int = 50


class KnowledgeFlagBody(BaseModel):
    favorite: bool | None = None
    pinned: bool | None = None
    archived: bool | None = None


class KnowledgeCollectionBody(BaseModel):
    name: str
    investigation_ids: list[str] | None = None


class KnowledgeCiteBody(BaseModel):
    cited_id: str


class KnowledgeHistoricalVersionBody(BaseModel):
    historical_version: str


@router.get("/dashboard")
async def lottery_ia_dashboard(
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> dict:
    return await build_ia_dashboard(db)


@router.get("/motor-freeze")
async def lottery_ia_motor_freeze(
    user: CurrentUser,
    _: Annotated[None, require_lottery_permission("lottery.access")],
) -> dict:
    """Read-only Motor v1.0 freeze. No PATCH/POST — UI cannot edit."""
    manifest = motor_v1_freeze_manifest()
    try:
        persist_freeze_artifact()
    except Exception:
        pass
    return manifest


@router.post("/discovery/run")
async def lottery_ia_discovery_run(
    body: DiscoveryRunBody,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    """Run observational Discovery Engine (read-only; never mutates motor/ranking)."""
    engine = get_discovery_engine()
    result = engine.discover(
        DiscoveryRequest(kind=body.kind, context=body.context, params=body.params)
    )
    return {
        "status": result.status,
        "enabled": result.enabled,
        "kind": result.kind,
        "version": getattr(engine, "VERSION", "2.2.0"),
        **(result.payload or {}),
    }


@router.get("/discovery/history")
async def lottery_ia_discovery_history(
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
    limit: int = 50,
    status: str | None = "published",
) -> dict:
    engine = get_discovery_engine()
    items = engine.list_history(limit=min(max(limit, 1), 200), status=status)
    return {"status": "ok", "count": len(items), "findings": items}


@router.get("/knowledge/status")
async def lottery_ia_knowledge_status(
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    return get_knowledge_engine().status()


@router.post("/knowledge/save")
async def lottery_ia_knowledge_save(
    body: KnowledgeSaveBody,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    """Persist a verified investigation (never conclusions-only)."""
    eng = get_knowledge_engine()
    return eng.save(
        KnowledgeSaveRequest(
            title=body.title,
            original_question=body.original_question,
            executive_summary=body.executive_summary,
            full_investigation=body.full_investigation,
            evidences=body.evidences,
            tools_used=body.tools_used,
            evidence_level=body.evidence_level,
            confidence=body.confidence,
            tags=body.tags,
            keywords=body.keywords,
            collections=body.collections,
            cited_ids=body.cited_ids,
            numbers=body.numbers,
            pairs=body.pairs,
            years=body.years,
            period=body.period,
            motor_version=body.motor_version,
            historical_version=body.historical_version,
            finished_ok=body.finished_ok,
            discarded=body.discarded,
            has_errors=body.has_errors,
        )
    )


@router.post("/knowledge/search")
async def lottery_ia_knowledge_search(
    body: KnowledgeSearchBody,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    eng = get_knowledge_engine()
    return eng.search(
        KnowledgeSearchQuery(
            number=body.number,
            pair=body.pair,
            group=body.group,
            table1=body.table1,
            table2=body.table2,
            lottery=body.lottery,
            position=body.position,
            year=body.year,
            period=body.period,
            keyword=body.keyword,
            tags=body.tags,
            collection=body.collection,
            favorite_only=body.favorite_only,
            pinned_only=body.pinned_only,
            include_archived=body.include_archived,
            include_obsolete=body.include_obsolete,
            motor_version=body.motor_version,
            historical_version=body.historical_version,
            limit=body.limit,
        )
    )


@router.get("/knowledge/collections/list")
async def lottery_ia_knowledge_collections(
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    cols = get_knowledge_engine().list_collections()
    return {"count": len(cols), "collections": cols}


@router.post("/knowledge/collections")
async def lottery_ia_knowledge_collection_upsert(
    body: KnowledgeCollectionBody,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    col = get_knowledge_engine().create_collection(body.name, body.investigation_ids)
    return {"ok": True, "collection": col}


@router.post("/knowledge/historical-version")
async def lottery_ia_knowledge_set_historical_version(
    body: KnowledgeHistoricalVersionBody,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    eng = get_knowledge_engine()
    eng.set_historical_version(body.historical_version)
    return {"ok": True, "status": eng.status()}


@router.get("/knowledge/{investigation_id}")
async def lottery_ia_knowledge_get(
    investigation_id: str,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    payload = get_knowledge_engine().get(investigation_id)
    if not payload:
        return {"found": False, "id": investigation_id}
    return {"found": True, **payload}


@router.post("/knowledge/{investigation_id}/flags")
async def lottery_ia_knowledge_flags(
    investigation_id: str,
    body: KnowledgeFlagBody,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    eng = get_knowledge_engine()
    out: dict[str, Any] | None = None
    if body.favorite is not None:
        out = eng.set_favorite(investigation_id, body.favorite)
    if body.pinned is not None:
        out = eng.set_pinned(investigation_id, body.pinned)
    if body.archived is not None:
        out = eng.set_archived(investigation_id, body.archived)
    if out is None:
        return {"found": False, "id": investigation_id}
    return {"found": True, "investigation": out}


@router.get("/knowledge/{investigation_id}/related")
async def lottery_ia_knowledge_related(
    investigation_id: str,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    return get_knowledge_engine().related_chain(investigation_id)


@router.post("/knowledge/{investigation_id}/cite")
async def lottery_ia_knowledge_cite(
    investigation_id: str,
    body: KnowledgeCiteBody,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    out = get_knowledge_engine().cite(investigation_id, body.cited_id)
    if not out:
        return {"ok": False, "id": investigation_id}
    return {"ok": True, "investigation": out}


@router.get("/knowledge/{investigation_id}/export/{fmt}")
async def lottery_ia_knowledge_export_plan(
    investigation_id: str,
    fmt: str,
    user: CurrentUser,
    _: Annotated[
        None,
        require_lottery_permission("lottery.access", "lottery.statistics", "lottery.chat"),
    ],
) -> dict:
    """Export architecture stub — generation not implemented yet."""
    return get_knowledge_engine().export_plan(investigation_id, fmt)
