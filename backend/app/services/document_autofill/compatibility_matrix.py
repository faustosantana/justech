"""Clasificación y análisis de causa raíz para matriz de compatibilidad autollenado."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.services.document_autofill.dgcp_autofill_batch_service import TemplateRunResult
from app.services.document_autofill.m365_template_cache import cache_status, is_likely_stub


@dataclass
class MatrixRow:
    formulario: str
    tipo: str
    plantilla_oficial: str
    fuente: str
    docx_generado: str
    pdf_generado: str
    campos_detectados: int
    campos_completados: int
    campos_faltantes: int
    campos_no_mapeados: int
    formato_preservado: str
    estado: str  # PASS | PARTIAL | FAIL
    causa_raiz: str = ""
    falta_plantilla: bool = False
    no_es_docx: bool = False
    plantilla_corrupta: bool = False
    sin_campos_detectables: bool = False
    requiere_mapeo_manual: bool = False
    requiere_ocr_conversion: bool = False
    accion_concreta: str = ""
    docx_path: str | None = None
    pdf_path: str | None = None
    m365_file_id: str | None = None
    campos_llenos_lista: list[str] = field(default_factory=list)
    campos_faltantes_lista: list[str] = field(default_factory=list)
    campos_no_mapeados_lista: list[str] = field(default_factory=list)


def _is_pdf(name: str) -> bool:
    return (name or "").lower().endswith(".pdf")


def _is_docx(name: str) -> bool:
    return (name or "").lower().endswith(".docx")


def _source_label(result: TemplateRunResult, *, cached: bool) -> str:
    if result.status == "FAILED" and not cached:
        err = " ".join(result.errors).lower()
        if _is_pdf(result.template_name):
            return "Sin plantilla oficial (PDF)"
        if "no se pudo descargar" in err:
            return "Sin plantilla oficial"
        return "Sin plantilla oficial"
    src = result.source or "pending"
    if cached and src in ("m365", "m365_cache", "pending"):
        return "caché oficial DGCP/M365"
    if src == "m365_cache":
        return "caché oficial DGCP/M365"
    if src == "m365":
        return "M365 / SharePoint"
    if cached:
        return "caché local"
    return "Sin plantilla oficial"


def _plantilla_oficial_label(result: TemplateRunResult, *, cached: bool) -> str:
    if result.status == "FAILED" and not cached:
        if _is_pdf(result.template_name):
            return "Requiere plantilla DOCX editable"
        return "Sin plantilla oficial"
    if result.docx_generated or result.pdf_generated:
        return result.template_name
    if cached:
        return result.template_name
    return "Sin plantilla oficial"


def classify_result(
    result: TemplateRunResult,
    *,
    unmapped_fields: list[str] | None = None,
    template_format: str = "docx",
) -> MatrixRow:
    unmapped = unmapped_fields or []
    cached = False
    likely_stub = False
    if result.m365_file_id:
        try:
            st = cache_status(uuid.UUID(result.m365_file_id))
            cached = st.cached
            likely_stub = st.likely_stub
        except (ValueError, TypeError):
            pass

    is_pdf_tpl = template_format == "pdf" or _is_pdf(result.template_name)
    errors_text = "; ".join(result.errors).lower()

    row = MatrixRow(
        formulario=result.form_type,
        tipo=result.detected_type,
        plantilla_oficial=_plantilla_oficial_label(result, cached=cached),
        fuente=_source_label(result, cached=cached),
        docx_generado="sí" if result.docx_generated else "no",
        pdf_generado="sí" if result.pdf_generated else "no",
        campos_detectados=result.aliases_detected,
        campos_completados=result.aliases_mapped,
        campos_faltantes=result.aliases_critical_pending + result.aliases_non_critical_pending,
        campos_no_mapeados=len(unmapped) if unmapped else len(result.fields_pending),
        formato_preservado="sí" if result.original_intact else "no",
        estado=_estado(result),
        docx_path=result.docx_path,
        pdf_path=result.pdf_path,
        m365_file_id=result.m365_file_id,
        campos_llenos_lista=list(result.fields_filled or []),
        campos_faltantes_lista=list(
            (result.critical_pending_aliases or []) + (result.non_critical_pending_aliases or [])
        ),
        campos_no_mapeados_lista=list(unmapped) if unmapped else list(result.fields_pending or []),
    )

    if row.estado == "FAIL":
        _analyze_fail(row, result, cached=cached, is_pdf_tpl=is_pdf_tpl, likely_stub=likely_stub, errors_text=errors_text)
    elif row.estado == "PARTIAL":
        _analyze_partial(row, result, unmapped=unmapped)
    else:
        row.causa_raiz = "Plantilla oficial DOCX autollenada; PDF desde LibreOffice; formato intacto."
        if row.campos_faltantes:
            row.accion_concreta = "Opcional: completar campos no críticos pendientes."
        elif row.campos_no_mapeados:
            row.requiere_mapeo_manual = True
            row.accion_concreta = "Opcional: mapear aliases no críticos en UI."

    return row


def _estado(result: TemplateRunResult) -> str:
    if result.status == "FAILED":
        return "FAIL"
    if not result.docx_generated or not result.pdf_generated:
        return "FAIL"
    if result.source not in ("m365", "m365_cache", "pending") and result.status != "FAILED":
        return "FAIL"
    if not result.original_intact:
        return "FAIL"
    if result.completion_status == "READY_FOR_SIGNATURE":
        return "PASS"
    if result.completion_status == "DRAFT_OK" and result.aliases_critical_pending == 0:
        return "PASS"
    if result.aliases_critical_pending > 0:
        return "PARTIAL"
    if result.completion_status == "BLOCKED":
        return "PARTIAL"
    return "PASS"


def _analyze_fail(
    row: MatrixRow,
    result: TemplateRunResult,
    *,
    cached: bool,
    is_pdf_tpl: bool,
    likely_stub: bool,
    errors_text: str,
) -> None:
    if is_pdf_tpl:
        row.no_es_docx = True
        row.falta_plantilla = not cached
        row.requiere_ocr_conversion = True
        row.causa_raiz = (
            "Plantilla indexada como PDF — el motor requiere DOCX oficial editable. "
            "No se descargó bytes (OAuth M365 desconectado; no hay caché local)."
        )
        row.accion_concreta = (
            "1) Obtener versión DOCX oficial o convertir manualmente a DOCX editable. "
            "2) Subir a biblioteca M365 / ejecutar bootstrap con OAuth. "
            "3) Re-ejecutar autollenado."
        )
        return

    if likely_stub or "stub" in errors_text:
        row.plantilla_corrupta = True
        row.causa_raiz = "Plantilla detectada como stub o simplificada — generación bloqueada."
        row.accion_concreta = "Eliminar stub de caché; descargar plantilla oficial DGCP o sincronizar M365."
        return

    if not cached and "no se pudo descargar" in errors_text:
        row.falta_plantilla = True
        row.causa_raiz = (
            "Plantilla indexada en biblioteca pero bytes no disponibles: "
            "caché vacía, portal DGCP sin este archivo, SharePoint devuelve 401 (OAuth desconectado)."
        )
        row.accion_concreta = (
            "1) Reconectar OAuth M365 (fausto@justech.do). "
            "2) Sincronizar repositorio Plantillas. "
            "3) Ejecutar bootstrap_m365_template_cache. "
            "4) Si no está en DGCP público, cargar manualmente a caché oficial."
        )
        return

    if "hash distinto" in errors_text or not result.original_intact:
        row.plantilla_corrupta = True
        row.causa_raiz = "La plantilla original fue modificada durante el proceso (hash distinto)."
        row.accion_concreta = "Revisar motor DOCX; no debe escribir sobre plantilla en caché."
        return

    row.causa_raiz = errors_text or "Error no clasificado"
    row.accion_concreta = "Revisar logs batch y corregir causa específica."


def _analyze_partial(row: MatrixRow, result: TemplateRunResult, *, unmapped: list[str]) -> None:
    crit = result.critical_pending_aliases or []
    non_crit = result.non_critical_pending_aliases or []

    post_adj = any(
        k in " ".join(crit).lower()
        for k in ("adjudicatario", "contrato", "liquidacion", "ejecucion")
    )

    if crit:
        row.requiere_mapeo_manual = True
        if post_adj:
            row.causa_raiz = (
                f"Plantilla oficial OK; campos de etapa post-adjudicación sin datos en expediente: "
                f"{', '.join(crit[:3])}."
            )
            row.accion_concreta = (
                "Completar manualmente campos de adjudicación/contrato o mapear aliases; "
                "no aplica en etapa de oferta."
            )
        else:
            row.causa_raiz = f"Campos críticos pendientes: {', '.join(crit[:5])}."
            row.accion_concreta = "Completar campos faltantes en UI o mapear aliases manualmente."
    elif non_crit:
        row.causa_raiz = f"Solo campos no críticos pendientes: {', '.join(non_crit[:5])}."
        row.accion_concreta = "Opcional: completar logo/institución u otros no críticos."

    if unmapped:
        row.requiere_mapeo_manual = True
        row.causa_raiz += f" Campos no mapeados: {len(unmapped)}."

    if result.aliases_detected == 0 and result.docx_generated:
        row.sin_campos_detectables = True
        row.causa_raiz = "Plantilla DOCX sin placeholders detectables (portada/pliego)."
        row.accion_concreta = "Clasificar como plantilla estructural; no requiere autollenado de datos empresa."


def result_from_batch_dict(data: dict[str, Any]) -> TemplateRunResult:
    """Reconstruye TemplateRunResult desde batch_summary JSON."""
    return TemplateRunResult(
        template_name=data["template_name"],
        template_key=data.get("template_key", ""),
        form_type=data["form_type"],
        m365_location=data.get("m365_location", ""),
        detected_type=data.get("detected_type", ""),
        source=data.get("source", "pending"),
        pdf_engine=data.get("pdf_engine", ""),
        fields_detected=data.get("fields_detected", []),
        fields_filled=data.get("fields_filled", []),
        fields_pending=data.get("fields_pending", []),
        pdf_generated=data.get("pdf_generated", False),
        docx_generated=data.get("docx_generated", False),
        original_intact=data.get("original_intact", False),
        errors=data.get("errors", []),
        status=data.get("status", "FAILED"),
        m365_file_id=data.get("m365_file_id"),
        web_url=data.get("web_url"),
        pdf_path=data.get("pdf_path"),
        docx_path=data.get("docx_path"),
        aliases_detected=data.get("aliases_detected", 0),
        aliases_mapped=data.get("aliases_mapped", 0),
        aliases_critical_pending=data.get("aliases_critical_pending", 0),
        aliases_non_critical_pending=data.get("aliases_non_critical_pending", 0),
        critical_pending_aliases=data.get("critical_pending_aliases", []),
        non_critical_pending_aliases=data.get("non_critical_pending_aliases", []),
        partial_reason=data.get("partial_reason"),
        completion_status=data.get("completion_status", "FAILED"),
    )
