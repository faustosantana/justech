"""Guardrails — protect motor, ranking, tables and evidence from mutation/invention."""

from __future__ import annotations

import re
from typing import Any


_FORBIDDEN_TOOL_PREFIXES = (
    "sql_",
    "admin_mutate_",
    " Ranking",
)

_INVENTION_PATTERNS = re.compile(
    r"(va a salir|saldr[aá] seguro|garantizado|apuesta\s+a|predicc[ií]on\s+segura|"
    r"probabilidad\s+garantizada|siempre\s+ocurre)",
    re.I,
)

_INTERNAL_CODES = re.compile(
    r"\b(FUERTE_T1_T2_MISMO_DIA|VECINO_T2_DIRECTO|primary_signal|"
    r"same_day_cross_support|exact_cases|confidence\s*=?\s*0\.\d+)\b",
    re.I,
)


class AnalystGuardrails:
    """Hard rails: Analista IA interprets only; never mutates motor outputs."""

    MOTOR_PROTECTED = True
    RANKING_PROTECTED = True
    TABLES_PROTECTED = True
    HISTORY_PROTECTED = True

    def allow_tool(self, tool_name: str) -> bool:
        name = (tool_name or "").strip()
        if not name.startswith("lottery_"):
            return False
        if any(name.startswith(p) for p in _FORBIDDEN_TOOL_PREFIXES):
            return False
        # Explicit deny of write/mutate sounding tools
        if re.search(r"(mutate|write|delete|drop|update_rank|override)", name, re.I):
            return False
        return True

    def sanitize_tool_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return a shallow copy without internal mutation hooks."""
        if not isinstance(data, dict):
            return {}
        out = dict(data)
        for key in list(out.keys()):
            if key in {"_mutable", "override_ranking", "force_primary", "rewrite_tables"}:
                out.pop(key, None)
        return out

    def sanitize_llm_text(self, text: str) -> str:
        raw = text or ""
        if _INVENTION_PATTERNS.search(raw):
            raw = _INVENTION_PATTERNS.sub("", raw)
            raw = (
                raw.strip()
                + "\n\nLimitaciones: el Analista IA no predice resultados futuros ni garantiza aciertos."
            )
        # Soften internal codes if any leaked
        raw = _INTERNAL_CODES.sub("relación del motor", raw)
        return raw.strip()

    def assert_ranking_unchanged(
        self,
        *,
        before_primary: int | None,
        after_primary: int | None,
    ) -> bool:
        if before_primary is None or after_primary is None:
            return True
        return int(before_primary) == int(after_primary)
