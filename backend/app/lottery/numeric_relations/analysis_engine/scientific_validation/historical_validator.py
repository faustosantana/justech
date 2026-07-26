"""Historical validation runner — thousands of analyses, results persisted."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog


ENGINE_VARIANTS: dict[str, dict[str, Any]] = {
    "motor_actual": {
        "mode": "socio",
        "derivation_depth": 2,
        "include_table2": True,
    },
    "sin_derivaciones": {
        "mode": "socio",
        "derivation_depth": 0,
        "include_table2": True,
    },
    "sin_tabla2": {
        "mode": "socio",
        "derivation_depth": 0,
        "include_table2": False,
    },
    "solo_tabla1": {
        "mode": "amplio",
        "derivation_depth": 0,
        "include_table2": False,
    },
    "perfil_socio": {
        "mode": "socio",
        "derivation_depth": 0,
        "include_table2": True,
    },
    "perfil_experimental": {
        "mode": "experimental",
        "derivation_depth": 2,
        "include_table2": True,
    },
    "perfil_conservador": {
        "mode": "conservador",
        "derivation_depth": 0,
        "include_table2": True,
    },
    "perfil_balanceado": {
        "mode": "balanceado",
        "derivation_depth": 0,
        "include_table2": True,
    },
    "perfil_agresivo": {
        "mode": "agresivo",
        "derivation_depth": 2,
        "include_table2": True,
    },
}


def _d_hits(first_day_offset: int | None) -> dict[str, int]:
    out = {f"D+{i}": 0 for i in range(1, 8)}
    if first_day_offset is not None and 1 <= int(first_day_offset) <= 7:
        out[f"D+{int(first_day_offset)}"] = 1
    return out


def evaluate_scenario(
    scenario: dict[str, Any],
    *,
    variant: str = "perfil_socio",
    catalog: TableCatalog | None = None,
) -> dict[str, Any]:
    cfg = ENGINE_VARIANTS.get(variant) or ENGINE_VARIANTS["perfil_socio"]
    result = run_complete_analysis(
        {
            "numbers": scenario["observed_numbers"],
            "date": scenario["case_date"],
            "mode": cfg["mode"],
            "derivation_depth": cfg["derivation_depth"],
            "positions": ["first"],
            "lotteries": [
                x
                for x in [scenario.get("origin_lottery"), scenario.get("confirmer_lottery")]
                if x
            ],
            "create_signals": False,
            "include_table2": cfg["include_table2"],
        },
        catalog=catalog,
        persist=False,
        include_table2=cfg["include_table2"],
    )
    primary = result.primary_signal or {}
    produced = primary.get("number")
    hist = int(scenario["historical_fuerte"])
    methodology_match = produced == hist
    day_hits = _d_hits(scenario.get("first_day_offset"))
    # Predictive exact only if historical fuerte appeared AND motor matched methodology
    # Also report whether PRODUCED number's historical row appeared (for matched cases)
    exact_window = {
        f"exact_{k}": (1 if methodology_match and v else 0) for k, v in day_hits.items()
    }
    # Broader: historical fuerte appearance independent of match
    hist_appear = {
        f"hist_fuerte_{k}": v for k, v in day_hits.items()
    }

    ranked_compact = [
        {
            "number": c["number"],
            "classification": c["classification"],
            "score": c["total_score"],
            "analytical_confidence": c["analytical_confidence"],
            "table1_sources": c["evidence"]["table1_sources"],
            "table2_confirmers": c["evidence"]["direct_confirmers"],
            "reason": c.get("classification_reason"),
        }
        for c in result.ranked_candidates[:8]
    ]

    return {
        "scenario_id": scenario["scenario_id"],
        "split": scenario.get("split"),
        "variant": variant,
        "date": scenario["case_date"],
        "year": scenario.get("year"),
        "origin_lottery": scenario.get("origin_lottery"),
        "confirmer_lottery": scenario.get("confirmer_lottery"),
        "origin_position": scenario.get("origin_position"),
        "confirmer_position": scenario.get("confirmer_position"),
        "observed_numbers": scenario["observed_numbers"],
        "historical_fuerte": hist,
        "produced_fuerte": produced,
        "produced_classification": primary.get("classification"),
        "methodology_match": methodology_match,
        "alternatives": result.alternatives,
        "ranked": ranked_compact,
        "evidence_summary": result.evidence_summary,
        "graph_node_count": (result.graph or {}).get("node_count"),
        "graph_edge_count": (result.graph or {}).get("edge_count"),
        "graph_complete_before_discovery": result.graph_complete_before_discovery,
        "stages": result.stages_completed,
        "fuerte_appeared_historically": scenario.get("fuerte_appeared"),
        "first_day_offset": scenario.get("first_day_offset"),
        "first_lottery": scenario.get("first_lottery"),
        "first_draw_position": scenario.get("first_draw_position"),
        **exact_window,
        **hist_appear,
        "failure": (not methodology_match),
    }


def run_historical_validation(
    scenarios: list[dict[str, Any]],
    *,
    variant: str = "perfil_socio",
    limit: int | None = None,
    catalog: TableCatalog | None = None,
) -> dict[str, Any]:
    cat = catalog or build_catalog()
    use = scenarios if limit is None else scenarios[:limit]
    rows: list[dict[str, Any]] = []
    for sc in use:
        rows.append(evaluate_scenario(sc, variant=variant, catalog=cat))

    n = len(rows) or 1
    matches = sum(1 for r in rows if r["methodology_match"])
    exact_d = {f"exact_D+{i}": sum(r.get(f"exact_D+{i}", 0) for r in rows) for i in range(1, 8)}
    hist_d = {
        f"hist_fuerte_D+{i}": sum(r.get(f"hist_fuerte_D+{i}", 0) for r in rows)
        for i in range(1, 8)
    }
    by_lottery: dict[str, dict[str, int]] = {}
    for r in rows:
        lot = r.get("origin_lottery") or "unknown"
        bucket = by_lottery.setdefault(lot, {"n": 0, "match": 0})
        bucket["n"] += 1
        bucket["match"] += int(r["methodology_match"])

    return {
        "variant": variant,
        "n_analyses": len(rows),
        "methodology_match_rate": matches / n,
        "methodology_matches": matches,
        "failures": len(rows) - matches,
        **exact_d,
        "exact_D1_D3": sum(exact_d[f"exact_D+{i}"] for i in (1, 2, 3)),
        "exact_D1_D7": sum(exact_d.values()),
        **hist_d,
        "by_lottery": by_lottery,
        "rows": rows,
        "limitations": [
            "exact_D+n cuenta acierto predictivo solo cuando el motor coincidió con el fuerte histórico.",
            "El dataset proviene de activaciones oficiales T1×T2; no es muestreo aleatorio de todos los días.",
            "No afirma ventaja predictiva sobre azar sin baseline explícito.",
        ],
    }
