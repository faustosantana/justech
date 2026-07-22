"""API — Document Intelligence Platform (Fase 7)."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import AdminMutator, AdminViewer, CurrentUser, DbSession, TenantCtx
from app.core.content_disposition import build_content_disposition
from app.core.tenant import require_tenant_context
from app.schemas.documents_hub import (
    CompanyCompletionResponse,
    CompanyDocumentProfileResponse,
    CompanyDocumentUploadResponse,
    CompanyFieldUpdateRequest,
    CompanyHubCard,
    CompanyMissingRequestPayload,
    CompanyProfileUpdateRequest,
    GeneralRepositoryCard,
    DocumentPendingItemResponse,
    DocumentsHubDashboardResponse,
    DocumentsTrackingSummary,
    MissingItemsResponse,
    ProfileFormResponse,
    RequestMissingPayload,
    RequestMissingResponse,
)
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
from app.schemas.settings import RepositoryBindingResponse, RepositorySyncResponse
from app.services.company_profile_field_service import CompanyProfileFieldService
from app.services.company_profile_form_service import CompanyProfileFormService
from app.services.corporate_identity_service import CorporateIdentityService
from app.services.document_completion_service import DocumentCompletionService
from app.services.document_pending_service import DocumentPendingService
from app.services.documents_hub_service import DocumentsHubService
from app.services.integration_repository_service import IntegrationRepositoryService
from app.services.licitador_dashboard_service import LicitadorDashboardService
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
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    company: str = "justech",
) -> DocumentCompletionPreview:
    ctx = require_tenant_context()
    return await DocumentCompletionService(db=db, tenant_id=ctx.tenant_id).preview(
        form_type=form_type, company_key=company
    )


# --- Hub Documentos y Repositorios (rutas estáticas antes de /{document_id}) ---


def _hub(db, user) -> DocumentsHubService:
    ctx = require_tenant_context()
    return DocumentsHubService(db, ctx.tenant_id, user_id=user.id)


def _pending(db, user) -> DocumentPendingService:
    ctx = require_tenant_context()
    return DocumentPendingService(db, ctx.tenant_id, user_id=user.id)


def _fields(db, user) -> CompanyProfileFieldService:
    ctx = require_tenant_context()
    return CompanyProfileFieldService(db, ctx.tenant_id, user_id=user.id)


@router.get("/dashboard", response_model=DocumentsHubDashboardResponse)
async def documents_hub_dashboard(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    scan_pending: bool = False,
) -> DocumentsHubDashboardResponse:
    try:
        return await _hub(db, user).dashboard(scan_pending=scan_pending)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No se pudo cargar el hub documental. Verifique la conexión M365 y los repositorios.",
        ) from exc


@router.get("/tracking", response_model=DocumentsTrackingSummary)
async def documents_tracking(db: DbSession, user: CurrentUser, _: TenantCtx) -> DocumentsTrackingSummary:
    return await _hub(db, user).tracking_summary()


@router.get("/repositories/general", response_model=list[GeneralRepositoryCard])
async def documents_general_repositories(db: DbSession, user: CurrentUser, _: TenantCtx) -> list:
    return await _hub(db, user).list_general_repositories()


@router.post("/sync/onedrive")
async def documents_sync_onedrive(db: DbSession, user: CurrentUser, _: TenantCtx) -> dict:
    try:
        return await _hub(db, user).sync_all_onedrive()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No se pudo sincronizar OneDrive. Verifique la conexión Microsoft 365.",
        ) from exc


@router.get("/companies", response_model=list[CompanyDocumentProfileResponse])
async def documents_list_companies(db: DbSession, user: CurrentUser, _: TenantCtx) -> list:
    return await _hub(db, user).list_companies()


@router.get("/companies/{company_id}", response_model=CompanyDocumentProfileResponse)
async def documents_get_company(
    company_id: uuid.UUID, db: DbSession, user: CurrentUser, _: TenantCtx
) -> CompanyDocumentProfileResponse:
    profile = await _hub(db, user).get_company(company_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return profile


@router.put("/companies/{company_id}/profile", response_model=CompanyDocumentProfileResponse)
@router.put("/companies/{company_id}", response_model=CompanyDocumentProfileResponse)
async def documents_update_company(
    company_id: uuid.UUID,
    payload: CompanyProfileUpdateRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> CompanyDocumentProfileResponse:
    try:
        return await _hub(db, user).update_company(company_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/companies/{company_id}/missing", response_model=MissingItemsResponse)
async def documents_company_missing(
    company_id: uuid.UUID, db: DbSession, user: CurrentUser, _: TenantCtx
) -> MissingItemsResponse:
    try:
        return await _pending(db, user).get_missing_for_company(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/companies/{company_id}/request-missing", response_model=RequestMissingResponse)
async def documents_request_missing(
    company_id: uuid.UUID,
    payload: RequestMissingPayload,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> RequestMissingResponse:
    try:
        return await _pending(db, user).request_missing(company_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/companies/{company_id}/profile-form", response_model=ProfileFormResponse)
async def documents_profile_form(
    company_id: uuid.UUID, db: DbSession, user: CurrentUser, _: TenantCtx
) -> ProfileFormResponse:
    ctx = require_tenant_context()
    try:
        return await CompanyProfileFormService(db, ctx.tenant_id, user_id=user.id).generate_form(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/companies/{company_id}/completion", response_model=CompanyCompletionResponse)
async def documents_company_completion(
    company_id: uuid.UUID, db: DbSession, user: CurrentUser, _: TenantCtx
) -> CompanyCompletionResponse:
    try:
        return await _fields(db, user).get_completion(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/companies/{company_id}/fields/{field_key}", response_model=CompanyDocumentProfileResponse)
async def documents_company_update_field(
    company_id: uuid.UUID,
    field_key: str,
    payload: CompanyFieldUpdateRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> CompanyDocumentProfileResponse:
    try:
        return await _fields(db, user).update_field(company_id, field_key, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/missing/request", response_model=RequestMissingResponse)
async def documents_company_missing_request(
    company_id: uuid.UUID,
    payload: CompanyMissingRequestPayload,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> RequestMissingResponse:
    try:
        return await _fields(db, user).request_missing_fields(company_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/companies/{company_id}/sync")
@router.post("/companies/{company_id}/onedrive/sync")
async def documents_company_onedrive_sync(
    company_id: uuid.UUID, db: DbSession, user: CurrentUser, _: TenantCtx
) -> dict:
    try:
        return await _fields(db, user).sync_onedrive(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def _company_document_upload(
    company_id: uuid.UUID,
    field_key: str,
    file: UploadFile,
    db: DbSession,
    user: CurrentUser,
    valid_until: str | None = None,
) -> CompanyDocumentUploadResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    expiry: date | None = None
    if valid_until:
        try:
            expiry = date.fromisoformat(valid_until)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Fecha de vencimiento inválida") from exc
    try:
        return await _fields(db, user).upload_document(
            company_id,
            field_key,
            filename=file.filename or f"{field_key}.pdf",
            content=content,
            content_type=file.content_type or "application/octet-stream",
            valid_until=expiry,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/upload", response_model=CompanyDocumentUploadResponse)
@router.post("/companies/{company_id}/documents/upload", response_model=CompanyDocumentUploadResponse)
async def documents_company_upload_document(
    company_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    field_key: str = Form(...),
    file: UploadFile = File(...),
    valid_until: str | None = Form(None),
) -> CompanyDocumentUploadResponse:
    return await _company_document_upload(company_id, field_key, file, db, user, valid_until)


@router.post("/companies/{company_id}/onedrive/upload", response_model=CompanyDocumentUploadResponse)
async def documents_company_onedrive_upload(
    company_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    field_key: str = Form(...),
    file: UploadFile = File(...),
    valid_until: str | None = Form(None),
) -> CompanyDocumentUploadResponse:
    return await _company_document_upload(company_id, field_key, file, db, user, valid_until)


@router.post("/public/profile-form/{token}")
async def documents_public_profile_submit(token: str, payload: CompanyProfileUpdateRequest, db: DbSession) -> dict:
    from sqlalchemy import select

    from app.models.document_pending import CompanyProfileFormToken

    token_row = (
        await db.execute(select(CompanyProfileFormToken).where(CompanyProfileFormToken.token == token))
    ).scalar_one_or_none()
    if not token_row:
        raise HTTPException(status_code=400, detail="Enlace inválido o expirado")
    try:
        return await CompanyProfileFormService(db, token_row.tenant_id).submit_form(token, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/repositories", response_model=list[RepositoryBindingResponse])
async def documents_list_repositories(db: DbSession, user: CurrentUser, _: TenantCtx) -> list:
    ctx = require_tenant_context()
    svc = IntegrationRepositoryService(db, ctx.tenant_id, actor_id=user.id)
    return await svc.list_bindings()


@router.post("/repositories/{binding_id}/sync", response_model=RepositorySyncResponse)
async def documents_sync_repository(
    binding_id: uuid.UUID, db: DbSession, user: CurrentUser, _: TenantCtx
) -> RepositorySyncResponse:
    ctx = require_tenant_context()
    svc = IntegrationRepositoryService(db, ctx.tenant_id, actor_id=user.id)
    try:
        data = await svc.sync_binding(binding_id)
        return RepositorySyncResponse(**data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/legal")
async def documents_legal_dashboard(db: DbSession, user: CurrentUser, _: TenantCtx) -> dict:
    ctx = require_tenant_context()
    result = await LicitadorDashboardService(db, ctx.tenant_id, user_id=user.id).legal_documents()
    return result.model_dump()


@router.get("/templates/dgcp")
async def documents_dgcp_templates(db: DbSession, user: CurrentUser, _: TenantCtx) -> dict:
    ctx = require_tenant_context()
    result = await LicitadorDashboardService(db, ctx.tenant_id, user_id=user.id).dgcp_templates()
    return result.model_dump()


@router.get("/prices/intelligence")
async def documents_price_intelligence(db: DbSession, user: CurrentUser, _: TenantCtx) -> dict:
    ctx = require_tenant_context()
    result = await LicitadorDashboardService(db, ctx.tenant_id, user_id=user.id).price_intelligence()
    return result.model_dump()


@router.get("/corporate-identity/{company_key}")
async def documents_corporate_identity(
    company_key: str, db: DbSession, user: CurrentUser, _: TenantCtx
) -> dict:
    try:
        overview = await CorporateIdentityService(
            db, require_tenant_context().tenant_id, user_id=user.id
        ).get_company_assets(company_key)
        return overview.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pending", response_model=list[DocumentPendingItemResponse])
async def documents_pending_list(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    status: str | None = None,
    company_key: str | None = None,
) -> list:
    return await _pending(db, user).list_pending(status=status, company_key=company_key)


@router.post("/pending/{pending_id}/received", response_model=DocumentPendingItemResponse)
async def documents_pending_received(
    pending_id: uuid.UUID, db: DbSession, user: CurrentUser, _: TenantCtx
) -> DocumentPendingItemResponse:
    try:
        return await _pending(db, user).mark_received(pending_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/pending/scan")
async def documents_pending_scan(db: DbSession, user: CurrentUser, _: TenantCtx) -> dict:
    count = await _pending(db, user).scan_and_upsert()
    return {"created": count}


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
