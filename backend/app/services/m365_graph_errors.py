"""Mapeo de errores Graph a respuestas API."""

from __future__ import annotations

from integrations.microsoft365.errors import GraphError


def graph_error_message(exc: GraphError) -> str:
    if exc.permission_hint:
        return f"{exc.message} — {exc.permission_hint}"
    return exc.message
