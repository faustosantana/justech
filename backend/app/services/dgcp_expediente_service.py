"""Generador de expediente DGCP — copias controladas (Fase 7.3)."""

from __future__ import annotations

import json
import logging
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.dgcp_process_document import DGCPProcessDocument
from app.schemas.dgcp_bid import DGCPBidPackageStatusResponse, DGCPExpedientePrepareResponse
from app.services.dgcp_compliance_engine import COMPLIANT_STATUSES, DGCPComplianceEngine
from app.services.dgcp_form_autofill_service import DGCPFormAutofillService
from app.services.dgcp_process_storage_service import DGCPProcessStorageService
from app.services.knowledge_source_provider import get_knowledge_source_provider

logger = logging.getLogger(__name__)

EXPEDIENTE_STATUSES = (
    "sin_preparar",
    "expediente_en_preparacion",
    "expediente_incompleto",
    "expediente_listo_para_revision",
    "expediente_listo_para_presentar",
)

FOLDER_MAP = {
    "legal": "01_Documentos_Legales",
    "administrativo": "02_Formularios_SNCC",
    "tecnico": "03_Oferta_Tecnica",
    "financiero": "04_Oferta_Economica",
    "economico": "04_Oferta_Economica",
    "proveedor": "05_Proveedor_Fabricante",
    "garantia": "06_Garantias",
    "garantias": "06_Garantias",
    "experiencia": "07_Experiencia",
    "personal": "08_Personal",
    "certificacion": "09_Certificaciones",
    "certificaciones": "09_Certificaciones",
    "cronograma": "10_Cronograma",
    "anexo": "11_Anexos",
    "anexos": "11_Anexos",
}

ROLE_FOLDER_MAP = {
    "pliego": "00_Informacion_General",
    "tdr": "03_Oferta_Tecnica",
    "formulario": "02_Formularios_SNCC",
    "anexo": "11_Anexos",
    "general": "01_Documentos_Legales",
    "invitacion": "00_Informacion_General",
    "ficha_tecnica": "05_Proveedor_Fabricante",
    "especificaciones": "03_Oferta_Tecnica",
    "checklist_evidence": "12_Revision",
}

EXPEDIENTE_FOLDERS = (
    "00_Informacion_General",
    "01_Documentos_Legales",
    "02_Formularios_SNCC",
    "03_Oferta_Tecnica",
    "04_Oferta_Economica",
    "05_Proveedor_Fabricante",
    "06_Garantias",
    "07_Experiencia",
    "08_Personal",
    "09_Certificaciones",
    "10_Cronograma",
    "11_Anexos",
    "12_Revision",
)

# Artefactos de empaquetado — no cuentan como documentos aportados/copiados.
_META_NAMES = {
    "manifest.json",
    "indice_expediente.json",
    "indice_expediente.md",
    "ficha_proceso.json",
    "validaciones_ia.json",
    "reporte_preparacion.json",
    "reporte_estado_expediente.pdf",
    "reporte_estado_expediente.txt",
    ".keep",
}


class ExpedienteMetricsConsistencyError(ValueError):
    """API / manifest / ZIP metrics do not agree."""


class DGCPExpedienteService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.forms = DGCPFormAutofillService(db, tenant_id)
        self.source = get_knowledge_source_provider()
        self.process_storage = DGCPProcessStorageService(tenant_id)

    def expediente_dir(self, opportunity: DGCPOpportunity) -> Path:
        safe = opportunity.code.replace("/", "_")
        return Path(settings.expediente_storage_path) / str(self.tenant_id) / safe

    @staticmethod
    def _safe_name(label: str, *, fallback: str = "documento") -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in " ._-" else "_" for ch in str(label)).strip()
        cleaned = " ".join(cleaned.split())
        return cleaned or fallback

    @classmethod
    def export_document_filename(
        cls,
        document_code: str,
        process_ref: str,
        ext: str,
        *,
        duplicate_index: int | None = None,
    ) -> str:
        """Nombre de exportación: ``F033 - REF.pdf`` o ``F033 - REF - 01.pdf``."""
        code = cls._safe_name(document_code, fallback="DOCUMENTO").upper()
        ref = cls._safe_name(process_ref, fallback="PROCESO")
        suffix = ext if ext.startswith(".") else f".{ext}" if ext else ""
        if duplicate_index is not None and duplicate_index > 0:
            return f"{code} - {ref} - {duplicate_index:02d}{suffix}"
        return f"{code} - {ref}{suffix}"

    @classmethod
    def inventory_content_files(cls, base: Path) -> list[Path]:
        if not base.exists():
            return []
        out: list[Path] = []
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.name in _META_NAMES or path.name.startswith("."):
                continue
            out.append(path)
        return out

    @classmethod
    def inventory_zip_content(cls, zip_bytes: bytes) -> list[str]:
        names: list[str] = []
        with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
            for name in archive.namelist():
                if name.endswith("/"):
                    continue
                leaf = Path(name).name
                if leaf in _META_NAMES or leaf.startswith("."):
                    continue
                names.append(name)
        return sorted(names)

    def _reset_base(self, base: Path) -> None:
        if base.exists():
            shutil.rmtree(base)
        for folder in EXPEDIENTE_FOLDERS:
            (base / folder).mkdir(parents=True, exist_ok=True)
            keep = base / folder / ".keep"
            keep.write_text("", encoding="utf-8")

    def _write_unique(self, dest_dir: Path, filename: str, content: bytes) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        safe = self._safe_name(filename, fallback="documento.bin")
        candidate = dest_dir / safe
        if not candidate.exists():
            candidate.write_bytes(content)
            return candidate
        stem, suffix = candidate.stem, candidate.suffix
        # Convención: ``nombre - 01.ext`` (sin UUID)
        idx = 1
        while True:
            alt = dest_dir / f"{stem} - {idx:02d}{suffix}"
            if not alt.exists():
                alt.write_bytes(content)
                return alt
            idx += 1

    async def _copy_knowledge_matches(
        self,
        *,
        base: Path,
        checklist: list[dict],
        matches: list[dict],
        process_ref: str,
    ) -> list[dict]:
        copied: list[dict] = []
        for match in matches:
            if match.get("status") not in (
                "encontrado",
                "encontrado_vigente",
                "cumple",
                "requiere_actualizacion",
                "plantilla_disponible",
                "validado_manual",
            ):
                continue
            rel = match.get("relative_path")
            req_key = match.get("requirement_key")
            req_label = match.get("requirement_label") or match.get("requirement") or req_key or "documento"
            tipo = next(
                (c.get("tipo") for c in checklist if c.get("requirement_key") == req_key),
                "legal",
            )
            folder = FOLDER_MAP.get(str(tipo).lower(), "01_Documentos_Legales")
            if not rel or not self.source.is_available():
                continue
            try:
                src_bytes = self.source.read_bytes(rel)
            except Exception:
                continue
            ext = Path(rel).suffix or ".pdf"
            code_hint = str(req_label or req_key or "DOCUMENTO")
            upper = code_hint.upper()
            if "SNCC." in upper:
                code_hint = upper.replace("SNCC.", "").split()[0]
            elif upper.startswith("F0") or upper in {"RPE", "RNC", "MIPYME", "DGII", "TSS"}:
                code_hint = upper.split()[0]
            dest_name = self.export_document_filename(code_hint, process_ref, ext)
            dest = self._write_unique(base / folder, dest_name, src_bytes)
            copied.append(
                {
                    "requirement": req_label,
                    "requirement_key": req_key,
                    "path": str(dest.relative_to(base)),
                    "source": "knowledge",
                    "pliego_filename": dest.name,
                }
            )
        return copied

    async def _copy_process_documents(
        self,
        *,
        opportunity: DGCPOpportunity,
        base: Path,
    ) -> list[dict]:
        if self.db is None:
            return []
        result = await self.db.execute(
            select(DGCPProcessDocument).where(
                DGCPProcessDocument.tenant_id == self.tenant_id,
                DGCPProcessDocument.opportunity_id == opportunity.id,
            )
        )
        docs = list(result.scalars().all())
        copied: list[dict] = []
        process_ref = opportunity.code.replace("/", "_")
        for doc in docs:
            meta = doc.metadata_ or {}
            filename = meta.get("storage_filename")
            if not filename:
                continue
            try:
                content = self.process_storage.read_bytes(opportunity.code, filename)
            except Exception:
                logger.debug("process doc missing on disk: %s", filename)
                continue
            folder = ROLE_FOLDER_MAP.get(str(doc.doc_role or "").lower(), "11_Anexos")
            code_hint = str(doc.doc_role or doc.title or Path(filename).stem)
            ext = Path(filename).suffix or ".pdf"
            dest_name = self.export_document_filename(code_hint, process_ref, ext)
            dest = self._write_unique(base / folder, dest_name, content)
            copied.append(
                {
                    "requirement": doc.title,
                    "requirement_key": doc.doc_role,
                    "path": str(dest.relative_to(base)),
                    "source": "process_document",
                    "doc_role": doc.doc_role,
                    "process_document_id": str(doc.id),
                    "pliego_filename": dest.name,
                }
            )
        return copied

    def _compute_metrics(
        self,
        *,
        opportunity: DGCPOpportunity,
        checklist: list[dict],
        bid_package: dict,
        copied_entries: list[dict],
        content_files: list[Path],
    ) -> dict:
        mandatory = [c for c in checklist if c.get("mandatory", True)]
        total_requirements = len(checklist)
        total_documents = len(mandatory) if mandatory else max(len(content_files), total_requirements)

        fresh = DGCPComplianceEngine().build_bid_package(opportunity, checklist)
        requirement_pct = float(fresh.preparation_pct)
        completed_requirements = int(fresh.compliant_count)
        pending_requirements = max(total_requirements - completed_requirements, 0)

        copied_count = len(content_files)
        if total_documents > 0:
            coverage_pct = round(min(100.0, (copied_count / total_documents) * 100.0), 1)
        else:
            coverage_pct = 0.0

        # Export metrics must reflect the package that was actually built.
        preparation_pct = max(requirement_pct, coverage_pct)
        incomplete = pending_requirements > 0 or any(
            c.get("status") not in COMPLIANT_STATUSES for c in mandatory
        )
        if incomplete and preparation_pct >= 100:
            preparation_pct = 99.9
        if not incomplete and mandatory and completed_requirements >= len(mandatory):
            preparation_pct = 100.0

        status = DGCPComplianceEngine.compute_expediente_status(checklist, preparation_pct)
        if status == "expediente_listo_para_revision" and incomplete:
            status = "expediente_incompleto"

        missing = [
            item.get("requirement") or item.get("requirement_key")
            for item in checklist
            if item.get("mandatory", True)
            and item.get("status") not in COMPLIANT_STATUSES
        ]

        return {
            "preparation_pct": float(preparation_pct),
            "copied_documents": copied_count,
            "copied_entries": copied_entries,
            "total_documents": int(total_documents),
            "total_requirements": int(total_requirements),
            "completed_requirements": int(completed_requirements),
            "pending_requirements": int(pending_requirements),
            "found_documents": int(fresh.found_documents),
            "expired_documents": int(fresh.expired_documents),
            "missing": missing,
            "expediente_status": status,
            "requirement_pct": requirement_pct,
            "coverage_pct": coverage_pct,
            # Keep prior bid_package keys for compatibility when useful
            "bid_package_snapshot": {
                **(bid_package or {}),
                "preparation_pct": float(preparation_pct),
                "found_documents": int(fresh.found_documents),
                "pending_documents": int(fresh.pending_documents),
                "expired_documents": int(fresh.expired_documents),
                "total_requirements": int(fresh.total_requirements),
                "mandatory_requirements": int(fresh.mandatory_requirements),
                "compliant_count": int(fresh.compliant_count),
            },
        }

    def _assert_metrics_consistency(
        self,
        *,
        api_copied: int,
        api_pct: float,
        manifest: dict,
        zip_content_count: int,
    ) -> None:
        """Ensure API metrics match the manifest.

        The ZIP may include generated artifacts (reportes, índices) beyond copied
        requirement documents, so zip file count is only a lower-bound check when
        documents were actually copied.
        """
        manifest_copied = manifest.get("copied_documents")
        if isinstance(manifest_copied, list):
            manifest_count = len(manifest_copied)
        else:
            manifest_count = int(manifest_copied or 0)
        manifest_pct = float(manifest.get("preparation_pct") or 0)
        if api_copied != manifest_count or round(api_pct, 1) != round(manifest_pct, 1):
            raise ExpedienteMetricsConsistencyError(
                "Inconsistencia de métricas de expediente: "
                f"api(copied={api_copied}, pct={api_pct}) "
                f"manifest(copied={manifest_count}, pct={manifest_pct}) "
                f"zip(files={zip_content_count})"
            )
        if api_copied > 0 and zip_content_count < api_copied:
            raise ExpedienteMetricsConsistencyError(
                "Inconsistencia de métricas de expediente: "
                f"el ZIP tiene menos archivos de contenido ({zip_content_count}) "
                f"que documentos copiados ({api_copied})"
            )

    async def prepare(
        self,
        opportunity: DGCPOpportunity,
        *,
        checklist: list[dict],
        matches: list[dict],
        bid_package: dict,
        user_input: dict | None = None,
        generated_forms: list | None = None,
        company_key: str | None = None,
    ) -> DGCPExpedientePrepareResponse:
        opp_id = opportunity.id
        opp_code = opportunity.code
        opp_title = opportunity.title
        opp_institution = opportunity.institution
        opp_amount = opportunity.amount
        opp_currency = opportunity.currency
        opp_deadline = opportunity.deadline
        opp_modalidad = opportunity.modalidad
        opp_status = opportunity.status
        opp_source_url = opportunity.source_url
        effective_company_key = (company_key or opportunity.company or "justech").strip() or "justech"

        base = self.expediente_dir(opportunity)
        self._reset_base(base)

        general = {
            "code": opp_code,
            "title": opp_title,
            "institution": opp_institution,
            "amount": str(opp_amount) if opp_amount is not None else None,
            "currency": opp_currency,
            "deadline": str(opp_deadline) if opp_deadline else None,
            "modalidad": opp_modalidad,
            "status": opp_status,
            "source_url": opp_source_url,
            "company_key": effective_company_key,
        }
        (base / "00_Informacion_General" / "ficha_proceso.json").write_text(
            json.dumps(general, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        copied_entries: list[dict] = []
        copied_entries.extend(
            await self._copy_knowledge_matches(
                base=base,
                checklist=checklist,
                matches=matches,
                process_ref=opp_code.replace("/", "_"),
            )
        )
        copied_entries.extend(
            await self._copy_process_documents(opportunity=opportunity, base=base)
        )

        forms_out = list(generated_forms or [])
        for form_type in ("SNCC.F042", "SNCC.F047", "SNCC.F033"):
            forms_out.append(
                {
                    "form_type": form_type,
                    "status": "skipped",
                    "message": "Plantilla M365 no requerida para preparación de expediente",
                    "company_key": effective_company_key,
                }
            )

        content_files = self.inventory_content_files(base)
        # Prefer inventory paths as canonical copied list (dedupe by path).
        by_path = {e.get("path"): e for e in copied_entries if e.get("path")}
        for path in content_files:
            rel = str(path.relative_to(base))
            if rel not in by_path:
                by_path[rel] = {
                    "requirement": path.name,
                    "path": rel,
                    "source": "inventory",
                    "pliego_filename": path.name,
                }
        copied_entries = list(by_path.values())

        metrics = self._compute_metrics(
            opportunity=opportunity,
            checklist=checklist,
            bid_package=bid_package or {},
            copied_entries=copied_entries,
            content_files=content_files,
        )
        prep_pct = metrics["preparation_pct"]
        status = metrics["expediente_status"]

        index_entries = []
        for idx, item in enumerate(checklist, start=1):
            index_entries.append(
                {
                    "orden": idx,
                    "requirement_key": item.get("requirement_key"),
                    "nombre": item.get("requirement") or item.get("requirement_key"),
                    "estado": item.get("status"),
                    "responsable": item.get("assignee"),
                    "fecha_limite": item.get("due_date") or item.get("valid_until"),
                    "documento": item.get("document_title"),
                    "obligatorio": bool(item.get("mandatory", True)),
                }
            )
        index_payload = {
            "opportunity_code": opp_code,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total": len(index_entries),
            "items": index_entries,
            "carpetas": list(EXPEDIENTE_FOLDERS),
        }
        (base / "00_Informacion_General" / "indice_expediente.json").write_text(
            json.dumps(index_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        index_md = [
            f"# Índice del expediente — {opp_code}",
            "",
            f"Generado: {index_payload['generated_at']}",
            "",
            "| Orden | Código | Documento | Estado | Responsable | Archivo |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for entry in index_entries:
            linked = next(
                (c for c in copied_entries if c.get("requirement_key") == entry.get("requirement_key")),
                None,
            )
            archivo = (linked or {}).get("pliego_filename") or entry.get("documento") or "—"
            index_md.append(
                f"| {entry['orden']} | {entry.get('requirement_key') or '—'} | "
                f"{entry['nombre']} | {entry['estado']} | "
                f"{entry.get('responsable') or '—'} | {archivo} |"
            )
        index_filename = self.export_document_filename("INDICE", opp_code.replace("/", "_"), ".md")
        (base / "00_Informacion_General" / index_filename).write_text(
            "\n".join(index_md),
            encoding="utf-8",
        )
        # Compat: mantener nombre histórico
        (base / "00_Informacion_General" / "indice_expediente.md").write_text(
            "\n".join(index_md),
            encoding="utf-8",
        )

        validaciones = []
        for item in checklist:
            ai_validation = item.get("ai_validation") if isinstance(item.get("ai_validation"), dict) else None
            if ai_validation or item.get("ia_observations") or item.get("manual_validation"):
                validaciones.append(
                    {
                        "requirement_key": item.get("requirement_key"),
                        "nombre": item.get("requirement"),
                        "cumple": None if not ai_validation else ai_validation.get("cumple"),
                        "observaciones": (ai_validation or {}).get("observaciones")
                        or item.get("ia_observations")
                        or item.get("observaciones_ia"),
                        "riesgo": item.get("risk") or (ai_validation or {}).get("riesgo"),
                        "estado": item.get("status"),
                        "manual_validation": item.get("manual_validation"),
                    }
                )
        (base / "12_Revision" / "validaciones_ia.json").write_text(
            json.dumps(validaciones, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        final_validation = (user_input or {}).get("_final_validation") if isinstance(user_input, dict) else None

        manifest = {
            "opportunity_code": opp_code,
            "opportunity_title": opp_title,
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "preparation_pct": prep_pct,
            "expediente_status": status,
            "company_key": effective_company_key,
            "copied_documents": copied_entries,
            "copied_documents_count": metrics["copied_documents"],
            "total_documents": metrics["total_documents"],
            "total_requirements": metrics["total_requirements"],
            "completed_requirements": metrics["completed_requirements"],
            "pending_requirements": metrics["pending_requirements"],
            "missing_requirements": metrics["missing"],
            "generated_forms": forms_out,
            "sections": list(EXPEDIENTE_FOLDERS),
            "index": index_payload,
            "validaciones_ia": validaciones,
            "final_validation": final_validation,
            "checklist_summary": {
                "total": metrics["total_requirements"],
                "found": metrics["found_documents"],
                "missing": metrics["pending_requirements"],
                "expired": metrics["expired_documents"],
                "completed_requirements": metrics["completed_requirements"],
                "pending_requirements": metrics["pending_requirements"],
            },
            "metrics": {
                "preparation_pct": prep_pct,
                "copied_documents": metrics["copied_documents"],
                "total_documents": metrics["total_documents"],
                "completed_requirements": metrics["completed_requirements"],
                "pending_requirements": metrics["pending_requirements"],
                "requirement_pct": metrics["requirement_pct"],
                "coverage_pct": metrics["coverage_pct"],
            },
            "user_input": {
                key: value
                for key, value in (user_input or {}).items()
                if not str(key).startswith("_")
            },
            "note": "Expediente generado como copia controlada — métricas derivadas del inventario real",
        }
        manifest_path = base / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        report_path = base / "12_Revision" / "reporte_preparacion.json"
        report_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        try:
            from app.services.real_expediente_report_pdf import build_preparation_report_pdf

            pdf_manifest = {
                "process_code": opp_code,
                "process_name": opp_title,
                "company_name": effective_company_key,
                "buyer": opp_institution,
                "generated_at": manifest["prepared_at"],
                "status": status,
                "preparation_percentage": prep_pct,
                "checklist_summary": {
                    "total": metrics["total_requirements"],
                    "compliant": metrics["completed_requirements"],
                },
                "missing": metrics["missing"],
                "expired": [
                    item.get("requirement")
                    for item in checklist
                    if item.get("status") in ("vencido", "encontrado_vencido")
                ],
                "requires_review": [
                    item.get("requirement")
                    for item in checklist
                    if item.get("status") in ("requiere_revision", "requiere_completado")
                ],
                "ready_to_upload": [e.get("path") for e in copied_entries],
                "requirements": [
                    {
                        "name": item.get("requirement"),
                        "status": item.get("status"),
                        "folder": FOLDER_MAP.get(
                            str(item.get("tipo") or "").lower(),
                            "01_Documentos_Legales",
                        ),
                        "ready_to_upload": bool(item.get("document_title")),
                        "assigned_file": item.get("document_title") or "",
                    }
                    for item in checklist
                ],
                "final_validation": final_validation,
            }
            pdf_bytes = build_preparation_report_pdf(pdf_manifest)
            (base / "12_Revision" / "reporte_estado_expediente.pdf").write_bytes(pdf_bytes)
        except Exception:
            (base / "12_Revision" / "reporte_estado_expediente.txt").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        zip_path = base.parent / f"{opp_code.replace('/', '_')}_expediente.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in base.rglob("*"):
                if path.is_file() and path.name != ".keep":
                    archive.write(path, arcname=str(path.relative_to(base)))

        zip_bytes = zip_path.read_bytes()
        zip_content = self.inventory_zip_content(zip_bytes)
        self._assert_metrics_consistency(
            api_copied=metrics["copied_documents"],
            api_pct=prep_pct,
            manifest=manifest,
            zip_content_count=len(zip_content),
        )

        manifest["zip_path"] = str(zip_path)
        manifest["zip_content_files"] = zip_content
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        return DGCPExpedientePrepareResponse(
            opportunity_id=opp_id,
            expediente_status=status,
            expediente_path=str(base),
            preparation_pct=prep_pct,
            copied_documents=metrics["copied_documents"],
            generated_forms=len(forms_out),
            manifest=manifest,
        )

    def status(
        self,
        opportunity: DGCPOpportunity,
        *,
        expediente_status: str,
        expediente_path: str | None,
        bid_package: dict,
        alerts: list,
        checklist: list | None = None,
        db_manifest: dict | None = None,
    ) -> DGCPBidPackageStatusResponse:
        manifest: dict = dict(db_manifest or {})
        if expediente_path:
            mp = Path(expediente_path) / "manifest.json"
            if mp.exists():
                fs_manifest = json.loads(mp.read_text(encoding="utf-8"))
                for key, value in fs_manifest.items():
                    manifest.setdefault(key, value)
        prep = float(
            (manifest.get("metrics") or {}).get("preparation_pct")
            or manifest.get("preparation_pct")
            or bid_package.get("preparation_pct", 0)
        )
        return DGCPBidPackageStatusResponse(
            opportunity_id=opportunity.id,
            opportunity_code=opportunity.code,
            expediente_status=expediente_status,
            expediente_path=expediente_path,
            preparation_pct=prep,
            total_requirements=int(
                manifest.get("total_requirements")
                or bid_package.get("total_requirements", 0)
            ),
            mandatory_requirements=int(bid_package.get("mandatory_requirements", 0)),
            compliant_count=int(
                manifest.get("completed_requirements")
                or bid_package.get("compliant_count", 0)
            ),
            found_documents=int(bid_package.get("found_documents", 0)),
            pending_documents=int(
                manifest.get("pending_requirements")
                or bid_package.get("pending_documents", 0)
            ),
            expired_documents=int(bid_package.get("expired_documents", 0)),
            forms_to_complete=int(bid_package.get("forms_to_complete", 0)),
            review_count=int(bid_package.get("review_count", 0)),
            alerts_count=len(alerts),
            manifest=manifest,
            can_mark_ready=bool(
                expediente_path
                and DGCPComplianceEngine.can_mark_ready_for_review(checklist or [])
            ),
            can_download=bool(expediente_path and Path(expediente_path).exists()),
            present_enabled=False,
        )

    def mark_ready_for_review(self, current_status: str) -> str:
        if current_status in ("expediente_en_preparacion", "expediente_incompleto", "sin_preparar"):
            return "expediente_listo_para_revision"
        return current_status

    def build_download_archive(self, expediente_path: str) -> tuple[bytes, str]:
        base = Path(expediente_path)
        if not base.exists():
            raise ValueError("Expediente no encontrado")
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in base.rglob("*"):
                if path.is_file() and path.name != ".keep":
                    zf.write(path, arcname=str(path.relative_to(base)))
        code = base.name
        return buffer.getvalue(), f"expediente_{code}.zip"
