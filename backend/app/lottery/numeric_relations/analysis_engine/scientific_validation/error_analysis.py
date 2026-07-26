"""Error analysis — document failures, do not auto-correct."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def analyze_errors(validation_rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [r for r in validation_rows if r.get("failure")]
    cases: list[dict[str, Any]] = []
    pattern_counter: Counter[str] = Counter()

    for r in failures:
        produced = r.get("produced_fuerte")
        hist = r.get("historical_fuerte")
        ranked = r.get("ranked") or []
        hist_rank = next((i for i, c in enumerate(ranked, 1) if c["number"] == hist), None)
        produced_row = next((c for c in ranked if c["number"] == produced), None)
        hist_row = next((c for c in ranked if c["number"] == hist), None)

        missing = []
        if hist_row is None:
            missing.append("fuerte_historico_ausente_del_ranking")
            pattern = "HIST_FUERTE_NOT_IN_RANKING"
        elif hist_rank and hist_rank > 1:
            missing.append("fuerte_historico_no_fue_primero")
            pattern = "HIST_FUERTE_RANKED_BELOW_PRIMARY"
        else:
            pattern = "OTHER_MISMATCH"

        if produced_row and produced_row.get("classification") == "VECINO_T2_DIRECTO":
            pattern_counter["PRIMARY_WAS_DIRECT_T2"] += 1
        if (r.get("alternatives") or []) and hist in {
            a.get("number") for a in (r.get("alternatives") or [])
        }:
            pattern_counter["HIST_IN_ALTERNATIVES"] += 1
            pattern = "HIST_FUERTE_IN_ALTERNATIVES"

        pattern_counter[pattern] += 1

        why_chosen = None
        if produced_row:
            why_chosen = {
                "classification": produced_row.get("classification"),
                "score": produced_row.get("score"),
                "reason": produced_row.get("reason"),
                "table1_sources": produced_row.get("table1_sources"),
                "table2_confirmers": produced_row.get("table2_confirmers"),
            }

        cases.append(
            {
                "scenario_id": r.get("scenario_id"),
                "date": r.get("date"),
                "observed_numbers": r.get("observed_numbers"),
                "chosen": produced,
                "historical_outcome_fuerte": hist,
                "why_motor_chose": why_chosen,
                "hist_rank_in_motor": hist_rank,
                "missing_evidence_flags": missing,
                "ignored_routes_note": (
                    "Si el fuerte histórico no está en ranking, las rutas T1×T2 "
                    "hacia ese destino no fueron descubiertas con las entradas observadas."
                ),
                "error_pattern": pattern,
                "lotteries": [r.get("origin_lottery"), r.get("confirmer_lottery")],
            }
        )

    by_year: dict[str, int] = defaultdict(int)
    for c in cases:
        by_year[str(c.get("date", "")[:4])] += 1

    return {
        "n_failures": len(failures),
        "n_analyzed": len(validation_rows),
        "failure_rate": (len(failures) / len(validation_rows)) if validation_rows else 0.0,
        "repetitive_patterns": dict(pattern_counter.most_common()),
        "failures_by_year": dict(by_year),
        "sample_cases": cases[:100],
        "all_case_ids": [c["scenario_id"] for c in cases],
        "note": (
            "Solo documentación. No se aplican correcciones automáticas al motor."
        ),
    }
