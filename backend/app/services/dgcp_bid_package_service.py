"""DGCP Bid Package — análisis, checklist, expediente y matching (Fase 7.1)."""

from __future__ import annotations

import hashlib
import logging
import uuid

logger = logging.getLogger(__name__)
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.dgcp_bid_package import DGCPBidPackage
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.dgcp_process_document import DGCPProcessDocument
from app.models.knowledge import KnowledgeAsset
from app.models.task import Task
from app.models.user import User
from app.schemas.dgcp_bid import (
    DGCPAnalyzeResponse,
    DGCPAssociateDocumentRequest,
    DGCPAssociateDocumentResponse,
    DGCPLinkM365DocumentRequest,
    DGCPBidAlertResponse,
    DGCPBidPackageResponse,
    DGCPBidPackageStatusResponse,
    DGCPChecklistItem,
    DGCPChecklistResponse,
    DGCPDocumentMatch,
    DGCPDocumentMatchesResponse,
    DGCPDocumentPreviewResponse,
    DGCPExpedientePrepareResponse,
    DGCPFormAutofillPreviewResponse,
    DGCPFormGenerateResponse,
    DGCPFormPreviewField,
    DGCPFormPreviewResponse,
    DGCPManualValidationRequest,
    DGCPManualValidationResponse,
    DGCPProcessDocumentsResponse,
    DGCPRequirementEvidence,
    DGCPRequirementItem,
    DGCPRequirementsResponse,
    DGCPUserInputRequest,
)
from app.schemas.tasks import TaskCreateRequest
from app.services.audit_service import AuditService
from app.services.bid_preparation_engine import BidPreparationEngine
from app.services.dgcp_compliance_engine import (
    ACTION_BY_STATUS as COMPLIANCE_ACTION_BY_STATUS,
    COMPLIANT_STATUSES,
    DGCPComplianceEngine,
    OFFICIAL_KNOWLEDGE_FOLDERS,
    REVIEW_STATUSES,
)
from app.services.dgcp_attachment_ingestion_service import DGCPAttachmentIngestionService
from app.services.dgcp_bid_alert_service import DGCPBidAlertService
from app.services.dgcp_expediente_service import DGCPExpedienteService
from app.services.dgcp_form_autofill_service import DGCPFormAutofillService
from app.services.dgcp_process_storage_service import DGCPProcessStorageService
from app.services.dgcp_smart_matching_engine import DGCPSmartMatchingEngine
from app.services.dgcp_requirements_extractor import DGCPRequirementsExtractor, ExtractedRequirement
from app.services.document_extraction_service import DocumentExtractionService
from app.services.document_completion_service import DocumentCompletionService
from app.services.document_service import DocumentService
from app.services.knowledge_source_provider import get_knowledge_source_provider
from app.services.task_service import TaskService

ACTIVE_TASK_STATUSES = frozenset({"pendiente", "en_proceso"})
OPERATIONAL_INTEREST_STATUSES = frozenset({
    "interested",
    "preparing",
    "to_bid",
    "pending_documents",
    "ready_to_submit",
    "submitted",
    "under_evaluation",
    "suspended",
    "awarded",
    "won",
    "lost",
    "discarded",
    "cancelled",
    "to_review",
    "review",
    "analyzing",
    "qualified",
})
EXPEDIENTE_TRACKING_STATUSES = frozenset({
    "interested",
    "preparing",
    "to_bid",
    "pending_documents",
    "ready_to_submit",
    "submitted",
    "under_evaluation",
    "awarded",
    "won",
    "lost",
})

# Estados de producto del expediente vivo (UI).
REQUIREMENT_UX_STATUS_MAP: dict[str, str] = {
    "pendiente": "Pendiente",
    "encontrado": "En proceso",
    "encontrado_vigente": "Aprobado",
    "encontrado_por_vencer": "En proceso",
    "requiere_actualizacion": "En proceso",
    "requiere_revision": "Revisado",
    "requiere_completado": "En proceso",
    "plantilla_disponible": "En proceso",
    "validado_manual": "Aprobado",
    "finalizado": "Completado",
    "pdf_final_generado": "Completado",
    "vencido": "Rechazado",
    "encontrado_vencido": "Rechazado",
    "incompleto": "Pendiente",
    "completar": "En proceso",
    "no_cumple": "Rechazado",
    "cumple": "Aprobado",
    "faltante": "Pendiente",
}

SNCC_FORM_MAP = {
    "sncc_f033": "SNCC.F033",
    "sncc_f034": "SNCC.F034",
    "sncc_f042": "SNCC.F042",
    "sncc_f047": "SNCC.F047",
}

ACTION_BY_STATUS = {
    "pendiente": "Solicitar o registrar documento",
    "vencido": "Renovar documento antes del cierre",
    "incompleto": "Completar campos faltantes",
    "completar": "Revisar vista previa y completar formulario",
    "requiere_completado": "Completar formulario SNCC con datos corporativos",
    "requiere_actualizacion": "Actualizar documento próximo a vencer",
    "plantilla_disponible": "Usar plantilla corporativa disponible",
    "encontrado": "Validar vigencia y adjuntar al expediente",
}


class DGCPAlreadyAnalyzedError(ValueError):
    """Expediente ya analizado — requiere force=true para reanalizar."""

    def __init__(self, analyzed_at: datetime):
        self.analyzed_at = analyzed_at
        super().__init__(
            "Este expediente ya fue analizado. ¿Deseas reanalizar y actualizar resultados?"
        )


class DGCPBidPackageService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.extractor = DGCPRequirementsExtractor()
        self.matcher = DGCPSmartMatchingEngine(db, tenant_id)
        self.compliance = DGCPComplianceEngine()
        self.preparation = BidPreparationEngine()
        self.ingestion = DGCPAttachmentIngestionService(db, tenant_id, user_id=user_id)
        self.alerts_svc = DGCPBidAlertService()
        self.forms = DGCPFormAutofillService(db, tenant_id, user_id=user_id)
        self.expediente = DGCPExpedienteService(db, tenant_id, user_id=user_id)
        self.audit = AuditService(db)

    @staticmethod
    def _deep_copy_checklist(checklist: list | None) -> list[dict]:
        return [dict(item) for item in (checklist or [])]

    def _operational_interest_active(self, opportunity: DGCPOpportunity) -> bool:
        return opportunity.status in OPERATIONAL_INTEREST_STATUSES

    def _require_operational_interest(self, opportunity: DGCPOpportunity) -> None:
        if not self._operational_interest_active(opportunity):
            raise ValueError(
                "Marque «Mostrar interés» en esta licitación antes de analizar, validar, agregar notas o crear tareas"
            )

    def _expediente_tracking_active(
        self,
        opportunity: DGCPOpportunity,
        pkg: DGCPBidPackage | None,
    ) -> bool:
        if pkg and pkg.expediente_path:
            return True
        return opportunity.status in EXPEDIENTE_TRACKING_STATUSES

    def _effective_expediente_status(
        self,
        opportunity: DGCPOpportunity,
        checklist: list[dict],
        preparation_pct: float,
        pkg: DGCPBidPackage | None,
    ) -> str:
        if not self._expediente_tracking_active(opportunity, pkg):
            return "sin_preparar"
        if pkg and pkg.expediente_path:
            return pkg.expediente_status or "expediente_en_preparacion"
        return self.compliance.compute_expediente_status(checklist, preparation_pct)

    async def _append_note_history(
        self,
        target: dict,
        note: str,
        *,
        action: str,
    ) -> None:
        if not self.user_id:
            return
        user_name = await self._user_display_name(self.user_id)
        history = list(target.get("note_history") or [])
        entry = {
            "note": note,
            "author_id": str(self.user_id),
            "author": user_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
        }
        history.append(entry)
        target["note_history"] = history
        if note.strip():
            target["notes"] = note.strip()

    async def _get_opportunity(self, opportunity_id: uuid.UUID) -> DGCPOpportunity | None:
        result = await self.db.execute(
            select(DGCPOpportunity).where(
                DGCPOpportunity.id == opportunity_id,
                DGCPOpportunity.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_package(self, opportunity_id: uuid.UUID) -> DGCPBidPackage | None:
        result = await self.db.execute(
            select(DGCPBidPackage).where(
                DGCPBidPackage.opportunity_id == opportunity_id,
                DGCPBidPackage.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _related_document_text(self, opportunity: DGCPOpportunity) -> str:
        doc_svc = DocumentService(self.db, self.tenant_id)
        hits = await doc_svc.search_content(opportunity.code, limit=5)
        if not hits.hits and opportunity.title:
            hits = await doc_svc.search_content(opportunity.title[:40], limit=3)
        return " ".join(h.snippet for h in hits.hits)

    def _req_to_schema(self, req: ExtractedRequirement) -> DGCPRequirementItem:
        evidence = [
            DGCPRequirementEvidence(
                requirement_key=e.requirement_key,
                documento_origen=e.documento_origen,
                pagina=e.pagina,
                seccion=e.seccion,
                fragmento=e.fragmento,
                confianza=e.confianza,
                process_document_id=uuid.UUID(e.process_document_id) if e.process_document_id else None,
            )
            for e in req.evidence
        ]
        return DGCPRequirementItem(
            key=req.key,
            label=req.label,
            tipo=req.tipo,
            mandatory=req.mandatory,
            subsanable=req.subsanable,
            source=req.source,
            matched_text=req.matched_text,
            evidence=evidence,
        )

    def _build_requirements_response(
        self,
        opportunity: DGCPOpportunity,
        extraction,
        analyzed_at: datetime | None,
    ) -> DGCPRequirementsResponse:
        return DGCPRequirementsResponse(
            opportunity_id=opportunity.id,
            opportunity_code=opportunity.code,
            opportunity_title=opportunity.title,
            analyzed_at=analyzed_at,
            technical=[self._req_to_schema(r) for r in extraction.technical],
            legal=[self._req_to_schema(r) for r in extraction.legal],
            financial=[self._req_to_schema(r) for r in extraction.financial],
            administrative=[self._req_to_schema(r) for r in extraction.administrative],
            mandatory_documents=[self._req_to_schema(r) for r in extraction.mandatory_documents],
            subsanable_documents=[self._req_to_schema(r) for r in extraction.subsanable_documents],
            critical_dates=extraction.critical_dates[:10],
            guarantees=extraction.guarantees,
            samples=extraction.samples,
            sncc_forms=extraction.sncc_forms,
            certifications=extraction.certifications,
        )

    def _build_checklist(
        self,
        requirements: list[ExtractedRequirement],
        matches: list[dict],
        existing: list[dict] | None = None,
    ) -> list[dict]:
        match_by_key = {m["requirement_key"]: m for m in matches}
        existing_by_key = {item["requirement_key"]: item for item in (existing or [])}
        items: list[dict] = []

        for req in requirements:
            m = match_by_key.get(req.key, {})
            prev = existing_by_key.get(req.key, {})
            status = m.get("status", "pendiente")
            item_id = prev.get("id") or str(uuid.uuid4())
            risk = None
            if status == "vencido":
                risk = "Documento vencido — riesgo de descalificación"
            elif status == "pendiente" and req.mandatory:
                risk = "Documento obligatorio no encontrado"
            elif status == "completar":
                risk = "Formulario pendiente de completar"
            elif status == "requiere_actualizacion":
                risk = "Documento próximo a vencer"
            elif status == "plantilla_disponible":
                risk = "Plantilla disponible — requiere completado"

            items.append({
                "id": item_id,
                "requirement_key": req.key,
                "requirement": req.label,
                "tipo": req.tipo,
                "mandatory": req.mandatory,
                "status": status,
                "document_id": m.get("document_id"),
                "document_title": m.get("document_title"),
                "valid_until": m.get("valid_until"),
                "risk": risk,
                "recommended_action": ACTION_BY_STATUS.get(status),
                "assignee": prev.get("assignee"),
                "task_id": prev.get("task_id"),
                "completable": status in ("completar", "requiere_completado", "plantilla_disponible") or req.key.startswith("sncc_"),
                "form_type": SNCC_FORM_MAP.get(req.key),
            })
        return items

    def _build_bid_package(
        self,
        opportunity: DGCPOpportunity,
        checklist: list[dict],
        analyzed_at: datetime | None,
    ) -> DGCPBidPackageResponse:
        mandatory = [c for c in checklist if c.get("mandatory")]
        total = len(mandatory) or len(checklist) or 1
        found = sum(1 for c in checklist if c.get("status") == "encontrado")
        pending = sum(1 for c in checklist if c.get("status") == "pendiente")
        expired = sum(1 for c in checklist if c.get("status") == "vencido")
        to_complete = sum(1 for c in checklist if c.get("status") in ("completar", "incompleto"))

        ready = found + sum(
            1 for c in checklist
            if c.get("status") == "completar" and c.get("document_id")
        )
        pct = round((ready / total) * 100, 1) if total else 0.0

        available = [c["requirement"] for c in checklist if c.get("status") == "encontrado"]
        missing = [c["requirement"] for c in checklist if c.get("status") == "pendiente"]
        expired_list = [c["requirement"] for c in checklist if c.get("status") == "vencido"]
        complete_list = [
            c["requirement"] for c in checklist if c.get("status") in ("completar", "incompleto")
        ]

        tasks = []
        if pending:
            tasks.append(f"Solicitar {pending} documento(s) faltante(s)")
        if expired:
            tasks.append(f"Renovar {expired} documento(s) vencido(s)")
        if to_complete:
            tasks.append(f"Completar {to_complete} formulario(s) SNCC")

        return DGCPBidPackageResponse(
            opportunity_id=opportunity.id,
            opportunity_code=opportunity.code,
            preparation_pct=pct,
            found_documents=found,
            pending_documents=pending,
            expired_documents=expired,
            forms_to_complete=to_complete,
            recommended_tasks=tasks,
            available=available,
            missing=missing,
            expired=expired_list,
            to_complete=complete_list,
            analyzed_at=analyzed_at,
        )

    def _build_risks(
        self,
        checklist: list[dict],
        opportunity: DGCPOpportunity,
        analysis_warnings: list[str] | None = None,
    ) -> list[dict]:
        risks: list[dict] = []
        for item in checklist:
            if item.get("risk"):
                risks.append({
                    "nivel": "alto" if item.get("status") in ("encontrado_vencido", "faltante") else "medio",
                    "descripcion": f"{item['requirement']}: {item['risk']}",
                })
        non_compliant = sum(
            1 for c in checklist
            if c.get("mandatory", True) and c.get("status") not in COMPLIANT_STATUSES
        )
        if non_compliant:
            risks.insert(0, {
                "nivel": "alto",
                "descripcion": (
                    f"Expediente incompleto — {non_compliant} requisito(s) obligatorio(s) "
                    "sin cumplir (faltantes, vencidos, por completar o sin validar)."
                ),
            })
        for warning in analysis_warnings or []:
            risks.append({"nivel": "medio", "descripcion": warning})
        if opportunity.deadline:
            days = (opportunity.deadline - date.today()).days
            if days <= 7:
                risks.append({
                    "nivel": "alto",
                    "descripcion": f"Cierre del proceso en {days} día(s)",
                })
        return risks

    async def _persist_analysis(
        self,
        opportunity_id: uuid.UUID,
        *,
        requirements: DGCPRequirementsResponse,
        checklist: list[dict],
        bid: DGCPBidPackageResponse,
        matches: list[dict],
        risks: list[dict],
        analyzed_at: datetime,
        process_documents: list[dict] | None = None,
        alerts: list[dict] | None = None,
        requirement_evidence: list[dict] | None = None,
        expediente_status: str | None = None,
        hermes_analysis: dict | None = None,
        pliego_analysis: dict | None = None,
    ) -> DGCPBidPackage:
        existing_pkg = await self._get_package(opportunity_id)
        pkg = existing_pkg or DGCPBidPackage(
            tenant_id=self.tenant_id,
            opportunity_id=opportunity_id,
        )
        pkg.requirements = requirements.model_dump(mode="json")
        pkg.checklist = checklist
        pkg.bid_package = bid.model_dump(mode="json")
        pkg.document_matches = matches
        pkg.requirement_risks = risks
        pkg.analyzed_at = analyzed_at
        if process_documents is not None:
            pkg.process_documents_summary = process_documents
        if alerts is not None:
            pkg.alerts = alerts
        if requirement_evidence is not None:
            pkg.requirement_evidence = requirement_evidence
        if expediente_status:
            pkg.expediente_status = expediente_status
        if hermes_analysis:
            manifest = dict(pkg.manifest or {})
            manifest["hermes_document_analysis"] = hermes_analysis
            pkg.manifest = manifest
        if pliego_analysis:
            manifest = dict(pkg.manifest or {})
            manifest["pliego_analysis"] = pliego_analysis
            pkg.manifest = manifest
        from app.services.dgcp_expediente_sync_service import DGCPExpedienteSyncService

        DGCPExpedienteSyncService.sync_package(
            pkg,
            checklist=checklist,
            preparation_pct=float(bid.preparation_pct or 0),
            expediente_status=expediente_status,
        )
        if not existing_pkg:
            self.db.add(pkg)
        try:
            await self.db.commit()
            await self.db.refresh(pkg)
            return pkg
        except IntegrityError:
            await self.db.rollback()
            winner = await self._get_package(opportunity_id)
            if not winner:
                raise
            winner.requirements = requirements.model_dump(mode="json")
            winner.checklist = checklist
            winner.bid_package = bid.model_dump(mode="json")
            winner.document_matches = matches
            winner.requirement_risks = risks
            winner.analyzed_at = analyzed_at
            if process_documents is not None:
                winner.process_documents_summary = process_documents
            if alerts is not None:
                winner.alerts = alerts
            if requirement_evidence is not None:
                winner.requirement_evidence = requirement_evidence
            if expediente_status:
                winner.expediente_status = expediente_status
            if hermes_analysis:
                manifest = dict(winner.manifest or {})
                manifest["hermes_document_analysis"] = hermes_analysis
                winner.manifest = manifest
            if pliego_analysis:
                manifest = dict(winner.manifest or {})
                manifest["pliego_analysis"] = pliego_analysis
                winner.manifest = manifest
            from app.services.dgcp_expediente_sync_service import DGCPExpedienteSyncService

            DGCPExpedienteSyncService.sync_package(
                winner,
                checklist=checklist,
                preparation_pct=float(bid.preparation_pct or 0),
                expediente_status=expediente_status,
            )
            await self.db.commit()
            await self.db.refresh(winner)
            return winner

    async def analyze(
        self,
        opportunity_id: uuid.UUID,
        *,
        force: bool = False,
        progress=None,
    ) -> DGCPAnalyzeResponse:
        async def _stage(stage: str, message: str | None = None, pct: int | None = None) -> None:
            if progress:
                await progress(stage, message, pct)

        await _stage("preparing", "Validando licitación e interés operativo")
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)

        existing_pkg = await self._get_package(opportunity_id)
        if existing_pkg and existing_pkg.analyzed_at and not force:
            raise DGCPAlreadyAnalyzedError(existing_pkg.analyzed_at)

        await _stage("reading_documents", "Ingestando y leyendo documentos del proceso")
        process_docs_summary = await self.ingestion.ingest(opportunity)
        process_corpus, process_docs = await self.ingestion.build_extraction_corpus(opportunity_id)
        related = await self._related_document_text(opportunity)
        extraction = self.extractor.extract(
            opportunity,
            related_text=related,
            process_corpus=process_corpus,
            process_documents=process_docs,
        )
        from app.services.dgcp_hermes_document_analysis_service import DGCPHermesDocumentAnalysisService

        await _stage("hermes", "Análisis documental Hermes")
        hermes_meta: dict = {}
        if process_corpus.strip():
            extraction, hermes_meta = await DGCPHermesDocumentAnalysisService().enrich_extraction(
                opportunity,
                extraction,
                process_corpus=process_corpus,
                process_documents=process_docs,
            )
        elif DGCPHermesDocumentAnalysisService.enabled():
            hermes_meta = {
                "status": "skipped",
                "reason": "no_process_corpus",
                "fallback_used": True,
                "message": "Sin texto de pliego indexado. Ingeste documentos del proceso con texto extraíble.",
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }
        if hermes_meta.get("status") == "failed":
            await _stage("hermes", "Hermes no disponible — extracción heurística", 45)

        await _stage("checklist", "Extrayendo requisitos y generando checklist")
        evidence_records = []
        all_reqs = self.compliance.collect_all_requirements(extraction)
        for req in all_reqs:
            for ev in req.evidence:
                evidence_records.append({
                    "requirement_key": ev.requirement_key,
                    "documento_origen": ev.documento_origen,
                    "pagina": ev.pagina,
                    "seccion": ev.seccion,
                    "fragmento": ev.fragmento,
                    "confianza": ev.confianza,
                    "process_document_id": ev.process_document_id,
                })

        company = opportunity.company or "justech"
        self.matcher = DGCPSmartMatchingEngine(self.db, self.tenant_id, company_key=company)
        matches = await self.matcher.match_all(all_reqs)
        existing_pkg = await self._get_package(opportunity_id)
        prev_checklist = existing_pkg.checklist if existing_pkg else []
        checklist = self.compliance.build_checklist(
            all_reqs, matches, prev_checklist, sncc_form_map=SNCC_FORM_MAP
        )
        from app.services.dgcp_expediente_event_service import DGCPExpedienteEventService

        checklist = DGCPExpedienteEventService.enrich_checklist_notes_from_hermes(checklist, hermes_meta)
        now = datetime.now(timezone.utc)
        bid = self.compliance.build_bid_package(opportunity, checklist, analyzed_at=now)
        bid = self._enrich_bid_with_area_pct(bid, existing_pkg or await self._get_package(opportunity_id), checklist)
        analysis_warnings = self.compliance.build_analysis_warnings(process_docs_summary, extraction)
        if hermes_meta.get("status") == "failed":
            analysis_warnings.append(
                "Análisis documental Hermes no disponible; se aplicó extracción heurística."
            )
        elif hermes_meta.get("status") == "completed":
            analysis_warnings.append(
                f"Análisis documental Hermes aplicado (confianza {int((hermes_meta.get('confidence') or 0) * 100)}%)."
            )
        risks = self._build_risks(checklist, opportunity, analysis_warnings)
        for hr in hermes_meta.get("risks") or []:
            if isinstance(hr, dict) and hr.get("descripcion"):
                risks.append(hr)
            elif isinstance(hr, str) and hr.strip():
                risks.append({"nivel": "medio", "descripcion": hr.strip()})
        if evidence_records:
            hermes_meta["evidence"] = evidence_records[:100]
        alerts = self.alerts_svc.build_alerts(
            opportunity, checklist, matches, analysis_warnings=analysis_warnings
        )
        requirements = self._build_requirements_response(opportunity, extraction, now)
        expediente_status = self._effective_expediente_status(
            opportunity, checklist, bid.preparation_pct, existing_pkg
        )

        await _stage("pliego_deep", "Análisis profundo del pliego (29 campos)")
        pliego_payload: dict | None = None
        try:
            from app.services.dgcp_pliego_deep_analysis_service import DGCPPliegoDeepAnalysisService

            pliego_svc = DGCPPliegoDeepAnalysisService(self.db, self.tenant_id, self.user_id)
            all_process_docs = await self.ingestion.load_process_documents(opportunity_id)
            pliego_result = await pliego_svc.run(
                opportunity,
                process_documents=all_process_docs or process_docs,
                process_corpus=process_corpus,
                extraction=extraction,
                hermes_meta=hermes_meta,
                requirement_evidence=evidence_records,
                checklist=checklist,
                risks=risks,
                force=force,
            )
            pliego_payload = pliego_result.model_dump(mode="json")
            if pliego_result.status.value == "partial":
                analysis_warnings.append(
                    "Análisis profundo del pliego quedó parcial; revise etapas fallidas."
                )
            elif pliego_result.meta.failed_stages:
                analysis_warnings.append(
                    "Análisis profundo completó con advertencias en etapas: "
                    + ", ".join(pliego_result.meta.failed_stages)
                )
        except Exception as exc:
            logger.exception("pliego deep analysis failed opportunity=%s", opportunity_id)
            analysis_warnings.append(
                f"Análisis profundo del pliego no disponible: {str(exc)[:180]}"
            )

        await self._persist_analysis(
            opportunity_id,
            requirements=requirements,
            checklist=checklist,
            bid=bid,
            matches=matches,
            risks=risks,
            analyzed_at=now,
            process_documents=process_docs_summary,
            alerts=alerts,
            requirement_evidence=evidence_records,
            expediente_status=expediente_status,
            hermes_analysis=hermes_meta or None,
            pliego_analysis=pliego_payload,
        )

        await _stage("expediente", "Actualizando fichas, inteligencia y expediente")
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        if DGCPTechnicalSheetService.enabled():
            await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).detect_after_analyze(
                opportunity_id,
                process_corpus=process_corpus,
            )

        from app.services.dgcp_product_intelligence_service import DGCPProductIntelligenceService

        if DGCPProductIntelligenceService.enabled():
            await DGCPProductIntelligenceService(self.db, self.tenant_id, self.user_id).run_after_analyze(
                opportunity_id,
                process_corpus=process_corpus,
            )

        from app.services.dgcp_process_update_service import DGCPProcessUpdateService

        if DGCPProcessUpdateService.enabled():
            await DGCPProcessUpdateService(self.db, self.tenant_id, self.user_id).save_snapshot_on_analyze(
                opportunity_id
            )

        await _stage("completed", "Análisis completado", 100)
        pkg = await self._get_package(opportunity_id)
        return DGCPAnalyzeResponse(
            opportunity_id=opportunity_id,
            requirements=requirements,
            checklist=self._checklist_response(opportunity_id, checklist),
            bid_package=bid,
            document_matches=self._matches_response(opportunity_id, checklist, matches),
            process_documents=process_docs_summary,
            alerts=alerts,
            analysis_warnings=analysis_warnings,
            expediente_status=pkg.expediente_status if pkg else expediente_status,
            pliego_analysis=pliego_payload,
        )

    async def get_pliego_analysis(self, opportunity_id: uuid.UUID) -> dict:
        from app.schemas.dgcp_pliego_analysis import PliegoAnalysisResponse
        from app.services.dgcp_pliego_deep_analysis_service import DGCPPliegoDeepAnalysisService

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        svc = DGCPPliegoDeepAnalysisService(self.db, self.tenant_id, self.user_id)
        current = await svc.get_current(opportunity_id)
        versions = await svc.list_versions(opportunity_id)
        return PliegoAnalysisResponse(
            opportunity_id=opportunity_id,
            current=current,
            versions=versions,
        ).model_dump(mode="json")

    async def run_pliego_analysis(self, opportunity_id: uuid.UUID, *, force: bool = True) -> dict:
        from app.services.dgcp_pliego_deep_analysis_service import DGCPPliegoDeepAnalysisService

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)
        process_docs_summary = await self.ingestion.ingest(opportunity)
        process_corpus, process_docs = await self.ingestion.build_extraction_corpus(opportunity_id)
        all_process_docs = await self.ingestion.load_process_documents(opportunity_id)
        related = await self._related_document_text(opportunity)
        extraction = self.extractor.extract(
            opportunity,
            related_text=related,
            process_corpus=process_corpus,
            process_documents=process_docs,
        )
        hermes_meta: dict = {}
        try:
            from app.services.dgcp_hermes_document_analysis_service import DGCPHermesDocumentAnalysisService

            if process_corpus.strip():
                extraction, hermes_meta = await DGCPHermesDocumentAnalysisService().enrich_extraction(
                    opportunity,
                    extraction,
                    process_corpus=process_corpus,
                    process_documents=process_docs,
                )
        except Exception as exc:
            logger.warning("hermes enrich skipped for pliego run: %s", exc)
            hermes_meta = {"status": "failed", "message": str(exc)[:200]}

        pkg = await self._get_package(opportunity_id)
        svc = DGCPPliegoDeepAnalysisService(self.db, self.tenant_id, self.user_id)
        result = await svc.run(
            opportunity,
            process_documents=all_process_docs or process_docs,
            process_corpus=process_corpus,
            extraction=extraction,
            hermes_meta=hermes_meta,
            requirement_evidence=(pkg.requirement_evidence if pkg else None) or [],
            checklist=(pkg.checklist if pkg else None) or [],
            risks=(pkg.requirement_risks if pkg else None) or [],
            force=force,
        )
        # ensure package has summary
        if pkg is None:
            pkg = await self._get_package(opportunity_id)
        if pkg is not None and process_docs_summary:
            pkg.process_documents_summary = process_docs_summary
        await self.db.commit()
        versions = await svc.list_versions(opportunity_id)
        from app.schemas.dgcp_pliego_analysis import PliegoAnalysisResponse

        return PliegoAnalysisResponse(
            opportunity_id=opportunity_id,
            current=result,
            versions=versions,
        ).model_dump(mode="json")

    async def review_pliego_field(
        self,
        opportunity_id: uuid.UUID,
        field_key: str,
        *,
        reviewed: bool = True,
        comment: str | None = None,
        corrected_value=None,
        corrected_items=None,
    ) -> dict:
        from app.services.dgcp_pliego_deep_analysis_service import DGCPPliegoDeepAnalysisService

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        svc = DGCPPliegoDeepAnalysisService(self.db, self.tenant_id, self.user_id)
        result = await svc.apply_field_review(
            opportunity_id,
            field_key,
            reviewed=reviewed,
            comment=comment,
            corrected_value=corrected_value,
            corrected_items=corrected_items,
        )
        await self.db.commit()
        return result.model_dump(mode="json")

    async def get_requirements(self, opportunity_id: uuid.UUID) -> DGCPRequirementsResponse:
        pkg = await self._get_package(opportunity_id)
        if pkg and pkg.requirements:
            return DGCPRequirementsResponse(**pkg.requirements)
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        related = await self._related_document_text(opportunity)
        extraction = self.extractor.extract(opportunity, related_text=related)
        return self._build_requirements_response(opportunity, extraction, pkg.analyzed_at if pkg else None)

    def _checklist_response(self, opportunity_id: uuid.UUID, items: list[dict]) -> DGCPChecklistResponse:
        from app.services.dgcp_expediente_sync_service import DGCPExpedienteSyncService

        sanitized = [self.compliance.sanitize_stored_checklist_item(i) for i in items]
        if DGCPExpedienteSyncService.enabled():
            sanitized = [DGCPExpedienteSyncService.enrich_checklist_item(i) for i in sanitized]
        parsed = [self._checklist_item_from_dict(i) for i in sanitized]
        counts = self.compliance.checklist_counts(items)
        return DGCPChecklistResponse(
            opportunity_id=opportunity_id,
            items=parsed,
            total=counts["total"],
            mandatory_total=counts["mandatory_total"],
            ready_count=counts["compliant_count"],
            compliant_count=counts["compliant_count"],
            pending_count=counts["pending_count"],
            expired_count=counts["expired_count"],
            incomplete_count=counts["incomplete_count"],
            review_count=counts["review_count"],
            unanalyzed_count=counts.get("unanalyzed_count", 0),
        )

    @staticmethod
    def _checklist_item_from_dict(data: dict) -> DGCPChecklistItem:
        doc_id = data.get("document_id")
        task_id = data.get("task_id")
        knowledge_id = data.get("knowledge_asset_id")
        process_id = data.get("process_document_id")
        valid = data.get("valid_until")
        return DGCPChecklistItem(
            id=uuid.UUID(str(data["id"])),
            requirement_key=data["requirement_key"],
            requirement=data["requirement"],
            tipo=data["tipo"],
            mandatory=data.get("mandatory", True),
            status=data.get("status", "pendiente"),
            document_id=uuid.UUID(doc_id) if doc_id else None,
            document_title=data.get("document_title"),
            valid_until=date.fromisoformat(valid) if valid else None,
            risk=data.get("risk"),
            recommended_action=data.get("recommended_action"),
            assignee=data.get("assignee"),
            task_id=uuid.UUID(task_id) if task_id else None,
            completable=data.get("completable", False),
            form_type=data.get("form_type"),
            display_status=data.get("display_status"),
            notes=data.get("notes"),
            knowledge_asset_id=uuid.UUID(knowledge_id) if knowledge_id else None,
            process_document_id=uuid.UUID(process_id) if process_id else None,
            relative_path=data.get("relative_path"),
            match_source=data.get("match_source"),
            odoo_quotation_id=data.get("odoo_quotation_id"),
            odoo_quotation_name=data.get("odoo_quotation_name"),
            economic_offer_meta=data.get("economic_offer_meta"),
            validity_analysis=data.get("validity_analysis"),
            manual_validation=data.get("manual_validation"),
            note_history=data.get("note_history") or [],
            unified_status=data.get("unified_status"),
            category=data.get("category"),
            priority=data.get("priority"),
            source_document=data.get("source_document"),
            source_page=data.get("source_page"),
            source_section=data.get("source_section"),
            evidence_fragment=data.get("evidence_fragment"),
            evidence_confidence=data.get("evidence_confidence"),
            suggested_document=data.get("suggested_document"),
            ia_observations=data.get("ia_observations"),
        )

    async def get_checklist(self, opportunity_id: uuid.UUID) -> DGCPChecklistResponse:
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            return DGCPChecklistResponse(
                opportunity_id=opportunity_id,
                items=[],
                total=0,
                mandatory_total=0,
                ready_count=0,
                compliant_count=0,
                pending_count=0,
                expired_count=0,
                incomplete_count=0,
                review_count=0,
            )
        return self._checklist_response(opportunity_id, pkg.checklist or [])

    def _matches_response(
        self,
        opportunity_id: uuid.UUID,
        checklist: list[dict],
        raw_matches: list[dict],
    ) -> DGCPDocumentMatchesResponse:
        raw_by_key = {m["requirement_key"]: m for m in raw_matches}
        parsed: list[DGCPDocumentMatch] = []
        for item in checklist:
            raw = raw_by_key.get(item["requirement_key"], {})
            valid = item.get("valid_until") or raw.get("valid_until")
            parsed.append(
                DGCPDocumentMatch(
                    requirement_key=item["requirement_key"],
                    requirement_label=item["requirement"],
                    document_id=uuid.UUID(item["document_id"]) if item.get("document_id") else None,
                    document_title=item.get("document_title") or raw.get("document_title"),
                    knowledge_asset_id=(
                        uuid.UUID(item["knowledge_asset_id"])
                        if item.get("knowledge_asset_id")
                        else None
                    ),
                    match_source=item.get("match_source") or raw.get("match_source"),
                    relative_path=item.get("relative_path") or raw.get("relative_path"),
                    match_score=raw.get("match_score", 0.0),
                    status=item.get("status", "faltante"),
                    vigency_status=item.get("vigency_status") or raw.get("vigency_status"),
                    valid_until=date.fromisoformat(valid) if valid else None,
                    notes=item.get("notes") or raw.get("notes"),
                    observation=item.get("recommended_action"),
                    validity_analysis=item.get("validity_analysis") or raw.get("validity_analysis"),
                )
            )
        return DGCPDocumentMatchesResponse(
            opportunity_id=opportunity_id,
            matches=parsed,
            found_count=sum(1 for m in parsed if m.status == "encontrado_vigente"),
            missing_count=sum(1 for m in parsed if m.status == "faltante"),
            expired_count=sum(1 for m in parsed if m.status == "encontrado_vencido"),
            review_count=sum(1 for m in parsed if m.status in REVIEW_STATUSES),
            complete_count=sum(1 for m in parsed if m.status == "requiere_completado"),
        )

    async def get_document_matches(self, opportunity_id: uuid.UUID) -> DGCPDocumentMatchesResponse:
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            return DGCPDocumentMatchesResponse(
                opportunity_id=opportunity_id,
                matches=[],
                found_count=0,
                missing_count=0,
                expired_count=0,
            )
        return self._matches_response(opportunity_id, pkg.checklist or [], pkg.document_matches or [])

    def _enrich_bid_with_area_pct(
        self,
        bid: DGCPBidPackageResponse,
        pkg: DGCPBidPackage | None,
        checklist: list[dict],
    ) -> DGCPBidPackageResponse:
        from app.services.dgcp_offer_preparation_center_service import DGCPOfferPreparationCenterService

        if not DGCPOfferPreparationCenterService.enabled():
            return bid
        stub = pkg or DGCPBidPackage(
            tenant_id=self.tenant_id,
            opportunity_id=bid.opportunity_id,
            checklist=checklist,
            manifest={},
            bid_package=bid.model_dump(mode="json"),
        )
        if stub.checklist != checklist:
            stub = DGCPBidPackage(
                tenant_id=stub.tenant_id,
                opportunity_id=stub.opportunity_id,
                checklist=checklist,
                manifest=stub.manifest or {},
                bid_package=stub.bid_package or {},
            )
        area_pct = DGCPOfferPreparationCenterService.compute_area_preparation_pct(stub)
        return bid.model_copy(update={"area_preparation_pct": area_pct})

    async def get_bid_package(self, opportunity_id: uuid.UUID) -> DGCPBidPackageResponse:
        pkg = await self._get_package(opportunity_id)
        if not pkg or not pkg.bid_package:
            opportunity = await self._get_opportunity(opportunity_id)
            if not opportunity:
                raise ValueError("Licitación no encontrada")
            return DGCPBidPackageResponse(
                opportunity_id=opportunity_id,
                opportunity_code=opportunity.code,
                preparation_pct=0.0,
                area_preparation_pct=0.0,
                total_requirements=0,
                mandatory_requirements=0,
                compliant_count=0,
                found_documents=0,
                pending_documents=0,
                expired_documents=0,
                forms_to_complete=0,
                review_count=0,
            )
        bid = DGCPBidPackageResponse(**pkg.bid_package)
        if bid.area_preparation_pct is None:
            from app.services.dgcp_offer_preparation_center_service import DGCPOfferPreparationCenterService

            if DGCPOfferPreparationCenterService.enabled():
                bid = bid.model_copy(
                    update={
                        "area_preparation_pct": DGCPOfferPreparationCenterService.compute_area_preparation_pct(
                            pkg
                        ),
                    }
                )
        return bid

    async def create_checklist_task(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
        *,
        assignee_name: str | None = None,
        due_date: date | None = None,
        force_new: bool = False,
    ) -> dict:
        if not self.user_id:
            raise ValueError("Usuario requerido")
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)

        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        checklist = self._deep_copy_checklist(pkg.checklist)
        target = None
        for item in checklist:
            if str(item.get("id")) == str(item_id):
                target = item
                break
        if not target:
            raise ValueError("Ítem de checklist no encontrado")

        await self._dedupe_requirement_tasks(opportunity_id, str(item_id))

        existing = await self._find_active_requirement_task(opportunity_id, str(item_id))
        if existing and not force_new:
            target["task_id"] = str(existing.id)
            if assignee_name:
                target["assignee"] = assignee_name
            pkg.checklist = checklist
            await self.audit.log(
                action="dgcp.checklist.task_link",
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                resource_type="dgcp_bid_package",
                resource_id=pkg.id,
                details={
                    "opportunity_id": str(opportunity_id),
                    "checklist_item_id": str(item_id),
                    "task_id": str(existing.id),
                    "existing": True,
                },
            )
            await self.db.commit()
            return {
                "task_id": str(existing.id),
                "title": existing.title,
                "checklist_item_id": str(item_id),
                "created": False,
                "existing": True,
            }

        opportunity = await self._get_opportunity(opportunity_id)
        title = f"DGCP {opportunity.code}: {target['requirement']}"
        tasks = TaskService(self.db, self.tenant_id, user_id=self.user_id)
        task = await tasks.create_task(
            TaskCreateRequest(
                title=title,
                description=target.get("recommended_action") or target["requirement"],
                category="licitacion",
                department="comercial",
                priority="alta",
                source="dgcp_requirement",
                dgcp_process_id=opportunity_id,
                suggested_assignee_name=assignee_name,
                due_date=due_date or (opportunity.deadline if opportunity else None),
                metadata={
                    "dgcp_opportunity_id": str(opportunity_id),
                    "dgcp_checklist_item_id": str(item_id),
                    "dgcp_requirement_key": target.get("requirement_key"),
                    "task_type": "requirement_followup",
                },
            )
        )
        target["task_id"] = str(task.id)
        if assignee_name:
            target["assignee"] = assignee_name
        pkg.checklist = checklist
        await self.audit.log(
            action="dgcp.checklist.task_create",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="dgcp_bid_package",
            resource_id=pkg.id,
            details={
                "opportunity_id": str(opportunity_id),
                "checklist_item_id": str(item_id),
                "task_id": str(task.id),
                "requirement_key": target.get("requirement_key"),
            },
        )
        await self.db.commit()
        return {
            "task_id": str(task.id),
            "title": task.title,
            "checklist_item_id": str(item_id),
            "created": True,
            "existing": False,
        }

    async def _find_active_requirement_task(
        self,
        opportunity_id: uuid.UUID,
        checklist_item_id: str,
    ) -> Task | None:
        result = await self.db.execute(
            select(Task).where(
                Task.tenant_id == self.tenant_id,
                Task.dgcp_process_id == opportunity_id,
                Task.status.in_(tuple(ACTIVE_TASK_STATUSES)),
            )
        )
        for task in result.scalars().all():
            meta = task.metadata_ or {}
            if meta.get("dgcp_checklist_item_id") == checklist_item_id:
                return task
            if meta.get("task_type") == "requirement_followup" and str(task.id) == checklist_item_id:
                continue
        return None

    async def _dedupe_requirement_tasks(self, opportunity_id: uuid.UUID, checklist_item_id: str) -> None:
        result = await self.db.execute(
            select(Task).where(
                Task.tenant_id == self.tenant_id,
                Task.dgcp_process_id == opportunity_id,
                Task.status.in_(tuple(ACTIVE_TASK_STATUSES)),
            )
        )
        grouped: dict[str, list[Task]] = {}
        for task in result.scalars().all():
            meta = task.metadata_ or {}
            key = meta.get("dgcp_checklist_item_id") or meta.get("dgcp_requirement_key") or task.title
            grouped.setdefault(str(key), []).append(task)

        for key, tasks in grouped.items():
            if len(tasks) <= 1:
                continue
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            keeper = tasks[0]
            for duplicate in tasks[1:]:
                duplicate.status = "cancelada"
                meta = dict(duplicate.metadata_ or {})
                meta["dedupe_reason"] = f"Duplicada — conservada tarea {keeper.id}"
                meta["dedupe_at"] = datetime.now(timezone.utc).isoformat()
                duplicate.metadata_ = meta
        await self.db.flush()

    async def apply_manual_validation(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: DGCPManualValidationRequest,
    ) -> DGCPManualValidationResponse:
        if not self.user_id:
            raise ValueError("Usuario requerido")
        allowed = {"validado_manual", "encontrado_vencido", "requiere_revision", "no_aplica"}
        if payload.status not in allowed:
            raise ValueError(f"Estado no permitido: {payload.status}")

        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)

        checklist = self._deep_copy_checklist(pkg.checklist)
        target = None
        for item in checklist:
            if str(item.get("id")) == str(item_id):
                target = item
                break
        if not target:
            raise ValueError("Ítem de checklist no encontrado")

        user_name = await self._user_display_name(self.user_id)
        previous_status = target.get("status", "pendiente")
        has_doc = DGCPComplianceEngine.has_document_evidence(
            {k: target.get(k) for k in ("document_id", "knowledge_asset_id")},
            target,
        )
        if payload.status == "validado_manual" and not has_doc and not payload.evidence.strip():
            raise ValueError(
                "No puede validar manualmente sin documento asociado. Use «No aplica» o adjunte evidencia."
            )

        manual_record = {
            "status": payload.status,
            "note": payload.note,
            "expiration_date": payload.expiration_date.isoformat() if payload.expiration_date else None,
            "evidence": payload.evidence,
            "validated_by_id": str(self.user_id),
            "validated_by": user_name,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "previous_status": previous_status,
            "document_id": target.get("document_id"),
            "document_title": target.get("document_title"),
        }
        target["manual_validation"] = manual_record
        target["status"] = payload.status
        if payload.expiration_date:
            target["valid_until"] = payload.expiration_date.isoformat()
        if payload.note.strip():
            await self._append_note_history(target, payload.note.strip(), action="validation")
        target["display_status"] = self.compliance.display_status_label(payload.status)

        matches = [dict(m) for m in (pkg.document_matches or [])]
        for match in matches:
            if match.get("requirement_key") == target.get("requirement_key"):
                match["status"] = payload.status
                if payload.expiration_date:
                    match["valid_until"] = payload.expiration_date.isoformat()
                if payload.note.strip():
                    match["notes"] = payload.note.strip()
                break

        bid = self.compliance.build_bid_package(opportunity, checklist, analyzed_at=pkg.analyzed_at)
        expediente_status = self._effective_expediente_status(
            opportunity, checklist, bid.preparation_pct, pkg
        )

        pkg.checklist = checklist
        pkg.document_matches = matches
        pkg.bid_package = bid.model_dump(mode="json")
        pkg.expediente_status = expediente_status
        from app.services.dgcp_expediente_event_service import DGCPExpedienteEventService

        await DGCPExpedienteEventService.publish(
            pkg,
            event_type="manual_validation",
            actor_id=self.user_id,
            detail={
                "checklist_item_id": str(item_id),
                "requirement_key": target.get("requirement_key"),
                "previous_status": previous_status,
                "new_status": payload.status,
            },
            checklist=checklist,
            preparation_pct=bid.preparation_pct,
        )
        await self.audit.log(
            action="dgcp.checklist.manual_validation",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="dgcp_bid_package",
            resource_id=pkg.id,
            details={
                "opportunity_id": str(opportunity_id),
                "checklist_item_id": str(item_id),
                "requirement_key": target.get("requirement_key"),
                "previous_status": previous_status,
                "new_status": payload.status,
                "preparation_pct": bid.preparation_pct,
                "expediente_status": expediente_status,
            },
        )
        await self.db.commit()

        return DGCPManualValidationResponse(
            opportunity_id=opportunity_id,
            checklist_item_id=item_id,
            requirement_key=target["requirement_key"],
            previous_status=previous_status,
            new_status=payload.status,
            manual_validation=manual_record,
            checklist=self._checklist_response(opportunity_id, checklist),
            bid_package=bid,
            expediente_status=expediente_status,
        )

    async def add_checklist_note(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
        note: str,
    ) -> dict:
        if not self.user_id:
            raise ValueError("Usuario requerido")
        cleaned = note.strip()
        if not cleaned:
            raise ValueError("La nota no puede estar vacía")

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)

        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        checklist = self._deep_copy_checklist(pkg.checklist)
        target = None
        for item in checklist:
            if str(item.get("id")) == str(item_id):
                target = item
                break
        if not target:
            raise ValueError("Ítem de checklist no encontrado")

        await self._append_note_history(target, cleaned, action="note")

        matches = [dict(m) for m in (pkg.document_matches or [])]
        for match in matches:
            if match.get("requirement_key") == target.get("requirement_key"):
                match["notes"] = cleaned
                break

        pkg.checklist = checklist
        pkg.document_matches = matches
        from app.services.dgcp_expediente_event_service import DGCPExpedienteEventService

        await DGCPExpedienteEventService.publish(
            pkg,
            event_type="comment_added",
            actor_id=self.user_id,
            detail={
                "checklist_item_id": str(item_id),
                "requirement_key": target.get("requirement_key"),
                "requirement_label": target.get("requirement"),
                "note": cleaned[:300],
                "summary": f"{target.get('requirement')}: {cleaned[:120]}",
            },
            checklist=checklist,
        )
        await self.audit.log(
            action="dgcp.checklist.note",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="dgcp_bid_package",
            resource_id=pkg.id,
            details={
                "opportunity_id": str(opportunity_id),
                "checklist_item_id": str(item_id),
                "requirement_key": target.get("requirement_key"),
                "note_preview": cleaned[:200],
            },
        )
        await self.db.commit()

        return {
            "opportunity_id": str(opportunity_id),
            "checklist_item_id": str(item_id),
            "notes": target.get("notes"),
            "note_history": target.get("note_history") or [],
            "checklist": self._checklist_response(opportunity_id, checklist),
        }

    async def associate_checklist_document(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: DGCPAssociateDocumentRequest,
    ) -> DGCPAssociateDocumentResponse:
        if not payload.document_id and not payload.knowledge_asset_id and not payload.process_document_id:
            raise ValueError("Indique document_id, knowledge_asset_id o process_document_id")

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)

        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        checklist = self._deep_copy_checklist(pkg.checklist)
        target = None
        for item in checklist:
            if str(item.get("id")) == str(item_id):
                target = item
                break
        if not target:
            raise ValueError("Ítem de checklist no encontrado")

        document_id: str | None = None
        knowledge_asset_id: str | None = None
        process_document_id: str | None = None
        document_title: str | None = None
        match_source: str | None = None
        relative_path: str | None = None
        new_status = "encontrado_vigente"
        ai_validation: dict | None = None

        if payload.process_document_id:
            proc = await self.db.get(DGCPProcessDocument, payload.process_document_id)
            if (
                not proc
                or proc.tenant_id != self.tenant_id
                or proc.opportunity_id != opportunity_id
            ):
                raise ValueError("Documento de proceso no válido para esta licitación")
            process_document_id = str(proc.id)
            document_title = proc.title
            match_source = "dgcp_process_repository"
            meta = proc.metadata_ or {}
            relative_path = meta.get("storage_uri")
            ai_validation = self._validate_uploaded_document(
                requirement_key=str(target.get("requirement_key") or ""),
                filename=meta.get("storage_filename") or proc.title,
                title=proc.title,
            )
            target["ai_validation"] = ai_validation
            target["ia_observations"] = ai_validation.get("observaciones")
            target["observaciones_ia"] = ai_validation.get("observaciones")
            if ai_validation.get("riesgo"):
                target["risk"] = ai_validation["riesgo"]
            if ai_validation.get("cumple") is False:
                new_status = "no_cumple"
            elif target.get("requirement_key", "").startswith("sncc_"):
                new_status = "requiere_completado"
            else:
                new_status = "cumple"

        if payload.knowledge_asset_id:
            asset = await self.db.get(KnowledgeAsset, payload.knowledge_asset_id)
            if (
                not asset
                or asset.tenant_id != self.tenant_id
                or not asset.is_active
                or asset.folder_category not in OFFICIAL_KNOWLEDGE_FOLDERS
            ):
                raise ValueError("Documento corporativo no válido (carpeta oficial requerida)")
            from app.services.document_requirement_validator import validate_asset_for_requirement

            req_key = target.get("requirement_key") or ""
            if req_key.startswith("sncc_"):
                from app.services.document_requirement_validator import validate_sncc_compliance

                sncc_vr = validate_sncc_compliance(
                    filename=asset.filename,
                    status="requiere_completado",
                    completable=True,
                )
                if not sncc_vr.ok:
                    raise ValueError("Documento SNCC no válido para este requisito")
            else:
                vr = validate_asset_for_requirement(
                    req_key,
                    filename=asset.filename,
                    title=asset.title,
                    document_type=asset.document_type,
                    asset=asset,
                )
                if not vr.ok:
                    raise ValueError(
                        f"El documento no corresponde al requisito ({vr.reason or 'validación fallida'})"
                    )
            knowledge_asset_id = str(asset.id)
            document_title = asset.title
            match_source = "knowledge_repository"
            relative_path = asset.relative_path
            if asset.folder_category.startswith("02_") or target.get("requirement_key", "").startswith("sncc_"):
                new_status = "requiere_completado"

        if payload.document_id:
            doc = await self.db.get(Document, payload.document_id)
            if not doc or doc.tenant_id != self.tenant_id or not doc.is_active:
                raise ValueError("Documento no encontrado")
            if " — " in doc.title and any(
                c in doc.title.upper() for c in ("MINERD", "DGCP", "CM-", "DAF-")
            ):
                raise ValueError("Documento contaminado de proceso DGCP — use repositorio corporativo")
            document_id = str(doc.id)
            document_title = doc.title
            match_source = "document_repository"
            if target.get("requirement_key", "").startswith("sncc_"):
                new_status = "requiere_completado"

        if target.get("requirement_key") == "oferta_economica" and process_document_id:
            new_status = "adjuntado"

        target["document_id"] = document_id
        target["knowledge_asset_id"] = knowledge_asset_id
        target["process_document_id"] = process_document_id
        target["document_title"] = document_title
        target["match_source"] = match_source
        target["relative_path"] = relative_path
        target["status"] = new_status
        target["ux_status"] = REQUIREMENT_UX_STATUS_MAP.get(new_status, "En proceso")
        target["display_status"] = self.compliance.display_status_label(new_status)
        target.pop("manual_validation", None)
        has_evidence = self.compliance.has_document_evidence({}, target)
        computed_risk = self.compliance.compute_risk(
            status=new_status,
            mandatory=bool(target.get("mandatory", True)),
            has_evidence=has_evidence,
        )
        if ai_validation and ai_validation.get("riesgo"):
            target["risk"] = f"{ai_validation['riesgo']} — {ai_validation.get('observaciones') or computed_risk}"
        else:
            target["risk"] = computed_risk
        target["recommended_action"] = COMPLIANCE_ACTION_BY_STATUS.get(new_status)

        matches = [dict(m) for m in (pkg.document_matches or [])]
        updated = False
        for match in matches:
            if match.get("requirement_key") == target.get("requirement_key"):
                match.update({
                    "document_id": document_id,
                    "knowledge_asset_id": knowledge_asset_id,
                    "process_document_id": process_document_id,
                    "document_title": document_title,
                    "match_source": match_source,
                    "relative_path": relative_path,
                    "status": new_status,
                    "match_score": 95.0,
                    "notes": f"Asociado manualmente — {document_title}",
                })
                updated = True
                break
        if not updated:
            matches.append({
                "requirement_key": target["requirement_key"],
                "requirement_label": target["requirement"],
                "document_id": document_id,
                "knowledge_asset_id": knowledge_asset_id,
                "process_document_id": process_document_id,
                "document_title": document_title,
                "match_source": match_source,
                "relative_path": relative_path,
                "status": new_status,
                "match_score": 95.0,
                "notes": f"Asociado manualmente — {document_title}",
            })

        bid = self.compliance.build_bid_package(opportunity, checklist, analyzed_at=pkg.analyzed_at)
        expediente_status = self._effective_expediente_status(
            opportunity, checklist, bid.preparation_pct, pkg
        )
        pkg.checklist = checklist
        pkg.document_matches = matches
        pkg.bid_package = bid.model_dump(mode="json")
        pkg.expediente_status = expediente_status

        from app.services.real_dgcp_expediente_builder import RealDGCPExpedienteBuilder

        await RealDGCPExpedienteBuilder.mark_stale_if_generated(
            self.db, self.tenant_id, opportunity_id
        )

        from app.services.dgcp_expediente_event_service import DGCPExpedienteEventService

        event_type = "document_added"
        if new_status in ("cumple", "encontrado_vigente", "validado_manual"):
            event_type = "document_approved"
        elif new_status in ("no_cumple", "vencido", "encontrado_vencido"):
            event_type = "document_rejected"
        await DGCPExpedienteEventService.publish(
            pkg,
            event_type=event_type,
            actor_id=self.user_id,
            detail={
                "checklist_item_id": str(item_id),
                "requirement_key": target.get("requirement_key"),
                "requirement_label": target.get("requirement"),
                "document_title": document_title,
                "status": new_status,
                "summary": f"{target.get('requirement')}: {document_title} → {new_status}",
            },
            checklist=checklist,
            preparation_pct=bid.preparation_pct,
        )

        await self.audit.log(
            action="dgcp.checklist.associate_document",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="dgcp_bid_package",
            resource_id=pkg.id,
            details={
                "opportunity_id": str(opportunity_id),
                "checklist_item_id": str(item_id),
                "requirement_key": target.get("requirement_key"),
                "document_id": document_id,
                "knowledge_asset_id": knowledge_asset_id,
                "process_document_id": process_document_id,
                "preparation_pct": bid.preparation_pct,
            },
        )
        await self.db.commit()

        return DGCPAssociateDocumentResponse(
            opportunity_id=opportunity_id,
            checklist_item_id=item_id,
            requirement_key=target["requirement_key"],
            document_id=uuid.UUID(document_id) if document_id else None,
            knowledge_asset_id=uuid.UUID(knowledge_asset_id) if knowledge_asset_id else None,
            process_document_id=uuid.UUID(process_document_id) if process_document_id else None,
            document_title=document_title,
            match_source=match_source,
            checklist=self._checklist_response(opportunity_id, checklist),
            bid_package=bid,
            expediente_status=expediente_status,
        )

    @staticmethod
    def _folder_category_from_m365_path(path: str) -> str:
        up = (path or "").upper()
        if "00_DATOS_EMPRESAS" in up:
            return "00_DATOS_EMPRESAS"
        if "01_DOCUMENTOS_LEGALES" in up or "DOCUMENTOS_LEGALES" in up:
            return "01_DOCUMENTOS_LEGALES"
        if "02_PLANTILLAS" in up or "PLANTILLAS" in up:
            return "02_PLANTILLAS"
        if "03_PROVEEDORES" in up:
            return "03_PROVEEDORES"
        if "04_FICHAS" in up:
            return "04_FICHAS_TECNICAS"
        if "05_COTIZACIONES" in up:
            return "05_COTIZACIONES"
        return "01_DOCUMENTOS_LEGALES"

    async def _knowledge_asset_for_m365_item(
        self,
        *,
        item_id: str,
        drive_id: str | None,
        source_type: str,
        site_id: str | None,
        name: str | None,
        web_url: str | None,
        path: str | None,
        company_key: str,
        download_content: bytes | None = None,
    ) -> KnowledgeAsset:
        from app.services.m365_documents_service import M365DocumentsService

        m365 = M365DocumentsService(self.db, self.tenant_id, user_id=self.user_id)
        item = await m365._resolve_item(item_id, drive_id=drive_id, source_type=source_type)
        filename = (name or item.name or "documento.pdf").strip()
        if not filename or filename.lower() == "sin nombre":
            filename = f"documento-{item.id[:8]}.pdf"
        folder_path = (path or item.path or "").replace("/drive/root:", "").strip("/")
        folder_category = self._folder_category_from_m365_path(folder_path)

        if download_content:
            rel = f"jaios/{company_key}/dgcp/{filename}".strip("/")
            content_hash = hashlib.sha256(download_content).hexdigest()
            source_provider = "jaios"
        else:
            rel = f"onedrive/{folder_path}/{filename}".strip("/") if folder_path else f"onedrive/{filename}"
            content_hash = hashlib.sha256(f"link:{item.id}".encode()).hexdigest()
            source_provider = "onedrive"

        existing = (
            await self.db.execute(
                select(KnowledgeAsset).where(
                    KnowledgeAsset.tenant_id == self.tenant_id,
                    KnowledgeAsset.relative_path == rel,
                    KnowledgeAsset.is_active.is_(True),
                ).limit(1)
            )
        ).scalar_one_or_none()

        if not existing:
            existing = (
                await self.db.execute(
                    select(KnowledgeAsset).where(
                        KnowledgeAsset.tenant_id == self.tenant_id,
                        KnowledgeAsset.is_active.is_(True),
                        KnowledgeAsset.metadata_["graph_item_id"].astext == item.id,
                    ).limit(1)
                )
            ).scalar_one_or_none()

        if existing:
            existing.filename = filename
            existing.title = filename
            existing.folder_category = folder_category
            existing.company_key = company_key or existing.company_key
            if download_content:
                existing.source_provider = source_provider
                existing.relative_path = rel
                existing.file_size = len(download_content)
                existing.content_hash = content_hash
            meta = dict(existing.metadata_ or {})
            meta.update(
                {
                    "graph_item_id": item.id,
                    "drive_id": drive_id,
                    "site_id": site_id,
                    "web_url": web_url or item.web_url,
                    "path": folder_path,
                    "source_type": source_type,
                    "link_mode": "import" if download_content else "link",
                }
            )
            existing.metadata_ = meta
            await self.db.flush()
            return existing

        asset = KnowledgeAsset(
            tenant_id=self.tenant_id,
            source_provider=source_provider,
            source_root="m365",
            relative_path=rel,
            folder_category=folder_category,
            filename=filename,
            title=filename,
            format=(filename.rsplit(".", 1)[-1] if "." in filename else "other").lower(),
            document_type="general",
            company_key=company_key or None,
            mime_type=item.mime_type,
            file_size=len(download_content) if download_content else (item.size_bytes or 0),
            content_hash=content_hash,
            metadata_={
                "graph_item_id": item.id,
                "drive_id": drive_id,
                "site_id": site_id,
                "web_url": web_url or item.web_url,
                "path": folder_path,
                "source_type": source_type,
                "link_mode": "import" if download_content else "link",
            },
        )
        self.db.add(asset)
        await self.db.flush()
        return asset

    async def _record_m365_document_link(
        self,
        *,
        opportunity_id: uuid.UUID,
        requirement_key: str,
        asset: KnowledgeAsset,
        item_id: str,
        drive_id: str | None,
        source_type: str,
        site_id: str | None,
        web_url: str | None,
        path: str | None,
        link_mode: str,
    ) -> None:
        from app.services.document_attachment_service import DocumentAttachmentService

        try:
            await DocumentAttachmentService(self.db, self.tenant_id, user_id=self.user_id).link_document(
                entity_type="dgcp_opportunity",
                entity_id=opportunity_id,
                requirement_id=requirement_key,
                file_name=asset.filename,
                source_system="m365",
                source_type=source_type,
                drive_id=drive_id,
                site_id=site_id,
                item_id=item_id,
                web_url=web_url,
                file_path=path,
                mime_type=asset.mime_type,
                size_bytes=asset.file_size,
                raw_payload={
                    "knowledge_asset_id": str(asset.id),
                    "link_mode": link_mode,
                    "requirement_key": requirement_key,
                },
                status="imported" if link_mode == "import" else "linked",
            )
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "document_links insert failed after dgcp m365 %s", link_mode
            )

    async def link_m365_checklist_document(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: DGCPLinkM365DocumentRequest,
    ) -> DGCPAssociateDocumentResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")

        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")
        target = next(
            (i for i in (pkg.checklist or []) if str(i.get("id")) == str(item_id)),
            None,
        )
        if not target:
            raise ValueError("Ítem de checklist no encontrado")

        asset = await self._knowledge_asset_for_m365_item(
            item_id=payload.item_id,
            drive_id=payload.drive_id,
            source_type=payload.source_type,
            site_id=payload.site_id,
            name=payload.name,
            web_url=payload.web_url,
            path=payload.path,
            company_key=opportunity.company,
        )

        result = await self.associate_checklist_document(
            opportunity_id,
            item_id,
            DGCPAssociateDocumentRequest(knowledge_asset_id=asset.id),
        )
        await self._record_m365_document_link(
            opportunity_id=opportunity_id,
            requirement_key=target["requirement_key"],
            asset=asset,
            item_id=payload.item_id,
            drive_id=payload.drive_id,
            source_type=payload.source_type,
            site_id=payload.site_id,
            web_url=payload.web_url or (asset.metadata_ or {}).get("web_url"),
            path=payload.path,
            link_mode="link",
        )
        return result

    async def import_m365_checklist_document(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: DGCPLinkM365DocumentRequest,
    ) -> DGCPAssociateDocumentResponse:
        from app.services.m365_documents_service import M365DocumentsService

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")

        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")
        target = next(
            (i for i in (pkg.checklist or []) if str(i.get("id")) == str(item_id)),
            None,
        )
        if not target:
            raise ValueError("Ítem de checklist no encontrado")

        m365 = M365DocumentsService(self.db, self.tenant_id, user_id=self.user_id)
        item = await m365._resolve_item(
            payload.item_id, drive_id=payload.drive_id, source_type=payload.source_type
        )
        content = await m365._download_item(
            item, drive_id=payload.drive_id, source_type=payload.source_type
        )
        if not content:
            raise ValueError("No pude descargar el archivo desde Microsoft 365.")

        asset = await self._knowledge_asset_for_m365_item(
            item_id=payload.item_id,
            drive_id=payload.drive_id,
            source_type=payload.source_type,
            site_id=payload.site_id,
            name=payload.name,
            web_url=payload.web_url,
            path=payload.path,
            company_key=opportunity.company,
            download_content=content,
        )

        result = await self.associate_checklist_document(
            opportunity_id,
            item_id,
            DGCPAssociateDocumentRequest(knowledge_asset_id=asset.id),
        )
        await self._record_m365_document_link(
            opportunity_id=opportunity_id,
            requirement_key=target["requirement_key"],
            asset=asset,
            item_id=payload.item_id,
            drive_id=payload.drive_id,
            source_type=payload.source_type,
            site_id=payload.site_id,
            web_url=payload.web_url or item.web_url,
            path=payload.path,
            link_mode="import",
        )
        return result

    async def upload_checklist_document(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None = None,
    ) -> DGCPAssociateDocumentResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)

        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        target = next(
            (i for i in (pkg.checklist or []) if str(i.get("id")) == str(item_id)),
            None,
        )
        if not target:
            raise ValueError("Ítem de checklist no encontrado")

        storage = DGCPProcessStorageService(self.tenant_id)
        ext = Path(filename).suffix or ".bin"
        safe_name = (
            f"{storage.slugify(target.get('requirement_key') or 'req')}_"
            f"{storage.slugify(Path(filename).stem)}{ext}"
        )
        storage.write_bytes(opportunity.code, safe_name, content)

        process_doc = DGCPProcessDocument(
            tenant_id=self.tenant_id,
            opportunity_id=opportunity_id,
            title=f"{target['requirement']} — {filename}",
            source_type="process_file",
            doc_role="checklist_evidence",
            priority="alta",
            format=ext.lstrip(".") or "other",
            ingestion_status="registered",
            metadata_={
                "storage_filename": safe_name,
                "storage_uri": storage.relative_uri(opportunity.code, safe_name),
                "requirement_key": target.get("requirement_key"),
                "checklist_item_id": str(item_id),
                "scope": "dgcp_process",
            },
        )
        self.db.add(process_doc)
        await self.db.flush()

        return await self.associate_checklist_document(
            opportunity_id,
            item_id,
            DGCPAssociateDocumentRequest(process_document_id=process_doc.id),
        )

    async def activate_expediente_tracking(self, opportunity_id: uuid.UUID) -> str | None:
        """Activa seguimiento de expediente tras marcar interés (Licitar)."""
        opportunity = await self._get_opportunity(opportunity_id)
        pkg = await self._get_package(opportunity_id)
        if not opportunity or not pkg:
            return None
        checklist = pkg.checklist or []
        bid_data = pkg.bid_package or {}
        prep = float(bid_data.get("preparation_pct") or 0)
        status = self.compliance.compute_expediente_status(checklist, prep)
        pkg.expediente_status = status
        await self.db.commit()
        return status

    def _validate_uploaded_document(
        self,
        *,
        requirement_key: str,
        filename: str | None,
        title: str | None,
    ) -> dict:
        from app.services.document_requirement_validator import (
            REQUIREMENT_KEYWORDS,
            has_forbidden_signals,
            keywords_match_requirement,
        )

        observaciones: list[str] = []
        riesgo = "bajo"
        cumple = True
        if has_forbidden_signals(requirement_key, filename, title, requirement_key):
            cumple = False
            riesgo = "alto"
            observaciones.append("El documento no corresponde a la categoría del requisito.")
        elif requirement_key in REQUIREMENT_KEYWORDS and not keywords_match_requirement(
            requirement_key, filename, title
        ):
            cumple = False
            riesgo = "alto"
            observaciones.append(
                "El nombre/título no coincide con el requisito solicitado en el pliego."
            )
        if not observaciones:
            observaciones.append("Documento alineado con el requisito según nombre y categoría.")
        return {
            "cumple": cumple,
            "no_cumple": not cumple,
            "observaciones": " ".join(observaciones),
            "riesgo": riesgo,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "requirement_key": requirement_key,
            "filename": filename,
        }

    @staticmethod
    def _section_for_requirement(item: dict) -> str:
        key = str(item.get("requirement_key") or "").lower()
        tipo = str(item.get("tipo") or item.get("category") or "").lower()
        label = str(item.get("requirement") or "").lower()
        blob = f"{key} {tipo} {label}"
        if any(t in blob for t in ("cronograma", "plazo", "entrega", "calendario")):
            return "cronograma"
        if any(t in blob for t in ("garantia", "fianza", "seguro")):
            return "garantias"
        if any(t in blob for t in ("experiencia", "antecedente", "referencia")):
            return "experiencia"
        if any(t in blob for t in ("personal", "curriculum", "cv", "equipo")):
            return "personal"
        if any(t in blob for t in ("certific", "tss", "dgii", "mipyme", "rpe")):
            return "certificaciones"
        if any(t in blob for t in ("econom", "precio", "cotiz", "f033", "oferta_economica")):
            return "oferta_economica"
        if any(t in blob for t in ("tecnic", "especif", "plano", "oferta_tecnica")):
            return "oferta_tecnica"
        if any(t in blob for t in ("anexo",)):
            return "anexos"
        if any(t in blob for t in ("formulario", "sncc", "administrativo", "legal")):
            return "documentos_requeridos"
        return "requisitos"

    def _enrich_requirement_item(self, item: dict) -> dict:
        status = str(item.get("status") or "pendiente")
        enriched = dict(item)
        enriched["ux_status"] = REQUIREMENT_UX_STATUS_MAP.get(
            status, enriched.get("ux_status") or "Pendiente"
        )
        enriched["nombre"] = item.get("requirement") or item.get("requirement_key")
        enriched["descripcion"] = (
            item.get("ia_observations")
            or item.get("notes")
            or item.get("recommended_action")
            or item.get("requirement")
        )
        enriched["obligatoriedad"] = "Obligatorio" if item.get("mandatory", True) else "Opcional"
        enriched["documento_asociado"] = item.get("document_title")
        enriched["estado"] = enriched["ux_status"]
        enriched["responsable"] = item.get("assignee")
        enriched["fecha_limite"] = item.get("due_date") or item.get("valid_until")
        history = item.get("note_history") or []
        last_mod = None
        if history:
            last_mod = history[-1].get("created_at")
        last_mod = (
            last_mod
            or (item.get("manual_validation") or {}).get("validated_at")
            or (item.get("ai_validation") or {}).get("validated_at")
            or item.get("updated_at")
        )
        enriched["ultima_modificacion"] = last_mod
        enriched["observaciones_ia"] = (
            item.get("observaciones_ia")
            or item.get("ia_observations")
            or ((item.get("ai_validation") or {}).get("observaciones") if isinstance(item.get("ai_validation"), dict) else None)
            or item.get("risk")
        )
        enriched["seccion"] = item.get("seccion") or self._section_for_requirement(item)
        return enriched

    def _build_proactive_insights(
        self,
        *,
        checklist: list[dict],
        missing_docs: list[dict],
        upcoming: list[dict],
        critical_alerts: list,
        risks: list,
        prep_pct: float,
    ) -> dict:
        recommendations: list[str] = []
        critical_reqs = [
            i
            for i in checklist
            if i.get("mandatory", True)
            and i.get("ux_status") in ("Pendiente", "Rechazado", "En proceso")
        ]
        if missing_docs:
            recommendations.append(
                f"Adjuntar {len(missing_docs)} documento(s) obligatorio(s) faltante(s)."
            )
        expiring = [u for u in upcoming if u.get("tipo") == "vigencia_documento"]
        if expiring:
            recommendations.append(
                f"Revisar {len(expiring)} documento(s) con vigencia próxima a vencer."
            )
        if critical_alerts:
            recommendations.append(
                f"Atender {len(critical_alerts)} alerta(s) crítica(s) del expediente."
            )
        if prep_pct < 80:
            recommendations.append(
                "El expediente está por debajo del 80% — priorice requisitos obligatorios pendientes."
            )
        elif prep_pct >= 95:
            recommendations.append(
                "Expediente casi completo — ejecute «Validar Expediente» antes de exportar."
            )
        if not recommendations:
            recommendations.append("Sin acciones críticas pendientes detectadas por la IA.")
        return {
            "documentos_faltantes": [
                {
                    "id": i.get("id"),
                    "nombre": i.get("nombre") or i.get("requirement"),
                    "responsable": i.get("responsable") or i.get("assignee"),
                    "estado": i.get("estado") or i.get("ux_status"),
                }
                for i in missing_docs[:20]
            ],
            "proximos_a_vencer": upcoming[:10],
            "riesgos": risks[:15],
            "requisitos_criticos": [
                {
                    "id": i.get("id"),
                    "nombre": i.get("nombre") or i.get("requirement"),
                    "estado": i.get("ux_status"),
                    "responsable": i.get("assignee"),
                    "riesgo": i.get("risk"),
                }
                for i in critical_reqs[:20]
            ],
            "recomendaciones": recommendations,
        }

    def _compute_final_validation(self, opportunity, pkg) -> dict:
        checklist = [self._enrich_requirement_item(i) for i in (pkg.checklist or [])]
        bid = pkg.bid_package or {}
        prep_pct = float(bid.get("preparation_pct") or 0)
        missing = []
        rejected = []
        in_review = []
        for item in checklist:
            if not item.get("mandatory", True):
                continue
            ux = item.get("ux_status")
            has_doc = bool(
                item.get("document_title")
                or item.get("process_document_id")
                or item.get("document_id")
                or item.get("knowledge_asset_id")
            )
            if ux == "Rechazado" or item.get("status") in ("no_cumple", "vencido", "encontrado_vencido"):
                rejected.append(item.get("nombre") or item.get("requirement"))
            elif not has_doc or ux == "Pendiente":
                missing.append(item.get("nombre") or item.get("requirement"))
            elif ux in ("En proceso", "Revisado") or item.get("status") in (
                "requiere_completado",
                "requiere_revision",
                "requiere_actualizacion",
            ):
                in_review.append(item.get("nombre") or item.get("requirement"))

        can_ready = self.compliance.can_mark_ready_for_review(pkg.checklist or [])
        listo = bool(can_ready and not missing and not rejected and prep_pct >= 90)
        gaps = []
        if missing:
            gaps.append({"tipo": "faltante", "items": missing})
        if rejected:
            gaps.append({"tipo": "rechazado", "items": rejected})
        if in_review:
            gaps.append({"tipo": "en_revision", "items": in_review})
        if prep_pct < 90:
            gaps.append(
                {
                    "tipo": "progreso",
                    "items": [f"Preparación actual {prep_pct:.0f}% (mínimo recomendado 90%)"],
                }
            )
        explanation = (
            "Listo para presentar."
            if listo
            else "No listo. "
            + "; ".join(
                f"{g['tipo']}: {', '.join(g['items'][:5])}"
                + ("…" if len(g["items"]) > 5 else "")
                for g in gaps
            )
        )
        return {
            "listo_para_presentar": listo,
            "estado": "Listo para presentar" if listo else "No listo",
            "preparation_pct": prep_pct,
            "faltantes": missing,
            "rechazados": rejected,
            "en_revision": in_review,
            "gaps": gaps,
            "explicacion": explanation,
            "validaciones_ia": [
                {
                    "requirement_key": i.get("requirement_key"),
                    "nombre": i.get("nombre") or i.get("requirement"),
                    "resultado": (i.get("ai_validation") or {}).get("cumple"),
                    "observaciones": i.get("observaciones_ia") or i.get("ia_observations"),
                    "riesgo": i.get("risk"),
                    "estado": i.get("ux_status"),
                }
                for i in checklist
                if i.get("ai_validation") or i.get("ia_observations") or i.get("manual_validation")
            ],
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "opportunity_code": opportunity.code,
        }

    async def get_expediente_dashboard(self, opportunity_id: uuid.UUID) -> dict:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        pkg = await self._get_package(opportunity_id)
        checklist = [self._enrich_requirement_item(i) for i in ((pkg.checklist if pkg else None) or [])]
        bid = (pkg.bid_package if pkg else None) or {}
        alerts = (pkg.alerts if pkg else None) or []
        matches = (pkg.document_matches if pkg else None) or []
        risks = (pkg.requirement_risks if pkg else None) or []

        approved = [i for i in checklist if i.get("ux_status") in ("Aprobado", "Completado")]
        rejected = [i for i in checklist if i.get("ux_status") == "Rechazado"]
        pending = [i for i in checklist if i.get("ux_status") == "Pendiente"]
        in_progress = [i for i in checklist if i.get("ux_status") == "En proceso"]
        in_review = [i for i in checklist if i.get("ux_status") == "Revisado"]
        missing_docs = [
            i
            for i in checklist
            if i.get("mandatory", True)
            and not (
                i.get("document_title")
                or i.get("process_document_id")
                or i.get("document_id")
                or i.get("knowledge_asset_id")
            )
        ]

        sections_order = [
            ("cronograma", "Cronograma"),
            ("requisitos", "Requisitos"),
            ("documentos_requeridos", "Documentos requeridos"),
            ("oferta_tecnica", "Oferta técnica"),
            ("oferta_economica", "Oferta económica"),
            ("garantias", "Garantías"),
            ("experiencia", "Experiencia"),
            ("personal", "Personal"),
            ("certificaciones", "Certificaciones"),
            ("anexos", "Anexos"),
        ]
        by_section: dict[str, list] = {k: [] for k, _ in sections_order}
        for item in checklist:
            sec = item.get("seccion") or "requisitos"
            if sec not in by_section:
                sec = "requisitos"
            by_section[sec].append(item)

        general = {
            "code": opportunity.code,
            "title": opportunity.title,
            "institution": opportunity.institution,
            "amount": str(opportunity.amount) if opportunity.amount is not None else None,
            "currency": opportunity.currency,
            "deadline": opportunity.deadline.isoformat() if opportunity.deadline else None,
            "modalidad": opportunity.modalidad,
            "status": opportunity.status,
            "source_url": opportunity.source_url,
            "objeto": opportunity.objeto_proceso or opportunity.description,
        }
        prep_pct = float(bid.get("preparation_pct") or 0)
        critical_alerts = [
            a
            for a in alerts
            if str((a or {}).get("severity") or (a or {}).get("nivel") or "").lower()
            in ("critica", "crítica", "alto", "high", "critical")
        ]
        risk_critical = [
            r
            for r in risks
            if str((r or {}).get("nivel") or "").lower() in ("alto", "critica", "crítica", "high")
        ]
        upcoming = []
        if opportunity.deadline:
            upcoming.append(
                {
                    "tipo": "cierre_proceso",
                    "fecha": opportunity.deadline.isoformat(),
                    "descripcion": f"Cierre / presentación — {opportunity.code}",
                }
            )
        for item in checklist:
            vu = item.get("valid_until") or item.get("fecha_limite")
            if vu:
                upcoming.append(
                    {
                        "tipo": "vigencia_documento",
                        "fecha": str(vu),
                        "descripcion": item.get("nombre") or item.get("requirement"),
                    }
                )
        upcoming.sort(key=lambda x: x.get("fecha") or "")

        from app.services.dgcp_expediente_event_service import DGCPExpedienteEventService

        timeline = DGCPExpedienteEventService.timeline(pkg, limit=40) if pkg else []
        proactive = self._build_proactive_insights(
            checklist=checklist,
            missing_docs=missing_docs,
            upcoming=upcoming,
            critical_alerts=critical_alerts,
            risks=risk_critical or risks,
            prep_pct=prep_pct,
        )
        validation_preview = (
            self._compute_final_validation(opportunity, pkg) if pkg else None
        )
        score = None
        if pkg:
            from app.services.dgcp_expediente_enterprise_service import (
                DGCPExpedienteEnterpriseService,
            )

            score = DGCPExpedienteEnterpriseService(
                self.db, self.tenant_id, self.user_id
            )._compute_score(pkg)

        return {
            "opportunity_id": str(opportunity_id),
            "opportunity_code": opportunity.code,
            "expediente_status": (pkg.expediente_status if pkg else None) or "sin_preparar",
            "preparation_pct": prep_pct,
            "score": score,
            "progreso": {
                "total_requisitos": len(checklist),
                "completados": len(approved),
                "pendientes": len(pending) + len(in_progress),
                "en_revision": len(in_review),
                "riesgos_criticos": len(risk_critical) or len(critical_alerts),
                "porcentaje_real": prep_pct,
            },
            "kpis": {
                "porcentaje_completado": prep_pct,
                "requisitos_pendientes": len(pending) + len(in_progress),
                "documentos_faltantes": len(missing_docs),
                "documentos_rechazados": len(rejected),
                "documentos_aprobados": len(approved),
                "en_revision": len(in_review),
                "proximos_vencimientos": len(upcoming),
                "alertas_criticas": len(critical_alerts),
                "total_requisitos": len(checklist),
                "riesgos_criticos": len(risk_critical) or len(critical_alerts),
            },
            "ia_proactiva": proactive,
            "timeline": timeline,
            "validacion_preview": validation_preview,
            "informacion_general": general,
            "cronograma": {
                "deadline": general["deadline"],
                "items": by_section.get("cronograma") or [],
            },
            "secciones": [
                {
                    "id": sid,
                    "nombre": sname,
                    "total": len(by_section.get(sid) or []),
                    "pendientes": sum(
                        1
                        for i in (by_section.get(sid) or [])
                        if i.get("ux_status") in ("Pendiente", "En proceso")
                    ),
                    "items": by_section.get(sid) or [],
                }
                for sid, sname in sections_order
            ],
            "requisitos": checklist,
            "documentos_faltantes": missing_docs,
            "documentos_rechazados": rejected,
            "documentos_aprobados": approved,
            "proximos_vencimientos": upcoming[:10],
            "alertas_criticas": critical_alerts,
            "document_matches_count": len(matches),
            "analyzed_at": pkg.analyzed_at.isoformat() if pkg and pkg.analyzed_at else None,
        }

    async def assign_checklist_item(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
        *,
        assignee: str,
        due_date: date | None = None,
    ) -> dict:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")
        cleaned = (assignee or "").strip()
        if not cleaned:
            raise ValueError("Indique un responsable")

        checklist = self._deep_copy_checklist(pkg.checklist)
        target = next((i for i in checklist if str(i.get("id")) == str(item_id)), None)
        if not target:
            raise ValueError("Ítem de checklist no encontrado")

        previous = target.get("assignee")
        target["assignee"] = cleaned
        if due_date:
            target["due_date"] = due_date.isoformat()
        target["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self._append_note_history(
            target,
            f"Responsable: {cleaned}"
            + (f" · Fecha límite: {due_date.isoformat()}" if due_date else ""),
            action="assignee",
        )
        pkg.checklist = checklist
        from app.services.dgcp_expediente_event_service import DGCPExpedienteEventService

        await DGCPExpedienteEventService.publish(
            pkg,
            event_type="assignee_changed",
            actor_id=self.user_id,
            detail={
                "checklist_item_id": str(item_id),
                "requirement_key": target.get("requirement_key"),
                "requirement_label": target.get("requirement"),
                "previous_assignee": previous,
                "assignee": cleaned,
                "due_date": due_date.isoformat() if due_date else target.get("due_date"),
                "summary": f"{target.get('requirement')}: responsable → {cleaned}",
            },
            checklist=checklist,
        )
        await self.audit.log(
            action="dgcp.checklist.assign",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="dgcp_bid_package",
            resource_id=pkg.id,
            details={
                "opportunity_id": str(opportunity_id),
                "checklist_item_id": str(item_id),
                "assignee": cleaned,
                "due_date": due_date.isoformat() if due_date else None,
            },
        )
        await self.db.commit()
        return {
            "opportunity_id": str(opportunity_id),
            "checklist_item_id": str(item_id),
            "assignee": cleaned,
            "due_date": target.get("due_date"),
            "checklist": self._checklist_response(opportunity_id, checklist),
        }

    async def validate_expediente_final(self, opportunity_id: uuid.UUID) -> dict:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        result = self._compute_final_validation(opportunity, pkg)
        from app.services.dgcp_expediente_event_service import DGCPExpedienteEventService

        await DGCPExpedienteEventService.publish(
            pkg,
            event_type="expediente_validated",
            actor_id=self.user_id,
            detail={
                "listo_para_presentar": result["listo_para_presentar"],
                "estado": result["estado"],
                "summary": result["explicacion"][:300],
            },
            checklist=pkg.checklist or [],
            preparation_pct=result["preparation_pct"],
        )
        manifest = dict(pkg.manifest or {})
        manifest["final_validation"] = result
        pkg.manifest = manifest
        await self.db.commit()
        return result

    async def get_document_preview(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
    ) -> DGCPDocumentPreviewResponse:
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        target = None
        for item in pkg.checklist or []:
            if str(item.get("id")) == str(item_id):
                target = item
                break
        if not target:
            raise ValueError("Ítem de checklist no encontrado")

        raw_matches = {m["requirement_key"]: m for m in (pkg.document_matches or [])}
        raw = raw_matches.get(target["requirement_key"], {})
        extracted_text = None
        download_url = None
        preview_url = None
        metadata: dict = {}

        knowledge_id = target.get("knowledge_asset_id") or raw.get("knowledge_asset_id")
        document_id = target.get("document_id") or raw.get("document_id")
        process_document_id = target.get("process_document_id") or raw.get("process_document_id")

        if process_document_id:
            proc = await self.db.get(DGCPProcessDocument, uuid.UUID(str(process_document_id)))
            if proc:
                document_title = target.get("document_title") or proc.title
                download_url = (
                    f"/api/v1/dgcp/opportunities/{opportunity_id}/process-documents/"
                    f"{proc.id}/file"
                )
                preview_url = download_url
                meta = proc.metadata_ or {}
                metadata = {
                    "filename": meta.get("storage_filename") or proc.title,
                    "storage_uri": meta.get("storage_uri"),
                    "scope": "dgcp_process",
                }

        if knowledge_id:
            asset = await self.db.get(KnowledgeAsset, uuid.UUID(str(knowledge_id)))
            if asset:
                from app.services.document_access_service import resolve_knowledge_asset_access

                access = await resolve_knowledge_asset_access(
                    self.db, asset.id, tenant_id=self.tenant_id
                )
                extracted_text = asset.extracted_text
                if not extracted_text and access.view_mode == "local" and asset.relative_path:
                    source = get_knowledge_source_provider()
                    try:
                        content = source.read_bytes(asset.relative_path)
                        extracted_text = DocumentExtractionService().extract(
                            content, filename=asset.filename
                        ).text
                    except Exception:
                        pass
                if access.view_mode == "local" and access.local_api_path:
                    download_url = access.local_api_path
                    preview_url = access.local_api_path
                elif access.web_url:
                    download_url = access.web_url
                    preview_url = access.web_url
                metadata = {
                    "filename": asset.filename,
                    "relative_path": asset.relative_path,
                    "folder_category": asset.folder_category,
                    "file_size": asset.file_size,
                    "web_url": access.web_url,
                    "view_mode": access.view_mode,
                    "canonical_source_id": access.canonical_source_id,
                }

        if document_id:
            doc_svc = DocumentService(self.db, self.tenant_id, self.user_id)
            doc = await doc_svc.get_document(uuid.UUID(str(document_id)))
            if doc:
                extracted_text = extracted_text or doc.extracted_text
                download_url = f"/api/v1/documents/{doc.id}/download"
                preview_url = download_url
                metadata.update({"filename": doc.filename, "storage_path": doc.storage_path})

        validity = target.get("validity_analysis") or raw.get("validity_analysis")
        web_url = metadata.get("web_url") if metadata else None
        view_mode = metadata.get("view_mode") if metadata else None

        return DGCPDocumentPreviewResponse(
            opportunity_id=opportunity_id,
            checklist_item_id=item_id,
            requirement_key=target["requirement_key"],
            requirement_label=target["requirement"],
            document_id=uuid.UUID(str(document_id)) if document_id else None,
            document_title=target.get("document_title") or raw.get("document_title"),
            knowledge_asset_id=uuid.UUID(str(knowledge_id)) if knowledge_id else None,
            relative_path=target.get("relative_path") or raw.get("relative_path"),
            match_source=target.get("match_source") or raw.get("match_source"),
            extracted_text=extracted_text,
            validity_analysis=validity,
            download_url=download_url,
            preview_url=preview_url,
            web_url=web_url,
            view_mode=view_mode,
            metadata=metadata,
        )

    async def _user_display_name(self, user_id: uuid.UUID) -> str:
        user = await self.db.get(User, user_id)
        if user and user.full_name:
            return user.full_name
        if user and user.email:
            return user.email
        return "Usuario"

    async def form_preview(
        self,
        opportunity_id: uuid.UUID,
        *,
        form_type: str = "SNCC.F042",
        company: str = "justech",
    ) -> DGCPFormPreviewResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")

        completion = DocumentCompletionService(db=self.db, tenant_id=self.tenant_id)
        preview = await completion.preview(form_type=form_type, company_key=company)

        field_labels = {
            "razon_social": "Razón social",
            "rnc": "RNC",
            "direccion": "Dirección",
            "representante_legal": "Representante legal",
            "telefono": "Teléfono",
            "correo": "Correo",
            "cuenta_bancaria": "Cuenta bancaria",
            "proceso_dgcp": "Proceso DGCP",
            "monto": "Monto oferta",
        }

        extra = {
            "proceso_dgcp": f"{opportunity.code} — {opportunity.title[:80]}",
            "monto": f"{float(opportunity.amount):,.2f} {opportunity.currency}",
        }

        fields: list[DGCPFormPreviewField] = []
        warnings: list[str] = []
        confidences: list[float] = []

        all_keys = set(preview.fields.keys()) | set(preview.missing_in_source) | set(extra.keys())
        for key in all_keys:
            val = preview.fields.get(key) or extra.get(key)
            if val:
                conf = 0.95 if key in preview.fields else 0.75
                fields.append(DGCPFormPreviewField(
                    label=field_labels.get(key, key),
                    value=str(val),
                    status="encontrado",
                    confidence=conf,
                ))
                confidences.append(conf)
            else:
                fields.append(DGCPFormPreviewField(
                    label=field_labels.get(key, key),
                    value=None,
                    status="pendiente",
                    confidence=0.0,
                ))
                warnings.append(f"Campo pendiente: {field_labels.get(key, key)}")

        overall = sum(confidences) / len(confidences) if confidences else 0.0

        return DGCPFormPreviewResponse(
            opportunity_id=opportunity_id,
            form_type=preview.form_type,
            company=preview.company,
            fields=fields,
            missing=preview.missing_in_source,
            warnings=warnings,
            overall_confidence=round(overall, 2),
            generate_enabled=False,
        )

    async def upload_process_pliego(
        self,
        opportunity_id: uuid.UUID,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None = None,
        doc_role: str | None = None,
    ):
        from app.schemas.dgcp_bid import DGCPProcessDocumentUploadResponse

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)

        doc = await self.ingestion.upload_process_document(
            opportunity,
            filename=filename,
            content=content,
            mime_type=mime_type,
            doc_role=doc_role or "pliego",
        )
        summary = self.ingestion._summary(doc)
        await self._sync_process_documents_summary(opportunity_id)
        await self.db.commit()
        text_len = len(doc.extracted_text or "")
        return DGCPProcessDocumentUploadResponse(
            opportunity_id=opportunity_id,
            process_document=summary,
            text_extracted=bool(doc.extracted_text),
            text_length=text_len,
            message=(
                "Pliego indexado con texto extraíble."
                if doc.extracted_text
                else "Archivo guardado pero no se extrajo texto. Verifique que el PDF tenga texto seleccionable."
            ),
        )

    async def get_process_documents(self, opportunity_id: uuid.UUID) -> DGCPProcessDocumentsResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        docs = await self.ingestion.load_process_documents(opportunity_id)
        payload = self.ingestion.build_documents_response(docs)
        return DGCPProcessDocumentsResponse(
            opportunity_id=opportunity_id,
            items=payload["items"],
            total=payload["total"],
            portal=payload.get("portal"),
        )

    async def refresh_process_documents(self, opportunity_id: uuid.UUID) -> dict:
        from app.schemas.dgcp_bid import DGCPProcessDocumentsRefreshResponse

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)
        stats = await self.ingestion.refresh_portal_documents(opportunity)
        await self._sync_process_documents_summary(opportunity_id)
        await self.db.commit()
        items = stats.get("items") or {}
        return DGCPProcessDocumentsRefreshResponse(
            opportunity_id=opportunity_id,
            discovered=stats.get("discovered", 0),
            downloaded=stats.get("downloaded", 0),
            items=items.get("items") or [],
            total=items.get("total") or 0,
            portal=items.get("portal"),
            message=(
                f"Se descargaron {stats.get('downloaded', 0)} documento(s) del portal DGCP."
                if stats.get("downloaded")
                else "Búsqueda completada. Revise los documentos detectados."
            ),
        )

    async def reingest_process_document(
        self,
        opportunity_id: uuid.UUID,
        process_document_id: uuid.UUID,
    ) -> dict:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        doc = await self.db.get(DGCPProcessDocument, process_document_id)
        if not doc or doc.opportunity_id != opportunity_id or doc.tenant_id != self.tenant_id:
            raise ValueError("Documento de proceso no encontrado")
        if doc.source_type == "portal":
            raise ValueError("El enlace del portal DGCP no admite reingesta de texto")
        updated = await self.ingestion.reingest_process_document(opportunity, doc)
        await self._sync_process_documents_summary(opportunity_id)
        await self.db.commit()
        return self.ingestion._summary(updated)

    async def update_process_document_role(
        self,
        opportunity_id: uuid.UUID,
        process_document_id: uuid.UUID,
        *,
        doc_role: str,
    ) -> dict:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        doc = await self.db.get(DGCPProcessDocument, process_document_id)
        if not doc or doc.opportunity_id != opportunity_id or doc.tenant_id != self.tenant_id:
            raise ValueError("Documento de proceso no encontrado")
        if doc.source_type == "portal":
            raise ValueError("No se puede reclasificar el enlace del portal DGCP")
        updated = await self.ingestion.update_document_role(doc, doc_role)
        await self._sync_process_documents_summary(opportunity_id)
        await self.db.commit()
        return self.ingestion._summary(updated)

    async def link_process_document_from_url(
        self,
        opportunity_id: uuid.UUID,
        *,
        url: str,
        title: str | None = None,
        doc_role: str = "pliego",
    ) -> dict:
        import httpx

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)
        clean_url = url.strip()
        if not clean_url.startswith("http"):
            raise ValueError("URL inválida")
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(clean_url, headers={"User-Agent": "JAIOS-DGCP/1.0"})
            response.raise_for_status()
            content = response.content
        if not content or content[:4] != b"%PDF":
            raise ValueError("La URL no devolvió un PDF descargable")
        filename = title or clean_url.split("/")[-1].split("?")[0] or "documento.pdf"
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        doc = await self.ingestion.upload_process_document(
            opportunity,
            filename=filename,
            content=content,
            mime_type="application/pdf",
            doc_role=doc_role,
        )
        meta = dict(doc.metadata_ or {})
        meta["linked_from_url"] = clean_url
        meta["source_label"] = "Vinculado por URL"
        doc.metadata_ = meta
        await self._sync_process_documents_summary(opportunity_id)
        await self.db.commit()
        return self.ingestion._summary(doc)

    async def _sync_process_documents_summary(self, opportunity_id: uuid.UUID) -> None:
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            return
        docs = await self.ingestion.load_process_documents(opportunity_id)
        payload = self.ingestion.build_documents_response(docs)
        summary = list(payload["items"])
        if payload.get("portal"):
            summary.append(payload["portal"])
        pkg.process_documents_summary = summary
        await self.db.flush()

    async def download_process_document_file(
        self,
        opportunity_id: uuid.UUID,
        process_document_id: uuid.UUID,
        *,
        disposition: str = "inline",
    ) -> tuple[bytes, str, str]:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        doc = await self.db.get(DGCPProcessDocument, process_document_id)
        if not doc or doc.opportunity_id != opportunity_id or doc.tenant_id != self.tenant_id:
            raise ValueError("Documento de proceso no encontrado")
        content, mime = await self.ingestion.read_process_file(opportunity, doc)
        filename = (doc.metadata_ or {}).get("storage_filename") or f"{doc.title}.txt"
        return content, mime, filename

    async def get_alerts(self, opportunity_id: uuid.UUID) -> DGCPBidAlertResponse:
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")
        return DGCPBidAlertResponse(
            opportunity_id=opportunity_id,
            alerts=pkg.alerts or [],
            total=len(pkg.alerts or []),
        )

    async def autofill_preview(
        self,
        opportunity_id: uuid.UUID,
        *,
        form_type: str = "SNCC.F042",
        company: str = "justech",
        field_overrides: dict | None = None,
    ) -> DGCPFormAutofillPreviewResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        pkg = await self._get_package(opportunity_id)
        raw_input = pkg.user_input if pkg else {}
        # Solo campos de oferta del usuario; identidad corporativa viene del perfil
        user_input = {
            k: v
            for k, v in (raw_input or {}).items()
            if k in {"fabricante", "plazo_entrega", "garantia", "monto", "notes", "productos", "condiciones", "extra"}
        }
        return await self.forms.autofill_preview(
            opportunity,
            form_type=form_type,
            company=company,
            user_input=user_input,
            field_overrides=field_overrides,
        )

    async def generate_form(
        self,
        opportunity_id: uuid.UUID,
        *,
        form_type: str = "SNCC.F042",
        company: str = "justech",
        field_overrides: dict | None = None,
        draft: bool = False,
    ) -> DGCPFormGenerateResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        pkg = await self._get_package(opportunity_id)
        user_input = pkg.user_input if pkg else {}
        try:
            result = await self.forms.generate_controlled_copy(
                opportunity,
                form_type=form_type,
                company=company,
                user_input=user_input,
                field_overrides=field_overrides,
                draft=draft,
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if pkg:
            forms = list(pkg.generated_forms or [])
            forms.append(result.model_dump(mode="json"))
            pkg.generated_forms = forms
            await self.db.commit()
        return result

    async def autofill_document_pdf(
        self,
        opportunity_id: uuid.UUID,
        *,
        form_type: str,
        company: str = "justech",
        field_overrides: dict | None = None,
    ) -> tuple[bytes, str]:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        pkg = await self._get_package(opportunity_id)
        user_input = pkg.user_input if pkg else {}
        pdf = await self.forms.document_preview_pdf(
            opportunity,
            form_type=form_type,
            company=company,
            user_input=user_input,
            field_overrides=field_overrides,
        )
        safe = form_type.replace(".", "_")
        filename = f"{safe}_{opportunity.code.replace('/', '_')}_preview.pdf"
        return pdf, filename

    async def list_autofill_templates(self) -> list[dict]:
        from app.services.document_autofill.m365_template_resolver import M365TemplateResolver

        resolver = M365TemplateResolver(self.db, self.tenant_id, self.user_id)
        entries = await resolver.list_all_templates()
        return [
            {
                "template_key": e.template_key,
                "form_type": e.form_type,
                "name": e.name,
                "m365_file_id": str(e.m365_file_id),
                "parent_path": e.parent_path,
                "web_url": e.web_url,
                "detected_category": e.detected_category,
                "detected_label": e.detected_label,
                "format": e.format,
            }
            for e in entries
        ]

    async def save_autofill_alias_mapping(
        self,
        data,
        *,
        user_email: str | None = None,
    ) -> dict:
        return self.forms.save_alias_mapping(data, user_email=user_email)

    def list_autofill_canonical_fields(self) -> list[dict]:
        return self.forms.list_canonical_fields()

    async def apply_user_input(
        self,
        opportunity_id: uuid.UUID,
        data: DGCPUserInputRequest,
    ) -> dict:
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")
        merged = dict(pkg.user_input or {})
        for key, val in data.model_dump(exclude_unset=True).items():
            if key == "extra" and isinstance(val, dict):
                merged.update(val)
            elif val is not None:
                merged[key] = val
        pkg.user_input = merged

        checklist = [dict(item) for item in (pkg.checklist or [])]
        for item in checklist:
            form_type = item.get("form_type")
            if form_type and self._user_input_covers_form(form_type, merged):
                if item.get("status") == "requiere_completado":
                    item["status"] = "requiere_revision"
                    item["recommended_action"] = "Revisar copia generada antes de presentar"

        pkg.checklist = checklist
        opportunity = await self._get_opportunity(opportunity_id)
        if opportunity:
            bid = self.compliance.build_bid_package(
                opportunity,
                checklist,
                analyzed_at=pkg.analyzed_at,
            )
            pkg.bid_package = bid.model_dump(mode="json")
            opportunity = await self._get_opportunity(opportunity_id)
            if opportunity:
                pkg.expediente_status = self._effective_expediente_status(
                    opportunity, checklist, bid.preparation_pct, pkg
                )
            from app.services.dgcp_expediente_event_service import DGCPExpedienteEventService

            await DGCPExpedienteEventService.publish(
                pkg,
                event_type="user_input_applied",
                actor_id=self.user_id,
                detail={"keys": list(data.model_dump(exclude_unset=True).keys())},
                checklist=checklist,
                preparation_pct=bid.preparation_pct,
            )

        await self.db.commit()
        return merged

    @staticmethod
    def _user_input_covers_form(form_type: str | None, user_input: dict) -> bool:
        key = (form_type or "").upper()
        if any(token in key for token in ("042", "047", "033")):
            return bool(user_input.get("monto") or user_input.get("fabricante"))
        if "ECONOMICA" in key or "OFERTA" in key:
            return bool(user_input.get("monto"))
        return bool(user_input)

    async def validate_company_documents(
        self,
        opportunity_id: uuid.UUID,
        *,
        company_key: str = "justech",
    ) -> dict:
        from app.services.dgcp_expediente_validation_service import DGCPExpedienteValidationService

        return await DGCPExpedienteValidationService(
            self.db, self.tenant_id, user_id=self.user_id
        ).validate(opportunity_id, company_key=company_key)

    async def prepare_expediente(
        self,
        opportunity_id: uuid.UUID,
        *,
        company_key: str | None = None,
    ) -> DGCPExpedientePrepareResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        if opportunity.status not in EXPEDIENTE_TRACKING_STATUSES:
            raise ValueError(
                "Marque «Mostrar interés» (o avance a preparación) antes de preparar el expediente"
            )
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        resolved_company = company_key or getattr(opportunity, "company", None) or "justech"
        validation = await self.validate_company_documents(
            opportunity_id, company_key=resolved_company
        )
        # Continue with observaciones instead of hard-blocking export (keeps ZIP/structure usable).
        if validation.get("blocked"):
            logger.warning(
                "prepare_expediente company=%s incomplete — generating with observaciones",
                resolved_company,
            )

        final_validation = self._compute_final_validation(opportunity, pkg)
        user_input = dict(pkg.user_input or {})
        user_input["_final_validation"] = final_validation
        if validation.get("blocked"):
            user_input["_document_validation_observaciones"] = validation

        prepare_kwargs: dict = {
            "checklist": pkg.checklist or [],
            "matches": pkg.document_matches or [],
            "bid_package": pkg.bid_package or {},
            "user_input": user_input,
            "generated_forms": pkg.generated_forms or [],
        }
        import inspect

        if "company_key" in inspect.signature(self.expediente.prepare).parameters:
            prepare_kwargs["company_key"] = resolved_company

        result = await self.expediente.prepare(opportunity, **prepare_kwargs)
        pkg.expediente_status = result.expediente_status
        pkg.expediente_path = result.expediente_path
        merged_manifest = dict(result.manifest or {})
        prev = dict(pkg.manifest or {})
        if prev.get("event_history"):
            merged_manifest["event_history"] = prev["event_history"]
        if prev.get("final_validation"):
            merged_manifest.setdefault("final_validation", prev["final_validation"])
        merged_manifest["final_validation"] = final_validation
        if validation.get("blocked"):
            merged_manifest["validation_observaciones"] = validation
            merged_manifest["status_note"] = "generado_con_observaciones"
        pkg.manifest = merged_manifest
        # Keep bid_package metrics aligned with the export that was just built.
        bid = dict(pkg.bid_package or {})
        metrics = merged_manifest.get("metrics") or {}
        bid["preparation_pct"] = float(
            metrics.get("preparation_pct", result.preparation_pct) or result.preparation_pct
        )
        bid["found_documents"] = int(
            merged_manifest.get("checklist_summary", {}).get("found")
            or bid.get("found_documents")
            or 0
        )
        bid["pending_documents"] = int(
            metrics.get("pending_requirements")
            or merged_manifest.get("pending_requirements")
            or bid.get("pending_documents")
            or 0
        )
        bid["total_requirements"] = int(
            metrics.get("total_requirements")
            or merged_manifest.get("total_requirements")
            or bid.get("total_requirements")
            or 0
        )
        bid["compliant_count"] = int(
            metrics.get("completed_requirements")
            or merged_manifest.get("completed_requirements")
            or bid.get("compliant_count")
            or 0
        )
        bid["copied_documents"] = int(result.copied_documents)
        bid["total_documents"] = int(
            metrics.get("total_documents") or merged_manifest.get("total_documents") or 0
        )
        pkg.bid_package = bid
        from app.services.dgcp_expediente_event_service import DGCPExpedienteEventService

        await DGCPExpedienteEventService.publish(
            pkg,
            event_type="expediente_prepared",
            actor_id=self.user_id,
            detail={
                "summary": f"Expediente preparado ({result.preparation_pct:.0f}%)",
                "copied_documents": result.copied_documents,
                "listo": final_validation.get("listo_para_presentar"),
            },
            checklist=pkg.checklist or [],
            preparation_pct=result.preparation_pct,
        )
        await self.db.commit()
        return result

    async def get_expediente_status(self, opportunity_id: uuid.UUID) -> DGCPBidPackageStatusResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            return self.expediente.status(
                opportunity,
                expediente_status="sin_preparar",
                expediente_path=None,
                bid_package={},
                alerts=[],
                checklist=[],
            )
        bid_data = pkg.bid_package or {}
        prep = float(bid_data.get("preparation_pct") or 0)
        effective_status = self._effective_expediente_status(
            opportunity, pkg.checklist or [], prep, pkg
        )
        from app.services.dgcp_expediente_sync_service import DGCPExpedienteSyncService

        manifest = dict(pkg.manifest or {})
        if DGCPExpedienteSyncService.enabled() and not manifest.get("expediente_unified"):
            sync = DGCPExpedienteSyncService.sync_package(
                pkg,
                checklist=pkg.checklist or [],
                preparation_pct=prep,
                expediente_status=effective_status,
            )
            if sync.get("synced"):
                manifest = dict(pkg.manifest or {})
                await self.db.commit()
        return self.expediente.status(
            opportunity,
            expediente_status=effective_status,
            expediente_path=pkg.expediente_path,
            bid_package=pkg.bid_package or {},
            alerts=pkg.alerts or [],
            checklist=pkg.checklist or [],
            db_manifest=manifest,
        )

    async def mark_ready_for_review(self, opportunity_id: uuid.UUID) -> DGCPBidPackageStatusResponse:
        pkg = await self._get_package(opportunity_id)
        if not pkg or not pkg.expediente_path:
            raise ValueError("Prepare el expediente primero")
        if not self.compliance.can_mark_ready_for_review(pkg.checklist or []):
            raise ValueError(
                "No se puede marcar listo para revisión: hay requisitos faltantes, "
                "vencidos, por completar o sin validar vigencia."
            )
        pkg.expediente_status = "expediente_listo_para_revision"
        await self.db.commit()
        return await self.get_expediente_status(opportunity_id)

    async def get_required_forms(self, opportunity_id: uuid.UUID, *, company: str = "justech"):
        from app.services.dgcp_smart_autofill_service import DGCPSmartAutofillService

        return await DGCPSmartAutofillService(self.db, self.tenant_id, self.user_id).list_required_forms(
            opportunity_id, company=company
        )

    async def get_missing_fields(
        self,
        opportunity_id: uuid.UUID,
        *,
        form_type: str = "SNCC.F042",
        company: str = "justech",
    ):
        from app.services.dgcp_smart_autofill_service import DGCPSmartAutofillService

        return await DGCPSmartAutofillService(self.db, self.tenant_id, self.user_id).missing_fields(
            opportunity_id, form_type=form_type, company=company
        )

    async def resolve_missing_field(
        self,
        opportunity_id: uuid.UUID,
        data,
        *,
        form_type: str = "SNCC.F042",
        company: str = "justech",
    ):
        from app.services.dgcp_smart_autofill_service import DGCPSmartAutofillService

        return await DGCPSmartAutofillService(self.db, self.tenant_id, self.user_id).resolve_missing_field(
            opportunity_id, data, form_type=form_type, company=company
        )

    async def get_document_analysis(self, opportunity_id: uuid.UUID):
        from app.schemas.dgcp_autofill import DGCPDocumentAnalysisResponse

        pkg = await self._get_package(opportunity_id)
        manifest = (pkg.manifest if pkg else None) or {}
        hermes = manifest.get("hermes_document_analysis") or {}
        history = manifest.get("event_history") or []
        status = hermes.get("status") or "not_run"
        fallback = bool(hermes.get("fallback_used", status in ("failed", "skipped", "not_run")))
        evidence = hermes.get("evidence") or []
        if not evidence and pkg and pkg.requirement_evidence:
            evidence = list(pkg.requirement_evidence)[:100]
        return DGCPDocumentAnalysisResponse(
            opportunity_id=opportunity_id,
            status=status,
            confidence=float(hermes.get("confidence") or 0),
            summary=hermes.get("summary"),
            required_documents=hermes.get("required_documents") or [],
            missing_documents=hermes.get("missing_documents") or [],
            next_actions=hermes.get("next_actions") or [],
            risks=hermes.get("risks") or [],
            evidence=evidence,
            analyzed_at=hermes.get("analyzed_at"),
            event_history_count=len(history),
            fallback_used=fallback,
            message=hermes.get("message") or hermes.get("reason"),
        )

    async def download_expediente(self, opportunity_id: uuid.UUID) -> tuple[bytes, str]:
        pkg = await self._get_package(opportunity_id)
        if not pkg or not pkg.expediente_path:
            raise ValueError("Expediente no preparado")
        return self.expediente.build_download_archive(pkg.expediente_path)

    async def list_technical_sheets(self, opportunity_id: uuid.UUID):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).list_sheets(opportunity_id)

    async def detect_technical_sheets(self, opportunity_id: uuid.UUID, *, force: bool = False):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).detect(
            opportunity_id, force=force
        )

    async def select_technical_sheet_product(self, opportunity_id: uuid.UUID, sheet_id: str, data):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).select_product(
            opportunity_id, sheet_id, data
        )

    async def generate_technical_sheet_draft(
        self,
        opportunity_id: uuid.UUID,
        sheet_id: str,
        *,
        company: str = "justech",
        extra_notes: str | None = None,
    ):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).generate_draft(
            opportunity_id, sheet_id, company=company, extra_notes=extra_notes
        )

    async def approve_technical_sheet(self, opportunity_id: uuid.UUID, sheet_id: str):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).approve(
            opportunity_id, sheet_id
        )

    async def reject_technical_sheet(self, opportunity_id: uuid.UUID, sheet_id: str):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).reject(
            opportunity_id, sheet_id
        )

    async def export_technical_sheet(
        self,
        opportunity_id: uuid.UUID,
        sheet_id: str,
        *,
        fmt: str = "markdown",
        company: str | None = None,
    ):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).export_sheet(
            opportunity_id, sheet_id, fmt=fmt, company=company
        )

    async def get_technical_sheet_branding(
        self,
        opportunity_id: uuid.UUID,
        sheet_id: str,
        *,
        company: str | None = None,
    ):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).get_branding(
            opportunity_id, sheet_id, company=company
        )

    async def add_technical_sheet_image(
        self,
        opportunity_id: uuid.UUID,
        sheet_id: str,
        data,
        *,
        upload_path=None,
    ):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).add_image(
            opportunity_id, sheet_id, data, upload_path=upload_path
        )

    async def reorder_technical_sheet_images(self, opportunity_id: uuid.UUID, sheet_id: str, data):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).reorder_images(
            opportunity_id, sheet_id, data
        )

    async def remove_technical_sheet_image(self, opportunity_id: uuid.UUID, sheet_id: str, image_id: str):
        from app.services.dgcp_technical_sheet_service import DGCPTechnicalSheetService

        return await DGCPTechnicalSheetService(self.db, self.tenant_id, self.user_id).remove_image(
            opportunity_id, sheet_id, image_id
        )

    async def list_product_intelligence(self, opportunity_id: uuid.UUID):
        from app.services.dgcp_product_intelligence_service import DGCPProductIntelligenceService

        return await DGCPProductIntelligenceService(self.db, self.tenant_id, self.user_id).list_intelligence(
            opportunity_id
        )

    async def run_product_intelligence(
        self,
        opportunity_id: uuid.UUID,
        *,
        force: bool = False,
    ):
        from app.services.dgcp_product_intelligence_service import DGCPProductIntelligenceService

        return await DGCPProductIntelligenceService(self.db, self.tenant_id, self.user_id).run_pipeline(
            opportunity_id, force=force
        )

    async def search_product_candidates(
        self,
        opportunity_id: uuid.UUID,
        requirement_id: str,
        *,
        include_internet: bool = True,
        include_repository: bool = True,
        include_commercial: bool = True,
    ):
        from app.services.dgcp_product_intelligence_service import DGCPProductIntelligenceService

        return await DGCPProductIntelligenceService(self.db, self.tenant_id, self.user_id).search_candidates(
            opportunity_id,
            requirement_id,
            include_internet=include_internet,
            include_repository=include_repository,
            include_commercial=include_commercial,
        )

    async def build_product_compliance_matrix(
        self,
        opportunity_id: uuid.UUID,
        requirement_id: str,
        candidate_id: str,
    ):
        from app.services.dgcp_product_intelligence_service import DGCPProductIntelligenceService

        return await DGCPProductIntelligenceService(self.db, self.tenant_id, self.user_id).build_matrix(
            opportunity_id, requirement_id, candidate_id
        )

    async def approve_product_intelligence(
        self,
        opportunity_id: uuid.UUID,
        requirement_id: str,
        data,
    ):
        from app.services.dgcp_product_intelligence_service import DGCPProductIntelligenceService

        return await DGCPProductIntelligenceService(self.db, self.tenant_id, self.user_id).approve_product(
            opportunity_id, requirement_id, data
        )

    async def reject_product_intelligence(self, opportunity_id: uuid.UUID, requirement_id: str):
        from app.services.dgcp_product_intelligence_service import DGCPProductIntelligenceService

        return await DGCPProductIntelligenceService(self.db, self.tenant_id, self.user_id).reject_product(
            opportunity_id, requirement_id
        )

    async def get_offer_preparation_center(self, opportunity_id: uuid.UUID):
        from app.services.dgcp_offer_preparation_center_service import DGCPOfferPreparationCenterService

        return await DGCPOfferPreparationCenterService(self.db, self.tenant_id, self.user_id).get_center(
            opportunity_id
        )

    async def generate_consolidated_technical_offer(self, opportunity_id: uuid.UUID):
        from app.services.dgcp_offer_preparation_center_service import DGCPOfferPreparationCenterService

        return await DGCPOfferPreparationCenterService(
            self.db, self.tenant_id, self.user_id
        ).generate_consolidated_offer(opportunity_id)

    async def get_process_updates(self, opportunity_id: uuid.UUID):
        from app.services.dgcp_process_update_service import DGCPProcessUpdateService

        return await DGCPProcessUpdateService(self.db, self.tenant_id, self.user_id).get_updates(
            opportunity_id
        )

    async def check_process_updates(self, opportunity_id: uuid.UUID):
        from app.services.dgcp_process_update_service import DGCPProcessUpdateService

        return await DGCPProcessUpdateService(self.db, self.tenant_id, self.user_id).check_now(
            opportunity_id
        )

    async def mark_process_update_reviewed(self, opportunity_id: uuid.UUID, update_id: str, note: str | None = None):
        from app.services.dgcp_process_update_service import DGCPProcessUpdateService

        return await DGCPProcessUpdateService(self.db, self.tenant_id, self.user_id).mark_reviewed(
            opportunity_id, update_id, note
        )

    async def mark_process_update_applied(self, opportunity_id: uuid.UUID, update_id: str, note: str | None = None):
        from app.services.dgcp_process_update_service import DGCPProcessUpdateService

        return await DGCPProcessUpdateService(self.db, self.tenant_id, self.user_id).mark_applied(
            opportunity_id, update_id, note
        )

    async def simulate_process_updates(self, opportunity_id: uuid.UUID, scenarios: list[str]):
        from app.services.dgcp_process_update_service import DGCPProcessUpdateService

        return await DGCPProcessUpdateService(self.db, self.tenant_id, self.user_id).simulate(
            opportunity_id, scenarios
        )

    async def get_process_updates_dashboard(self):
        from app.services.dgcp_process_update_service import DGCPProcessUpdateService

        return await DGCPProcessUpdateService(self.db, self.tenant_id, self.user_id).dashboard()
