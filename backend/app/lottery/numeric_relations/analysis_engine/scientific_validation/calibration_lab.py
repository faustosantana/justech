"""Calibration lab — compare deterministic weight profiles (no ML decisions)."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.scientific_validation.historical_validator import (
    run_historical_validation,
)


CALIBRATION_PROFILES = (
    "perfil_conservador",
    "perfil_balanceado",
    "perfil_agresivo",
    "perfil_socio",
    "perfil_experimental",
)


def run_calibration_lab(
    scenarios: list[dict[str, Any]],
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    results = {}
    for profile in CALIBRATION_PROFILES:
        summary = run_historical_validation(scenarios, variant=profile, limit=limit)
        # drop heavy rows from comparison table
        results[profile] = {
            "n_analyses": summary["n_analyses"],
            "methodology_match_rate": summary["methodology_match_rate"],
            "methodology_matches": summary["methodology_matches"],
            "failures": summary["failures"],
            "exact_D+1": summary.get("exact_D+1", 0),
            "exact_D+3": summary.get("exact_D+3", 0),
            "exact_D1_D3": summary.get("exact_D1_D3", 0),
            "exact_D1_D7": summary.get("exact_D1_D7", 0),
            "rows": summary["rows"],
        }

    ranked = sorted(
        (
            {
                "profile": k,
                "methodology_match_rate": v["methodology_match_rate"],
                "exact_D1_D7": v["exact_D1_D7"],
                "exact_D1_D3": v["exact_D1_D3"],
                "failures": v["failures"],
            }
            for k, v in results.items()
        ),
        key=lambda x: (-x["methodology_match_rate"], -x["exact_D1_D7"], x["failures"]),
    )
    best = ranked[0]["profile"] if ranked else None
    return {
        "profiles_compared": list(CALIBRATION_PROFILES),
        "ranking": ranked,
        "best_methodology_reproduction": best,
        "recommendation": (
            f"El perfil '{best}' reproduce mejor el fuerte histórico oficial T1×T2 "
            "en este dataset ciego (match metodológico). "
            "Esto no implica ventaja predictiva sobre azar."
            if best
            else "Sin datos."
        ),
        "details": {k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in results.items()},
        "full": results,
        "ml_used_for_decision": False,
    }
