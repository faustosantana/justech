"""Contexto de plantilla — etapa del proceso y uso documental."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.document_autofill.m365_template_catalog import classify_template

PRE_ADJUDICATION = "pre_adjudication"
POST_ADJUDICATION = "post_adjudication"

# Categorías típicamente usadas antes de la adjudicación
PRE_ADJUDICATION_CATEGORIES = frozenset(
    {
        "oferta_economica",
        "oferta_tecnica",
        "sncc_pliego",
        "sncc_formulario",
        "portada",
        "consultoria",
        "proveedor",
        "declaracion",
        "datos_empresa",
        "carta",
    }
)

POST_ADJUDICATION_CATEGORIES = frozenset({"contrato"})

# Nombres de archivo SNCC documento posterior a adjudicación
POST_ADJUDICATION_DOC_RE = re.compile(
    r"contrato|orden_compra|orden_servicio|liquidacion|recepcion|garantia|"
    r"ejecucion|devolucion|acta|designacion_agente|aceptacion_agente",
    re.I,
)

# Aliases que solo aplican tras adjudicación
POST_ADJUDICATION_FIELD_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"adjudicatario", re.I), "nombre_adjudicatario"),
    (re.compile(r"fecha.*adjudic", re.I), "fecha_adjudicacion"),
    (
        re.compile(r"no\.?\s*de\s*contrato|numero.*contrato|n[uú]mero.*contrato|no\.?\s*contrato", re.I),
        "numero_contrato",
    ),
    (re.compile(r"monto.*adjudic|monto del contrato adjudicado", re.I), "monto_adjudicado"),
]


@dataclass(frozen=True)
class TemplateProcessContext:
    process_stage: str
    detected_category: str
    document_usage: str
    template_name: str

    @property
    def is_post_adjudication(self) -> bool:
        return self.process_stage == POST_ADJUDICATION


def resolve_process_stage(
    template_name: str,
    detected_category: str,
    *,
    parent_path: str = "",
    document_type: str = "",
) -> str:
    name = template_name.lower()
    if detected_category in POST_ADJUDICATION_CATEGORIES:
        return POST_ADJUDICATION
    if detected_category == "sncc_documento" and POST_ADJUDICATION_DOC_RE.search(name):
        return POST_ADJUDICATION
    if detected_category in PRE_ADJUDICATION_CATEGORIES:
        return PRE_ADJUDICATION
    if detected_category == "sncc_documento":
        return PRE_ADJUDICATION
    if "contrato" in name or document_type == "contrato":
        return POST_ADJUDICATION
    return PRE_ADJUDICATION


def resolve_document_usage(detected_category: str, process_stage: str, template_name: str) -> str:
    if process_stage == POST_ADJUDICATION:
        if detected_category == "contrato" or "liquidacion" in template_name.lower():
            return "contrato_post_adjudicacion"
        if "orden" in template_name.lower():
            return "orden_ejecucion"
        if "recepcion" in template_name.lower():
            return "acta_recepcion"
        return "documento_post_adjudicacion"
    if detected_category in ("oferta_economica", "oferta_tecnica"):
        return "oferta_propuesta"
    if detected_category == "sncc_pliego":
        return "pliego_convocatoria"
    if detected_category == "sncc_formulario":
        return "formulario_oferta"
    if detected_category == "carta":
        return "carta_proceso"
    return "documento_pre_adjudicacion"


def resolve_template_context(
    template_name: str,
    *,
    detected_category: str | None = None,
    parent_path: str = "",
    document_type: str = "",
) -> TemplateProcessContext:
    if not detected_category:
        detected_category, _, _ = classify_template(template_name, parent_path, document_type)
    stage = resolve_process_stage(
        template_name,
        detected_category,
        parent_path=parent_path,
        document_type=document_type,
    )
    usage = resolve_document_usage(detected_category, stage, template_name)
    return TemplateProcessContext(
        process_stage=stage,
        detected_category=detected_category,
        document_usage=usage,
        template_name=template_name,
    )


def match_post_adjudication_field(alias: str, alias_normalized: str) -> str | None:
    text = f"{alias} {alias_normalized}"
    for pattern, canonical in POST_ADJUDICATION_FIELD_RULES:
        if pattern.search(text):
            return canonical
    return None
