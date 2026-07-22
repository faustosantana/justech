"""Errores Microsoft Graph con contexto para UI."""

from __future__ import annotations

import json
import re


class GraphError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        error_code: str | None = None,
        permission_hint: str | None = None,
    ):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        self.permission_hint = permission_hint
        super().__init__(message)

    @classmethod
    def from_response(cls, status_code: int, body: str) -> GraphError:
        error_code = None
        message = body[:500]
        try:
            data = json.loads(body)
            err = data.get("error", {})
            error_code = err.get("code")
            message = err.get("message") or message
        except json.JSONDecodeError:
            pass
        hint = _permission_hint(status_code, error_code, message)
        return cls(status_code, message, error_code=error_code, permission_hint=hint)


def _permission_hint(status_code: int, code: str | None, message: str) -> str | None:
    if status_code == 401:
        return "Token expirado o inválido — reconecte la cuenta OAuth."
    if status_code == 403:
        scope = _extract_scope(message)
        if scope:
            return f"Falta permiso Graph: {scope}. Agregue en Azure y reconecte."
        return "Permiso insuficiente en Microsoft Graph — revise Admin Consent en Azure."
    if code == "InvalidAuthenticationToken":
        return "Token inválido — reconecte la cuenta."
    return None


def _extract_scope(message: str) -> str | None:
    m = re.search(r"scope[s]?\s+'([^']+)'", message, re.I)
    return m.group(1) if m else None
