import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.content_disposition import build_content_disposition
from app.core.tenant import require_tenant_context
from app.schemas.dgcp import (
    DGCPOpportunityActionRequest,
    DGCPOpportunityListResponse,
    DGCPOpportunityResponse,
    DGCPOpportunitySummary,
    DGCPOpportunityUpdate,
    DGCPAuditLogResponse,
    DGCPOpportunityHistoryResponse,
    DGCPSyncJobResponse,
    DGCPSyncRequest,
    DGCPSyncScheduleResponse,
    DGCPSyncScheduleUpdate,
    OpportunityCompany,
    OpportunityPriority,
    OpportunityStatus,
    OpportunityAction,
)
from app.services.audit_service import AuditService


def _http_error_for_dgcp_value_error(exc: ValueError) -> HTTPException:
    msg = str(exc)
    if any(
        phrase in msg
        for phrase in (
            "Mostrar interés",
            "Licitar",
            "Ejecute el análisis",
            "Usuario requerido",
            "no puede estar vacía",
            "No puede validar",
            "Estado no permitido",
            "Ítem de checklist",
            "Indique document_id",
            "Documento corporativo",
            "Documento contaminado",
            "Documento no encontrado",
        )
    ):
        return HTTPException(status_code=400, detail=msg)
    return HTTPException(status_code=404, detail=msg)
from app.schemas.dgcp_bid import (
    DGCPAnalyzeResponse,
    DGCPAssociateDocumentRequest,
    DGCPAssociateDocumentResponse,
    DGCPBidAlertResponse,
    DGCPBidPackageResponse,
    DGCPBidPackageStatusResponse,
    DGCPChecklistResponse,
    DGCPDocumentMatchesResponse,
    DGCPExpedientePrepareResponse,
    DGCPFormAutofillPreviewResponse,
    DGCPFormGenerateResponse,
    DGCPFormPreviewRequest,
    DGCPFormPreviewResponse,
    DGCPManualValidationRequest,
    DGCPManualValidationResponse,
    DGCPChecklistNoteRequest,
    DGCPChecklistNoteResponse,
    DGCPDocumentPreviewResponse,
    DGCPProcessDocumentsResponse,
    DGCPRequirementsResponse,
    DGCPUserInputRequest,
)
from app.schemas.dgcp_economic_offer import (
    CreateEconomicOfferDraftTaskRequest,
    CreateEconomicOfferTaskResponse,
    EconomicOfferStatusResponse,
)
from app.schemas.real_expediente import (
    RealExpedienteGenerateResponse,
    RealExpedienteStatusResponse,
    RealExpedienteValidationResponse,
)
from app.schemas.document_finalization import (
    DocumentFinalizationBatchResponse,
    DocumentFinalizationGenerateRequest,
    DocumentFinalizationGenerateResponse,
    DocumentFinalizationPreviewRequest,
    DocumentFinalizationPreviewResponse,
    DocumentFinalizationRecordResponse,
)
from app.services.dgcp_bid_package_service import DGCPBidPackageService
from app.services.dgcp_economic_offer_service import DGCPEconomicOfferService
from app.services.real_dgcp_expediente_builder import RealDGCPExpedienteBuilder
from app.services.document_finalization_engine import DocumentFinalizationEngine
from app.services.dgcp_service import DGCPService
from app.services.dgcp_sync_service import DGCPSyncService

router = APIRouter(prefix="/dgcp", tags=["DGCP Intelligence"])


@router.get("/dashboard", response_model=DGCPOpportunitySummary)
async def get_dashboard(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    include_expired: Annotated[bool, Query()] = False,
) -> DGCPOpportunitySummary:
    ctx = require_tenant_context()
    service = DGCPService(db)
    return await service.compute_dashboard(
        ctx.tenant_id,
        user_id=user.id,
        include_expired=include_expired,
    )


@router.get("/opportunities", response_model=DGCPOpportunityListResponse)
async def list_opportunities(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    status: Annotated[OpportunityStatus | None, Query()] = None,
    company: Annotated[OpportunityCompany | None, Query()] = None,
    priority: Annotated[OpportunityPriority | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    include_expired: Annotated[bool, Query()] = False,
) -> DGCPOpportunityListResponse:
    ctx = require_tenant_context()
    service = DGCPService(db)
    return await service.list_opportunities(
        ctx.tenant_id,
        user_id=user.id,
        status=status,
        company=company,
        priority=priority,
        skip=skip,
        limit=limit,
        include_expired=include_expired,
    )


@router.get("/opportunities/{opportunity_id}", response_model=DGCPOpportunityResponse)
async def get_opportunity(
    opportunity_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
) -> DGCPOpportunityResponse:
    ctx = require_tenant_context()
    service = DGCPService(db)
    opportunity = await service.get_opportunity(ctx.tenant_id, opportunity_id)
    return DGCPOpportunityResponse.model_validate(opportunity)


@router.patch("/opportunities/{opportunity_id}", response_model=DGCPOpportunityResponse)
async def update_opportunity(
    opportunity_id: uuid.UUID,
    data: DGCPOpportunityUpdate,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    __: TenantCtx,
) -> DGCPOpportunityResponse:
    ctx = require_tenant_context()
    service = DGCPService(db)
    opportunity = await service.update_opportunity(
        ctx.tenant_id,
        opportunity_id,
        data,
        user_id=user.id,
        request=request,
    )
    return DGCPOpportunityResponse.model_validate(opportunity)


@router.post("/opportunities/{opportunity_id}/actions", response_model=DGCPOpportunityResponse)
async def apply_opportunity_action(
    opportunity_id: uuid.UUID,
    data: DGCPOpportunityActionRequest,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    __: TenantCtx,
) -> DGCPOpportunityResponse:
    ctx = require_tenant_context()
    service = DGCPService(db)
    opportunity = await service.apply_action(
        ctx.tenant_id,
        opportunity_id,
        data,
        user_id=user.id,
        request=request,
    )
    if data.action == OpportunityAction.LICITAR:
        try:
            await _bid_svc(db, user).activate_expediente_tracking(opportunity_id)
        except ValueError:
            pass
    return DGCPOpportunityResponse.model_validate(opportunity)


def _bid_svc(db, user) -> DGCPBidPackageService:
    ctx = require_tenant_context()
    return DGCPBidPackageService(db, ctx.tenant_id, user_id=user.id)


def _economic_offer_svc(db, user) -> DGCPEconomicOfferService:
    ctx = require_tenant_context()
    return DGCPEconomicOfferService(db, ctx.tenant_id, user_id=user.id)


def _finalization_engine(db, user) -> DocumentFinalizationEngine:
    ctx = require_tenant_context()
    return DocumentFinalizationEngine(db, ctx.tenant_id, user_id=user.id)


def _real_expediente_builder(db, user) -> RealDGCPExpedienteBuilder:
    ctx = require_tenant_context()
    return RealDGCPExpedienteBuilder(db, ctx.tenant_id, user_id=user.id)


@router.get("/opportunities/{opportunity_id}/requirements", response_model=DGCPRequirementsResponse)
async def get_opportunity_requirements(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPRequirementsResponse:
    try:
        return await _bid_svc(db, user).get_requirements(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/requirements/analyze", response_model=DGCPAnalyzeResponse)
async def analyze_opportunity_requirements(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPAnalyzeResponse:
    try:
        return await _bid_svc(db, user).analyze(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get("/opportunities/{opportunity_id}/checklist", response_model=DGCPChecklistResponse)
async def get_opportunity_checklist(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPChecklistResponse:
    try:
        return await _bid_svc(db, user).get_checklist(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/checklist/{item_id}/task")
async def create_checklist_task(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    assignee: str | None = None,
    due_date: date | None = None,
    force_new: bool = False,
):
    try:
        return await _bid_svc(db, user).create_checklist_task(
            opportunity_id,
            item_id,
            assignee_name=assignee,
            due_date=due_date,
            force_new=force_new,
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/checklist/{item_id}/manual-validation",
    response_model=DGCPManualValidationResponse,
)
async def manual_requirement_validation(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    data: DGCPManualValidationRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPManualValidationResponse:
    try:
        return await _bid_svc(db, user).apply_manual_validation(opportunity_id, item_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/requirements/{requirement_id}/manual-validation",
    response_model=DGCPManualValidationResponse,
)
async def manual_requirement_validation_by_key(
    opportunity_id: uuid.UUID,
    requirement_id: str,
    data: DGCPManualValidationRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPManualValidationResponse:
    try:
        checklist = await _bid_svc(db, user).get_checklist(opportunity_id)
        item = next((i for i in checklist.items if i.requirement_key == requirement_id), None)
        if not item:
            raise ValueError("Requisito no encontrado en checklist")
        return await _bid_svc(db, user).apply_manual_validation(opportunity_id, item.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/checklist/{item_id}/notes",
    response_model=DGCPChecklistNoteResponse,
)
async def add_checklist_note(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    data: DGCPChecklistNoteRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPChecklistNoteResponse:
    try:
        result = await _bid_svc(db, user).add_checklist_note(opportunity_id, item_id, data.note)
        return DGCPChecklistNoteResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/checklist/{item_id}/associate-document",
    response_model=DGCPAssociateDocumentResponse,
)
async def associate_checklist_document(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    data: DGCPAssociateDocumentRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPAssociateDocumentResponse:
    try:
        return await _bid_svc(db, user).associate_checklist_document(opportunity_id, item_id, data)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/checklist/{item_id}/upload-document",
    response_model=DGCPAssociateDocumentResponse,
)
async def upload_checklist_document(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    file: UploadFile = File(...),
) -> DGCPAssociateDocumentResponse:
    try:
        content = await file.read()
        return await _bid_svc(db, user).upload_checklist_document(
            opportunity_id,
            item_id,
            filename=file.filename or "documento.pdf",
            content=content,
            mime_type=file.content_type,
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/checklist/{item_id}/document-preview",
    response_model=DGCPDocumentPreviewResponse,
)
async def checklist_document_preview(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPDocumentPreviewResponse:
    try:
        return await _bid_svc(db, user).get_document_preview(opportunity_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/{opportunity_id}/bid-package", response_model=DGCPBidPackageResponse)
async def get_opportunity_bid_package(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPBidPackageResponse:
    try:
        return await _bid_svc(db, user).get_bid_package(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/{opportunity_id}/document-matches", response_model=DGCPDocumentMatchesResponse)
async def get_opportunity_document_matches(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPDocumentMatchesResponse:
    try:
        return await _bid_svc(db, user).get_document_matches(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/forms/preview", response_model=DGCPFormPreviewResponse)
async def preview_opportunity_form(
    opportunity_id: uuid.UUID,
    data: DGCPFormPreviewRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPFormPreviewResponse:
    try:
        return await _bid_svc(db, user).form_preview(
            opportunity_id, form_type=data.form_type, company=data.company
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/{opportunity_id}/process-documents", response_model=DGCPProcessDocumentsResponse)
async def get_process_documents(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPProcessDocumentsResponse:
    try:
        return await _bid_svc(db, user).get_process_documents(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/{opportunity_id}/process-documents/{process_document_id}/file")
async def download_process_document_file(
    opportunity_id: uuid.UUID,
    process_document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    disposition: str = Query("inline", pattern="^(inline|attachment)$"),
):
    try:
        content, mime, filename = await _bid_svc(db, user).download_process_document_file(
            opportunity_id,
            process_document_id,
            disposition=disposition,
        )
        return Response(
            content=content,
            media_type=mime,
            headers={
                "Content-Disposition": build_content_disposition(disposition, filename),
                "Cache-Control": "private, no-store",
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/{opportunity_id}/alerts", response_model=DGCPBidAlertResponse)
async def get_opportunity_alerts(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPBidAlertResponse:
    try:
        return await _bid_svc(db, user).get_alerts(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/forms/autofill-preview", response_model=DGCPFormAutofillPreviewResponse)
async def autofill_preview_form(
    opportunity_id: uuid.UUID,
    data: DGCPFormPreviewRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPFormAutofillPreviewResponse:
    try:
        return await _bid_svc(db, user).autofill_preview(
            opportunity_id, form_type=data.form_type, company=data.company
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/forms/generate", response_model=DGCPFormGenerateResponse)
async def generate_opportunity_form(
    opportunity_id: uuid.UUID,
    data: DGCPFormPreviewRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPFormGenerateResponse:
    try:
        return await _bid_svc(db, user).generate_form(
            opportunity_id, form_type=data.form_type, company=data.company
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/bid-package/prepare", response_model=DGCPExpedientePrepareResponse)
async def prepare_bid_package(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPExpedientePrepareResponse:
    try:
        return await _bid_svc(db, user).prepare_expediente(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/{opportunity_id}/bid-package/status", response_model=DGCPBidPackageStatusResponse)
async def get_bid_package_status(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPBidPackageStatusResponse:
    try:
        return await _bid_svc(db, user).get_expediente_status(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/bid-package/user-input")
async def set_bid_package_user_input(
    opportunity_id: uuid.UUID,
    data: DGCPUserInputRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).apply_user_input(opportunity_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/bid-package/mark-ready-review", response_model=DGCPBidPackageStatusResponse)
async def mark_bid_package_ready(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPBidPackageStatusResponse:
    try:
        return await _bid_svc(db, user).mark_ready_for_review(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/{opportunity_id}/bid-package/download")
async def download_bid_package(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        content, filename = await _bid_svc(db, user).download_expediente(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/opportunities/{opportunity_id}/real-expediente/generate",
    response_model=RealExpedienteGenerateResponse,
)
async def generate_real_expediente(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> RealExpedienteGenerateResponse:
    try:
        return await _real_expediente_builder(db, user).generate(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/real-expediente/validate",
    response_model=RealExpedienteValidationResponse,
)
async def validate_real_expediente(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> RealExpedienteValidationResponse:
    try:
        return await _real_expediente_builder(db, user).validate_package(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/real-expediente/prepare-package",
    response_model=RealExpedienteGenerateResponse,
)
async def prepare_dgcp_submission_package(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> RealExpedienteGenerateResponse:
    try:
        return await _real_expediente_builder(db, user).prepare_submission_package(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/real-expediente/status",
    response_model=RealExpedienteStatusResponse,
)
async def get_real_expediente_status(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> RealExpedienteStatusResponse:
    try:
        return await _real_expediente_builder(db, user).get_status(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get("/opportunities/{opportunity_id}/real-expediente/manifest")
async def get_real_expediente_manifest(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        builder = _real_expediente_builder(db, user)
        _, pkg = await builder._load_package(opportunity_id)
        return builder.get_manifest(pkg)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get("/opportunities/{opportunity_id}/real-expediente/report")
async def download_real_expediente_report(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> Response:
    try:
        builder = _real_expediente_builder(db, user)
        _, pkg = await builder._load_package(opportunity_id)
        data = builder.get_report_bytes(pkg)
        await builder.log_download(opportunity_id, kind="report", filename="reporte_preparacion.pdf")
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": build_content_disposition("reporte_preparacion.pdf")},
    )


@router.get("/opportunities/{opportunity_id}/real-expediente/download")
async def download_real_expediente_zip(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> Response:
    try:
        builder = _real_expediente_builder(db, user)
        opp, pkg = await builder._load_package(opportunity_id)
        content, filename = builder.get_download_zip(opp, pkg)
        await builder.log_download(opportunity_id, kind="zip", filename=filename)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": build_content_disposition(filename)},
    )


@router.post(
    "/opportunities/{opportunity_id}/real-expediente/mark-ready-review",
    response_model=RealExpedienteStatusResponse,
)
async def mark_real_expediente_ready_review(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> RealExpedienteStatusResponse:
    try:
        return await _real_expediente_builder(db, user).mark_ready_review(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/real-expediente/mark-ready-upload",
    response_model=RealExpedienteStatusResponse,
)
async def mark_real_expediente_ready_upload(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> RealExpedienteStatusResponse:
    try:
        return await _real_expediente_builder(db, user).mark_ready_upload(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/economic-offer/status",
    response_model=EconomicOfferStatusResponse,
)
async def get_economic_offer_status(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> EconomicOfferStatusResponse:
    try:
        return await _economic_offer_svc(db, user).get_status(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/economic-offer/create-draft-task",
    response_model=CreateEconomicOfferTaskResponse,
)
async def create_economic_offer_draft_task(
    opportunity_id: uuid.UUID,
    data: CreateEconomicOfferDraftTaskRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> CreateEconomicOfferTaskResponse:
    try:
        return await _economic_offer_svc(db, user).create_draft_task(opportunity_id, data)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/finalization/preview",
    response_model=DocumentFinalizationPreviewResponse,
)
async def preview_document_finalization(
    opportunity_id: uuid.UUID,
    data: DocumentFinalizationPreviewRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DocumentFinalizationPreviewResponse:
    try:
        return await _finalization_engine(db, user).preview(opportunity_id, data)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/finalization/generate",
    response_model=DocumentFinalizationGenerateResponse,
)
async def generate_document_finalization(
    opportunity_id: uuid.UUID,
    data: DocumentFinalizationGenerateRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DocumentFinalizationGenerateResponse:
    try:
        return await _finalization_engine(db, user).generate_final(opportunity_id, data)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/finalization/generate-all",
    response_model=DocumentFinalizationBatchResponse,
)
async def generate_all_document_finalizations(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    company_key: str | None = None,
) -> DocumentFinalizationBatchResponse:
    try:
        return await _finalization_engine(db, user).generate_all_ready(
            opportunity_id, company_key=company_key
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/finalization/records",
    response_model=list[DocumentFinalizationRecordResponse],
)
async def list_finalization_records(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> list[DocumentFinalizationRecordResponse]:
    return await _finalization_engine(db, user).list_records(opportunity_id)


@router.get("/opportunities/{opportunity_id}/finalization/{record_id}/file")
async def download_finalization_pdf(
    opportunity_id: uuid.UUID,
    record_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> Response:
    try:
        data, filename, mime = await _finalization_engine(db, user).get_final_file(record_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": build_content_disposition(filename)},
    )


@router.get(
    "/opportunities/{opportunity_id}/history",
    response_model=list[DGCPOpportunityHistoryResponse],
)
async def get_opportunity_history(
    opportunity_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
) -> list[DGCPOpportunityHistoryResponse]:
    ctx = require_tenant_context()
    service = DGCPService(db)
    return await service.get_history(ctx.tenant_id, opportunity_id)


@router.post("/reclassify")
async def reclassify_opportunities(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    __: TenantCtx,
) -> dict[str, int | dict[str, int]]:
    ctx = require_tenant_context()
    service = DGCPService(db)
    stats = await service.reclassify_opportunities(ctx.tenant_id, use_ai=True)
    audit = AuditService(db)
    await audit.log(
        action="dgcp.reclassify",
        tenant_id=ctx.tenant_id,
        user_id=user.id,
        details=stats,
        request=request,
    )
    return stats


@router.post("/sync", response_model=DGCPSyncJobResponse, status_code=202)
async def trigger_sync(
    data: DGCPSyncRequest,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    __: TenantCtx,
) -> DGCPSyncJobResponse:
    ctx = require_tenant_context()
    sync = DGCPSyncService(db)
    job = await sync.run_sync(
        ctx.tenant_id,
        trigger="manual",
        max_pages=data.max_pages,
        page_size=data.page_size,
    )
    audit = AuditService(db)
    await audit.log(
        action="dgcp.sync.manual",
        tenant_id=ctx.tenant_id,
        user_id=user.id,
        resource_type="dgcp_sync_job",
        resource_id=job.id,
        details={
            "created": job.created_count,
            "updated": job.updated_count,
            "pages": job.pages_synced,
            "max_pages": data.max_pages,
        },
        request=request,
    )
    return DGCPSyncJobResponse.model_validate(job)


@router.get("/sync/jobs", response_model=list[DGCPSyncJobResponse])
async def list_sync_jobs(
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[DGCPSyncJobResponse]:
    from sqlalchemy import select

    from app.models.dgcp_sync_job import DGCPSyncJob

    ctx = require_tenant_context()
    result = await db.execute(
        select(DGCPSyncJob)
        .where(DGCPSyncJob.tenant_id == ctx.tenant_id)
        .order_by(DGCPSyncJob.started_at.desc())
        .limit(limit)
    )
    return [DGCPSyncJobResponse.model_validate(j) for j in result.scalars().all()]


@router.get("/sync/schedule", response_model=DGCPSyncScheduleResponse)
async def get_sync_schedule(
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
) -> DGCPSyncScheduleResponse:
    ctx = require_tenant_context()
    sync = DGCPSyncService(db)
    schedule = await sync.get_or_create_schedule(ctx.tenant_id)
    return DGCPSyncScheduleResponse.model_validate(schedule)


@router.put("/sync/schedule", response_model=DGCPSyncScheduleResponse)
async def update_sync_schedule(
    data: DGCPSyncScheduleUpdate,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    __: TenantCtx,
) -> DGCPSyncScheduleResponse:
    from datetime import UTC, datetime, timedelta

    ctx = require_tenant_context()
    sync = DGCPSyncService(db)
    schedule = await sync.get_or_create_schedule(ctx.tenant_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    if data.interval_hours is not None:
        schedule.next_run_at = datetime.now(UTC) + timedelta(hours=schedule.interval_hours)
    audit = AuditService(db)
    await audit.log(
        action="dgcp.sync.schedule_update",
        tenant_id=ctx.tenant_id,
        user_id=user.id,
        resource_type="dgcp_sync_schedule",
        resource_id=schedule.id,
        details=data.model_dump(exclude_unset=True),
        request=request,
    )
    await db.flush()
    await db.refresh(schedule)
    return DGCPSyncScheduleResponse.model_validate(schedule)


@router.get("/audit", response_model=list[DGCPAuditLogResponse])
async def list_dgcp_audit(
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[DGCPAuditLogResponse]:
    ctx = require_tenant_context()
    service = DGCPService(db)
    return await service.list_audit_logs(ctx.tenant_id, limit=limit)
