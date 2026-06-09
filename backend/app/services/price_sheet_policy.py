"""Política de hojas comerciales vs auxiliares para listas de precios."""

from __future__ import annotations

import re

# Hojas que NUNCA deben indexarse como catálogo comercial
AUX_SHEET_PATTERNS = re.compile(
    r"(?i)(^loc\.?id$|alloc|openpurchaseorder|prueba|pivot|summary|totals?|config|metadata|notes?|sheet\d+$)",
)

# Hojas comerciales conocidas (prioridad alta)
COMMERCIAL_SHEET_NAMES = frozenset({
    "comercial",
    "consumo",
    "monitores",
    "accesorios",
    "warranties",
    "desktop local",
    "laptop local",
    "samsung local",
    "samsung fob miami",
    "lenovo fob miami",
})

PARSER_VERSION = "v2.3"


def is_non_laptop_commercial_sheet(sheet_name: str) -> bool:
    """Hojas indexables que nunca deben aparecer en búsqueda/comparación laptop."""
    name = sheet_name.strip().lower()
    patterns = (
        "warrant", "garant", "support", "service", "servicio",
        "accesor", "accessor", "parts", "cables", "licen", "software",
        "renewal", "loc.id", "alloc", "openpurchaseorder", "summary",
        "notes", "config", "totals", "pivot",
    )
    return any(p in name for p in patterns)


def is_auxiliary_sheet(sheet_name: str) -> bool:
    name = sheet_name.strip()
    if AUX_SHEET_PATTERNS.search(name):
        return True
    if name.lower() == "hoja1":
        return True
    return False


def is_commercial_sheet(sheet_name: str) -> bool:
    if is_auxiliary_sheet(sheet_name):
        return False
    return sheet_name.strip().lower() in COMMERCIAL_SHEET_NAMES


def sheet_skip_reason(sheet_name: str) -> str | None:
    if is_auxiliary_sheet(sheet_name):
        return "hoja_auxiliar"
    return None
