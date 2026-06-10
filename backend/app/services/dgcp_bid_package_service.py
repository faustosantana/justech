"""DGCP Bid Package — análisis, checklist, expediente y matching (Fase 7.1)."""

from __future__ import annotations

import uuid
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
OPERATIONAL_INTEREST_STATUSES = frozenset({"interested", "to_bid", "won", "lost"})
EXPEDIENTE_TRACKING_STATUSES = frozenset({"to_bid", "won", "lost"})

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
        self.forms = DGCPFormAutofillService(db, tenant_id)
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
            await self.db.commit()
            await self.db.refresh(winner)
            return winner

    async def analyze(self, opportunity_id: uuid.UUID) -> DGCPAnalyzeResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self._require_operational_interest(opportunity)

        process_docs_summary = await self.ingestion.ingest(opportunity)
        process_corpus, process_docs = await self.ingestion.build_extraction_corpus(opportunity_id)
        related = await self._related_document_text(opportunity)
        extraction = self.extractor.extract(
            opportunity,
            related_text=related,
            process_corpus=process_corpus,
            process_documents=process_docs,
        )
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

        matches = await self.matcher.match_all(all_reqs)
        existing_pkg = await self._get_package(opportunity_id)
        prev_checklist = existing_pkg.checklist if existing_pkg else []
        checklist = self.compliance.build_checklist(
            all_reqs, matches, prev_checklist, sncc_form_map=SNCC_FORM_MAP
        )
        now = datetime.now(timezone.utc)
        bid = self.compliance.build_bid_package(opportunity, checklist, analyzed_at=now)
        analysis_warnings = self.compliance.build_analysis_warnings(process_docs_summary, extraction)
        risks = self._build_risks(checklist, opportunity, analysis_warnings)
        alerts = self.alerts_svc.build_alerts(
            opportunity, checklist, matches, analysis_warnings=analysis_warnings
        )
        requirements = self._build_requirements_response(opportunity, extraction, now)
        expediente_status = self._effective_expediente_status(
            opportunity, checklist, bid.preparation_pct, existing_pkg
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
        )

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
        )

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
        parsed = [self._checklist_item_from_dict(i) for i in items]
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
                total_requirements=0,
                mandatory_requirements=0,
                compliant_count=0,
                found_documents=0,
                pending_documents=0,
                expired_documents=0,
                forms_to_complete=0,
                review_count=0,
            )
        return DGCPBidPackageResponse(**pkg.bid_package)

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
        if not payload.document_id and not payload.knowledge_asset_id:
            raise ValueError("Indique document_id o knowledge_asset_id")

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
            if target.get("requirement_key", "").startswith("sncc_"):
                new_status = "requiere_completado"

        if payload.knowledge_asset_id:
            asset = await self.db.get(KnowledgeAsset, payload.knowledge_asset_id)
            if (
                not asset
                or asset.tenant_id != self.tenant_id
                or not asset.is_active
                or asset.folder_category not in OFFICIAL_KNOWLEDGE_FOLDERS
            ):
                raise ValueError("Documento corporativo no válido (carpeta oficial requerida)")
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
        target["display_status"] = self.compliance.display_status_label(new_status)
        target.pop("manual_validation", None)

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
                extracted_text = asset.extracted_text
                source = get_knowledge_source_provider()
                if not extracted_text and source.is_available() and asset.relative_path:
                    try:
                        content = source.read_bytes(asset.relative_path)
                        extracted_text = DocumentExtractionService().extract(
                            content, filename=asset.filename
                        ).text
                    except Exception:
                        pass
                download_url = f"/api/v1/knowledge/assets/{asset.id}/file"
                preview_url = download_url
                metadata = {
                    "filename": asset.filename,
                    "relative_path": asset.relative_path,
                    "folder_category": asset.folder_category,
                    "file_size": asset.file_size,
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
        preview = completion.preview(form_type=form_type, company_key=company)

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

    async def get_process_documents(self, opportunity_id: uuid.UUID) -> DGCPProcessDocumentsResponse:
        from app.services.dgcp_attachment_ingestion_service import PROCESS_SOURCE_TYPES

        pkg = await self._get_package(opportunity_id)
        raw = pkg.process_documents_summary if pkg else []
        items = [i for i in raw if i.get("source_type") in PROCESS_SOURCE_TYPES]
        return DGCPProcessDocumentsResponse(
            opportunity_id=opportunity_id,
            items=items,
            total=len(items),
        )

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
    ) -> DGCPFormAutofillPreviewResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        pkg = await self._get_package(opportunity_id)
        user_input = pkg.user_input if pkg else {}
        return await self.forms.autofill_preview(
            opportunity, form_type=form_type, company=company, user_input=user_input
        )

    async def generate_form(
        self,
        opportunity_id: uuid.UUID,
        *,
        form_type: str = "SNCC.F042",
        company: str = "justech",
    ) -> DGCPFormGenerateResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        pkg = await self._get_package(opportunity_id)
        user_input = pkg.user_input if pkg else {}
        result = await self.forms.generate_controlled_copy(
            opportunity, form_type=form_type, company=company, user_input=user_input
        )
        if pkg:
            forms = list(pkg.generated_forms or [])
            forms.append(result.model_dump(mode="json"))
            pkg.generated_forms = forms
            await self.db.commit()
        return result

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

    async def prepare_expediente(self, opportunity_id: uuid.UUID) -> DGCPExpedientePrepareResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        if opportunity.status not in EXPEDIENTE_TRACKING_STATUSES:
            raise ValueError("Marque «Licitar» (en preparación) antes de preparar el expediente")
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        result = await self.expediente.prepare(
            opportunity,
            checklist=pkg.checklist or [],
            matches=pkg.document_matches or [],
            bid_package=pkg.bid_package or {},
            user_input=pkg.user_input or {},
            generated_forms=pkg.generated_forms or [],
        )
        pkg.expediente_status = result.expediente_status
        pkg.expediente_path = result.expediente_path
        pkg.manifest = result.manifest
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
        return self.expediente.status(
            opportunity,
            expediente_status=effective_status,
            expediente_path=pkg.expediente_path,
            bid_package=pkg.bid_package or {},
            alerts=pkg.alerts or [],
            checklist=pkg.checklist or [],
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

    async def download_expediente(self, opportunity_id: uuid.UUID) -> tuple[bytes, str]:
        pkg = await self._get_package(opportunity_id)
        if not pkg or not pkg.expediente_path:
            raise ValueError("Expediente no preparado")
        return self.expediente.build_download_archive(pkg.expediente_path)
