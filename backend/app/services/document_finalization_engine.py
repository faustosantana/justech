"""Motor de finalización documental — firma, sello, PDF final y expediente DGCP."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.dgcp_process_document import DGCPProcessDocument
from app.models.document_finalization import DocumentFinalizationRecord
from app.schemas.document_finalization import (
    DocumentFinalizationBatchResponse,
    DocumentFinalizationGenerateRequest,
    DocumentFinalizationGenerateResponse,
    DocumentFinalizationPreviewRequest,
    DocumentFinalizationPreviewResponse,
    DocumentFinalizationRecordResponse,
)
from app.services.audit_service import AuditService
from app.services.company_scope_filter import CompanyScopeFilter
from app.services.corporate_identity_constants import COMPANY_LABELS
from app.services.corporate_identity_service import CorporateIdentityService
from app.services.dgcp_bid_package_service import DGCPBidPackageService
from app.services.dgcp_compliance_engine import DGCPComplianceEngine
from app.services.dgcp_form_autofill_service import DGCPFormAutofillService
from app.services.dgcp_process_storage_service import DGCPProcessStorageService
from app.services.document_finalization_rules import (
    REQUIREMENT_OUTPUT_BASENAME,
    REQUIREMENT_TO_EXPEDIENTE_FOLDER,
    REQUIREMENTS_REQUIRING_FINALIZATION,
    requires_finalization,
)
from app.services.global_company_context_service import GlobalCompanyContextService
from app.services.pdf_signature_overlay import apply_signature_and_stamp, text_to_pdf_bytes
from app.services.task_service import TaskService
from app.schemas.tasks import TaskCreateRequest


class DocumentFinalizationEngine:
    def __init__(self, db, tenant_id: uuid.UUID, *, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.identity = CorporateIdentityService(db, tenant_id, user_id=user_id)
        self.bid_svc = DGCPBidPackageService(db, tenant_id, user_id=user_id)
        self.compliance = DGCPComplianceEngine()
        self.forms = DGCPFormAutofillService(db, tenant_id)
        self.audit = AuditService(db)
        self.scope = CompanyScopeFilter(db, tenant_id, user_id) if user_id else None

    async def preview(
        self,
        opportunity_id: uuid.UUID,
        payload: DocumentFinalizationPreviewRequest,
    ) -> DocumentFinalizationPreviewResponse:
        opportunity, item, company_key = await self._resolve_context(opportunity_id, payload)
        req_key = payload.requirement_key
        if not requires_finalization(req_key):
            raise ValueError(f"Requisito {req_key} no requiere PDF final firmado/sellado")

        sig_path, sig_name, sig_status = await self.identity.resolve_signature_path(payload.signature_filename)
        stamp_path, stamp_name, stamp_status = await self.identity.resolve_stamp_path(
            company_key, filename=payload.stamp_filename
        )
        if stamp_name:
            await self.identity.assert_stamp_allowed(company_key, stamp_name)

        source_doc, source_name = await self._resolve_source_pdf(opportunity, item, payload)
        warnings: list[str] = []
        if sig_status != "disponible":
            warnings.append(f"Firma {sig_name or '—'}: {sig_status}")
        if stamp_status != "disponible":
            warnings.append(f"Sello {stamp_name or '—'}: {stamp_status}")
        if not source_doc and not source_name:
            warnings.append("No hay documento base PDF/DOCX asociado — se generará borrador de texto")

        placement = self.identity.placement_for(req_key)
        can_finalize = sig_status == "disponible" and stamp_status == "disponible"

        return DocumentFinalizationPreviewResponse(
            opportunity_id=opportunity_id,
            requirement_key=req_key,
            document_type=req_key,
            document_title=item.get("document_title") or item.get("requirement"),
            company_key=company_key,
            company_label=COMPANY_LABELS.get(company_key, company_key),
            signature={"filename": sig_name, "status": sig_status, "path": str(sig_path) if sig_path else None},
            stamp={"filename": stamp_name, "status": stamp_status, "path": str(stamp_path) if stamp_path else None},
            placement=placement,
            source_filename=source_name,
            warnings=warnings,
            can_finalize=can_finalize,
            requires_signature=True,
            requires_stamp=True,
        )

    async def generate_final(
        self,
        opportunity_id: uuid.UUID,
        payload: DocumentFinalizationGenerateRequest,
    ) -> DocumentFinalizationGenerateResponse:
        if not self.user_id:
            raise ValueError("Usuario requerido")

        preview = await self.preview(opportunity_id, payload)
        if not preview.can_finalize:
            raise ValueError("No se puede generar PDF final: " + "; ".join(preview.warnings))

        opportunity, item, company_key = await self._resolve_context(opportunity_id, payload)
        pkg = await self.bid_svc._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        req_key = payload.requirement_key
        prev_status = item.get("status", "faltante")
        pdf_bytes, source_name, source_doc_id = await self._load_source_bytes(opportunity, item, payload)

        sig_path, sig_name, _ = await self.identity.resolve_signature_path(payload.signature_filename)
        stamp_path, stamp_name, _ = await self.identity.resolve_stamp_path(
            company_key, filename=payload.stamp_filename
        )
        await self.identity.assert_stamp_allowed(company_key, stamp_name)

        placement = self.identity.placement_for(req_key)
        final_bytes = apply_signature_and_stamp(
            pdf_bytes,
            signature_path=sig_path,
            stamp_path=stamp_path,
            placement=placement,
        )

        out_name = REQUIREMENT_OUTPUT_BASENAME.get(req_key, f"{req_key.upper()}_FINAL.pdf")
        folder = REQUIREMENT_TO_EXPEDIENTE_FOLDER.get(req_key, "06_Revision")
        expediente_base = self._expediente_dir(opportunity)
        target_folder = expediente_base / folder
        target_folder.mkdir(parents=True, exist_ok=True)

        storage = DGCPProcessStorageService(self.tenant_id)
        proc_filename = out_name.replace(".pdf", f"_{opportunity.code.replace('/', '-')}.pdf")
        storage.write_bytes(opportunity.code, proc_filename, final_bytes)

        now = datetime.now(timezone.utc)
        process_doc = DGCPProcessDocument(
            tenant_id=self.tenant_id,
            opportunity_id=opportunity_id,
            title=f"PDF final — {item.get('requirement', req_key)}",
            source_type="finalization",
            doc_role="final_pdf",
            priority="alta",
            format="pdf",
            ingestion_status="registered",
            metadata_={
                "storage_filename": proc_filename,
                "storage_uri": storage.relative_uri(opportunity.code, proc_filename),
                "requirement_key": req_key,
                "checklist_item_id": str(item.get("id")),
                "scope": "dgcp_final",
                "company_key": company_key,
                "signature": sig_name,
                "stamp": stamp_name,
                "source_filename": source_name,
                "finalized_at": now.isoformat(),
            },
        )
        self.db.add(process_doc)
        await self.db.flush()

        dest = target_folder / out_name
        dest.write_bytes(final_bytes)

        record = DocumentFinalizationRecord(
            tenant_id=self.tenant_id,
            opportunity_id=opportunity_id,
            requirement_key=req_key,
            checklist_item_id=uuid.UUID(str(item["id"])) if item.get("id") else None,
            document_type=req_key,
            company_key=company_key,
            source_document_id=source_doc_id,
            source_filename=source_name,
            signature_filename=sig_name,
            stamp_filename=stamp_name,
            output_filename=out_name,
            output_storage_uri=str(dest.relative_to(expediente_base)),
            previous_status=prev_status,
            new_status="finalizado",
            created_by=self.user_id,
            finalized_at=now,
            metadata_={
                "expediente_folder": folder,
                "process_document_id": str(process_doc.id),
                "regenerate": payload.regenerate,
            },
            notes=payload.notes,
        )
        self.db.add(record)

        checklist = self.bid_svc._deep_copy_checklist(pkg.checklist)
        target = next((i for i in checklist if str(i.get("id")) == str(item.get("id"))), item)
        target["process_document_id"] = str(process_doc.id)
        target["document_title"] = process_doc.title
        target["match_source"] = "finalization"
        target["relative_path"] = process_doc.metadata_.get("storage_uri")
        target["status"] = "finalizado"
        target["display_status"] = self.compliance.display_status_label("finalizado")
        target["final_pdf_uri"] = record.output_storage_uri
        target["finalized_at"] = now.isoformat()

        matches = [dict(m) for m in (pkg.document_matches or [])]
        for match in matches:
            if match.get("requirement_key") == req_key:
                match.update({
                    "process_document_id": str(process_doc.id),
                    "document_title": process_doc.title,
                    "match_source": "finalization",
                    "relative_path": record.output_storage_uri,
                    "status": "finalizado",
                    "match_score": 99.0,
                })
                break
        else:
            matches.append({
                "requirement_key": req_key,
                "requirement_label": target.get("requirement", req_key),
                "process_document_id": str(process_doc.id),
                "document_title": process_doc.title,
                "status": "finalizado",
                "match_source": "finalization",
                "relative_path": record.output_storage_uri,
            })

        bid = self.compliance.build_bid_package(opportunity, checklist, analyzed_at=pkg.analyzed_at)
        expediente_status = self.bid_svc._effective_expediente_status(
            opportunity, checklist, bid.preparation_pct, pkg
        )
        pkg.checklist = checklist
        pkg.document_matches = matches
        pkg.bid_package = bid.model_dump(mode="json")
        pkg.expediente_status = expediente_status

        await self.audit.log(
            action="dgcp.document_finalization.generate",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="document_finalization",
            resource_id=record.id,
            details={
                "opportunity_id": str(opportunity_id),
                "requirement_key": req_key,
                "company_key": company_key,
                "signature": sig_name,
                "stamp": stamp_name,
                "output": out_name,
                "previous_status": prev_status,
                "new_status": "finalizado",
            },
        )
        await self.db.commit()

        return DocumentFinalizationGenerateResponse(
            record=self._record_response(record, opportunity_id),
            preparation_pct=bid.preparation_pct,
            expediente_status=expediente_status,
            checklist_status="finalizado",
            message="PDF final generado — original intacto, copia en expediente",
        )

    async def generate_all_ready(
        self,
        opportunity_id: uuid.UUID,
        *,
        company_key: str | None = None,
    ) -> DocumentFinalizationBatchResponse:
        pkg = await self.bid_svc._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")
        processed: list[DocumentFinalizationRecordResponse] = []
        skipped: list[dict[str, str]] = []
        warnings: list[str] = []

        for item in pkg.checklist or []:
            key = item.get("requirement_key") or ""
            if key not in REQUIREMENTS_REQUIRING_FINALIZATION:
                continue
            if item.get("status") in ("finalizado", "pdf_final_generado", "no_aplica"):
                skipped.append({"requirement_key": key, "reason": "Ya finalizado"})
                continue
            if not self._item_has_source(item):
                skipped.append({"requirement_key": key, "reason": "Sin documento base"})
                continue
            try:
                res = await self.generate_final(
                    opportunity_id,
                    DocumentFinalizationGenerateRequest(
                        requirement_key=key,
                        checklist_item_id=uuid.UUID(str(item["id"])) if item.get("id") else None,
                        company_key=company_key,
                    ),
                )
                processed.append(res.record)
            except Exception as exc:
                skipped.append({"requirement_key": key, "reason": str(exc)})
                warnings.append(f"{key}: {exc}")

        pkg = await self.bid_svc._get_package(opportunity_id)
        bid = (pkg.bid_package or {}) if pkg else {}
        return DocumentFinalizationBatchResponse(
            processed=processed,
            skipped=skipped,
            warnings=warnings,
            preparation_pct=float(bid.get("preparation_pct") or 0),
            expediente_status=pkg.expediente_status if pkg else None,
        )

    async def get_final_file(self, record_id: uuid.UUID) -> tuple[bytes, str, str]:
        record = await self.db.get(DocumentFinalizationRecord, record_id)
        if not record or record.tenant_id != self.tenant_id:
            raise ValueError("Registro no encontrado")
        opp = await self.db.get(DGCPOpportunity, record.opportunity_id)
        if not opp:
            raise ValueError("Licitación no encontrada")
        path = self._expediente_dir(opp) / record.output_storage_uri
        if not path.is_file():
            raise ValueError("PDF final no disponible")
        return path.read_bytes(), record.output_filename, "application/pdf"

    async def list_records(self, opportunity_id: uuid.UUID) -> list[DocumentFinalizationRecordResponse]:
        result = await self.db.execute(
            select(DocumentFinalizationRecord).where(
                DocumentFinalizationRecord.tenant_id == self.tenant_id,
                DocumentFinalizationRecord.opportunity_id == opportunity_id,
            )
        )
        return [self._record_response(r, opportunity_id) for r in result.scalars().all()]

    async def _resolve_context(
        self,
        opportunity_id: uuid.UUID,
        payload: DocumentFinalizationPreviewRequest,
    ) -> tuple[DGCPOpportunity, dict, str]:
        opp = await self.db.get(DGCPOpportunity, opportunity_id)
        if not opp or opp.tenant_id != self.tenant_id:
            raise ValueError("Licitación no encontrada")
        self.bid_svc._require_operational_interest(opp)

        pkg = await self.bid_svc._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        item = None
        if payload.checklist_item_id:
            item = next(
                (i for i in (pkg.checklist or []) if str(i.get("id")) == str(payload.checklist_item_id)),
                None,
            )
        if not item:
            item = next(
                (i for i in (pkg.checklist or []) if i.get("requirement_key") == payload.requirement_key),
                None,
            )
        if not item:
            raise ValueError("Ítem de checklist no encontrado")

        company_key = self.identity.normalize_company_key(payload.company_key)
        if not company_key and self.user_id:
            ctx = await GlobalCompanyContextService(self.db, self.tenant_id, self.user_id).get_context()
            if ctx.active_company_name:
                company_key = CompanyScopeFilter.odoo_name_to_dgcp_key(ctx.active_company_name)
            keys = await self.scope.dgcp_company_keys() if self.scope else []
            company_key = company_key or (keys[0] if keys else "justech")
        company_key = company_key or "justech"

        if self.scope:
            label = COMPANY_LABELS.get(company_key, company_key)
            await self.scope.assert_company_name_allowed(label)

        return opp, item, company_key

    async def _resolve_source_pdf(
        self,
        opportunity: DGCPOpportunity,
        item: dict,
        payload: DocumentFinalizationPreviewRequest,
    ) -> tuple[DGCPProcessDocument | None, str | None]:
        doc_id = payload.source_process_document_id or item.get("process_document_id")
        if not doc_id:
            return None, None
        proc = await self.db.get(DGCPProcessDocument, uuid.UUID(str(doc_id)))
        if not proc or proc.tenant_id != self.tenant_id:
            return None, None
        meta = proc.metadata_ or {}
        name = meta.get("storage_filename") or proc.title
        return proc, name

    async def _load_source_bytes(
        self,
        opportunity: DGCPOpportunity,
        item: dict,
        payload: DocumentFinalizationPreviewRequest,
    ) -> tuple[bytes, str | None, uuid.UUID | None]:
        proc, name = await self._resolve_source_pdf(opportunity, item, payload)
        if proc:
            storage = DGCPProcessStorageService(self.tenant_id)
            meta = proc.metadata_ or {}
            fname = meta.get("storage_filename")
            if fname:
                data = storage.read_bytes(opportunity.code, fname)
                if fname.lower().endswith(".pdf"):
                    return data, fname, proc.id
                if fname.lower().endswith((".docx", ".doc")):
                    return self._docx_or_fallback_pdf(item, opportunity), fname, proc.id
                return data, fname, proc.id

        # SNCC / carta: generar PDF base desde autollenado
        form_map = {
            "sncc_f033": "SNCC.F033",
            "sncc_f034": "SNCC.F034",
            "sncc_f042": "SNCC.F042",
            "sncc_f047": "SNCC.F047",
            "carta_presentacion": "CARTA.PRESENTACION",
        }
        form_type = form_map.get(payload.requirement_key)
        if form_type:
            preview = await self.forms.autofill_preview(opportunity, form_type=form_type)
            lines = [f"{f.label}: {f.value or '—'}" for f in preview.fields]
            pdf = text_to_pdf_bytes(preview.form_type, lines)
            return pdf, f"{form_type}_BORRADOR.pdf", None

        lines = [item.get("requirement") or payload.requirement_key, opportunity.code]
        return text_to_pdf_bytes(payload.requirement_key, lines), f"{payload.requirement_key}_BORRADOR.pdf", None

    @staticmethod
    def _docx_or_fallback_pdf(item: dict, opportunity: DGCPOpportunity) -> bytes:
        lines = [
            item.get("document_title") or "Documento",
            f"Licitación {opportunity.code}",
            "Conversión DOCX→PDF pendiente — contenido placeholder para firma/sello",
        ]
        return text_to_pdf_bytes(item.get("requirement_key") or "documento", lines)

    @staticmethod
    def _item_has_source(item: dict) -> bool:
        return bool(item.get("process_document_id") or item.get("document_id") or item.get("knowledge_asset_id"))

    def _expediente_dir(self, opportunity: DGCPOpportunity) -> Path:
        safe = opportunity.code.replace("/", "_")
        return Path(settings.expediente_storage_path) / str(self.tenant_id) / safe

    def _record_response(
        self,
        record: DocumentFinalizationRecord,
        opportunity_id: uuid.UUID,
    ) -> DocumentFinalizationRecordResponse:
        return DocumentFinalizationRecordResponse(
            id=record.id,
            requirement_key=record.requirement_key,
            document_type=record.document_type,
            output_filename=record.output_filename,
            output_storage_uri=record.output_storage_uri,
            previous_status=record.previous_status,
            new_status=record.new_status,
            signature_filename=record.signature_filename,
            stamp_filename=record.stamp_filename,
            company_key=record.company_key,
            finalized_at=record.finalized_at,
            download_url=f"/api/v1/dgcp/opportunities/{opportunity_id}/finalization/{record.id}/file",
        )

    async def ensure_identity_tasks(self, opportunity_id: uuid.UUID, company_key: str) -> None:
        """Crea tareas únicas si falta firma o sello."""
        if not self.user_id:
            return
        alerts = await self.identity.detect_missing_alerts(company_key)
        if not alerts:
            return
        tasks = TaskService(self.db, self.tenant_id, user_id=self.user_id)
        from app.models.task import Task
        from sqlalchemy import select

        for alert in alerts:
            task_type = "load_signature" if "firma" in alert.lower() else "load_stamp"
            dedup_key = f"{self.tenant_id}:{company_key}:{opportunity_id}:{task_type}"
            result = await self.db.execute(
                select(Task).where(
                    Task.tenant_id == self.tenant_id,
                    Task.dgcp_process_id == opportunity_id,
                    Task.status.in_(("pendiente", "en_proceso")),
                )
            )
            if any((t.metadata_ or {}).get("finalization_dedup") == dedup_key for t in result.scalars()):
                continue
            await tasks.create_task(
                TaskCreateRequest(
                    title=alert[:120],
                    description=f"Identidad corporativa requerida para expediente DGCP.\nOportunidad: {opportunity_id}",
                    category="dgcp",
                    department="legal",
                    priority="alta",
                    source="document_finalization",
                    dgcp_process_id=opportunity_id,
                    metadata={
                        "task_type": task_type,
                        "finalization_dedup": dedup_key,
                        "company_key": company_key,
                    },
                    tags=["dgcp", "identidad_corporativa"],
                )
            )
