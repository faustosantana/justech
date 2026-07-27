"""Deterministic explanation builder for Complete Analysis + J-11A fallback."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.same_day_context import (
    SameDayCrossConfirmation,
    explain_same_day_cross,
)
from app.lottery.numeric_relations.analysis_engine.schemas import (
    ExplanationLevel,
    RankedCandidate,
)


def explain_analysis(
    *,
    observed: list[int],
    ranked: list[RankedCandidate],
    level: str = ExplanationLevel.ANALYTICAL.value,
    same_day_cross: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    primary = next(
        (
            c
            for c in ranked
            if c.classification in {"FUERTE_PRINCIPAL", "FUERTE_T1_T2_MISMO_DIA"}
        ),
        ranked[0] if ranked else None,
    )
    if primary is None:
        return {
            "level": level,
            "summary": "No se encontró un candidato con evidencia suficiente tras el análisis completo.",
            "disclaimer": "CONFIANZA ANALÍTICA / RESPALDO ESTRUCTURAL — no es probabilidad de ganar.",
        }

    crosses = list(same_day_cross or [])
    primary_cross = next(
        (c for c in crosses if int(c.get("companion_c") or 0) == primary.number),
        crosses[0] if crosses else None,
    )

    if primary_cross:
        try:
            ev = SameDayCrossConfirmation(**{
                k: primary_cross[k]
                for k in SameDayCrossConfirmation.__dataclass_fields__
                if k in primary_cross
            })
            executive = explain_same_day_cross(ev)
        except Exception:
            executive = (
                f"El {primary_cross.get('observed_x')} relaciona al {primary.number} mediante Tabla 1. "
                f"El {primary_cross.get('confirmer_y')} confirma al {primary.number} mediante Tabla 2 "
                f"el mismo día. El {primary.number} queda fortalecido."
            )
        relation_direct = (
            f"El {primary_cross.get('observed_x')} comparte Tabla 1 con {primary.number}."
        )
        confirmation_external = (
            f"El {primary_cross.get('confirmer_y')} apareció en otra lotería ese mismo día "
            f"y confirma al {primary.number} en Tabla 2."
        )
        conclusion = (
            f"El {primary.number} recibe respaldo independiente de ambas tablas."
        )
    else:
        obs_txt = " y ".join(str(n) for n in observed)
        t1 = primary.evidence.table1_sources
        t2 = primary.evidence.direct_confirmers
        if t1 and t2:
            relation_direct = (
                f"El {t1[0]} relaciona al {primary.number} mediante Tabla 1."
            )
            confirmation_external = (
                f"El {t2[0]} confirma al {primary.number} mediante Tabla 2."
            )
            conclusion = (
                f"El {primary.number} recibe respaldo independiente de ambas tablas."
            )
            executive = f"{relation_direct} {confirmation_external} {conclusion}"
        else:
            executive = (
                f"El {primary.number} obtuvo el mayor respaldo estructural después de cruzar "
                f"todas las relaciones de {obs_txt}. No fue elegido antes de completar el análisis."
            )
            relation_direct = executive
            confirmation_external = ""
            conclusion = executive

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
        "relation_direct": relation_direct,
        "confirmation_external": confirmation_external,
        "conclusion": conclusion,
        "same_day_cross": crosses,
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
        "relation_direct": relation_direct,
        "confirmation_external": confirmation_external,
        "conclusion": conclusion,
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
