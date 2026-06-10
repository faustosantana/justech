"""Motor de cumplimiento DGCP — preparación real vs requisitos extraídos (Fase 7.3)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.dgcp_bid import DGCPBidPackageResponse
from app.services.dgcp_requirements_extractor import (
    DEFAULT_LICITACION_DOCS,
    REQUIREMENT_RULES,
    ExtractedRequirement,
    ExtractionResult,
)
from app.services.document_validity_analyzer import DocumentValidityAnalyzer

# Cumplidos para cálculo de preparación
COMPLIANT_STATUSES = frozenset({
    "encontrado_vigente",
    "validado_manual",
    "no_aplica",
    "adjuntado",
    "finalizado",
    "pdf_final_generado",
})

OFFICIAL_KNOWLEDGE_FOLDERS = frozenset({
    "00_DATOS_EMPRESAS",
    "01_DOCUMENTOS_LEGALES",
    "02_PLANTILLAS",
    "03_PROVEEDORES",
    "04_FICHAS_TECNICAS",
    "05_COTIZACIONES",
})

DELIVERABLE_REQUIREMENT_KEYS = frozenset({
    "oferta_tecnica",
    "oferta_economica",
    "carta_presentacion",
    "propuesta_tecnica",
    "propuesta_economica",
})

FALTANTE_STATUSES = frozenset({"faltante", "pendiente"})
VENCIDO_STATUSES = frozenset({"encontrado_vencido", "vencido"})
REVIEW_STATUSES = frozenset({
    "requiere_revision",
    "encontrado_sin_fecha",
    "requiere_actualizacion",
    "encontrado_sin_analizar",
})
UNANALYZED_STATUSES = frozenset({"encontrado_sin_analizar"})
COMPLETE_STATUSES = frozenset({"requiere_completado", "plantilla_disponible", "completar", "incompleto"})

SNCC_KEY_BY_FORM = {
    "033": "sncc_f033",
    "034": "sncc_f034",
    "042": "sncc_f042",
    "047": "sncc_f047",
}

ACTION_BY_STATUS = {
    "faltante": "Solicitar o registrar documento",
    "pendiente": "Solicitar o registrar documento",
    "encontrado_vencido": "Renovar documento antes del cierre",
    "vencido": "Renovar documento antes del cierre",
    "encontrado_sin_fecha": "Encontrado, pero vigencia no verificada — revisar manualmente",
    "encontrado_sin_analizar": "Documento encontrado — pendiente de lectura/análisis",
    "requiere_revision": "Validar vigencia y contenido antes de presentar",
    "requiere_completado": "Completar formulario / plantilla con datos corporativos",
    "plantilla_disponible": "Usar plantilla corporativa y completar vista previa",
    "completar": "Revisar vista previa y completar formulario",
    "incompleto": "Completar campos faltantes",
    "encontrado_vigente": "Validar y adjuntar al expediente",
    "validado_manual": "Validado manualmente — conservar evidencia",
    "no_aplica": "Marcado como no aplica — conservar evidencia",
    "validado": "Revisar copia generada antes de presentar",
}


class DGCPComplianceEngine:
    """Calcula cumplimiento contra TODOS los requisitos extraídos, no solo documentos encontrados."""

    def collect_all_requirements(self, extraction: ExtractionResult) -> list[ExtractedRequirement]:
        by_key: dict[str, ExtractedRequirement] = {}

        for req in (
            extraction.technical
            + extraction.legal
            + extraction.financial
            + extraction.administrative
            + extraction.mandatory_documents
            + extraction.subsanable_documents
        ):
            by_key[req.key] = req

        for key in DEFAULT_LICITACION_DOCS:
            if key in by_key:
                continue
            rule = next((r for r in REQUIREMENT_RULES if r["key"] == key), None)
            if not rule:
                continue
            by_key[key] = ExtractedRequirement(
                key=rule["key"],
                label=rule["label"],
                tipo=rule["tipo"],
                mandatory=True,
                source="baseline_licitacion",
            )

        for form_label in extraction.sncc_forms:
            digits = "".join(c for c in form_label if c.isdigit())[-3:]
            key = SNCC_KEY_BY_FORM.get(digits)
            if key and key not in by_key:
                rule = next((r for r in REQUIREMENT_RULES if r["key"] == key), None)
                if rule:
                    by_key[key] = ExtractedRequirement(
                        key=rule["key"],
                        label=rule["label"],
                        tipo=rule["tipo"],
                        mandatory=True,
                        source="sncc_heuristic",
                    )

        for idx, guarantee in enumerate(extraction.guarantees):
            key = f"garantia_{idx}"
            if key not in by_key:
                by_key[key] = ExtractedRequirement(
                    key=key,
                    label=guarantee,
                    tipo="financiero",
                    mandatory=True,
                    source="garantia_heuristic",
                )

        for idx, sample in enumerate(extraction.samples):
            key = f"muestra_{idx}"
            if key not in by_key:
                by_key[key] = ExtractedRequirement(
                    key=key,
                    label=sample,
                    tipo="tecnico",
                    mandatory=True,
                    source="muestra_heuristic",
                )

        return list(by_key.values())

    @staticmethod
    def normalize_status(
        raw_status: str,
        *,
        vigency_status: str | None = None,
        marked_no_aplica: bool = False,
        requirement_key: str | None = None,
    ) -> str:
        if marked_no_aplica:
            return "no_aplica"

        pre_normalized = {
            "encontrado_vigente",
            "encontrado_vencido",
            "encontrado_sin_fecha",
            "encontrado_sin_analizar",
            "faltante",
            "requiere_completado",
            "requiere_revision",
            "validado_manual",
            "no_aplica",
            "adjuntado",
            "borrador_pendiente",
            "cotizacion_encontrada",
            "pdf_descargado",
            "generado",
            "pendiente_firma",
            "pendiente_sello",
            "firmado",
            "sellado",
            "pdf_final_generado",
            "finalizado",
        }
        if raw_status in pre_normalized:
            return raw_status

        if raw_status in FALTANTE_STATUSES:
            return "faltante"
        if raw_status in COMPLETE_STATUSES:
            return "requiere_completado"
        if raw_status in VENCIDO_STATUSES:
            return "encontrado_vencido"
        if raw_status in REVIEW_STATUSES:
            return "requiere_revision"
        if raw_status == "validado":
            return "requiere_revision"
        if raw_status == "no_aplica":
            return "no_aplica"

        # Documentos sin control de vigencia: encontrado y leído = cumplido
        if requirement_key and not DocumentValidityAnalyzer.requires_vigency_check(requirement_key):
            if raw_status in ("encontrado", "encontrado_vigente"):
                return "encontrado_vigente"
            if raw_status == "encontrado_sin_analizar":
                return "encontrado_sin_analizar"

        if raw_status == "encontrado":
            if vigency_status == "vencido":
                return "encontrado_vencido"
            if vigency_status == "proximo_a_vencer":
                return "requiere_revision"
            if vigency_status in (None, "sin_fecha", "sin_fecha_detectada", "no_aplica_vigencia"):
                if requirement_key and DocumentValidityAnalyzer.requires_vigency_check(requirement_key):
                    return "encontrado_sin_fecha"
                return "encontrado_vigente"
            if vigency_status == "vigente":
                return "encontrado_vigente"
            return "requiere_revision"

        return "faltante"

    @staticmethod
    def has_document_evidence(match: dict, item: dict | None = None) -> bool:
        item = item or {}
        return bool(
            match.get("document_id")
            or match.get("knowledge_asset_id")
            or match.get("process_document_id")
            or match.get("odoo_quotation_id")
            or item.get("document_id")
            or item.get("knowledge_asset_id")
            or item.get("process_document_id")
            or item.get("odoo_quotation_id")
        )

    def enforce_evidence_rules(
        self,
        req: ExtractedRequirement,
        match: dict,
        status: str,
        manual: dict,
        item: dict,
    ) -> str:
        """Evita estados cumplidos sin documento/evidencia real."""
        has_doc = self.has_document_evidence(match, item)

        if status == "no_aplica":
            return status

        if status == "validado_manual":
            if not has_doc and not (manual.get("evidence") or "").strip():
                return "faltante"
            return status

        if req.key == "oferta_economica" and status == "adjuntado":
            if has_doc or item.get("odoo_quotation_id") or match.get("odoo_quotation_id"):
                return status
            return "faltante"

        if status in COMPLIANT_STATUSES and not has_doc:
            return "faltante"

        if status == "encontrado_vigente" and not has_doc:
            return "faltante"

        if req.key in DELIVERABLE_REQUIREMENT_KEYS and status == "encontrado_vigente":
            return "requiere_completado" if has_doc else "faltante"

        return status

    def build_checklist_item(
        self,
        req: ExtractedRequirement,
        match: dict,
        *,
        prev: dict | None = None,
        sncc_form_map: dict[str, str],
    ) -> dict:
        prev = prev or {}
        marked_no_aplica = bool(prev.get("no_aplica"))
        manual = prev.get("manual_validation") or {}
        if manual.get("status") in {"validado_manual", "encontrado_vencido", "requiere_revision", "no_aplica"}:
            status = manual["status"]
        else:
            status = self.normalize_status(
                match.get("status", "pendiente"),
                vigency_status=match.get("vigency_status"),
                marked_no_aplica=marked_no_aplica,
                requirement_key=req.key,
            )

        risk = None
        if status == "encontrado_vencido":
            risk = "Documento vencido — riesgo de descalificación"
        elif status == "faltante" and req.mandatory:
            risk = "Requisito obligatorio sin documento asociado"
        elif status == "requiere_completado":
            risk = "Formulario o entregable pendiente de completar"
        elif status in ("requiere_revision", "encontrado_sin_fecha", "encontrado_sin_analizar"):
            risk = "Documento encontrado — vigencia o contenido requiere revisión"
        elif status == "encontrado_vigente" and req.mandatory:
            risk = None

        notes = match.get("notes")
        if manual.get("note"):
            notes = manual["note"]
        elif status == "encontrado_sin_fecha":
            notes = "Encontrado, pero vigencia no verificada."
        elif status == "encontrado_sin_analizar":
            notes = "Documento encontrado — contenido no analizado."

        validity_analysis = match.get("validity_analysis")
        if manual.get("expiration_date"):
            valid_until = manual["expiration_date"]
        else:
            valid_until = match.get("valid_until")

        partial = {
            "document_id": match.get("document_id"),
            "knowledge_asset_id": match.get("knowledge_asset_id"),
        }
        status = self.enforce_evidence_rules(req, match, status, manual, {**partial, **prev})

        return {
            "id": prev.get("id") or str(uuid.uuid4()),
            "requirement_key": req.key,
            "requirement": req.label,
            "tipo": req.tipo,
            "mandatory": req.mandatory,
            "status": status,
            "document_id": match.get("document_id"),
            "document_title": match.get("document_title"),
            "valid_until": valid_until,
            "vigency_status": match.get("vigency_status"),
            "match_source": match.get("match_source"),
            "knowledge_asset_id": match.get("knowledge_asset_id"),
            "relative_path": match.get("relative_path"),
            "risk": risk,
            "recommended_action": ACTION_BY_STATUS.get(status),
            "notes": notes,
            "assignee": prev.get("assignee"),
            "task_id": prev.get("task_id"),
            "no_aplica": marked_no_aplica or status == "no_aplica",
            "completable": status == "requiere_completado" or req.key.startswith("sncc_"),
            "form_type": sncc_form_map.get(req.key),
            "evidence_source": req.source,
            "display_status": self.display_status_label(status),
            "validity_analysis": validity_analysis,
            "manual_validation": manual or None,
        }

    def build_checklist(
        self,
        requirements: list[ExtractedRequirement],
        matches: list[dict],
        existing: list[dict] | None = None,
        *,
        sncc_form_map: dict[str, str],
    ) -> list[dict]:
        match_by_key = {m["requirement_key"]: m for m in matches}
        existing_by_key = {item["requirement_key"]: item for item in (existing or [])}
        items: list[dict] = []
        for req in requirements:
            m = match_by_key.get(req.key, {
                "requirement_key": req.key,
                "requirement_label": req.label,
                "status": "pendiente",
                "match_score": 0.0,
                "notes": f"Requisito extraído — {req.label}",
            })
            items.append(
                self.build_checklist_item(
                    req,
                    m,
                    prev=existing_by_key.get(req.key),
                    sncc_form_map=sncc_form_map,
                )
            )
        return items

    def build_bid_package(
        self,
        opportunity: DGCPOpportunity,
        checklist: list[dict],
        *,
        analyzed_at: datetime | None = None,
    ) -> DGCPBidPackageResponse:
        now = analyzed_at or datetime.now(timezone.utc)
        mandatory = [c for c in checklist if c.get("mandatory", True)]
        total_mandatory = len(mandatory) or 1

        def _counts_as_compliant(item: dict) -> bool:
            status = item.get("status")
            if status not in COMPLIANT_STATUSES:
                return False
            if status == "no_aplica":
                return True
            return self.has_document_evidence({}, item)

        compliant = sum(1 for c in mandatory if _counts_as_compliant(c))
        faltante = sum(1 for c in checklist if c.get("status") == "faltante")
        vencido = sum(1 for c in checklist if c.get("status") == "encontrado_vencido")
        requiere_completado = sum(1 for c in checklist if c.get("status") == "requiere_completado")
        requiere_revision = sum(
            1 for c in checklist
            if c.get("status") in ("requiere_revision", "encontrado_sin_fecha", "encontrado_sin_analizar")
        )
        sin_analizar = sum(1 for c in checklist if c.get("status") == "encontrado_sin_analizar")
        validado_manual = sum(1 for c in checklist if c.get("status") == "validado_manual")
        encontrado_vigente = sum(
            1 for c in checklist if c.get("status") in ("encontrado_vigente", "validado_manual")
        )

        pct = round((compliant / total_mandatory) * 100, 1)
        blocking = faltante or vencido or requiere_completado or requiere_revision or sin_analizar
        if mandatory and blocking:
            pct = min(pct, 99.9)

        tasks: list[str] = []
        if faltante:
            tasks.append(f"Solicitar {faltante} requisito(s) faltante(s)")
        if vencido:
            tasks.append(f"Renovar {vencido} documento(s) vencido(s)")
        if requiere_completado:
            tasks.append(f"Completar {requiere_completado} formulario(s) / entregable(s)")
        if sin_analizar:
            tasks.append(f"Analizar {sin_analizar} documento(s) sin lectura confirmada")
        if requiere_revision:
            tasks.append(f"Revisar {requiere_revision} requisito(s) con vigencia no verificada")

        return DGCPBidPackageResponse(
            opportunity_id=opportunity.id,
            opportunity_code=opportunity.code,
            preparation_pct=pct,
            total_requirements=len(checklist),
            mandatory_requirements=total_mandatory,
            compliant_count=compliant,
            found_documents=encontrado_vigente,
            pending_documents=faltante,
            expired_documents=vencido,
            forms_to_complete=requiere_completado,
            review_count=requiere_revision,
            recommended_tasks=tasks,
            available=[c["requirement"] for c in checklist if c.get("status") == "encontrado_vigente"],
            missing=[c["requirement"] for c in checklist if c.get("status") == "faltante"],
            expired=[c["requirement"] for c in checklist if c.get("status") == "encontrado_vencido"],
            to_complete=[c["requirement"] for c in checklist if c.get("status") == "requiere_completado"],
            requires_review=[
                c["requirement"]
                for c in checklist
                if c.get("status") in REVIEW_STATUSES | UNANALYZED_STATUSES
            ],
            analyzed_at=now,
        )

    @staticmethod
    def compute_expediente_status(checklist: list[dict], preparation_pct: float) -> str:
        mandatory = [c for c in checklist if c.get("mandatory", True)]
        if not mandatory:
            return "sin_preparar"

        statuses = {c.get("status") for c in mandatory}
        if statuses <= COMPLIANT_STATUSES and preparation_pct >= 99.9:
            return "expediente_listo_para_revision"

        if any(s in VENCIDO_STATUSES for s in statuses):
            return "expediente_con_documentos_vencidos"

        if any(s in COMPLETE_STATUSES for s in statuses):
            return "expediente_en_preparacion"

        if any(s in UNANALYZED_STATUSES for s in statuses):
            return "expediente_incompleto"

        if any(s in FALTANTE_STATUSES | REVIEW_STATUSES for s in statuses):
            return "expediente_incompleto"

        if preparation_pct >= 70:
            return "expediente_incompleto"
        return "expediente_en_preparacion"

    @staticmethod
    def can_mark_ready_for_review(checklist: list[dict]) -> bool:
        mandatory = [c for c in checklist if c.get("mandatory", True)]
        if not mandatory:
            return False
        return all(c.get("status") in COMPLIANT_STATUSES for c in mandatory)

    @staticmethod
    def display_status_label(status: str) -> str:
        labels = {
            "encontrado_vigente": "Cumplido",
            "encontrado_sin_fecha": "Requiere validación de vigencia",
            "encontrado_sin_analizar": "Pendiente de análisis",
            "requiere_revision": "Requiere revisión",
            "requiere_completado": "Pendiente de completar",
            "faltante": "Faltante",
            "no_aplica": "No aplica",
            "encontrado_vencido": "Vencido",
            "validado_manual": "Validado manualmente",
            "adjuntado": "Adjuntado al expediente",
            "borrador_pendiente": "Borrador pendiente de crear en Odoo",
            "cotizacion_encontrada": "Cotización encontrada",
            "pdf_descargado": "PDF descargado",
            "generado": "Generado",
            "pendiente_firma": "Pendiente de firma",
            "pendiente_sello": "Pendiente de sello",
            "firmado": "Firmado",
            "sellado": "Sellado",
            "pdf_final_generado": "PDF final generado",
            "finalizado": "Finalizado",
            "requiere_revision": "Requiere revisión",
        }
        return labels.get(status, status.replace("_", " ").title())

    @staticmethod
    def build_analysis_warnings(
        process_documents: list[dict],
        extraction: ExtractionResult,
    ) -> list[str]:
        warnings: list[str] = []
        has_pliego_tdr = any(
            d.get("doc_role") in ("pliego", "tdr", "especificaciones")
            and d.get("has_text")
            and d.get("source_type") not in ("reference",)
            and d.get("source_type") in ("portal", "dgcp_api", "portal_text", "process_file")
            for d in process_documents
        )
        if not has_pliego_tdr:
            warnings.append(
                "No se encontró pliego/TDR real adjunto. El análisis puede estar incompleto."
            )
        if len(extraction.mandatory_documents) < len(DEFAULT_LICITACION_DOCS):
            warnings.append(
                "Se aplicó línea base de requisitos de licitación porque la extracción del pliego es parcial."
            )
        return warnings

    @staticmethod
    def checklist_counts(items: list[dict]) -> dict[str, int]:
        mandatory = [i for i in items if i.get("mandatory", True)]

        def _counts_as_compliant(item: dict) -> bool:
            status = item.get("status")
            if status not in COMPLIANT_STATUSES:
                return False
            if status == "no_aplica":
                return True
            return DGCPComplianceEngine.has_document_evidence({}, item)

        return {
            "total": len(items),
            "mandatory_total": len(mandatory),
            "compliant_count": sum(1 for i in mandatory if _counts_as_compliant(i)),
            "pending_count": sum(1 for i in items if i.get("status") == "faltante"),
            "expired_count": sum(1 for i in items if i.get("status") == "encontrado_vencido"),
            "incomplete_count": sum(1 for i in items if i.get("status") == "requiere_completado"),
            "review_count": sum(
                1 for i in items
                if i.get("status") in ("requiere_revision", "encontrado_sin_fecha", "encontrado_sin_analizar")
            ),
            "unanalyzed_count": sum(1 for i in items if i.get("status") == "encontrado_sin_analizar"),
        }
