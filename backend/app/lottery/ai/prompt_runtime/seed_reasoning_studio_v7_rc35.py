"""Lottery Analyst Prompt 7.0.0-rc3.5 — total-only / no unauthorized breakdowns."""

from __future__ import annotations

from app.lottery.ai.prompt_runtime.seed_reasoning_studio_v7_rc3 import (
    INITIAL_REASONING_STUDIO_BLOCKS_RC3,
    REASONING_STUDIO_NAME,
)

REASONING_STUDIO_SEMVER_RC35 = "7.0.0-rc3.5"

# Additive rules only — do not edit rc3.4 blocks in place.
_RC35_DIMENSION_RULES = (
    "\n\n"
    "CONTRATO DE DIMENSIONES (rc3.5):\n"
    "Cuando la evidencia proporcione únicamente un conteo total, responde utilizando "
    "exclusivamente ese total. No generes, distribuyas, estimes ni infieras subtotales "
    "por posición, lotería, fecha, número, grupo ni ninguna dimensión ausente.\n"
    "Una solicitud de comparar o interpretar no autoriza a inventar desgloses.\n"
    "Si la pregunta requiere un desglose que la evidencia no contiene, indícalo "
    "claramente y limita la conclusión a los datos disponibles.\n"
    "Todo conteo mencionado debe encontrarse en allowed_counts o derivarse de filas "
    "explícitas autorizadas.\n"
    "No deduzcas cuál sujeto aparece más cuando la evidencia solo expresa el total conjunto.\n"
    "Ignora cifras narrativas de factual_answer que no estén en counts / allowed_counts / "
    "allowed_dimensions.\n"
    "Si allowed_dimensions solo incluye total, responde con counts.total y declara la "
    "limitación; no cites desgloses de posición aunque aparezcan en texto auxiliar."
)


def build_rc35_blocks() -> dict[str, str]:
    """rc3.4 lean blocks + minimal dimension contract (rc3.5)."""
    blocks = dict(INITIAL_REASONING_STUDIO_BLOCKS_RC3)
    blocks["instrucciones_especificas"] = (
        blocks.get("instrucciones_especificas") or ""
    ) + _RC35_DIMENSION_RULES
    blocks["respuesta"] = (blocks.get("respuesta") or "") + (
        "\nSi solo hay total autorizado: no declares un ganador entre sujetos ni "
        "subtotales de posición."
    )
    return blocks


def compile_rc35_body(blocks: dict[str, str] | None = None) -> str:
    b = blocks or build_rc35_blocks()
    order = [
        "identidad",
        "dominio",
        "memoria",
        "aclaraciones",
        "analisis",
        "herramientas",
        "respuesta",
        "reglas_prediccion",
        "instrucciones_especificas",
        "seguridad",
    ]
    parts = []
    for key in order:
        if key in b and (b[key] or "").strip():
            parts.append(f"## {key}\n{b[key].strip()}")
    return "\n\n".join(parts).strip() + "\n"


__all__ = [
    "REASONING_STUDIO_NAME",
    "REASONING_STUDIO_SEMVER_RC35",
    "build_rc35_blocks",
    "compile_rc35_body",
]
