"""Registro de aliases Word → campos canónicos JAIOS."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Campos canónicos y etiquetas
CANONICAL_FIELDS: dict[str, str] = {
    "razon_social": "Razón social",
    "rnc": "RNC",
    "direccion": "Dirección",
    "representante_legal": "Representante legal",
    "cedula_representante": "Cédula representante",
    "cargo_representante": "Cargo representante",
    "telefono": "Teléfono",
    "correo": "Correo",
    "cuenta_bancaria": "Cuenta bancaria",
    "banco": "Banco",
    "proceso_dgcp": "Código proceso DGCP",
    "entidad_contratante": "Entidad contratante",
    "objeto_contratacion": "Objeto del contrato",
    "objeto_proceso": "Objeto del proceso",
    "monto_oferta": "Monto oferta",
    "monto": "Monto",
    "fecha": "Fecha",
    "plazo_entrega": "Plazo de entrega",
    "condiciones_pago": "Condiciones de pago",
    "condiciones": "Condiciones",
    "productos": "Productos/servicios",
    "garantia": "Garantía",
    "fabricante": "Fabricante",
    "firma": "Firma",
    "sello": "Sello",
    "logo_dependencia": "Logo dependencia",
    "nombre_adjudicatario": "Nombre del adjudicatario",
    "fecha_adjudicacion": "Fecha de adjudicación",
    "numero_contrato": "Número de contrato",
    "monto_adjudicado": "Monto adjudicado",
}

# Campos críticos — impiden uso del documento / firma si aparecen sin valor
CRITICAL_CANONICAL_FIELDS = frozenset(
    {
        "razon_social",
        "rnc",
        "representante_legal",
        "cedula_representante",
        "proceso_dgcp",
        "entidad_contratante",
        "monto_oferta",
        "monto",
        "fecha",
        "plazo_entrega",
        "condiciones_pago",
        "condiciones",
    }
)

# Campos no críticos — se muestran pendientes pero no bloquean generación
NON_CRITICAL_CANONICAL_FIELDS = frozenset(
    {
        "direccion",
        "telefono",
        "correo",
        "cuenta_bancaria",
        "banco",
        "objeto_contratacion",
        "objeto_proceso",
        "cargo_representante",
        "fabricante",
        "firma",
        "sello",
        "logo_dependencia",
        "productos",
        "garantia",
    }
)

# Aliases / patrones ignorables por defecto (metadatos, pliegos, instrucciones)
IGNORABLE_ALIAS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"codigo.oficial.del.formato|nombre.del.formato", re.I),
    re.compile(r"horario.*pliego|lugar.*pliego|costo.*pliego", re.I),
    re.compile(r"presentacion.de.propuestas|lugar.de.entrega", re.I),
    re.compile(r"responsable.daf|observaciones|tipo.de.documento", re.I),
    re.compile(r"^indicar\s+(lugar|horario|costo)\s*$", re.I),
]

# Aliases no críticos por patrón (sin canónico asignado)
NON_CRITICAL_ALIAS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"logo", re.I),
    re.compile(r"codigo.oficial|nombre.del.formato", re.I),
    re.compile(r"horario|pliego|lugar.de.obtencion", re.I),
    re.compile(r"observacion|descripcion|nombre.comercial|nombre.del.item", re.I),
    re.compile(r"tipo.de.garantia|tipo.de.contrato", re.I),
]

# Aliases críticos por patrón cuando no hay canónico
CRITICAL_ALIAS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brnc\b|registro.nacional", re.I),
    re.compile(r"razon.?social|nombre.*oferente|nombre.*empresa", re.I),
    re.compile(r"representante|cédula|cedula", re.I),
    re.compile(r"expediente|proceso.?dgcp|no\.?\s*de\s*documento", re.I),
    re.compile(r"instituc|entidad.?contratante|entidad.?emisora", re.I),
    re.compile(r"monto|precio|oferta.?econom", re.I),
    re.compile(r"^fecha\b|fecha.de.emision", re.I),
    re.compile(r"plazo|condicion", re.I),
]

# Aliases estáticos exactos (normalizado → canónico)
STATIC_ALIAS_MAP: dict[str, str] = {
    "3212": "rnc",
    "3213": "razon_social",
    "rpe": "rpe",
    "no._rpe": "rpe",
    "registro_proveedor_estado": "rpe",
    "r.n.c": "rnc",
    "r.n.c.": "rnc",
    "no._del_expediente_de_compras": "proceso_dgcp",
    "no_del_expediente_de_compras": "proceso_dgcp",
    "no__del_expediente_de_compras": "proceso_dgcp",
    "expediente": "proceso_dgcp",
    "codigo_proceso": "proceso_dgcp",
    "proceso_dgcp": "proceso_dgcp",
    "proceso": "proceso_dgcp",
    "institucion": "entidad_contratante",
    "institución": "entidad_contratante",
    "nombre_de_la_institución": "entidad_contratante",
    "nombre_de_la_institucion": "entidad_contratante",
    "entidad_contratante": "entidad_contratante",
    "entidad": "entidad_contratante",
    "dependencia": "entidad_contratante",
    "razon_social": "razon_social",
    "razón_social": "razon_social",
    "nombre_oferente": "razon_social",
    "nombre_del_oferente": "razon_social",
    "oferente": "razon_social",
    "representante": "representante_legal",
    "representante_legal": "representante_legal",
    "nombre_representante": "representante_legal",
    "direccion": "direccion",
    "dirección": "direccion",
    "domicilio": "direccion",
    "telefono": "telefono",
    "teléfono": "telefono",
    "telefono_de_contacto": "telefono",
    "correo": "correo",
    "correo_electronico": "correo",
    "correo_electrónico": "correo",
    "email": "correo",
    "e-mail": "correo",
    "cuenta_bancaria": "cuenta_bancaria",
    "cuenta": "cuenta_bancaria",
    "no._cuenta": "cuenta_bancaria",
    "banco": "banco",
    "objeto": "objeto_contratacion",
    "objeto_contratacion": "objeto_contratacion",
    "objeto_del_contrato": "objeto_contratacion",
    "objeto_proceso": "objeto_proceso",
    "monto": "monto_oferta",
    "monto_oferta": "monto_oferta",
    "precio": "monto_oferta",
    "fecha": "fecha",
    "fecha_de_emisión_del_documento": "fecha",
    "fecha_de_emision_del_documento": "fecha",
    "plazo": "plazo_entrega",
    "plazo_entrega": "plazo_entrega",
    "condiciones": "condiciones_pago",
    "condiciones_pago": "condiciones_pago",
    "firma": "firma",
    "cargo": "cargo_representante",
    "cargo_representante": "cargo_representante",
    "cedula": "cedula_representante",
    "cédula": "cedula_representante",
    "logo_de_la_dependencia_gubernamental": "logo_dependencia",
    "fabricante": "fabricante",
    "departamento_ó_unidad_funcional": "entidad_contratante",
    "departamento_o_unidad_funcional": "entidad_contratante",
    "indicar_nombre_de_la_empresa": "razon_social",
    "indicar_nombre_del_adjudicatario": "nombre_adjudicatario",
    "nombre_del_adjudicatario": "nombre_adjudicatario",
    "nombre_adjudicatario": "nombre_adjudicatario",
    "indicar_nombre_de_la_entidad_emisora": "entidad_contratante",
    "indicar_bienes_servicios_u_obras": "objeto_contratacion",
    "no_de_documento": "proceso_dgcp",
}

# Reglas por patrón (regex sobre alias normalizado)
PATTERN_RULES: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"rnc|registro.nacional", re.I), "rnc", 0.92),
    (re.compile(r"razon.?social|nombre.*oferente|^oferente$", re.I), "razon_social", 0.9),
    (re.compile(r"representante", re.I), "representante_legal", 0.88),
    (re.compile(r"expediente|proceso.?dgcp|codigo.?proceso", re.I), "proceso_dgcp", 0.88),
    (re.compile(r"instituc|dependencia|entidad", re.I), "entidad_contratante", 0.85),
    (re.compile(r"direccion|domicilio", re.I), "direccion", 0.9),
    (re.compile(r"telefono|tel\b", re.I), "telefono", 0.88),
    (re.compile(r"correo|email|e-mail", re.I), "correo", 0.88),
    (re.compile(r"cuenta.?banc|no.?cuenta", re.I), "cuenta_bancaria", 0.85),
    (re.compile(r"\bbanco\b", re.I), "banco", 0.82),
    (re.compile(r"objeto", re.I), "objeto_contratacion", 0.8),
    (re.compile(r"monto|precio|oferta.?econom", re.I), "monto_oferta", 0.85),
    (re.compile(r"fecha", re.I), "fecha", 0.85),
    (re.compile(r"plazo", re.I), "plazo_entrega", 0.82),
    (re.compile(r"condicion", re.I), "condiciones_pago", 0.8),
    (re.compile(r"fabricante", re.I), "fabricante", 0.88),
    (re.compile(r"cedula|cédula", re.I), "cedula_representante", 0.85),
    (re.compile(r"cargo", re.I), "cargo_representante", 0.82),
    (re.compile(r"firma", re.I), "firma", 0.75),
    (re.compile(r"logo", re.I), "logo_dependencia", 0.7),
    (re.compile(r"indicar.*nombre.*empresa|nombre.*empresa", re.I), "razon_social", 0.86),
    (re.compile(r"adjudicatario", re.I), "nombre_adjudicatario", 0.88),
    (re.compile(r"fecha.*adjudic", re.I), "fecha_adjudicacion", 0.85),
    (re.compile(r"no\.?\s*de\s*contrato|numero.*contrato", re.I), "numero_contrato", 0.82),
    (re.compile(r"monto.*adjudic", re.I), "monto_adjudicado", 0.82),
    (re.compile(r"indicar.*entidad|entidad.?emisora", re.I), "entidad_contratante", 0.84),
    (re.compile(r"indicar.*bienes|servicios.*obras", re.I), "objeto_contratacion", 0.82),
    (re.compile(r"indicar.*monto|monto.*garant|monto.*contrato", re.I), "monto_oferta", 0.8),
    (re.compile(r"indicar.*fecha|fecha.*vencim|fecha.*letras", re.I), "fecha", 0.78),
    (re.compile(r"indicar.*no\b|no\.?\s*de\s*documento", re.I), "proceso_dgcp", 0.72),
    (re.compile(r"indicar.*tipo.*contrato", re.I), "objeto_contratacion", 0.7),
]

NUMERIC_ALIAS_RE = re.compile(r"^\d{3,5}$")

COMPLETE_STATUSES = frozenset({"completo", "ignorado", "no_aplica_etapa"})

STATUS_RANK: dict[str, int] = {
    "completo": 5,
    "no_aplica_etapa": 4,
    "ignorado": 4,
    "no_critico": 3,
    "pendiente": 2,
    "critico": 1,
}


def normalize_alias(alias: str) -> str:
    text = alias.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def canonical_field_key(key: str | None) -> str:
    """Clave canónica única para deduplicar variantes (acentos, puntuación, alias numéricos)."""
    if not key:
        return ""
    norm = normalize_alias(key)
    for candidate in (norm, norm.rstrip("_")):
        if candidate in STATIC_ALIAS_MAP:
            return STATIC_ALIAS_MAP[candidate]
    if norm in CANONICAL_FIELDS:
        return norm
    return norm.rstrip("_") or norm


def _field_status_rank(status: str | None) -> int:
    return STATUS_RANK.get(status or "", 0)


def deduplicate_field_statuses(fields: list) -> list:
    """Fusiona entradas duplicadas; conserva el mejor estado por clave canónica."""
    best: dict[str, object] = {}
    for field in fields:
        key = getattr(field, "key", None) or getattr(field, "label", "")
        canon = canonical_field_key(str(key))
        if not canon:
            continue
        prev = best.get(canon)
        if prev is None:
            best[canon] = field
            continue
        f_rank = _field_status_rank(getattr(field, "status", None))
        p_rank = _field_status_rank(getattr(prev, "status", None))
        if f_rank > p_rank:
            best[canon] = field
        elif f_rank == p_rank and getattr(field, "value", None) and not getattr(prev, "value", None):
            best[canon] = field
    return list(best.values())


def partition_fields_by_canonical(fields: list) -> tuple[list, list]:
    """Particiona campos deduplicados en completados vs pendientes."""
    deduped = deduplicate_field_statuses(fields)
    completed: list = []
    pending: list = []
    for field in deduped:
        status = getattr(field, "status", None) or "pendiente"
        if status in COMPLETE_STATUSES:
            completed.append(field)
        else:
            pending.append(field)
    return completed, pending


@dataclass
class AliasMappingSuggestion:
    alias: str
    alias_normalized: str
    canonical: str | None
    confidence: float
    source: str  # static, pattern, manual_global, manual_template, ignored, unresolved
    status: str  # mapeado, pendiente, ignorado


def suggest_canonical(
    alias: str,
    *,
    stored_global: dict[str, dict] | None = None,
    stored_template: dict[str, dict] | None = None,
    template_name: str = "",
) -> AliasMappingSuggestion:
    norm = normalize_alias(alias)
    stored_global = stored_global or {}
    stored_template = stored_template or {}

    if norm in stored_template:
        entry = stored_template[norm]
        if entry.get("status") == "ignorado" and norm not in {"3212", "3213"}:
            return AliasMappingSuggestion(alias, norm, None, 1.0, "manual_template", "ignorado")
        canon = entry.get("canonical") or STATIC_ALIAS_MAP.get(norm)
        if canon or entry.get("status") != "ignorado":
            return AliasMappingSuggestion(
                alias,
                norm,
                canon,
                float(entry.get("confidence", 0.95)),
                "manual_template",
                "mapeado" if canon else "pendiente",
            )

    if norm in stored_global:
        entry = stored_global[norm]
        if entry.get("status") == "ignorado" and norm not in {"3212", "3213"}:
            return AliasMappingSuggestion(alias, norm, None, 1.0, "manual_global", "ignorado")
        canon = entry.get("canonical") or STATIC_ALIAS_MAP.get(norm)
        if canon or entry.get("status") != "ignorado":
            return AliasMappingSuggestion(
                alias,
                norm,
                canon,
                float(entry.get("confidence", 0.95)),
                "manual_global",
                "mapeado" if canon else "pendiente",
            )

    if norm in STATIC_ALIAS_MAP:
        return AliasMappingSuggestion(
            alias, norm, STATIC_ALIAS_MAP[norm], 0.93, "static", "mapeado"
        )

    from app.services.document_autofill.form_template_registry import SNCC_NUMERIC_ALIAS_MAP

    if norm in SNCC_NUMERIC_ALIAS_MAP:
        return AliasMappingSuggestion(
            alias,
            norm,
            SNCC_NUMERIC_ALIAS_MAP[norm],
            0.98,
            "sncc_numeric",
            "mapeado",
        )

    for pattern, canonical, conf in PATTERN_RULES:
        if pattern.search(norm) or pattern.search(alias):
            return AliasMappingSuggestion(alias, norm, canonical, conf, "pattern", "mapeado")

    if NUMERIC_ALIAS_RE.match(norm):
        return AliasMappingSuggestion(alias, norm, None, 0.0, "unresolved", "pendiente")

    # Si el alias ya es un campo canónico
    if norm in CANONICAL_FIELDS:
        return AliasMappingSuggestion(alias, norm, norm, 0.95, "static", "mapeado")

    return AliasMappingSuggestion(alias, norm, None, 0.0, "unresolved", "pendiente")


def canonical_value_key(canonical: str) -> str:
    """Normaliza clave canónica al dict de valores del completion service."""
    if canonical == "objeto_contratacion":
        return "objeto_proceso"
    if canonical == "monto_oferta":
        return "monto"
    if canonical == "condiciones_pago":
        return "condiciones"
    if canonical == "cargo_representante":
        return "cargo"
    if canonical == "entidad_contratante":
        return "institucion"
    return canonical


def is_critical_canonical(canonical: str | None) -> bool:
    if not canonical:
        return False
    if canonical in CRITICAL_CANONICAL_FIELDS:
        return True
    key = canonical_value_key(canonical)
    return key in CRITICAL_CANONICAL_FIELDS


def classify_pending(
    *,
    alias: str,
    alias_normalized: str,
    canonical: str | None,
    status: str,
    has_value: bool,
    process_stage: str = "pre_adjudication",
) -> str:
    """Retorna: completado | critico | no_critico | ignorado | no_aplica_etapa."""
    from app.services.document_autofill.template_process_context import (
        POST_ADJUDICATION,
        match_post_adjudication_field,
    )

    if status == "ignorado":
        return "ignorado"
    if has_value and status == "mapeado":
        return "completado"

    post_field = match_post_adjudication_field(alias, alias_normalized)
    post_canonicals = {
        "nombre_adjudicatario",
        "fecha_adjudicacion",
        "numero_contrato",
        "monto_adjudicado",
    }
    is_post_field = post_field is not None or (canonical in post_canonicals)

    if is_post_field:
        if process_stage != POST_ADJUDICATION:
            return "no_aplica_etapa"
        return "completado" if has_value else "critico"

    if canonical:
        if is_critical_canonical(canonical):
            return "critico"
        return "no_critico"

    text = f"{alias} {alias_normalized}"
    for pat in IGNORABLE_ALIAS_PATTERNS:
        if pat.search(text):
            return "ignorado"
    for pat in CRITICAL_ALIAS_PATTERNS:
        if pat.search(text):
            return "critico"
    for pat in NON_CRITICAL_ALIAS_PATTERNS:
        if pat.search(text):
            return "no_critico"

    if NUMERIC_ALIAS_RE.match(alias_normalized):
        return "critico"

    return "no_critico"
