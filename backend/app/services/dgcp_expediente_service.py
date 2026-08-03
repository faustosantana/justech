"""Generador de expediente DGCP — copias controladas (Fase 7.3)."""

from __future__ import annotations

import json
import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.dgcp_bid import DGCPBidPackageStatusResponse, DGCPExpedientePrepareResponse
from app.services.dgcp_compliance_engine import DGCPComplianceEngine
from app.services.dgcp_form_autofill_service import DGCPFormAutofillService
from app.services.knowledge_source_provider import get_knowledge_source_provider


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


class DGCPExpedienteService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.forms = DGCPFormAutofillService(db, tenant_id)
        self.source = get_knowledge_source_provider()

    def expediente_dir(self, opportunity: DGCPOpportunity) -> Path:
        safe = opportunity.code.replace("/", "_")
        return Path(settings.expediente_storage_path) / str(self.tenant_id) / safe

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
        for folder in EXPEDIENTE_FOLDERS:
            (base / folder).mkdir(parents=True, exist_ok=True)

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
            ext = Path(rel).suffix if rel else ".pdf"
            safe_label = "".join(
                ch if ch.isalnum() or ch in " ._-" else "_"
                for ch in str(req_label)
            ).strip() or "documento"
            dest_name = f"{safe_label}{ext}"
            if rel and self.source.is_available():
                try:
                    src_bytes = self.source.read_bytes(rel)
                    dest = base / folder / dest_name
                    dest.write_bytes(src_bytes)
                    copied.append(
                        {
                            "requirement": req_label,
                            "requirement_key": req_key,
                            "path": str(dest.relative_to(base)),
                            "pliego_filename": dest_name,
                        }
                    )
                except Exception:
                    continue

        forms_out = list(generated_forms or [])
        # Plantillas M365 son opcionales para preparar el ZIP de expediente en DEV.
        for form_type in ("SNCC.F042", "SNCC.F047", "SNCC.F033"):
            forms_out.append(
                {
                    "form_type": form_type,
                    "status": "skipped",
                    "message": "Plantilla M365 no requerida para preparación de expediente",
                    "company_key": effective_company_key,
                }
            )

        prep_pct = float(bid_package.get("preparation_pct", 0))
        status = DGCPComplianceEngine.compute_expediente_status(checklist, prep_pct)
        if status == "expediente_listo_para_revision":
            status = "expediente_incompleto"

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
        ]
        for entry in index_entries:
            index_md.append(
                f"{entry['orden']}. **{entry['nombre']}** — {entry['estado']}"
                + (f" · Resp: {entry['responsable']}" if entry.get("responsable") else "")
            )
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
            "copied_documents": copied,
            "generated_forms": forms_out,
            "sections": list(EXPEDIENTE_FOLDERS),
            "index": index_payload,
            "validaciones_ia": validaciones,
            "final_validation": final_validation,
            "checklist_summary": {
                "total": len(checklist),
                "found": bid_package.get("found_documents", 0),
                "missing": bid_package.get("pending_documents", 0),
                "expired": bid_package.get("expired_documents", 0),
            },
            "user_input": {
                key: value
                for key, value in (user_input or {}).items()
                if not str(key).startswith("_")
            },
            "note": "Expediente generado como copia controlada — nombres según pliego; originales intactos",
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
                    "total": len(checklist),
                    "compliant": bid_package.get("compliant_count") or bid_package.get("found_documents", 0),
                },
                "missing": [
                    item.get("requirement")
                    for item in checklist
                    if item.get("mandatory", True)
                    and not (
                        item.get("document_title")
                        or item.get("document_id")
                        or item.get("knowledge_asset_id")
                    )
                ],
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
                "ready_to_upload": [],
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
                if path.is_file():
                    archive.write(path, arcname=str(path.relative_to(base)))
        manifest["zip_path"] = str(zip_path)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        return DGCPExpedientePrepareResponse(
            opportunity_id=opp_id,
            expediente_status=status,
            expediente_path=str(base),
            preparation_pct=prep_pct,
            copied_documents=len(copied),
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
        return DGCPBidPackageStatusResponse(
            opportunity_id=opportunity.id,
            opportunity_code=opportunity.code,
            expediente_status=expediente_status,
            expediente_path=expediente_path,
            preparation_pct=float(bid_package.get("preparation_pct", 0)),
            total_requirements=int(bid_package.get("total_requirements", 0)),
            mandatory_requirements=int(bid_package.get("mandatory_requirements", 0)),
            compliant_count=int(bid_package.get("compliant_count", 0)),
            found_documents=int(bid_package.get("found_documents", 0)),
            pending_documents=int(bid_package.get("pending_documents", 0)),
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
                if path.is_file():
                    zf.write(path, arcname=str(path.relative_to(base)))
        code = base.name
        return buffer.getvalue(), f"expediente_{code}.zip"
