"""Pre-publish validation for Prompt Studio (architecture-aware)."""

from __future__ import annotations

import re
from typing import Any

from app.lottery.ai.prompt_runtime.compiler import PromptStudioCompiler
from app.lottery.ai.prompt_studio import PROMPT_STUDIO_BLOCKS, scan_secrets

# Claims that contradict certified architecture (Hermes / tools / Workspace)
_ARCH_FALSE_CLAIMS: list[tuple[str, re.Pattern[str]]] = [
    (
        "llm_executes_sql",
        re.compile(r"(?i)(ejecut\w+\s+sql|acceso\s+directo\s+a\s+(la\s+)?base|corr\w+\s+consultas\s+sql)"),
    ),
    (
        "llm_controls_hermes",
        re.compile(r"(?i)(t[uú]\s+controlas?\s+hermes|el\s+modelo\s+decide\s+routing|sustituy\w+\s+hermes)"),
    ),
    (
        "llm_runs_tools",
        re.compile(
            r"(?i)(t[uú]\s+ejecutas?\s+las?\s+herramientas|el\s+modelo\s+decide\s+qu[eé]\s+herramientas|"
            r"invocas?\s+tools?\s+directamente)"
        ),
    ),
    (
        "llm_owns_workspace",
        re.compile(r"(?i)(accedes?\s+directamente\s+al\s+workspace|modificas?\s+el\s+asset)"),
    ),
    (
        "ignore_evidence",
        re.compile(r"(?i)(ignora(r)?\s+el\s+evidence\s+package|no\s+uses?\s+la\s+evidencia)"),
    ),
    (
        "alter_math_motor",
        re.compile(r"(?i)(modifica(r)?\s+el\s+motor\s+matem|altera(r)?\s+tabla\s*[12]|recalcula\s+rankings)"),
    ),
    (
        "guaranteed_prediction",
        re.compile(
            r"(?i)((garantiza(r)?|asegura(r)?)\s+que\s+(mañana|hoy)\s+sale|"
            r"seguro\s+que\s+sale|"
            r"promete(r)?\s+ganancia)"
        ),
    ),
]


class PromptStudioValidator:
    @classmethod
    def validate(cls, blocks: dict[str, str] | None) -> dict[str, Any]:
        compiled = PromptStudioCompiler.compile(blocks)
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        for meta in PROMPT_STUDIO_BLOCKS:
            key = meta["key"]
            v = meta.get("validation") or {}
            text = (compiled["blocks"] or {}).get(key) or ""
            if v.get("required") and len(text.strip()) < int(v.get("min_chars") or 1):
                errors.append({"code": f"empty_{key}", "message": f"Bloque obligatorio vacío o corto: {key}"})
            if len(text) > int(v.get("max_chars") or 100_000):
                warnings.append({"code": f"long_{key}", "message": f"Bloque excede max_chars: {key}"})

        for hit in scan_secrets(compiled["body"]):
            errors.append({"code": f"secret_{hit.get('type')}", "message": hit.get("message") or "secreto"})

        if not compiled.get("within_limit"):
            errors.append({"code": "compiled_too_long", "message": "Compilado excede límite configurado"})

        for code, pat in _ARCH_FALSE_CLAIMS:
            if pat.search(compiled["body"]):
                errors.append(
                    {
                        "code": code,
                        "message": (
                            f"Afirmación incompatible con arquitectura certificada ({code}). "
                            "Hermes decide; herramientas producen evidencia; Huawei interpreta; "
                            "Workspace opera fuera del LLM."
                        ),
                    }
                )

        # Extreme duplication heuristic
        body = compiled["body"]
        if body and len(body) > 500:
            chunk = body[:200]
            if body.count(chunk) >= 3:
                warnings.append({"code": "extreme_duplication", "message": "Posible duplicación extrema en compilado"})

        ok = not errors
        return {
            "ok": ok,
            "errors": errors,
            "warnings": warnings,
            "compiled": compiled,
            "compiled_prompt_hash": compiled["compiled_prompt_hash"],
            "chars": compiled["chars"],
            "tokens_estimated": compiled["tokens_estimated"],
        }
