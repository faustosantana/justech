"""Explainability helpers — why 1st / 2nd / discarded (deterministic)."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.schemas import RankedCandidate


def explain_ranking_decisions(ranked: list[dict[str, Any]] | list[RankedCandidate]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in ranked:
        if isinstance(item, RankedCandidate):
            rows.append(item.to_dict())
        else:
            rows.append(item)
    if not rows:
        return {
            "first": None,
            "second": None,
            "discarded": [],
            "summary": "Sin candidatos tras el análisis completo.",
        }

    first = rows[0]
    second = rows[1] if len(rows) > 1 else None
    discarded = rows[2:8]

    def _pack(c: dict[str, Any], role: str) -> dict[str, Any]:
        ev = c.get("evidence") or {}
        return {
            "role": role,
            "number": c.get("number"),
            "classification": c.get("classification"),
            "score": c.get("total_score") or c.get("score"),
            "why": c.get("classification_reason") or c.get("reason"),
            "evidence_had": {
                "table1_sources": ev.get("table1_sources") or c.get("table1_sources"),
                "table2_confirmers": ev.get("direct_confirmers") or c.get("table2_confirmers"),
                "independent_paths": ev.get("independent_path_count"),
                "cross_table_support": ev.get("cross_table_support"),
            },
            "evidence_lacked": _lacked(c),
            "components": c.get("components"),
            "penalties": c.get("penalties") or [],
        }

    def _lacked(c: dict[str, Any]) -> list[str]:
        ev = c.get("evidence") or {}
        lacked = []
        t1 = ev.get("table1_sources") or c.get("table1_sources") or []
        t2 = ev.get("direct_confirmers") or c.get("table2_confirmers") or []
        if not t1:
            lacked.append("sin_fuente_tabla1")
        if not t2:
            lacked.append("sin_confirmacion_tabla2")
        if not (ev.get("cross_table_support") or (t1 and t2)):
            lacked.append("sin_cruce_t1_t2")
        return lacked

    return {
        "first": _pack(first, "primero"),
        "second": _pack(second, "segundo") if second else None,
        "discarded": [_pack(c, "descartado_relativo") for c in discarded],
        "summary": (
            f"Primero {first.get('number')} por mayor respaldo estructural "
            f"({first.get('classification')}). "
            + (
                f"Segundo {second.get('number')}."
                if second
                else "Sin segunda opción."
            )
        ),
    }


def explain_analysis_decisions(
    numbers: list[int],
    *,
    mode: str = "socio",
    date: str | None = None,
) -> dict[str, Any]:
    result = run_complete_analysis(
        {
            "numbers": numbers,
            "date": date,
            "mode": mode,
            "derivation_depth": 0,
            "create_signals": False,
        },
        persist=False,
    )
    decisions = explain_ranking_decisions(result.ranked_candidates)
    return {
        "observed_numbers": result.observed_numbers,
        "primary_signal": result.primary_signal,
        "decisions": decisions,
        "evidence_summary": result.evidence_summary,
        "graph_complete_before_discovery": result.graph_complete_before_discovery,
    }
