"""API — Document Intelligence Platform (Fase 7)."""

from __future__ import annotations

import uuid

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.content_disposition import build_content_disposition
from app.core.tenant import require_tenant_context
from app.schemas.document import (
    DocumentAlertResponse,
    DocumentCompletionPreview,
    DocumentExpedienteResponse,
    DocumentHealthResponse,
    DocumentListResponse,
    DocumentRelationshipResponse,
    DocumentResponse,
    DocumentScanResult,
    DocumentSearchResponse,
)
from app.services.document_completion_service import DocumentCompletionService
from app.services.document_expediente_service import DocumentExpedienteService
from app.services.document_service import DocumentService
from app.schemas.bulk_actions import BulkActionResult, DocumentBulkRequest
from app.schemas.tasks import TaskCreateRequest
from app.services.bulk_actions_service import BulkActionsService
from app.services.task_service import TaskService
from sqlalchemy import select

from app.models.document import DocumentAlert

router = APIRouter(prefix="/documents", tags=["Documentos"])


def _svc(db, user) -> DocumentService:
    ctx = require_tenant_context()
    return DocumentService(db, ctx.tenant_id, user.id)


def _bulk(db, user) -> BulkActionsService:
    ctx = require_tenant_context()
    return BulkActionsService(db, ctx.tenant_id, user.id)


@router.get("/health", response_model=DocumentHealthResponse)
async def documents_health(db: DbSession, user: CurrentUser, _: TenantCtx) -> DocumentHealthResponse:
    return await _svc(db, user).health()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    search: str = "",
    category: str | None = None,
    client: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> DocumentListResponse:
    return await _svc(db, user).list_documents(
        search=search, category=category, client=client, limit=limit, offset=offset
    )


@router.get("/search", response_model=DocumentSearchResponse)
async def search_documents(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: str,
    limit: int = 25,
) -> DocumentSearchResponse:
    return await _svc(db, user).search_content(q, limit=limit)


@router.post("", response_model=DocumentResponse)
async def register_document(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    category: str | None = Form(None),
    company: str | None = Form(None),
    client_name: str | None = Form(None),
    supplier_name: str | None = Form(None),
) -> DocumentResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    return await _svc(db, user).register_document(
        filename=file.filename or "documento.bin",
        content=content,
        title=title,
        category=category,
        company=company,
        client_name=client_name,
        supplier_name=supplier_name,
        mime_type=file.content_type,
    )


@router.get("/alerts", response_model=list[DocumentAlertResponse])
async def list_alerts(db: DbSession, user: CurrentUser, _: TenantCtx, limit: int = 30) -> list[DocumentAlertResponse]:
    ctx = require_tenant_context()
    result = await db.execute(
        select(DocumentAlert)
        .where(
            DocumentAlert.tenant_id == ctx.tenant_id,
            DocumentAlert.is_resolved.is_(False),
        )
        .order_by(DocumentAlert.created_at.desc())
        .limit(limit)
    )
    return [DocumentAlertResponse.model_validate(a) for a in result.scalars().all()]


@router.post("/scan", response_model=DocumentScanResult)
async def scan_folder(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    path: str = "",
) -> DocumentScanResult:
    return await _svc(db, user).scan_folder(path)


@router.get("/expedientes/{expediente_type}", response_model=DocumentExpedienteResponse)
async def get_expediente(
    expediente_type: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    subject: str = "",
) -> DocumentExpedienteResponse:
    ctx = require_tenant_context()
    return await DocumentExpedienteService(db, ctx.tenant_id).build(expediente_type, subject)


@router.get("/completion/{form_type}", response_model=DocumentCompletionPreview)
async def completion_preview(
    form_type: str,
    company: str = "justech",
) -> DocumentCompletionPreview:
    return DocumentCompletionService().preview(form_type=form_type, company_key=company)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DocumentResponse:
    doc = await _svc(db, user).get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return DocumentResponse.from_orm_doc(doc)


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    disposition: str = Query("inline", pattern="^(inline|attachment)$"),
):
    doc = await _svc(db, user).get_document(document_id)
    if not doc or not doc.storage_path:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    path = Path(doc.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no disponible en almacenamiento")
    media = doc.mime_type or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media,
        headers={
            "Content-Disposition": build_content_disposition(disposition, doc.filename),
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/{document_id}/analyze", response_model=DocumentResponse)
async def analyze_document(
    document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DocumentResponse:
    try:
        return await _svc(db, user).analyze_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{document_id}/relationships", response_model=list[DocumentRelationshipResponse])
async def document_relationships(
    document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> list[DocumentRelationshipResponse]:
    return await _svc(db, user).get_relationships(document_id)


@router.post("/{document_id}/tasks")
async def create_task_from_document(
    document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    title: str | None = None,
):
    ctx = require_tenant_context()
    doc = await _svc(db, user).get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    tasks = TaskService(db, ctx.tenant_id, user_id=user.id)
    task = await tasks.create_task(
        TaskCreateRequest(
            title=title or f"Revisar documento: {doc.title}",
            description=f"Documento: {doc.title} ({doc.category})",
            category="documento",
            department="legal",
            priority="media",
            related_document_id=str(doc.id),
        )
    )
    return {"task_id": str(task.id), "title": task.title}


@router.post("/bulk", response_model=BulkActionResult)
async def documents_bulk(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: DocumentBulkRequest
) -> BulkActionResult:
    return await _bulk(db, user).documents_bulk(payload.ids, payload.action)
