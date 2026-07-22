"""Mapeo legacy checklist ↔ 8 estados aprobados (Fase 1)."""

from __future__ import annotations

APPROVED_STATUSES = frozenset({
    "pending",
    "detected",
    "associated",
    "needs_review",
    "valid",
    "expired",
    "not_applicable",
    "completed",
})

_LEGACY_TO_APPROVED: dict[str, str] = {
    "faltante": "pending",
    "pendiente": "pending",
    "detectado": "detected",
    "encontrado": "detected",
    "encontrado_sin_analizar": "detected",
    "encontrado_vigente": "associated",
    "vinculado": "associated",
    "pdf_final_generado": "associated",
    "adjuntado": "associated",
    "finalizado": "associated",
    "disponible": "associated",
    "requiere_revision": "needs_review",
    "requiere_completado": "needs_review",
    "borrador_pendiente": "needs_review",
    "plantilla_disponible": "needs_review",
    "completar": "needs_review",
    "incompleto": "needs_review",
    "encontrado_sin_fecha": "needs_review",
    "requiere_actualizacion": "needs_review",
    "validado": "valid",
    "completo": "valid",
    "listo_firma": "valid",
    "validado_manual": "valid",
    "vencido": "expired",
    "encontrado_vencido": "expired",
    "no_aplica": "not_applicable",
    "excluido": "not_applicable",
    "completado": "completed",
    "cerrado": "completed",
    "rejected": "needs_review",
    "rechazado": "needs_review",
}

_APPROVED_TO_LEGACY: dict[str, str] = {
    "pending": "pendiente",
    "detected": "encontrado_sin_analizar",
    "associated": "encontrado_vigente",
    "needs_review": "requiere_revision",
    "valid": "validado_manual",
    "expired": "vencido",
    "not_applicable": "no_aplica",
    "completed": "completado",
}


def legacy_status_to_approved(raw: str | None) -> str:
    if not raw:
        return "pending"
    normalized = raw.strip().lower()
    if normalized in APPROVED_STATUSES:
        return normalized
    return _LEGACY_TO_APPROVED.get(normalized, "pending")


def approved_status_to_legacy(status: str | None) -> str:
    if not status:
        return "pendiente"
    normalized = status.strip().lower()
    if normalized in _APPROVED_TO_LEGACY:
        return _APPROVED_TO_LEGACY[normalized]
    if normalized in _LEGACY_TO_APPROVED:
        return normalized
    return "pendiente"


def legacy_checklist_item_status(item: dict) -> str:
    manual = item.get("manual_validation") or {}
    if manual.get("status"):
        return str(manual["status"])
    if item.get("no_aplica"):
        return "no_aplica"
    return str(item.get("status") or "pendiente")
