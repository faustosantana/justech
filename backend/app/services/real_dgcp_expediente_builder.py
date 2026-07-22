"""Motor de expediente real DGCP — Fase 3 / 3.5."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.dgcp_process_document import DGCPProcessDocument
from app.models.document_finalization import DocumentFinalizationRecord
from app.schemas.real_expediente import (
    RealExpedienteGenerateResponse,
    RealExpedienteStatusResponse,
    RealExpedienteValidationResponse,
)
from app.services.audit_service import AuditService
from app.services.company_scope_filter import CompanyScopeFilter
from app.services.dgcp_compliance_engine import DGCPComplianceEngine, COMPLIANT_STATUSES
from app.services.dgcp_process_storage_service import DGCPProcessStorageService
from app.services.document_finalization_rules import (
    REQUIREMENT_OUTPUT_BASENAME,
    REQUIREMENTS_REQUIRING_FINALIZATION,
    requires_finalization,
)
from app.services.global_company_context_service import GlobalCompanyContextService
from app.services.knowledge_source_provider import get_knowledge_source_provider
from app.services.real_expediente_classifier import (
    REAL_EXPEDIENTE_FOLDERS,
    classify_requirement,
    compute_real_expediente_status,
    is_ready_for_upload,
)
from app.services.dgcp_operational_stages import (
    STAGE_LABELS,
    expediente_status_for_real,
    operational_stage_for_real_status,
)
from app.services.real_expediente_report_pdf import build_preparation_report_pdf


class RealDGCPExpedienteBuilder:
    PACKAGE_ROOT = "EXPEDIENTES_DGCP"
    PRESENTATION_ROOT = "12_EXPEDIENTES"

    def __init__(self, db, tenant_id: uuid.UUID, *, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.audit = AuditService(db)
        self.compliance = DGCPComplianceEngine()
        self.source = get_knowledge_source_provider()

    @staticmethod
    def safe_code(opportunity: DGCPOpportunity) -> str:
        return DGCPProcessStorageService.sanitize_code(opportunity.code)

    def expediente_base(self, opportunity: DGCPOpportunity) -> Path:
        return (
            Path(settings.expediente_storage_path)
            / str(self.tenant_id)
            / self.PACKAGE_ROOT
            / self.safe_code(opportunity)
            / "EXPEDIENTE"
        )

    def zip_path(self, opportunity: DGCPOpportunity, company_slug: str) -> Path:
        parent = self.expediente_base(opportunity).parent
        name = f"{self.safe_code(opportunity)}_EXPEDIENTE_DGCP.zip"
        return parent / name

    async def generate(
        self,
        opportunity_id: uuid.UUID,
        *,
        company_key: str | None = None,
    ) -> RealExpedienteGenerateResponse:
        if not self.user_id:
            raise ValueError("Usuario requerido")

        opportunity, pkg = await self._load_package(opportunity_id)
        company_name, company_slug = await self._resolve_company(company_key)

        if pkg.real_expediente_generated_at and pkg.analyzed_at and pkg.analyzed_at > pkg.real_expediente_generated_at:
            pkg.real_expediente_status = "requiere_actualizacion"

        base = self.expediente_base(opportunity)
        if base.exists():
            shutil.rmtree(base)
        for folder in REAL_EXPEDIENTE_FOLDERS:
            (base / folder).mkdir(parents=True, exist_ok=True)

        checklist = pkg.checklist or []
        matches = {m.get("requirement_key"): m for m in (pkg.document_matches or [])}
        finals = await self._load_finalization_map(opportunity_id)
        storage = DGCPProcessStorageService(self.tenant_id)

        files_meta: list[dict] = []
        requirements_meta: list[dict] = []
        missing: list[dict] = []
        expired: list[dict] = []
        requires_review: list[dict] = []
        ready_to_upload: list[dict] = []
        warnings: list[str] = []
        audit_entries: list[dict] = []

        bid = pkg.bid_package or {}
        prep_pct = float(bid.get("preparation_pct") or 0)

        for item in checklist:
            req_key = item.get("requirement_key") or ""
            req_name = item.get("requirement") or req_key
            status = item.get("status") or "faltante"
            mandatory = bool(item.get("mandatory", True))
            folder = classify_requirement(req_key, item.get("tipo") or "")

            file_bytes, filename, source, signed, stamped, is_final = await self._resolve_file(
                opportunity,
                item,
                matches.get(req_key),
                finals.get(req_key),
                storage,
            )

            if not file_bytes and mandatory and status in ("faltante", "pendiente", "borrador_pendiente"):
                ph_name = f"FALTA_{self._safe_filename(req_name)}.txt"
                ph_content = self._placeholder_content(opportunity, item)
                dest_folder = "07_Revision"
                dest = base / dest_folder / ph_name
                dest.write_text(ph_content, encoding="utf-8")
                missing.append({"requirement_key": req_key, "name": req_name, "file": ph_name})
                requirements_meta.append(self._req_meta(
                    item, folder=dest_folder, assigned=ph_name, ready=False,
                    notes="Documento faltante — placeholder en revisión",
                ))
                continue

            if status in ("encontrado_vencido", "vencido"):
                expired.append({"requirement_key": req_key, "name": req_name})

            ready, reason = is_ready_for_upload(
                requirement_key=req_key,
                status=status,
                filename=filename,
                mandatory=mandatory,
            )

            if not file_bytes:
                if mandatory:
                    requires_review.append({"requirement_key": req_key, "name": req_name, "reason": reason or "Sin archivo"})
                requirements_meta.append(self._req_meta(item, folder=folder, assigned=None, ready=False, notes=reason))
                continue

            dest_folder = folder
            if not ready:
                dest_folder = "07_Revision"
                requires_review.append({"requirement_key": req_key, "name": req_name, "reason": reason})
            else:
                ready_to_upload.append({"requirement_key": req_key, "name": req_name, "file": filename})

            safe_name = self._unique_name(base / dest_folder, filename or "documento.pdf")
            dest = base / dest_folder / safe_name
            dest.write_bytes(file_bytes)
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            if ready and dest_folder != "08_Listo_Para_Subir":
                upload_dest = base / "08_Listo_Para_Subir" / safe_name
                upload_dest.write_bytes(file_bytes)

            fm = {
                "file_name": safe_name,
                "original_file_name": filename,
                "folder": dest_folder,
                "source": source,
                "document_type": req_key,
                "requirement_id": str(item.get("id")),
                "is_final_pdf": is_final or safe_name.lower().endswith(".pdf"),
                "signed": signed,
                "stamped": stamped,
                "validity_status": status,
                "expiration_date": item.get("valid_until"),
                "hash_sha256": file_hash,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": str(self.user_id),
            }
            files_meta.append(fm)
            requirements_meta.append(self._req_meta(
                item,
                folder=dest_folder,
                assigned=safe_name,
                ready=ready,
                notes=reason if not ready else "",
            ))
            target_item = next((i for i in checklist if i.get("requirement_key") == req_key), None)
            if target_item is not None:
                target_item["expediente_folder"] = dest_folder
                target_item["in_real_expediente"] = True
                target_item["ready_to_upload"] = ready
                target_item["expediente_file"] = safe_name
            audit_entries.append({"file": safe_name, "folder": dest_folder, "included": True})

        if missing:
            warnings.append(f"{len(missing)} requisito(s) faltante(s) — placeholders en 07_Revision")
        if expired:
            warnings.append(f"{len(expired)} documento(s) vencido(s) — excluidos de Listo Para Subir")
        if requires_review:
            warnings.append(f"{len(requires_review)} documento(s) en revisión")

        real_status = compute_real_expediente_status(
            missing_count=len(missing),
            expired_count=len(expired),
            review_count=len(requires_review),
            ready_count=len(ready_to_upload),
            mandatory_total=sum(1 for i in checklist if i.get("mandatory", True)),
        )

        manifest = {
            "tenant_id": str(self.tenant_id),
            "company_id": company_slug,
            "company_name": company_name,
            "opportunity_id": str(opportunity_id),
            "process_code": opportunity.code,
            "process_name": opportunity.title,
            "buyer": opportunity.institution or "",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": str(self.user_id),
            "status": real_status,
            "preparation_percentage": prep_pct,
            "folders": list(REAL_EXPEDIENTE_FOLDERS),
            "requirements": requirements_meta,
            "files": files_meta,
            "missing": missing,
            "expired": expired,
            "requires_review": requires_review,
            "ready_to_upload": ready_to_upload,
            "warnings": warnings,
            "audit": audit_entries,
            "checklist_summary": {
                "total": len(checklist),
                "compliant": sum(1 for i in checklist if i.get("status") in COMPLIANT_STATUSES),
                "mandatory": sum(1 for i in checklist if i.get("mandatory", True)),
            },
            "version": "1.0",
        }
        manifest["audit_hash"] = hashlib.sha256(
            json.dumps({k: v for k, v in manifest.items() if k != "audit"}, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        manifest_path = base / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        report_pdf = build_preparation_report_pdf(manifest)
        (base / "reporte_preparacion.pdf").write_bytes(report_pdf)

        zip_bytes = self._build_zip(base)
        zip_file = self.zip_path(opportunity, company_slug)
        zip_file.write_bytes(zip_bytes)

        pkg.real_expediente_path = str(base)
        pkg.real_expediente_generated_at = datetime.now(timezone.utc)
        pkg.checklist = checklist
        real_manifest = dict(manifest)
        real_manifest["zip_path"] = str(zip_file)
        real_manifest["zip_filename"] = zip_file.name
        pkg.real_expediente_manifest = real_manifest
        self._sync_operational_state(pkg, real_status)

        await self.audit.log(
            action="dgcp.real_expediente.generate",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="dgcp_bid_package",
            resource_id=pkg.id,
            details={
                "opportunity_id": str(opportunity_id),
                "status": real_status,
                "files_count": len(files_meta),
                "missing_count": len(missing),
                "zip": zip_file.name,
            },
        )
        await self.db.commit()

        return RealExpedienteGenerateResponse(
            opportunity_id=opportunity_id,
            status=real_status,
            expediente_path=str(base),
            zip_filename=zip_file.name,
            preparation_pct=prep_pct,
            files_count=len(files_meta),
            missing_count=len(missing),
            ready_to_upload_count=len(ready_to_upload),
            manifest=manifest,
            message="Expediente real generado — originales intactos",
        )

    async def validate_package(self, opportunity_id: uuid.UUID) -> RealExpedienteValidationResponse:
        _, pkg = await self._load_package(opportunity_id)
        checklist = pkg.checklist or []
        manifest = pkg.real_expediente_manifest or {}

        completed: list[str] = []
        faltantes: list[str] = []
        vencidos: list[str] = []
        pendientes_revision: list[str] = []
        errores: list[str] = []
        advertencias: list[str] = []

        for item in checklist:
            name = item.get("requirement") or item.get("requirement_key")
            st = item.get("status") or "faltante"
            key = item.get("requirement_key") or ""
            if st in ("faltante", "pendiente", "borrador_pendiente"):
                faltantes.append(name)
                if item.get("mandatory", True):
                    errores.append(f"Faltante crítico: {name}")
            elif st in ("encontrado_vencido", "vencido"):
                vencidos.append(name)
                advertencias.append(f"Vencido: {name}")
            elif st in ("requiere_revision", "requiere_completado", "incompleto"):
                pendientes_revision.append(name)
            elif st in COMPLIANT_STATUSES:
                completed.append(name)
            if requires_finalization(key) and st not in ("finalizado", "pdf_final_generado", "validado_manual", "adjuntado"):
                if key == "oferta_economica" and not item.get("process_document_id"):
                    faltantes.append(f"{name} (sin PDF)")
                    errores.append("Oferta económica sin PDF adjunto")

        prep = float((pkg.bid_package or {}).get("preparation_pct") or 0)
        critical = len(errores) > 0

        return RealExpedienteValidationResponse(
            opportunity_id=opportunity_id,
            preparation_pct=prep,
            general_status=pkg.real_expediente_status or "sin_generar",
            completed=completed,
            missing=faltantes,
            expired=vencidos,
            pending_review=pendientes_revision,
            critical_errors=errores,
            warnings=advertencias,
            can_prepare_package=not critical,
            manifest_generated=bool(pkg.real_expediente_path),
        )

    async def prepare_submission_package(self, opportunity_id: uuid.UUID) -> RealExpedienteGenerateResponse:
        validation = await self.validate_package(opportunity_id)
        if not validation.can_prepare_package:
            raise ValueError("Paquete no preparable: " + "; ".join(validation.critical_errors[:5]))

        result = await self.generate(opportunity_id)
        opportunity, pkg = await self._load_package(opportunity_id)
        company_name, company_slug = await self._resolve_company(None)

        src = self.expediente_base(opportunity)
        dest_root = (
            Path(settings.expediente_storage_path)
            / str(self.tenant_id)
            / self.PRESENTATION_ROOT
            / company_slug
            / self.safe_code(opportunity)
            / "08_LISTO_PARA_PRESENTAR"
        )
        if dest_root.exists():
            shutil.rmtree(dest_root)
        shutil.copytree(src, dest_root, dirs_exist_ok=True)

        pkg.real_expediente_status = "paquete_dgcp_preparado"
        manifest = dict(pkg.real_expediente_manifest or {})
        manifest["presentation_path"] = str(dest_root)
        manifest["status"] = "paquete_dgcp_preparado"
        pkg.real_expediente_manifest = manifest

        zip_name = f"DGCP_{self.safe_code(opportunity)}_{company_slug}.zip"
        zip_dest = dest_root.parent / zip_name
        zip_dest.write_bytes(self._build_zip(src, prefix="EXPEDIENTE"))
        manifest["presentation_zip"] = zip_name
        manifest["audit_hash"] = hashlib.sha256(
            json.dumps({k: v for k, v in manifest.items() if k != "audit_hash"}, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        pkg.real_expediente_manifest = manifest
        self._sync_operational_state(pkg, "paquete_dgcp_preparado")

        await self.audit.log(
            action="dgcp.real_expediente.prepare_package",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="dgcp_bid_package",
            resource_id=pkg.id,
            details={"opportunity_id": str(opportunity_id), "zip": zip_name},
        )
        await self.db.commit()

        result.status = "paquete_dgcp_preparado"
        result.message = "Paquete DGCP preparado — listo para revisión y subida manual"
        result.zip_filename = zip_name
        return result

    async def get_status(self, opportunity_id: uuid.UUID) -> RealExpedienteStatusResponse:
        opportunity, pkg = await self._load_package(opportunity_id)
        real_st = pkg.real_expediente_status or "sin_generar"
        manifest = pkg.real_expediente_manifest or {}
        base = pkg.real_expediente_path
        folder_counts: dict[str, int] = {}
        if base and Path(base).is_dir():
            for folder in REAL_EXPEDIENTE_FOLDERS:
                p = Path(base) / folder
                folder_counts[folder] = len([f for f in p.iterdir() if f.is_file()]) if p.is_dir() else 0

        zip_ok = bool(manifest.get("zip_filename") and base and Path(base).exists())
        return RealExpedienteStatusResponse(
            opportunity_id=opportunity_id,
            opportunity_code=opportunity.code,
            status=real_st,
            operational_stage=operational_stage_for_real_status(real_st),
            expediente_status=expediente_status_for_real(real_st),
            expediente_path=base,
            zip_filename=manifest.get("zip_filename"),
            preparation_pct=float((pkg.bid_package or {}).get("preparation_pct") or 0),
            generated_at=pkg.real_expediente_generated_at,
            folder_counts=folder_counts,
            missing=manifest.get("missing") or [],
            expired=manifest.get("expired") or [],
            requires_review=manifest.get("requires_review") or [],
            ready_to_upload=manifest.get("ready_to_upload") or [],
            warnings=manifest.get("warnings") or [],
            can_download=zip_ok,
            can_mark_ready_review=real_st in (
                "generado_con_observaciones",
                "generado_incompleto",
                "listo_para_revision",
                "paquete_dgcp_preparado",
            ),
            can_mark_ready_upload=real_st in (
                "listo_para_revision",
                "generado_con_observaciones",
                "paquete_dgcp_preparado",
            ),
            presentation_enabled=False,
            presentation_expediente="Completo" if real_st not in ("sin_generar", "requiere_actualizacion") else "Pendiente",
            presentation_package="Generado" if real_st in ("paquete_dgcp_preparado", "descargado", "listo_para_subir") else "Pendiente",
            presentation_zip="Disponible" if zip_ok else "No disponible",
            presentation_upload="Listo (subida manual)" if real_st == "listo_para_subir" else "Pendiente",
        )

    async def mark_ready_review(self, opportunity_id: uuid.UUID) -> RealExpedienteStatusResponse:
        _, pkg = await self._load_package(opportunity_id)
        if not pkg.real_expediente_path:
            raise ValueError("Genere el expediente real primero")
        pkg.real_expediente_status = "listo_para_revision"
        if pkg.real_expediente_manifest:
            m = dict(pkg.real_expediente_manifest)
            m["status"] = "listo_para_revision"
            pkg.real_expediente_manifest = m
        self._sync_operational_state(pkg, "listo_para_revision")
        await self.db.commit()
        return await self.get_status(opportunity_id)

    async def mark_ready_upload(self, opportunity_id: uuid.UUID) -> RealExpedienteStatusResponse:
        _, pkg = await self._load_package(opportunity_id)
        if not pkg.real_expediente_path:
            raise ValueError("Genere el expediente real primero")
        manifest = pkg.real_expediente_manifest or {}
        if manifest.get("missing"):
            raise ValueError("No se puede marcar listo para subir: hay requisitos faltantes")
        pkg.real_expediente_status = "listo_para_subir"
        m = dict(manifest)
        m["status"] = "listo_para_subir"
        pkg.real_expediente_manifest = m
        self._sync_operational_state(pkg, "listo_para_subir")
        await self.db.commit()
        return await self.get_status(opportunity_id)

    def get_manifest(self, pkg) -> dict:
        if pkg.real_expediente_manifest:
            return pkg.real_expediente_manifest
        path = Path(pkg.real_expediente_path or "") / "manifest.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def get_report_bytes(self, pkg) -> bytes:
        path = Path(pkg.real_expediente_path or "") / "reporte_preparacion.pdf"
        if not path.is_file():
            manifest = self.get_manifest(pkg)
            return build_preparation_report_pdf(manifest)
        return path.read_bytes()

    def get_download_zip(self, opportunity: DGCPOpportunity, pkg) -> tuple[bytes, str]:
        manifest = pkg.real_expediente_manifest or {}
        zip_name = manifest.get("zip_filename")
        if zip_name:
            zp = self.expediente_base(opportunity).parent / zip_name
            if zp.is_file():
                return zp.read_bytes(), zip_name
        base = Path(pkg.real_expediente_path or "")
        if not base.is_dir():
            raise ValueError("Expediente real no generado")
        name = f"{self.safe_code(opportunity)}_EXPEDIENTE_DGCP.zip"
        return self._build_zip(base), name

    async def log_download(
        self,
        opportunity_id: uuid.UUID,
        *,
        kind: str,
        filename: str,
    ) -> None:
        _, pkg = await self._load_package(opportunity_id)
        prev = pkg.real_expediente_status or "sin_generar"
        if prev == "paquete_dgcp_preparado":
            pkg.real_expediente_status = "descargado"
            self._sync_operational_state(pkg, "descargado")
        manifest = dict(pkg.real_expediente_manifest or {})
        manifest["last_download_at"] = datetime.now(timezone.utc).isoformat()
        manifest["last_download_kind"] = kind
        pkg.real_expediente_manifest = manifest
        await self.audit.log(
            action=f"dgcp.real_expediente.download_{kind}",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="dgcp_bid_package",
            resource_id=pkg.id,
            details={
                "opportunity_id": str(opportunity_id),
                "filename": filename,
                "previous_status": prev,
                "new_status": pkg.real_expediente_status,
            },
        )
        await self.db.commit()

    @classmethod
    async def mark_stale_if_generated(cls, db, tenant_id: uuid.UUID, opportunity_id: uuid.UUID) -> None:
        from app.models.dgcp_bid_package import DGCPBidPackage

        result = await db.execute(
            select(DGCPBidPackage).where(
                DGCPBidPackage.tenant_id == tenant_id,
                DGCPBidPackage.opportunity_id == opportunity_id,
            )
        )
        pkg = result.scalar_one_or_none()
        if not pkg or not pkg.real_expediente_path:
            return
        if pkg.real_expediente_status in ("sin_generar", "requiere_actualizacion"):
            return
        pkg.real_expediente_status = "requiere_actualizacion"
        bid = dict(pkg.bid_package or {})
        bid["operational_stage"] = operational_stage_for_real_status("requiere_actualizacion")
        pkg.bid_package = bid
        manifest = dict(pkg.real_expediente_manifest or {})
        manifest["status"] = "requiere_actualizacion"
        manifest["stale_reason"] = "Documentos del checklist modificados después de generar expediente"
        pkg.real_expediente_manifest = manifest
        pkg.expediente_status = expediente_status_for_real("requiere_actualizacion")

    @staticmethod
    def _sync_operational_state(pkg, real_status: str) -> None:
        pkg.real_expediente_status = real_status
        pkg.expediente_status = expediente_status_for_real(real_status)
        bid = dict(pkg.bid_package or {})
        bid["operational_stage"] = operational_stage_for_real_status(real_status)
        bid["operational_stage_label"] = STAGE_LABELS.get(bid["operational_stage"], bid["operational_stage"])
        pkg.bid_package = bid
        if pkg.real_expediente_manifest:
            m = dict(pkg.real_expediente_manifest)
            m["status"] = real_status
            m["operational_stage"] = bid["operational_stage"]
            pkg.real_expediente_manifest = m

    async def _load_package(self, opportunity_id: uuid.UUID):
        from app.models.dgcp_bid_package import DGCPBidPackage

        opp = await self.db.get(DGCPOpportunity, opportunity_id)
        if not opp or opp.tenant_id != self.tenant_id:
            raise ValueError("Licitación no encontrada")
        result = await self.db.execute(
            select(DGCPBidPackage).where(
                DGCPBidPackage.tenant_id == self.tenant_id,
                DGCPBidPackage.opportunity_id == opportunity_id,
            )
        )
        pkg = result.scalar_one_or_none()
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")
        from app.services.dgcp_bid_package_service import DGCPBidPackageService

        DGCPBidPackageService(self.db, self.tenant_id, user_id=self.user_id)._require_operational_interest(opp)
        return opp, pkg

    async def _resolve_company(self, company_key: str | None) -> tuple[str, str]:
        name = "Justech SRL"
        slug = "justech"
        if self.user_id:
            ctx = await GlobalCompanyContextService(self.db, self.tenant_id, self.user_id).get_context()
            if ctx.active_company_name:
                name = ctx.active_company_name
                slug = CompanyScopeFilter.odoo_name_to_dgcp_key(name) or slug
        if company_key:
            slug = company_key
        return name, slug

    async def _load_finalization_map(self, opportunity_id: uuid.UUID) -> dict[str, DocumentFinalizationRecord]:
        result = await self.db.execute(
            select(DocumentFinalizationRecord).where(
                DocumentFinalizationRecord.tenant_id == self.tenant_id,
                DocumentFinalizationRecord.opportunity_id == opportunity_id,
            )
        )
        out: dict[str, DocumentFinalizationRecord] = {}
        for row in result.scalars().all():
            out[row.requirement_key] = row
        return out

    async def _resolve_file(
        self,
        opportunity: DGCPOpportunity,
        item: dict,
        match: dict | None,
        final_record: DocumentFinalizationRecord | None,
        storage: DGCPProcessStorageService,
    ) -> tuple[bytes | None, str | None, str, bool, bool, bool]:
        req_key = item.get("requirement_key") or ""
        base = self.expediente_base(opportunity)

        if final_record and final_record.output_storage_uri:
            legacy_base = (
                Path(settings.expediente_storage_path)
                / str(self.tenant_id)
                / opportunity.code.replace("/", "_")
            )
            fp = legacy_base / final_record.output_storage_uri
            if fp.is_file():
                return (
                    fp.read_bytes(),
                    final_record.output_filename,
                    "finalization",
                    bool(final_record.signature_filename),
                    bool(final_record.stamp_filename),
                    True,
                )

        proc_id = item.get("process_document_id")
        if proc_id:
            proc = await self.db.get(DGCPProcessDocument, uuid.UUID(str(proc_id)))
            if proc and proc.tenant_id == self.tenant_id:
                meta = proc.metadata_ or {}
                fname = meta.get("storage_filename")
                if fname:
                    try:
                        data = storage.read_bytes(opportunity.code, fname)
                        return data, fname, meta.get("source") or proc.source_type, False, False, fname.lower().endswith(".pdf")
                    except FileNotFoundError:
                        pass

        if match and match.get("relative_path") and self.source.is_available():
            try:
                rel = match["relative_path"]
                if rel.startswith("DGCP/"):
                    fname = rel.split("/")[-1]
                    data = storage.read_bytes(opportunity.code, fname)
                    return data, fname, match.get("match_source") or "match", False, False, fname.lower().endswith(".pdf")
                data = self.source.read_bytes(rel)
                return data, Path(rel).name, match.get("match_source") or "knowledge", False, False, Path(rel).suffix.lower() == ".pdf"
            except Exception:
                pass

        out_name = REQUIREMENT_OUTPUT_BASENAME.get(req_key)
        if out_name:
            legacy = Path(settings.expediente_storage_path) / str(self.tenant_id) / opportunity.code.replace("/", "_")
            for folder in ("02_Formularios_SNCC", "04_Oferta_Economica", "02_Formularios"):
                fp = legacy / folder / out_name
                if fp.is_file():
                    return fp.read_bytes(), out_name, "legacy_final", True, True, True

        return None, None, "", False, False, False

    @staticmethod
    def _placeholder_content(opportunity: DGCPOpportunity, item: dict) -> str:
        return "\n".join([
            f"Proceso: {opportunity.code}",
            f"Requisito: {item.get('requirement')}",
            f"Tipo: {item.get('tipo')}",
            f"Prioridad: {'Alta' if item.get('mandatory') else 'Media'}",
            "Responsable sugerido: Equipo licitaciones",
            f"Acción recomendada: {item.get('recommended_action') or 'Registrar documento'}",
            f"Fecha límite: {opportunity.deadline or 'Por confirmar'}",
            f"Fuente del requisito: {item.get('requirement_key')}",
            f"Notas: {item.get('notes') or '—'}",
        ])

    @staticmethod
    def _req_meta(item: dict, *, folder: str, assigned: str | None, ready: bool, notes: str) -> dict:
        return {
            "requirement_id": str(item.get("id")),
            "name": item.get("requirement"),
            "category": item.get("tipo"),
            "required": bool(item.get("mandatory", True)),
            "status": item.get("status"),
            "source": item.get("match_source"),
            "evidence": item.get("document_title"),
            "assigned_file": assigned,
            "folder": folder,
            "ready_to_upload": ready,
            "notes": notes,
        }

    @staticmethod
    def _safe_filename(name: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return safe[:60] or "REQUISITO"

    @staticmethod
    def _unique_name(folder: Path, filename: str) -> str:
        target = folder / filename
        if not target.exists():
            return filename
        stem = Path(filename).stem
        ext = Path(filename).suffix
        n = 2
        while (folder / f"{stem}_{n}{ext}").exists():
            n += 1
        return f"{stem}_{n}{ext}"

    @staticmethod
    def _build_zip(base: Path, prefix: str = "") -> bytes:
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                if path.name in (".DS_Store",) or "__MACOSX" in str(path):
                    continue
                rel = path.relative_to(base)
                arc = f"{prefix}/{rel}" if prefix else str(rel)
                if prefix == "EXPEDIENTE":
                    arc = f"EXPEDIENTE/{rel}"
                zf.write(path, arcname=arc)
        return buf.getvalue()
