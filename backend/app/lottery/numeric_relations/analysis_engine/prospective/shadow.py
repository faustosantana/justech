"""Shadow profile comparison — never mutates the operational locked signal."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.tiebreak_engine import apply_hypothesis


SHADOW_PROFILES = (
    "baseline_no_tiebreak",
    "TIEBREAK_SOURCE_ORDER",
    "no_derivations",
    "experimental",
)


def run_shadow_profiles(
    *,
    numbers: list[int],
    date: str | None,
    positions: list[str] | None = None,
) -> dict[str, Any]:
    """Run comparison profiles on the same inputs. Does not lock or replace operational."""
    base_req = {
        "numbers": numbers,
        "date": date,
        "positions": positions or ["first"],
        "create_signals": False,
        "mode": "socio",
    }
    out: dict[str, Any] = {}

    # baseline without tiebreak
    r0 = run_complete_analysis(
        {**base_req, "derivation_depth": 0, "enable_tiebreak": False},
        persist=False,
        enable_tiebreak=False,
    )
    out["baseline_no_tiebreak"] = _summary(r0)

    # source order
    r1 = run_complete_analysis(
        {**base_req, "derivation_depth": 0, "enable_tiebreak": False},
        persist=False,
        enable_tiebreak=False,
    )
    ordered, _ = apply_hypothesis(
        list(r1.ranked_candidates),
        hypothesis="TIEBREAK_SOURCE_ORDER",
        observed_numbers=list(numbers),
        allow_multi_fuerte=False,
    )
    out["TIEBREAK_SOURCE_ORDER"] = {
        "primary": ordered[0]["number"] if ordered else None,
        "top": [c["number"] for c in ordered[:3]],
        "classifications": [c.get("classification") for c in ordered[:3]],
    }

    # no derivations (same as depth 0 operational graph without experimental extras)
    out["no_derivations"] = out["baseline_no_tiebreak"]

    # experimental mode
    r2 = run_complete_analysis(
        {**base_req, "mode": "experimental", "derivation_depth": 0, "enable_tiebreak": True},
        persist=False,
        enable_tiebreak=True,
    )
    out["experimental"] = _summary(r2)
    out["note"] = "Shadow profiles do not modify the operational locked prediction."
    return out


def _summary(result: Any) -> dict[str, Any]:
    multi = (result.tiebreak or {}).get("multi_fuerte_numbers") or []
    return {
        "primary": (result.primary_signal or {}).get("number"),
        "classification": (result.primary_signal or {}).get("classification"),
        "multi": multi,
        "top": [c["number"] for c in result.ranked_candidates[:3]],
    }
