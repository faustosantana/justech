"""Registro genérico de plantillas — aliases numéricos y resolución por familia."""

from __future__ import annotations

import re

# Aliases numéricos M365 compartidos por formularios SNCC (F.033, F.042, F.047, …)
SNCC_NUMERIC_ALIAS_MAP: dict[str, str] = {
    "3212": "rnc",
    "3213": "razon_social",
}

FORM_FAMILY_NUMERIC_ALIASES: dict[str, dict[str, str]] = {
    "SNCC": SNCC_NUMERIC_ALIAS_MAP,
}


def form_family(form_type: str) -> str:
    ft = (form_type or "").upper().replace(" ", ".")
    if ft.startswith("SNCC"):
        return "SNCC"
    return ft.split(".")[0] if "." in ft else ft


def numeric_alias_map(form_type: str) -> dict[str, str]:
    return dict(FORM_FAMILY_NUMERIC_ALIASES.get(form_family(form_type), {}))


def resolve_numeric_canonical(alias_normalized: str, form_type: str) -> str | None:
    return numeric_alias_map(form_type).get(alias_normalized)


def default_form_type_from_checklist(checklist: list[dict] | None) -> str | None:
    if not checklist:
        return None
    for item in checklist:
        ft = item.get("form_type")
        if ft:
            return normalize_form_type(str(ft))
    return None


SNCC_REQ_TO_FORM_TYPE: dict[str, str] = {
    "sncc_f033": "SNCC.F033",
    "sncc_f034": "SNCC.F034",
    "sncc_f042": "SNCC.F042",
    "sncc_f047": "SNCC.F047",
}

_FORM_TYPE_ALIASES: dict[str, str] = {
    "F.033": "SNCC.F033",
    "F033": "SNCC.F033",
    "033": "SNCC.F033",
    "SNCC.033": "SNCC.F033",
    "SNCC.F.033": "SNCC.F033",
    "SNCC_F033": "SNCC.F033",
    "SNCC-F033": "SNCC.F033",
    "F.034": "SNCC.F034",
    "F034": "SNCC.F034",
    "034": "SNCC.F034",
    "SNCC.034": "SNCC.F034",
    "SNCC.F.034": "SNCC.F034",
    "SNCC_F034": "SNCC.F034",
    "SNCC-F034": "SNCC.F034",
    "F.042": "SNCC.F042",
    "F042": "SNCC.F042",
    "042": "SNCC.F042",
    "SNCC.042": "SNCC.F042",
    "SNCC.F.042": "SNCC.F042",
    "SNCC_F042": "SNCC.F042",
    "SNCC-F042": "SNCC.F042",
    "F.047": "SNCC.F047",
    "F047": "SNCC.F047",
    "047": "SNCC.F047",
    "SNCC.047": "SNCC.F047",
    "SNCC.F.047": "SNCC.F047",
    "SNCC_F047": "SNCC.F047",
}


def form_type_from_requirement_key(requirement_key: str) -> str | None:
    return SNCC_REQ_TO_FORM_TYPE.get((requirement_key or "").lower())


def normalize_form_type(form_type: str) -> str:
    """Normaliza alias cortos (F.033, SNCC F033, SNCC_F033) a SNCC.F033."""
    raw = (form_type or "").strip().upper()
    if not raw:
        return "SNCC.F042"
    compact = re.sub(r"[\s_]+", ".", raw)
    if compact in _FORM_TYPE_ALIASES:
        return _FORM_TYPE_ALIASES[compact]
    m = re.match(r"^SNCC\.?F?\.?0*(\d{2,3})$", compact)
    if m:
        return f"SNCC.F{int(m.group(1)):03d}"
    if compact.startswith("SNCC."):
        return compact
    if compact.startswith("F.") and compact[2:].isdigit():
        return f"SNCC.{compact}"
    if compact.startswith("F") and compact[1:].isdigit():
        return f"SNCC.F{int(compact[1:]):03d}"
    return compact
