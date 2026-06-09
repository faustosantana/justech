"""API — Corporate Knowledge Repository (Fase 7.2)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.api.deps import CurrentUser, DbSession, TenantCtx, require_tenant_context
from app.core.content_disposition import build_content_disposition
from app.schemas.knowledge import (
    KnowledgeAssetListResponse,
    KnowledgeGraphResponse,
    KnowledgeHealthResponse,
    KnowledgeSearchResponse,
    KnowledgeSyncResult,
    KnowledgeVigencyResponse,
)
from app.schemas.tasks import TaskCreateRequest
from app.services.corporate_knowledge_engine import CorporateKnowledgeEngine
from app.services.knowledge_source_provider import get_knowledge_source_provider
from app.services.task_service import TaskService
from app.models.knowledge import KnowledgeAsset
from sqlalchemy import select

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _engine(db, user) -> CorporateKnowledgeEngine:
    ctx = require_tenant_context()
    return CorporateKnowledgeEngine(db, ctx.tenant_id)


@router.get("/health", response_model=KnowledgeHealthResponse)
async def knowledge_health(db: DbSession, user: CurrentUser, _: TenantCtx) -> KnowledgeHealthResponse:
    return await _engine(db, user).health()


@router.post("/sync", response_model=KnowledgeSyncResult)
async def knowledge_sync(db: DbSession, user: CurrentUser, _: TenantCtx) -> KnowledgeSyncResult:
    return await _engine(db, user).sync()


@router.get("/assets", response_model=KnowledgeAssetListResponse)
async def list_knowledge_assets(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    document_type: str | None = None,
    company_key: str | None = None,
    repository_category: str | None = None,
    search: str = Query("", max_length=200),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> KnowledgeAssetListResponse:
    return await _engine(db, user).list_assets(
        document_type=document_type,
        company_key=company_key,
        repository_category=repository_category,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=100),
) -> KnowledgeSearchResponse:
    return await _engine(db, user).search(q, limit=limit)


@router.get("/graph", response_model=KnowledgeGraphResponse)
async def knowledge_graph(db: DbSession, user: CurrentUser, _: TenantCtx) -> KnowledgeGraphResponse:
    return await _engine(db, user).get_graph()


@router.get("/vigencies", response_model=KnowledgeVigencyResponse)
async def knowledge_vigencies(db: DbSession, user: CurrentUser, _: TenantCtx) -> KnowledgeVigencyResponse:
    return await _engine(db, user).vigencies()


@router.post("/assets/{asset_id}/task")
async def create_task_from_knowledge_asset(
    asset_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    engine = _engine(db, user)
    assets = await engine.list_assets(limit=500)
    asset = next((a for a in assets.items if a.id == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Activo de conocimiento no encontrado")

    ctx = require_tenant_context()
    tasks = TaskService(db, ctx.tenant_id, user_id=user.id)
    title = f"Conocimiento: {asset.document_type.upper()} — {asset.title[:80]}"
    action = "Renovar documento" if asset.vigency_status == "vencido" else "Revisar documento corporativo"
    task = await tasks.create_task(
        TaskCreateRequest(
            title=title,
            description=f"{action}: {asset.relative_path}",
            category="documento",
            department="legal",
            priority="alta" if asset.vigency_status in ("vencido", "proximo_a_vencer") else "media",
        )
    )
    return {"task_id": str(task.id), "title": task.title}


@router.get("/assets/{asset_id}/file")
async def download_knowledge_asset_file(
    asset_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    disposition: str = Query("inline", pattern="^(inline|attachment)$"),
):
    ctx = require_tenant_context()
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.tenant_id == ctx.tenant_id,
            KnowledgeAsset.is_active.is_(True),
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    source = get_knowledge_source_provider()
    if not source.is_available() or not asset.relative_path:
        raise HTTPException(status_code=404, detail="Archivo no disponible")
    try:
        content = source.read_bytes(asset.relative_path)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="No se pudo leer el archivo") from exc
    media = asset.mime_type or "application/octet-stream"
    return Response(
        content=content,
        media_type=media,
        headers={
            "Content-Disposition": build_content_disposition(disposition, asset.filename),
            "Cache-Control": "private, no-store",
        },
    )
