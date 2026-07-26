"""Benchmark variants — current vs ablations vs profiles."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.scientific_validation.dataset import (
    MANUAL_BENCHMARK_CASES,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.historical_validator import (
    ENGINE_VARIANTS,
    evaluate_scenario,
    run_historical_validation,
)
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.catalog import build_catalog


BENCHMARK_VARIANTS = (
    "motor_actual",
    "sin_derivaciones",
    "sin_tabla2",
    "solo_tabla1",
    "perfil_socio",
    "perfil_experimental",
)


def run_benchmark(
    scenarios: list[dict[str, Any]],
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    cat = build_catalog()
    table = []
    details = {}
    for variant in BENCHMARK_VARIANTS:
        summary = run_historical_validation(
            scenarios, variant=variant, limit=limit, catalog=cat
        )
        details[variant] = {k: v for k, v in summary.items() if k != "rows"}
        details[variant]["rows"] = summary["rows"]
        table.append(
            {
                "variant": variant,
                "n": summary["n_analyses"],
                "methodology_match_rate": round(summary["methodology_match_rate"], 4),
                "exact_D+1": summary.get("exact_D+1", 0),
                "exact_D1_D3": summary.get("exact_D1_D3", 0),
                "exact_D1_D7": summary.get("exact_D1_D7", 0),
                "failures": summary["failures"],
            }
        )
    table.sort(key=lambda x: (-x["methodology_match_rate"], -x["exact_D1_D7"]))

    # Final manual benchmark (not used in blind training)
    manual_results = []
    for case in MANUAL_BENCHMARK_CASES:
        for variant in ("perfil_socio", "motor_actual", "sin_derivaciones"):
            r = run_complete_analysis(
                {
                    "numbers": case["numbers"],
                    "mode": ENGINE_VARIANTS[variant]["mode"],
                    "derivation_depth": ENGINE_VARIANTS[variant]["derivation_depth"],
                    "create_signals": False,
                    "include_table2": ENGINE_VARIANTS[variant]["include_table2"],
                },
                catalog=cat,
                persist=False,
                include_table2=ENGINE_VARIANTS[variant]["include_table2"],
            )
            produced = (r.primary_signal or {}).get("number")
            manual_results.append(
                {
                    "case": case["id"],
                    "variant": variant,
                    "expected": case["expected"],
                    "produced": produced,
                    "match": produced == case["expected"],
                    "classification": (r.primary_signal or {}).get("classification"),
                }
            )

    return {
        "blind_benchmark_table": table,
        "best_blind_variant": table[0]["variant"] if table else None,
        "manual_benchmark_final": manual_results,
        "details": details,
        "note": (
            "Casos manuales solo como benchmark final. "
            "Mejor variante ciega según match metodológico, no ML."
        ),
    }
