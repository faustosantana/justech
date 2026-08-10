import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.api.permission_deps import DGCP_VIEW, DGCP_MUTATE
from app.core.content_disposition import build_content_disposition
from app.core.tenant import require_tenant_context
from app.schemas.dgcp import (
    DGCPOpportunityActionRequest,
    DGCPOpportunityCreate,
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
from app.schemas.dgcp_expediente_context import (
    DGCPExpedienteContextBootstrapRequest,
    DGCPExpedienteContextResponse,
)
from app.schemas.dgcp_historical import (
    DGCPHistoricalIndexRequest,
    DGCPHistoricalIndexResponse,
    DGCPHistoricalIndexStatsResponse,
    DGCPHistoricalSimilarResponse,
    DGCPHistoricalSimilarSearchRequest,
)
from app.services.dgcp_historical_awards_service import DGCPHistoricalAwardsService
from app.services.dgcp_historical_similar_search_service import DGCPHistoricalSimilarSearchService
from app.services.dgcp_expediente_context_service import DGCPExpedienteContextService
from app.services.audit_service import AuditService
from app.schemas.dgcp_intelligence import (
    CommercialMemoryQueryRequest,
    CommercialMemoryResponse,
    DGCPIntelligenceResponse,
    QuotationIntelligenceRequest,
    AgentRunResponse,
    intelligence_payload_ready,
)
from app.services.commercial_memory_service import CommercialMemoryService
from app.services.dgcp_intelligence.service import DGCPIntelligenceService
from app.services.jaios_agent_runner import run_agent, run_all_agents_for_tenant
from app.services.quotation_intelligence_service import QuotationIntelligenceService


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
from app.models.user import User
from app.schemas.dgcp_analysis_job import (
    DGCPAnalysisJobAcceptedResponse,
    DGCPAnalysisJobResponse,
    DGCPAnalysisStatusResponse,
)
from app.schemas.dgcp_bid import (
    DGCPAnalyzeResponse,
    DGCPAliasMappingSaveRequest,
    DGCPAssociateDocumentRequest,
    DGCPLinkM365DocumentRequest,
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
    DGCPProcessDocumentsRefreshResponse,
    DGCPProcessDocumentRoleUpdate,
    DGCPProcessDocumentLinkRequest,
    DGCPProcessDocumentUploadResponse,
    DGCPRequirementsResponse,
    DGCPUserInputRequest,
)
from app.schemas.dgcp_pliego_analysis import PliegoFieldReviewRequest
from app.schemas.dgcp_economic_offer import (
    CreateEconomicOfferDraftTaskRequest,
    CreateEconomicOfferTaskResponse,
    EconomicOfferStatusResponse,
)
from app.schemas.dgcp_autofill import (
    DGCPDocumentAnalysisResponse,
    DGCPMissingFieldsResponse,
    DGCPRequiredFormsResponse,
    DGCPResolveMissingFieldRequest,
    DGCPResolveMissingFieldResponse,
)
from app.schemas.dgcp_product_intelligence import (
    DGCPProductIntelligenceApproveRequest,
    DGCPProductIntelligenceMatrixRequest,
    DGCPProductIntelligenceSearchRequest,
)
from app.schemas.dgcp_process_updates import (
    DGCPProcessUpdateDashboardResponse,
    DGCPProcessUpdateReviewRequest,
    DGCPProcessUpdateSimulateRequest,
    DGCPProcessUpdatesResponse,
)
from app.schemas.dgcp_technical_sheet import (
    DGCPTechSheetAddImageRequest,
    DGCPTechSheetReorderImagesRequest,
    DGCPTechSheetSelectProductRequest,
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
from app.services.dgcp_analysis_job_service import (
    DGCPAnalysisAlreadyRunningError,
    DGCPAnalysisJobService,
)
from app.services.dgcp_bid_package_service import DGCPAlreadyAnalyzedError, DGCPBidPackageService
from app.services.dgcp_economic_offer_service import DGCPEconomicOfferService
from app.services.real_dgcp_expediente_builder import RealDGCPExpedienteBuilder
from app.services.document_finalization_engine import DocumentFinalizationEngine
from app.services.dgcp_funnel import FunnelStage
from app.services.dgcp_service import DGCPService
from app.services.integrated_commercial_flow_service import IntegratedCommercialFlowService
from app.services.dgcp_sync_service import DGCPSyncService

router = APIRouter(prefix="/dgcp", tags=["DGCP Intelligence"])


@router.get("/dashboard", response_model=DGCPOpportunitySummary, dependencies=DGCP_VIEW)
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


@router.get("/opportunities", response_model=DGCPOpportunityListResponse, dependencies=DGCP_VIEW)
async def list_opportunities(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    status: Annotated[OpportunityStatus | None, Query()] = None,
    funnel_stage: Annotated[FunnelStage | None, Query(description="Etapa del embudo operativo")] = None,
    company: Annotated[OpportunityCompany | None, Query()] = None,
    priority: Annotated[OpportunityPriority | None, Query()] = None,
    search: Annotated[str | None, Query(min_length=2, description="Código, título, institución o UUID")] = None,
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
        funnel_stage=funnel_stage,
        company=company,
        priority=priority,
        search=search,
        skip=skip,
        limit=limit,
        include_expired=include_expired,
    )


@router.post("/opportunities", response_model=DGCPOpportunityResponse, status_code=201, dependencies=DGCP_MUTATE)
async def create_opportunity_manual(
    data: DGCPOpportunityCreate,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPOpportunityResponse:
    """Crear licitación manualmente o registrar proceso externo."""
    ctx = require_tenant_context()
    service = DGCPService(db)
    opportunity = await service.create_opportunity(
        ctx.tenant_id,
        data,
        user_id=user.id,
        request=request,
    )
    await db.commit()
    return DGCPOpportunityResponse.model_validate(opportunity)


@router.get("/opportunities/{opportunity_id}", response_model=DGCPOpportunityResponse, dependencies=DGCP_VIEW)
async def get_opportunity(
    opportunity_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
) -> DGCPOpportunityResponse:
    ctx = require_tenant_context()
    service = DGCPService(db)
    opportunity = await service.get_opportunity(ctx.tenant_id, opportunity_id)
    return service.to_response(opportunity)


@router.get("/opportunities/{opportunity_id}/commercial-context", dependencies=DGCP_VIEW)
async def get_opportunity_commercial_context(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> dict:
    """Odoo + precios + intel persistida — respuesta rápida sin Hermes/autofill live."""
    ctx = require_tenant_context()
    service = DGCPService(db)
    opportunity = await service.get_opportunity(ctx.tenant_id, opportunity_id)
    flow = IntegratedCommercialFlowService(db, ctx.tenant_id, user_id=user.id)
    return await flow.analyze_opportunity(opportunity)


@router.post("/opportunities/{opportunity_id}/commercial-context/enrich", dependencies=DGCP_VIEW)
async def enrich_opportunity_commercial_context(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> dict:
    """Enriquecimiento en segundo plano — autofill preview (no bloquea carga inicial)."""
    ctx = require_tenant_context()
    service = DGCPService(db)
    opportunity = await service.get_opportunity(ctx.tenant_id, opportunity_id)
    flow = IntegratedCommercialFlowService(db, ctx.tenant_id, user_id=user.id)
    return await flow.enrich_opportunity(opportunity)


@router.post(
    "/opportunities/{opportunity_id}/expediente-context/bootstrap",
    response_model=DGCPExpedienteContextResponse,
    dependencies=DGCP_VIEW,
)
@router.post(
    "/processes/{opportunity_id}/expediente-context/bootstrap",
    response_model=DGCPExpedienteContextResponse,
    dependencies=DGCP_VIEW,
)
async def bootstrap_expediente_context(
    opportunity_id: uuid.UUID,
    data: DGCPExpedienteContextBootstrapRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPExpedienteContextResponse:
    """Fase 1: histórico + comercial Odoo en background al abrir expediente (feature flag)."""
    ctx = require_tenant_context()
    service = DGCPExpedienteContextService(db, ctx.tenant_id, user_id=user.id)
    return await service.bootstrap(opportunity_id, data)


@router.patch("/opportunities/{opportunity_id}", response_model=DGCPOpportunityResponse, dependencies=DGCP_MUTATE)
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


@router.post("/opportunities/{opportunity_id}/actions", response_model=DGCPOpportunityResponse, dependencies=DGCP_MUTATE)
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
    bid = _bid_svc(db, user)

    # Tras «Mostrar interés»: análisis de TODOS los documentos + expediente vivo + similares reales.
    if data.action in (
        OpportunityAction.MARCAR_INTERES,
        OpportunityAction.MOSTRAR_INTERES,
    ):
        try:
            await bid.analyze(opportunity_id)
        except Exception:
            pass
        try:
            await bid.activate_expediente_tracking(opportunity_id)
        except ValueError:
            pass
        try:
            hist = DGCPHistoricalSimilarSearchService(db, ctx.tenant_id)
            await hist.search_bootstrap(
                opportunity_id,
                DGCPHistoricalSimilarSearchRequest(refresh=False, limit=10),
            )
        except Exception:
            pass

    if data.action in (
        OpportunityAction.LICITAR,
        OpportunityAction.INICIAR_PREPARACION,
    ):
        try:
            await bid.activate_expediente_tracking(opportunity_id)
        except ValueError:
            pass
    await db.commit()
    return service.to_response(opportunity)


def _bid_svc(db, user) -> DGCPBidPackageService:
    ctx = require_tenant_context()
    return DGCPBidPackageService(db, ctx.tenant_id, user_id=user.id)


def _analysis_job_svc(db, user) -> DGCPAnalysisJobService:
    ctx = require_tenant_context()
    return DGCPAnalysisJobService(db, ctx.tenant_id, user_id=user.id)


def _economic_offer_svc(db, user) -> DGCPEconomicOfferService:
    ctx = require_tenant_context()
    return DGCPEconomicOfferService(db, ctx.tenant_id, user_id=user.id)


def _finalization_engine(db, user) -> DocumentFinalizationEngine:
    ctx = require_tenant_context()
    return DocumentFinalizationEngine(db, ctx.tenant_id, user_id=user.id)


def _real_expediente_builder(db, user) -> RealDGCPExpedienteBuilder:
    ctx = require_tenant_context()
    return RealDGCPExpedienteBuilder(db, ctx.tenant_id, user_id=user.id)


@router.get("/opportunities/{opportunity_id}/requirements", response_model=DGCPRequirementsResponse, dependencies=DGCP_VIEW)
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


@router.post(
    "/opportunities/{opportunity_id}/requirements/analyze",
    dependencies=DGCP_MUTATE,
    responses={
        200: {"model": DGCPAnalyzeResponse},
        202: {"model": DGCPAnalysisJobAcceptedResponse},
    },
)
async def analyze_opportunity_requirements(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    force: bool = False,
    async_job: bool | None = Query(default=None, alias="async"),
):
    use_async = async_job if async_job is not None else force
    job_svc = _analysis_job_svc(db, user)
    try:
        if use_async:
            accepted = await job_svc.start_job(opportunity_id, force=force)
            await db.commit()
            job_svc.spawn_run(opportunity_id, accepted.job_id, force=force)
            return JSONResponse(
                status_code=202,
                content=accepted.model_dump(mode="json"),
            )
        result = await _bid_svc(db, user).analyze(opportunity_id, force=force)
        await db.commit()
        return result
    except DGCPAnalysisAlreadyRunningError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "analysis_already_running": True,
                "job_id": str(exc.job_id),
            },
        ) from exc
    except DGCPAlreadyAnalyzedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "already_analyzed": True,
                "analyzed_at": exc.analyzed_at.isoformat(),
            },
        ) from exc
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/analysis-status",
    response_model=DGCPAnalysisStatusResponse,
    dependencies=DGCP_VIEW,
)
async def get_opportunity_analysis_status(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPAnalysisStatusResponse:
    return await _analysis_job_svc(db, user).get_analysis_status(opportunity_id)


@router.get(
    "/opportunities/{opportunity_id}/analysis-jobs/{job_id}",
    response_model=DGCPAnalysisJobResponse,
    dependencies=DGCP_VIEW,
)
async def get_opportunity_analysis_job(
    opportunity_id: uuid.UUID,
    job_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPAnalysisJobResponse:
    job = await _analysis_job_svc(db, user).get_job(opportunity_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job de análisis no encontrado")
    return job


@router.get(
    "/opportunities/{opportunity_id}/pliego-analysis",
    dependencies=DGCP_VIEW,
)
async def get_pliego_analysis(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> dict:
    try:
        return await _bid_svc(db, user).get_pliego_analysis(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/pliego-analysis/run",
    dependencies=DGCP_MUTATE,
)
async def run_pliego_analysis(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    force: bool = True,
) -> dict:
    try:
        return await _bid_svc(db, user).run_pliego_analysis(opportunity_id, force=force)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/pliego-analysis/fields/{field_key}/review",
    dependencies=DGCP_MUTATE,
)
async def review_pliego_analysis_field(
    opportunity_id: uuid.UUID,
    field_key: str,
    body: PliegoFieldReviewRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> dict:
    try:
        return await _bid_svc(db, user).review_pliego_field(
            opportunity_id,
            field_key,
            reviewed=body.reviewed,
            comment=body.comment,
            corrected_value=body.corrected_value,
            corrected_items=body.corrected_items,
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get("/opportunities/{opportunity_id}/checklist", response_model=DGCPChecklistResponse, dependencies=DGCP_VIEW)
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


@router.post("/opportunities/{opportunity_id}/checklist/items", dependencies=DGCP_MUTATE)
async def add_manual_checklist_item(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    body: dict,
):
    try:
        return await _bid_svc(db, user).add_manual_checklist_item(
            opportunity_id,
            name=str(body.get("name") or ""),
            tipo=str(body.get("tipo") or body.get("category") or "administrativo"),
            mandatory=bool(body.get("mandatory", True)),
            description=body.get("description"),
            source=body.get("source"),
            page=body.get("page"),
            due_date=body.get("due_date"),
            assignee=body.get("assignee"),
            notes=body.get("notes") or body.get("observations"),
            document_type=body.get("document_type") or body.get("type"),
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post("/opportunities/{opportunity_id}/checklist/{item_id}/task", dependencies=DGCP_MUTATE)
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
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_MUTATE,
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
    "/opportunities/{opportunity_id}/checklist/{item_id}/unlink-document",
    response_model=DGCPAssociateDocumentResponse,
    dependencies=DGCP_MUTATE,
)
async def unlink_checklist_document(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPAssociateDocumentResponse:
    try:
        return await _bid_svc(db, user).unlink_checklist_document(opportunity_id, item_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/checklist/{item_id}/upload-document",
    response_model=DGCPAssociateDocumentResponse,
    dependencies=DGCP_MUTATE,
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


@router.post(
    "/opportunities/{opportunity_id}/checklist/{item_id}/link-m365",
    response_model=DGCPAssociateDocumentResponse,
    dependencies=DGCP_MUTATE,
)
async def link_m365_checklist_document(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    data: DGCPLinkM365DocumentRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPAssociateDocumentResponse:
    try:
        return await _bid_svc(db, user).link_m365_checklist_document(opportunity_id, item_id, data)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/checklist/{item_id}/import-m365",
    response_model=DGCPAssociateDocumentResponse,
    dependencies=DGCP_MUTATE,
)
async def import_m365_checklist_document(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    data: DGCPLinkM365DocumentRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPAssociateDocumentResponse:
    try:
        return await _bid_svc(db, user).import_m365_checklist_document(opportunity_id, item_id, data)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/checklist/{item_id}/document-preview",
    response_model=DGCPDocumentPreviewResponse,
    dependencies=DGCP_VIEW,
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


@router.get("/opportunities/{opportunity_id}/bid-package", response_model=DGCPBidPackageResponse, dependencies=DGCP_VIEW)
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


@router.get("/opportunities/{opportunity_id}/document-matches", response_model=DGCPDocumentMatchesResponse, dependencies=DGCP_VIEW)
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


@router.post("/opportunities/{opportunity_id}/forms/preview", response_model=DGCPFormPreviewResponse, dependencies=DGCP_MUTATE)
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


@router.get("/opportunities/{opportunity_id}/process-documents", response_model=DGCPProcessDocumentsResponse, dependencies=DGCP_VIEW)
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


@router.post(
    "/opportunities/{opportunity_id}/process-documents/upload",
    response_model=DGCPProcessDocumentUploadResponse,
    dependencies=DGCP_MUTATE,
)
async def upload_process_pliego(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    file: UploadFile = File(...),
    doc_role: str | None = Query(default=None, description="Rol del documento: pliego, tdr, bases…"),
) -> DGCPProcessDocumentUploadResponse:
    try:
        content = await file.read()
        if not content:
            raise ValueError("Archivo vacío")
        return await _bid_svc(db, user).upload_process_pliego(
            opportunity_id,
            filename=file.filename or "pliego.pdf",
            content=content,
            mime_type=file.content_type,
            doc_role=doc_role,
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/process-documents/refresh",
    response_model=DGCPProcessDocumentsRefreshResponse,
    dependencies=DGCP_MUTATE,
)
async def refresh_process_documents(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPProcessDocumentsRefreshResponse:
    try:
        return await _bid_svc(db, user).refresh_process_documents(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/process-documents/{process_document_id}/reingest",
    dependencies=DGCP_MUTATE,
)
async def reingest_process_document(
    opportunity_id: uuid.UUID,
    process_document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).reingest_process_document(opportunity_id, process_document_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.patch(
    "/opportunities/{opportunity_id}/process-documents/{process_document_id}/role",
    dependencies=DGCP_MUTATE,
)
async def update_process_document_role(
    opportunity_id: uuid.UUID,
    process_document_id: uuid.UUID,
    data: DGCPProcessDocumentRoleUpdate,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).update_process_document_role(
            opportunity_id,
            process_document_id,
            doc_role=data.doc_role,
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.patch(
    "/opportunities/{opportunity_id}/process-documents/{process_document_id}/flags",
    dependencies=DGCP_MUTATE,
)
async def update_process_document_flags(
    opportunity_id: uuid.UUID,
    process_document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    body: dict,
):
    try:
        return await _bid_svc(db, user).update_process_document_flags(
            opportunity_id,
            process_document_id,
            is_primary=body.get("is_primary"),
            include_in_analysis=body.get("include_in_analysis"),
            doc_role=body.get("doc_role"),
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/process-documents/link",
    dependencies=DGCP_MUTATE,
)
async def link_process_document(
    opportunity_id: uuid.UUID,
    data: DGCPProcessDocumentLinkRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).link_process_document_from_url(
            opportunity_id,
            url=data.url,
            title=data.title,
            doc_role=data.doc_role,
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get("/opportunities/{opportunity_id}/process-documents/{process_document_id}/file", dependencies=DGCP_VIEW)
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


@router.get("/opportunities/{opportunity_id}/alerts", response_model=DGCPBidAlertResponse, dependencies=DGCP_VIEW)
async def get_opportunity_alerts(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPBidAlertResponse:
    try:
        return await _bid_svc(db, user).get_alerts(opportunity_id)
    except ValueError:
        return DGCPBidAlertResponse(opportunity_id=opportunity_id, alerts=[], total=0)


@router.get("/autofill-templates", dependencies=DGCP_VIEW)
async def list_autofill_templates(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> dict:
    items = await _bid_svc(db, user).list_autofill_templates()
    return {"items": items, "total": len(items)}


@router.get("/autofill-canonical-fields", dependencies=DGCP_VIEW)
async def list_autofill_canonical_fields(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> dict:
    return {"items": _bid_svc(db, user).list_autofill_canonical_fields()}


@router.post("/autofill-alias-mappings", dependencies=DGCP_MUTATE)
async def save_autofill_alias_mapping(
    data: DGCPAliasMappingSaveRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> dict:
    u = await db.get(User, user.id)
    return await _bid_svc(db, user).save_autofill_alias_mapping(
        data,
        user_email=u.email if u else None,
    )


@router.post("/opportunities/{opportunity_id}/forms/autofill-preview", response_model=DGCPFormAutofillPreviewResponse, dependencies=DGCP_MUTATE)
async def autofill_preview_form(
    opportunity_id: uuid.UUID,
    data: DGCPFormPreviewRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPFormAutofillPreviewResponse:
    try:
        return await _bid_svc(db, user).autofill_preview(
            opportunity_id,
            form_type=data.form_type,
            company=data.company,
            field_overrides=data.field_overrides or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/forms/document-preview", dependencies=DGCP_MUTATE)
async def autofill_document_preview(
    opportunity_id: uuid.UUID,
    data: DGCPFormPreviewRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        pdf_bytes, filename = await _bid_svc(db, user).autofill_document_pdf(
            opportunity_id,
            form_type=data.form_type,
            company=data.company,
            field_overrides=data.field_overrides or None,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": build_content_disposition("inline", filename),
                "Cache-Control": "private, no-store",
            },
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/forms/generate", response_model=DGCPFormGenerateResponse, dependencies=DGCP_MUTATE)
async def generate_opportunity_form(
    opportunity_id: uuid.UUID,
    data: DGCPFormPreviewRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPFormGenerateResponse:
    try:
        return await _bid_svc(db, user).generate_form(
            opportunity_id,
            form_type=data.form_type,
            company=data.company,
            field_overrides=data.field_overrides or None,
            draft=data.draft,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/opportunities/{opportunity_id}/forms/required",
    response_model=DGCPRequiredFormsResponse,
    dependencies=DGCP_VIEW,
)
async def list_required_forms(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    company: str = Query(default="justech"),
) -> DGCPRequiredFormsResponse:
    try:
        return await _bid_svc(db, user).get_required_forms(opportunity_id, company=company)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/opportunities/{opportunity_id}/forms/missing-fields",
    response_model=DGCPMissingFieldsResponse,
    dependencies=DGCP_VIEW,
)
async def list_missing_autofill_fields(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    form_type: str = Query(default="SNCC.F042"),
    company: str = Query(default="justech"),
) -> DGCPMissingFieldsResponse:
    try:
        return await _bid_svc(db, user).get_missing_fields(
            opportunity_id, form_type=form_type, company=company
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/forms/resolve-missing-field",
    response_model=DGCPResolveMissingFieldResponse,
    dependencies=DGCP_MUTATE,
)
async def resolve_missing_autofill_field(
    opportunity_id: uuid.UUID,
    data: DGCPResolveMissingFieldRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    form_type: str = Query(default="SNCC.F042"),
    company: str = Query(default="justech"),
) -> DGCPResolveMissingFieldResponse:
    try:
        return await _bid_svc(db, user).resolve_missing_field(
            opportunity_id, data, form_type=form_type, company=company
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/document-analysis",
    response_model=DGCPDocumentAnalysisResponse,
    dependencies=DGCP_VIEW,
)
async def get_opportunity_document_analysis(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPDocumentAnalysisResponse:
    try:
        return await _bid_svc(db, user).get_document_analysis(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/opportunities/{opportunity_id}/technical-sheets",
    dependencies=DGCP_VIEW,
)
async def list_technical_sheets(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).list_technical_sheets(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/technical-sheets/detect",
    dependencies=DGCP_MUTATE,
)
async def detect_technical_sheets(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    force: bool = Query(default=False),
):
    try:
        return await _bid_svc(db, user).detect_technical_sheets(opportunity_id, force=force)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/technical-sheets/manual",
    dependencies=DGCP_MUTATE,
)
async def create_manual_technical_sheet(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    body: dict,
):
    try:
        return await _bid_svc(db, user).create_manual_technical_sheet(
            opportunity_id,
            name=str(body.get("name") or body.get("article") or ""),
            description=body.get("description"),
            quantity=body.get("quantity"),
            unit=body.get("unit"),
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/technical-sheets/upload-existing",
    dependencies=DGCP_MUTATE,
)
async def upload_existing_technical_sheet(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    file: UploadFile = File(...),
    name: str = Query(...),
    description: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    model: str | None = Query(default=None),
    manufacturer: str | None = Query(default=None),
    country: str | None = Query(default=None),
    warranty: str | None = Query(default=None),
    observation: str | None = Query(default=None),
    initial_status: str = Query(default="en_elaboracion"),
):
    from pathlib import Path

    from app.config import settings

    try:
        content = await file.read()
        if not content:
            raise ValueError("Archivo vacío")
        ctx = require_tenant_context()
        storage = Path(settings.expediente_storage_path) / str(ctx.tenant_id) / "technical_sheets" / "uploads"
        storage.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename or "ficha.pdf").name
        dest = storage / f"{uuid.uuid4().hex}_{safe_name}"
        dest.write_bytes(content)
        return await _bid_svc(db, user).upload_existing_technical_sheet(
            opportunity_id,
            name=name,
            description=description,
            brand=brand,
            model=model,
            manufacturer=manufacturer,
            country=country,
            warranty=warranty,
            observation=observation,
            initial_status=initial_status,
            upload_path=dest,
            filename=safe_name,
            mime_type=file.content_type,
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/replace-file",
    dependencies=DGCP_MUTATE,
)
async def replace_technical_sheet_file(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    file: UploadFile = File(...),
):
    from pathlib import Path

    from app.config import settings

    try:
        content = await file.read()
        if not content:
            raise ValueError("Archivo vacío")
        ctx = require_tenant_context()
        storage = Path(settings.expediente_storage_path) / str(ctx.tenant_id) / "technical_sheets" / sheet_id
        storage.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename or "ficha.pdf").name
        dest = storage / f"{uuid.uuid4().hex}_{safe_name}"
        dest.write_bytes(content)
        return await _bid_svc(db, user).replace_technical_sheet_file(
            opportunity_id,
            sheet_id,
            upload_path=dest,
            filename=safe_name,
            mime_type=file.content_type,
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/uploaded-file",
    dependencies=DGCP_VIEW,
)
async def download_technical_sheet_uploaded_file(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    disposition: str = Query(default="attachment"),
):
    from fastapi.responses import Response

    try:
        content, mime, filename = await _bid_svc(db, user).download_technical_sheet_uploaded_file(
            opportunity_id, sheet_id
        )
        disp = "inline" if disposition == "inline" else "attachment"
        return Response(
            content=content,
            media_type=mime,
            headers={"Content-Disposition": f'{disp}; filename="{filename}"'},
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/select-product",
    dependencies=DGCP_MUTATE,
)
async def select_technical_sheet_product(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    data: DGCPTechSheetSelectProductRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).select_technical_sheet_product(opportunity_id, sheet_id, data)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/generate-draft",
    dependencies=DGCP_MUTATE,
)
async def generate_technical_sheet_draft(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    company: str = Query(default="justech"),
):
    try:
        return await _bid_svc(db, user).generate_technical_sheet_draft(
            opportunity_id, sheet_id, company=company
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/approve",
    dependencies=DGCP_MUTATE,
)
async def approve_technical_sheet(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).approve_technical_sheet(opportunity_id, sheet_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/reject",
    dependencies=DGCP_MUTATE,
)
async def reject_technical_sheet(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).reject_technical_sheet(opportunity_id, sheet_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/export",
    dependencies=DGCP_VIEW,
)
async def export_technical_sheet(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    fmt: str = Query(default="markdown"),
    company: str | None = Query(default=None),
):
    try:
        result = await _bid_svc(db, user).export_technical_sheet(
            opportunity_id, sheet_id, fmt=fmt, company=company
        )
        if fmt.lower() == "pdf":
            pdf_bytes, filename = result
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": build_content_disposition("attachment", filename),
                    "Cache-Control": "private, no-store",
                },
            )
        return result
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/branding",
    dependencies=DGCP_VIEW,
)
async def get_technical_sheet_branding(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    company: str | None = Query(default=None),
):
    try:
        return await _bid_svc(db, user).get_technical_sheet_branding(
            opportunity_id, sheet_id, company=company
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/images",
    dependencies=DGCP_MUTATE,
)
async def add_technical_sheet_image(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    label: str | None = Query(default=None),
    source: str = Query(default="manual"),
    url: str | None = Query(default=None),
    file: UploadFile | None = File(default=None),
):
    from pathlib import Path

    from app.config import settings

    try:
        upload_path = None
        if file and file.filename:
            ctx = require_tenant_context()
            storage = Path(settings.expediente_storage_path) / str(ctx.tenant_id) / "technical_sheets" / sheet_id
            storage.mkdir(parents=True, exist_ok=True)
            safe_name = Path(file.filename).name
            dest = storage / f"{uuid.uuid4().hex}_{safe_name}"
            dest.write_bytes(await file.read())
            upload_path = dest
            label = label or safe_name
        data = DGCPTechSheetAddImageRequest(label=label, source=source, url=url)
        return await _bid_svc(db, user).add_technical_sheet_image(
            opportunity_id, sheet_id, data, upload_path=upload_path
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.put(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/images/reorder",
    dependencies=DGCP_MUTATE,
)
async def reorder_technical_sheet_images(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    data: DGCPTechSheetReorderImagesRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).reorder_technical_sheet_images(opportunity_id, sheet_id, data)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.delete(
    "/opportunities/{opportunity_id}/technical-sheets/{sheet_id}/images/{image_id}",
    dependencies=DGCP_MUTATE,
)
async def remove_technical_sheet_image(
    opportunity_id: uuid.UUID,
    sheet_id: str,
    image_id: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).remove_technical_sheet_image(opportunity_id, sheet_id, image_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/product-intelligence",
    dependencies=DGCP_VIEW,
)
async def list_product_intelligence(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).list_product_intelligence(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/product-intelligence/run",
    dependencies=DGCP_MUTATE,
)
async def run_product_intelligence(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    force: bool = Query(default=False),
):
    try:
        return await _bid_svc(db, user).run_product_intelligence(opportunity_id, force=force)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/product-intelligence/{requirement_id}/search-candidates",
    dependencies=DGCP_MUTATE,
)
async def search_product_candidates(
    opportunity_id: uuid.UUID,
    requirement_id: str,
    data: DGCPProductIntelligenceSearchRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).search_product_candidates(
            opportunity_id,
            requirement_id,
            include_internet=data.include_internet,
            include_repository=data.include_repository,
            include_commercial=data.include_commercial,
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/product-intelligence/{requirement_id}/compliance-matrix",
    dependencies=DGCP_MUTATE,
)
async def build_product_compliance_matrix(
    opportunity_id: uuid.UUID,
    requirement_id: str,
    data: DGCPProductIntelligenceMatrixRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).build_product_compliance_matrix(
            opportunity_id, requirement_id, data.candidate_id
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/product-intelligence/{requirement_id}/approve",
    dependencies=DGCP_MUTATE,
)
async def approve_product_intelligence(
    opportunity_id: uuid.UUID,
    requirement_id: str,
    data: DGCPProductIntelligenceApproveRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).approve_product_intelligence(
            opportunity_id, requirement_id, data
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/product-intelligence/{requirement_id}/reject",
    dependencies=DGCP_MUTATE,
)
async def reject_product_intelligence(
    opportunity_id: uuid.UUID,
    requirement_id: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).reject_product_intelligence(opportunity_id, requirement_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/opportunities/{opportunity_id}/offer-preparation-center",
    dependencies=DGCP_VIEW,
)
async def get_offer_preparation_center(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).get_offer_preparation_center(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/offer-preparation-center/consolidated-offer",
    dependencies=DGCP_MUTATE,
)
async def generate_consolidated_technical_offer(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).generate_consolidated_technical_offer(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get(
    "/process-updates/dashboard",
    response_model=DGCPProcessUpdateDashboardResponse,
    dependencies=DGCP_VIEW,
)
async def get_process_updates_dashboard(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    return await _bid_svc(db, user).get_process_updates_dashboard()


@router.get(
    "/opportunities/{opportunity_id}/process-updates",
    response_model=DGCPProcessUpdatesResponse,
    dependencies=DGCP_VIEW,
)
async def get_process_updates(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).get_process_updates(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/process-updates/check",
    response_model=DGCPProcessUpdatesResponse,
    dependencies=DGCP_MUTATE,
)
async def check_process_updates(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).check_process_updates(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/process-updates/{update_id}/review",
    dependencies=DGCP_MUTATE,
)
async def mark_process_update_reviewed(
    opportunity_id: uuid.UUID,
    update_id: str,
    data: DGCPProcessUpdateReviewRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).mark_process_update_reviewed(
            opportunity_id, update_id, data.note
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/process-updates/{update_id}/apply",
    dependencies=DGCP_MUTATE,
)
async def mark_process_update_applied(
    opportunity_id: uuid.UUID,
    update_id: str,
    data: DGCPProcessUpdateReviewRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).mark_process_update_applied(
            opportunity_id, update_id, data.note
        )
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.post(
    "/opportunities/{opportunity_id}/process-updates/simulate",
    response_model=DGCPProcessUpdatesResponse,
    dependencies=DGCP_MUTATE,
)
async def simulate_process_updates(
    opportunity_id: uuid.UUID,
    data: DGCPProcessUpdateSimulateRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _bid_svc(db, user).simulate_process_updates(opportunity_id, data.scenarios)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get("/opportunities/{opportunity_id}/bid-package/document-validation", dependencies=DGCP_VIEW)
async def validate_bid_package_documents(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    company_key: str = "justech",
) -> dict:
    try:
        return await _bid_svc(db, user).validate_company_documents(
            opportunity_id, company_key=company_key
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities/{opportunity_id}/bid-package/prepare", response_model=DGCPExpedientePrepareResponse, dependencies=DGCP_MUTATE)
async def prepare_bid_package(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    company_key: str = "justech",
) -> DGCPExpedientePrepareResponse:
    from app.services.dgcp_expediente_errors import ExpedienteIncompleteError

    try:
        return await _bid_svc(db, user).prepare_expediente(
            opportunity_id, company_key=company_key
        )
    except ExpedienteIncompleteError as exc:
        raise HTTPException(status_code=409, detail=exc.validation) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/{opportunity_id}/bid-package/status", response_model=DGCPBidPackageStatusResponse, dependencies=DGCP_VIEW)
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


@router.post("/opportunities/{opportunity_id}/bid-package/user-input", dependencies=DGCP_MUTATE)
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


@router.post("/opportunities/{opportunity_id}/bid-package/mark-ready-review", response_model=DGCPBidPackageStatusResponse, dependencies=DGCP_MUTATE)
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


@router.get("/opportunities/{opportunity_id}/bid-package/download", dependencies=DGCP_VIEW)
async def download_bid_package(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    """Prefer prepared bid-package ZIP; fall back to real-expediente ZIP when not prepared."""
    try:
        content, filename = await _bid_svc(db, user).download_expediente(opportunity_id)
    except ValueError:
        try:
            builder = _real_expediente_builder(db, user)
            opp, pkg = await builder._load_package(opportunity_id)
            content, filename = builder.get_download_zip(opp, pkg)
            await builder.log_download(opportunity_id, kind="zip", filename=filename)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": build_content_disposition("attachment", filename)},
    )


@router.post(
    "/opportunities/{opportunity_id}/real-expediente/generate",
    response_model=RealExpedienteGenerateResponse,
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_VIEW,
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
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_VIEW,
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


@router.get("/opportunities/{opportunity_id}/expediente", dependencies=DGCP_VIEW)
async def get_expediente_alias(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    """Alias canónico → expediente/dashboard (evita 404 en clientes legacy)."""
    try:
        return await _bid_svc(db, user).get_expediente_dashboard(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/{opportunity_id}/expediente/status", dependencies=DGCP_VIEW)
async def get_expediente_status_alias(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    """Alias canónico → real-expediente/status."""
    try:
        return await _real_expediente_builder(db, user).get_status(opportunity_id)
    except ValueError as exc:
        raise _http_error_for_dgcp_value_error(exc) from exc


@router.get("/opportunities/{opportunity_id}/adjudicaciones", dependencies=DGCP_VIEW)
async def get_adjudicaciones_alias(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    """Alias canónico → historical-similar (cached)."""
    ctx = require_tenant_context()
    service = DGCPHistoricalSimilarSearchService(db, ctx.tenant_id)
    try:
        return await service.get_cached(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/{opportunity_id}/real-expediente/manifest", dependencies=DGCP_VIEW)
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


@router.get("/opportunities/{opportunity_id}/real-expediente/report", dependencies=DGCP_VIEW)
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
        headers={"Content-Disposition": build_content_disposition("attachment", "reporte_preparacion.pdf")},
    )


@router.get("/opportunities/{opportunity_id}/real-expediente/download", dependencies=DGCP_VIEW)
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
        headers={"Content-Disposition": build_content_disposition("attachment", filename)},
    )


@router.post(
    "/opportunities/{opportunity_id}/real-expediente/mark-ready-review",
    response_model=RealExpedienteStatusResponse,
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_VIEW,
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
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_MUTATE,
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
    dependencies=DGCP_VIEW,
)
async def list_finalization_records(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> list[DocumentFinalizationRecordResponse]:
    return await _finalization_engine(db, user).list_records(opportunity_id)


@router.get("/opportunities/{opportunity_id}/finalization/{record_id}/file", dependencies=DGCP_VIEW)
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
        headers={"Content-Disposition": build_content_disposition("attachment", filename)},
    )


@router.get(
    "/opportunities/{opportunity_id}/history",
    response_model=list[DGCPOpportunityHistoryResponse],
    dependencies=DGCP_VIEW,
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


@router.post("/reclassify", dependencies=DGCP_MUTATE)
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


@router.post("/sync", response_model=DGCPSyncJobResponse, status_code=202, dependencies=DGCP_MUTATE)
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


@router.get("/sync/jobs", response_model=list[DGCPSyncJobResponse], dependencies=DGCP_VIEW)
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


@router.get("/sync/schedule", response_model=DGCPSyncScheduleResponse, dependencies=DGCP_VIEW)
async def get_sync_schedule(
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
) -> DGCPSyncScheduleResponse:
    ctx = require_tenant_context()
    sync = DGCPSyncService(db)
    schedule = await sync.get_or_create_schedule(ctx.tenant_id)
    return DGCPSyncScheduleResponse.model_validate(schedule)


@router.put("/sync/schedule", response_model=DGCPSyncScheduleResponse, dependencies=DGCP_MUTATE)
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


@router.get("/audit", response_model=list[DGCPAuditLogResponse], dependencies=DGCP_VIEW)
async def list_dgcp_audit(
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[DGCPAuditLogResponse]:
    ctx = require_tenant_context()
    service = DGCPService(db)
    return await service.list_audit_logs(ctx.tenant_id, limit=limit)


@router.get(
    "/historical-awards/stats",
    response_model=DGCPHistoricalIndexStatsResponse,
    dependencies=DGCP_VIEW,
)
async def get_historical_awards_stats(
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
    institution: str | None = Query(None),
    institution_code: str | None = Query(None),
) -> DGCPHistoricalIndexStatsResponse:
    ctx = require_tenant_context()
    service = DGCPHistoricalAwardsService(db, ctx.tenant_id)
    stats = await service.get_index_stats(
        institution_name=institution,
        institution_code=institution_code,
    )
    return DGCPHistoricalIndexStatsResponse(**stats)


@router.post(
    "/historical-awards/index",
    response_model=DGCPHistoricalIndexResponse,
    dependencies=DGCP_MUTATE,
)
async def run_historical_awards_index(
    data: DGCPHistoricalIndexRequest,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    __: TenantCtx,
    institution_code: str | int | None = Query(None),
    institution_name: str | None = Query(None),
) -> DGCPHistoricalIndexResponse:
    ctx = require_tenant_context()
    service = DGCPHistoricalAwardsService(db, ctx.tenant_id)
    result = await service.run_index(
        max_pages=data.max_pages,
        page_size=data.page_size,
        institution_code=institution_code,
        institution_name=institution_name,
    )
    audit = AuditService(db)
    await audit.log(
        action="dgcp.historical_awards.index",
        tenant_id=ctx.tenant_id,
        user_id=user.id,
        resource_type="dgcp_historical_awards",
        resource_id=None,
        details={
            "institution_code": institution_code,
            "institution_name": institution_name,
            "items_indexed": result.items_indexed,
            "status": result.status,
        },
        request=request,
    )
    return result


@router.get(
    "/opportunities/{opportunity_id}/historical-similar",
    response_model=DGCPHistoricalSimilarResponse,
    dependencies=DGCP_VIEW,
)
@router.get(
    "/processes/{opportunity_id}/historical-similar",
    response_model=DGCPHistoricalSimilarResponse,
    dependencies=DGCP_VIEW,
)
async def get_historical_similar_cached(
    opportunity_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    __: TenantCtx,
) -> DGCPHistoricalSimilarResponse:
    ctx = require_tenant_context()
    service = DGCPHistoricalSimilarSearchService(db, ctx.tenant_id)
    try:
        return await service.get_cached(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/historical-similar/search",
    response_model=DGCPHistoricalSimilarResponse,
    dependencies=DGCP_MUTATE,
)
@router.post(
    "/processes/{opportunity_id}/historical-similar/search",
    response_model=DGCPHistoricalSimilarResponse,
    dependencies=DGCP_MUTATE,
)
async def search_historical_similar(
    opportunity_id: uuid.UUID,
    data: DGCPHistoricalSimilarSearchRequest,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    __: TenantCtx,
) -> DGCPHistoricalSimilarResponse:
    ctx = require_tenant_context()
    user_id = user.id
    service = DGCPHistoricalSimilarSearchService(db, ctx.tenant_id)
    try:
        result = await service.search(opportunity_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit = AuditService(db)
    await audit.log(
        action="dgcp.historical_similar.search",
        tenant_id=ctx.tenant_id,
        user_id=user_id,
        resource_type="dgcp_opportunity",
        resource_id=opportunity_id,
        details={
            "refresh": data.refresh,
            "matches": result.total_matches,
            "pages_scanned": result.pages_scanned,
            "cached": result.cached,
        },
        request=request,
    )
    return result


@router.get(
    "/opportunities/{opportunity_id}/expediente/dashboard",
    dependencies=DGCP_VIEW,
)
async def get_expediente_dashboard(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    """Dashboard del expediente vivo — KPIs + secciones + requisitos con estado UX."""
    try:
        return await _bid_svc(db, user).get_expediente_dashboard(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _enterprise_svc(db, user) -> "DGCPExpedienteEnterpriseService":
    from app.services.dgcp_expediente_enterprise_service import DGCPExpedienteEnterpriseService

    ctx = require_tenant_context()
    return DGCPExpedienteEnterpriseService(db, ctx.tenant_id, user_id=user.id)


@router.get(
    "/opportunities/{opportunity_id}/expediente/compliance-matrix",
    dependencies=DGCP_VIEW,
)
async def get_compliance_matrix(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _enterprise_svc(db, user).get_compliance_matrix(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/opportunities/{opportunity_id}/expediente/compliance-matrix/excel",
    dependencies=DGCP_VIEW,
)
async def export_compliance_matrix_excel(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        content, filename = await _enterprise_svc(db, user).export_compliance_matrix_excel(
            opportunity_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": build_content_disposition("attachment", filename)},
    )


@router.get(
    "/opportunities/{opportunity_id}/expediente/compliance-matrix/pdf",
    dependencies=DGCP_VIEW,
)
async def export_compliance_matrix_pdf(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        content, filename = await _enterprise_svc(db, user).export_compliance_matrix_pdf(
            opportunity_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": build_content_disposition("attachment", filename)},
    )


@router.get(
    "/opportunities/{opportunity_id}/checklist/{item_id}/evidence",
    dependencies=DGCP_VIEW,
)
async def get_requirement_evidence(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _enterprise_svc(db, user).get_requirement_evidence(opportunity_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/checklist/{item_id}/ask",
    dependencies=DGCP_VIEW,
)
async def ask_requirement_ai(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    question: str = Query(..., min_length=2, max_length=2000),
):
    try:
        return await _enterprise_svc(db, user).ask_requirement_ai(
            opportunity_id, item_id, question
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/opportunities/{opportunity_id}/expediente/score",
    dependencies=DGCP_VIEW,
)
async def get_expediente_score(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _enterprise_svc(db, user).get_expediente_score(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/opportunities/{opportunity_id}/expediente/preview",
    dependencies=DGCP_VIEW,
)
async def get_expediente_preview(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    try:
        return await _enterprise_svc(db, user).get_expediente_preview(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/opportunities/{opportunity_id}/expediente/preview/file",
    dependencies=DGCP_VIEW,
)
async def preview_expediente_file(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    path: Annotated[str, Query(min_length=1)],
):
    try:
        content, mime, filename = await _enterprise_svc(db, user).read_preview_file(
            opportunity_id, path
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": build_content_disposition("inline", filename)},
    )


def _bid_copilot_svc(db, user) -> "DGCPBidCopilotService":
    from app.services.dgcp_bid_copilot_service import DGCPBidCopilotService

    ctx = require_tenant_context()
    return DGCPBidCopilotService(db, ctx.tenant_id, user_id=user.id)


@router.get(
    "/opportunities/{opportunity_id}/bid-copilot",
    dependencies=DGCP_VIEW,
)
async def get_bid_copilot(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    """Bid Copilot Enterprise: competitividad, score, plan, riesgos y resumen."""
    try:
        return await _bid_copilot_svc(db, user).get_copilot(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/bid-copilot/simulate-committee",
    dependencies=DGCP_VIEW,
)
async def simulate_bid_committee(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    """Simula evaluación del comité con base en el expediente real."""
    try:
        return await _bid_copilot_svc(db, user).simulate_committee(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/bid-copilot/executive-dashboard",
    dependencies=DGCP_VIEW,
)
async def get_bid_copilot_executive_dashboard(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    """Dashboard gerencial multi-expediente (DEV)."""
    return await _bid_copilot_svc(db, user).get_executive_dashboard()


@router.post(
    "/opportunities/{opportunity_id}/expediente/validate",
    dependencies=DGCP_MUTATE,
)
async def validate_expediente_final(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
):
    """Validación final IA del expediente antes de exportar."""
    try:
        return await _bid_svc(db, user).validate_expediente_final(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/checklist/{item_id}/assign",
    dependencies=DGCP_MUTATE,
)
async def assign_checklist_item(
    opportunity_id: uuid.UUID,
    item_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    assignee: str = Query(..., min_length=1),
    due_date: date | None = None,
):
    try:
        return await _bid_svc(db, user).assign_checklist_item(
            opportunity_id,
            item_id,
            assignee=assignee,
            due_date=due_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/opportunities/{opportunity_id}/intelligence",
    response_model=DGCPIntelligenceResponse,
    dependencies=DGCP_VIEW,
)
async def get_opportunity_intelligence(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    refresh: bool = Query(False),
) -> DGCPIntelligenceResponse:
    ctx = require_tenant_context()
    svc = DGCPIntelligenceService(db, ctx.tenant_id, user_id=user.id)
    opp = await svc._get_opportunity(opportunity_id)
    data = opp.jaios_intelligence or {}
    if refresh:
        data = await svc.analyze_opportunity(opportunity_id, persist=True)
        await db.commit()
    elif not intelligence_payload_ready(data):
        return DGCPIntelligenceResponse(
            premium_score=0,
            probability_band="baja",
            score_factors={},
            participation={
                "recommendation": "revisar",
                "reason": "Sin análisis. Use «Actualizar análisis» para calcular.",
            },
            executive={"summary": ""},
            expediente={
                "traffic_light": "yellow",
                "stage_label": "Sin análisis",
                "completeness_pct": 0,
                "checklist": [],
            },
            recommendations={},
            analyzed_at=None,
        )
    return DGCPIntelligenceResponse.model_validate(data)


@router.post(
    "/opportunities/{opportunity_id}/intelligence/analyze",
    response_model=DGCPIntelligenceResponse,
    dependencies=DGCP_MUTATE,
)
async def analyze_opportunity_intelligence(
    opportunity_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> DGCPIntelligenceResponse:
    ctx = require_tenant_context()
    svc = DGCPIntelligenceService(db, ctx.tenant_id, user_id=user.id)
    data = await svc.analyze_opportunity(opportunity_id, persist=True)
    await db.commit()
    return DGCPIntelligenceResponse.model_validate(data)


@router.post("/intelligence/analyze-all", dependencies=DGCP_MUTATE)
async def analyze_all_opportunities_intelligence(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    ctx = require_tenant_context()
    svc = DGCPIntelligenceService(db, ctx.tenant_id, user_id=user.id)
    result = await svc.analyze_tenant_opportunities(limit=limit)
    return result


@router.get("/commercial-memory", response_model=CommercialMemoryResponse, dependencies=DGCP_VIEW)
async def query_commercial_memory(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    q: str = Query(..., min_length=2),
) -> CommercialMemoryResponse:
    ctx = require_tenant_context()
    result = await CommercialMemoryService(db, ctx.tenant_id).query(q)
    return CommercialMemoryResponse.model_validate(result)


@router.post("/quotation-intelligence", dependencies=DGCP_MUTATE)
async def analyze_quotation_email(
    payload: QuotationIntelligenceRequest,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> dict:
    ctx = require_tenant_context()
    return await QuotationIntelligenceService(db, ctx.tenant_id).analyze_email(
        subject=payload.subject,
        body=payload.body,
        client_hint=payload.client_hint,
        products_hint=payload.products_hint,
    )


@router.post("/agents/{agent_name}/run", response_model=AgentRunResponse, dependencies=DGCP_MUTATE)
async def run_jaios_agent(
    agent_name: str,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> AgentRunResponse:
    ctx = require_tenant_context()
    result = await run_agent(agent_name, ctx.tenant_id, user_id=user.id)
    return AgentRunResponse.model_validate(result)


@router.post("/agents/run-all", dependencies=DGCP_MUTATE)
async def run_all_jaios_agents(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
) -> list[dict]:
    ctx = require_tenant_context()
    return await run_all_agents_for_tenant(ctx.tenant_id, user_id=user.id)