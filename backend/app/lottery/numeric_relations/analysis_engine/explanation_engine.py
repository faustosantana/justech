"""Deterministic explanation builder for Complete Analysis + J-11A fallback."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.schemas import (
    ExplanationLevel,
    RankedCandidate,
)


def explain_analysis(
    *,
    observed: list[int],
    ranked: list[RankedCandidate],
    level: str = ExplanationLevel.ANALYTICAL.value,
) -> dict[str, Any]:
    primary = next(
        (c for c in ranked if c.classification == "FUERTE_PRINCIPAL"),
        ranked[0] if ranked else None,
    )
    if primary is None:
        return {
            "level": level,
            "summary": "No se encontró un candidato con evidencia suficiente tras el análisis completo.",
            "disclaimer": "CONFIANZA ANALÍTICA / RESPALDO ESTRUCTURAL — no es probabilidad de ganar.",
        }

    obs_txt = " y ".join(str(n) for n in observed)
    executive = (
        f"El {primary.number} obtuvo el mayor respaldo estructural después de cruzar "
        f"todas las relaciones de {obs_txt}. No fue elegido antes de completar el análisis."
    )

    analytical = {
        "primary": primary.number,
        "classification": primary.classification,
        "analytical_confidence": primary.analytical_confidence,
        "table1_sources": primary.evidence.table1_sources,
        "table2_confirmers": primary.evidence.direct_confirmers,
        "independent_paths": primary.evidence.independent_path_count,
        "score": primary.total_score,
        "components": primary.components.to_dict(),
        "alternatives": [
            {
                "number": c.number,
                "classification": c.classification,
                "score": c.total_score,
            }
            for c in ranked
            if c.number != primary.number
        ],
        "reason": primary.classification_reason,
        "selection_timing": "after_full_analysis",
    }

    technical = {
        **analytical,
        "evidence": primary.evidence.to_dict(),
        "positive_evidence": primary.positive_evidence,
        "penalties": primary.penalties,
        "rank": primary.rank,
        "gap_to_next": primary.gap_to_next,
        "all_ranked": [c.to_dict() for c in ranked],
    }

    body: Any
    if level == ExplanationLevel.EXECUTIVE.value or level == "ejecutivo":
        body = executive
    elif level == ExplanationLevel.TECHNICAL.value or level == "tecnico":
        body = technical
    else:
        body = analytical

    return {
        "level": level,
        "summary": executive,
        "body": body,
        "disclaimer": (
            "Este número obtuvo el mayor respaldo estructural del análisis. "
            "No afirma que el número vaya a salir."
        ),
    }


def explain_why_strong(number: int, ranked: list[RankedCandidate], observed: list[int]) -> str:
    target = next((c for c in ranked if c.number == number), None)
    if target is None:
        return (
            "No encontré evidencia suficiente en el motor para afirmar esa relación "
            f"sobre el {number}."
        )
    obs = " y ".join(str(n) for n in observed)
    return (
        f"El {number} fue seleccionado después de analizar todas las relaciones de {obs}, "
        "comparar los destinos encontrados y verificar que obtuvo el mayor respaldo conjunto. "
        "No fue elegido antes de completar el análisis."
    )


def explain_relation_types_39_58_94(ranked: list[RankedCandidate]) -> dict[str, Any]:
    c = next((x for x in ranked if x.number == 94), None)
    if c is None:
        return {"ok": False, "message": "No hay candidato 94 en el ranking."}
    return {
        "ok": True,
        "candidate": 94,
        "table1_relation": {
            "from": c.evidence.table1_sources,
            "claim": "39 tiene relación de Tabla 1 con 94 (madre→compañero).",
        },
        "table2_relation": {
            "from": c.evidence.direct_confirmers,
            "claim": "58 confirma 94 vía Tabla 2 (vecino/grupo T2).",
        },
        "forbidden_claim": "No se afirma que 58 y 94 sean compañeros de Tabla 1.",
        "table1_companions_of_58": "consultar get_table1_family(58) — 94 no debe listarse como compañero T1 de 58",
    }
