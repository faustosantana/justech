"""Clasificación de documentos del proceso DGCP (Fase 7.3)."""

from __future__ import annotations

ROLE_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("pliego", ("pliego", "condiciones", "bases"), "alta"),
    ("tdr", ("tdr", "terminos de referencia", "términos de referencia", "tor"), "alta"),
    ("ficha_tecnica", ("ficha tecnica", "ficha técnica", "especificacion", "especificación"), "alta"),
    ("especificaciones", ("especificaciones tecnicas", "especificaciones técnicas"), "alta"),
    ("invitacion", ("invitacion", "invitación"), "alta"),
    ("anexo_tecnico", ("anexo tecnico", "anexo técnico"), "alta"),
    ("formulario", ("formulario", "sncc", "modelo"), "media"),
    ("cronograma", ("cronograma", "calendario"), "media"),
    ("contrato", ("modelo de contrato", "contrato tipo"), "media"),
    ("enmienda", ("enmienda", "modificacion", "modificación"), "media"),
    ("circular", ("circular",), "media"),
    ("imagen", (".png", ".jpg", ".jpeg", ".gif"), "baja"),
)


def classify_process_document(title: str, *, source_url: str | None = None) -> tuple[str, str]:
    blob = f"{title} {source_url or ''}".lower()
    for role, patterns, priority in ROLE_RULES:
        if any(p in blob for p in patterns):
            return role, priority
    if any(ext in blob for ext in (".png", ".jpg", ".jpeg")):
        return "imagen", "baja"
    return "general", "media"
