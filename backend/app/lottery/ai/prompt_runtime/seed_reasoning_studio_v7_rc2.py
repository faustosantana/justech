"""Build Lottery Analyst Prompt 7.0.0-rc2 from Prompt Studio UI blocks + architecture fixes."""

from __future__ import annotations

import json
from pathlib import Path

REASONING_STUDIO_NAME = "LOTTERY_ANALYST_REASONING_STUDIO"
REASONING_STUDIO_SEMVER = "7.0.0-rc2"

# Prefer packaged blocks (Docker-safe); fall back to evidence UI export for local rebuilds.
_PACKAGED_BLOCKS_PATH = Path(__file__).resolve().parent / "data" / "reasoning_studio_7_0_0_rc2_blocks.json"
_UI_BLOCKS_PATH = (
    Path(__file__).resolve().parents[5]
    / "evidence/prompt_runtime/7.0.0-rc1/PROMPT_STUDIO_UI_DRAFT_BLOCKS.json"
)

# Documented in docs/prompt_runtime/PROMPT_CONTENT_COMPATIBILITY_REVIEW.md
_COMPAT_REPLACEMENTS: list[tuple[str, str, str, str]] = [
    (
        "herramientas",
        "Siempre utiliza las herramientas en este orden.",
        "Hermes y el backend utilizan las capacidades en este orden (tú no las invocas):",
        "El modelo no ejecuta herramientas; Hermes/backend producen la evidencia.",
    ),
    (
        "herramientas",
        "Si existe un Workspace activo debes utilizarlo antes de iniciar cualquier nueva investigación.",
        "Si existe un Workspace activo, Hermes/backend lo reutilizan antes de una nueva investigación; "
        "tú no operas el Workspace — solo interpretas el Evidence Package que recibes.",
        "Workspace opera fuera del LLM.",
    ),
    (
        "herramientas",
        "No vuelvas a consultar datos que ya existen dentro del Workspace.",
        "No pidas ni inventes una nueva consulta cuando la evidencia ya está en el Evidence Package "
        "(el Workspace/backend ya reutilizan el asset).",
        "El modelo no consulta Workspace/SQL.",
    ),
    (
        "herramientas",
        "Si existe un asset válido debes reutilizarlo.\n\nNo reconstruir la información.\n\nNo volver a ejecutar SQL.\n\nNo volver a preguntar.",
        "Si el Evidence Package ya refleja un asset válido, interprétalo sin reconstruir ni alterar hechos.\n\n"
        "No solicites repetir consultas a la base de datos.\n\n"
        "No reinventes la pregunta cuando la evidencia ya responde.",
        "SQL lo ejecuta el backend; el modelo interpreta.",
    ),
    (
        "respuesta",
        "Cuando el usuario solicite una operación sobre resultados existentes debes ejecutar únicamente esa operación.",
        "Cuando el usuario solicite una operación sobre resultados existentes "
        "(mostrar, filtrar, ordenar, exportar), esa operación ocurre en Workspace fuera del LLM; "
        "tú no la ejecutas — si te llega evidencia, interpreta solo lo necesario sin repetir la tabla completa.",
        "Mostrar/filtrar/ordenar/exportar están fuera del LLM.",
    ),
    (
        "memoria",
        "No describas la tabla.\n\nUtilízala.",
        "No narres la tabla completa si Workspace ya la muestra al usuario.\n\n"
        "Interpreta solo la evidencia del Evidence Package de este turno.",
        "Workspace muestra tablas; el modelo no las opera.",
    ),
]

_ARCHITECTURE_ADDENDUM = (
    "\n\n======================================================================\n"
    "CONTRATO DE RUNTIME — ANALYST REASONING (OBLIGATORIO)\n"
    "======================================================================\n"
    "Hermes decide routing y herramientas.\n"
    "El backend produce el Evidence Package (consultas y tools ya ocurrieron).\n"
    "Huawei / el modelo solo interpreta la evidencia recibida.\n"
    "El modelo no lanza consultas SQL, no opera Workspace y no decide routing.\n"
    "Mostrar, filtrar, ordenar y exportar ocurren fuera del LLM.\n"
)


def load_ui_blocks() -> dict[str, str]:
    if _PACKAGED_BLOCKS_PATH.is_file():
        raw = json.loads(_PACKAGED_BLOCKS_PATH.read_text(encoding="utf-8"))
        return {str(k): str(v or "") for k, v in raw.items()}
    raw = json.loads(_UI_BLOCKS_PATH.read_text(encoding="utf-8"))
    return {str(k): str(v or "") for k, v in raw.items()}


def apply_compatibility(blocks: dict[str, str]) -> tuple[dict[str, str], list[dict[str, str]]]:
    # Packaged blocks are already compatibility-patched; skip re-application when marked.
    if _PACKAGED_BLOCKS_PATH.is_file() and "CONTRATO DE RUNTIME — ANALYST REASONING" in (
        (blocks.get("instrucciones_especificas") or "")
    ):
        return dict(blocks), [{"key": "*", "status": "packaged_rc2", "reason": "already_patched"}]
    out = dict(blocks)
    applied: list[dict[str, str]] = []
    for key, original, corrected, reason in _COMPAT_REPLACEMENTS:
        text = out.get(key) or ""
        if original not in text:
            applied.append(
                {
                    "key": key,
                    "status": "missing_original",
                    "original": original,
                    "corrected": corrected,
                    "reason": reason,
                }
            )
            continue
        out[key] = text.replace(original, corrected, 1)
        applied.append(
            {
                "key": key,
                "status": "applied",
                "original": original,
                "corrected": corrected,
                "reason": reason,
            }
        )
    # Addendum once on instrucciones_especificas
    spec = out.get("instrucciones_especificas") or ""
    if "CONTRATO DE RUNTIME — ANALYST REASONING" not in spec:
        out["instrucciones_especificas"] = spec.rstrip() + _ARCHITECTURE_ADDENDUM
        applied.append(
            {
                "key": "instrucciones_especificas",
                "status": "applied",
                "original": "(fin de bloque)",
                "corrected": _ARCHITECTURE_ADDENDUM.strip()[:200] + "…",
                "reason": "Anclar contrato Hermes/backend/Evidence Package / no SQL / no Workspace.",
            }
        )
    return out, applied


def build_rc2_blocks() -> dict[str, str]:
    blocks, _ = apply_compatibility(load_ui_blocks())
    return blocks


# Eager constant for tests / seed (loaded at import)
try:
    INITIAL_REASONING_STUDIO_BLOCKS_RC2: dict[str, str] = build_rc2_blocks()
except FileNotFoundError:
    INITIAL_REASONING_STUDIO_BLOCKS_RC2 = {}
