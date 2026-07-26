"""Pilot metrics aggregation — keep exact / multi / top2 / top3 / family separate."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Any


def compute_pilot_metrics(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    locked = [p for p in predictions if p.get("status") in {"LOCKED", "AWAITING_RESULTS", "EVALUATED"}]
    evaluated = [p for p in predictions if p.get("status") == "EVALUATED"]
    expired = [p for p in predictions if p.get("status") == "EXPIRED"]
    integrity_errors = [
        p
        for p in predictions
        if (p.get("evaluation") or {}).get("hit_class") == "INTEGRITY_ERROR"
        or p.get("integrity_ok") is False
    ]

    def _rate(pred_list: list[dict[str, Any]], key: str, dn: int | None = None) -> float | None:
        if not pred_list:
            return None
        hits = 0
        for p in pred_list:
            ev = p.get("evaluation") or {}
            if dn is not None and ev.get("relative_day") != dn:
                # also accept if appearance recorded under D+n
                dmap = ev.get("d_plus") or {}
                bucket = dmap.get(f"D+{dn}") or []
                if not bucket:
                    continue
                if key == "hit_primary_exact" and ev.get("hit_primary_exact"):
                    hits += 1
                elif key == "hit_multi_fuerte" and ev.get("hit_multi_fuerte"):
                    hits += 1
                elif key == "hit_top2_exact" and ev.get("hit_top2_exact"):
                    hits += 1
                elif key == "hit_top3_exact" and ev.get("hit_top3_exact"):
                    hits += 1
                continue
            if ev.get(key):
                hits += 1
        return hits / len(pred_list)

    def _exact_at(dn: int, kind: str) -> int:
        n = 0
        for p in evaluated:
            ev = p.get("evaluation") or {}
            if ev.get("relative_day") != dn:
                continue
            if kind == "primary" and ev.get("hit_primary_exact"):
                n += 1
            elif kind == "multi" and ev.get("hit_multi_fuerte"):
                n += 1
            elif kind == "top2" and ev.get("hit_top2_exact"):
                n += 1
            elif kind == "top3" and ev.get("hit_top3_exact"):
                n += 1
        return n

    days_to_exact = [
        (p.get("evaluation") or {}).get("relative_day")
        for p in evaluated
        if (p.get("evaluation") or {}).get("is_exact_hit")
        and (p.get("evaluation") or {}).get("relative_day") is not None
    ]

    by_lottery: dict[str, int] = defaultdict(int)
    by_position: dict[str, int] = defaultdict(int)
    by_week: dict[str, int] = defaultdict(int)
    by_engine: dict[str, int] = defaultdict(int)
    by_profile: dict[str, int] = defaultdict(int)
    by_tiebreak: dict[str, int] = defaultdict(int)

    for p in evaluated:
        fr = p.get("future_result") or {}
        by_lottery[str(fr.get("lottery") or p.get("lottery") or "unknown")] += 1
        by_position[str(fr.get("position") or p.get("position") or "unknown")] += 1
        d = str(fr.get("date") or "")[:10]
        by_week[d[:7] if d else "unknown"] += 1
        by_engine[str(p.get("engine_version") or "unknown")] += 1
        by_profile[str(p.get("ranking_profile") or "socio")] += 1
        by_tiebreak[str(p.get("tiebreak_profile") or "unknown")] += 1

    multi_n = sum(1 for p in locked if p.get("multi_strong_candidates"))
    primary_n = sum(
        1
        for p in locked
        if not p.get("multi_strong_candidates")
        and (p.get("primary_signal") or {}).get("classification") == "FUERTE_PRINCIPAL"
    )
    cand_counts = [len(p.get("candidates") or []) for p in locked]

    return {
        "total_predictions": len(predictions),
        "total_locked": len(locked),
        "total_evaluated": len(evaluated),
        "total_expired": len(expired),
        "total_integrity_errors": len(integrity_errors),
        "primary_exact_d1": _exact_at(1, "primary"),
        "primary_exact_d3": _exact_at(3, "primary"),
        "primary_exact_d7": _exact_at(7, "primary"),
        "multi_strong_exact_d1": _exact_at(1, "multi"),
        "multi_strong_exact_d3": _exact_at(3, "multi"),
        "multi_strong_exact_d7": _exact_at(7, "multi"),
        "top2_exact_d1": _exact_at(1, "top2"),
        "top2_exact_d3": _exact_at(3, "top2"),
        "top2_exact_d7": _exact_at(7, "top2"),
        "top3_exact_d1": _exact_at(1, "top3"),
        "top3_exact_d3": _exact_at(3, "top3"),
        "top3_exact_d7": _exact_at(7, "top3"),
        "t1_family_hits": sum(
            1 for p in evaluated if (p.get("evaluation") or {}).get("hit_class") == "T1_FAMILY_HIT"
        ),
        "t2_neighbor_hits": sum(
            1 for p in evaluated if (p.get("evaluation") or {}).get("hit_class") == "T2_NEIGHBOR_HIT"
        ),
        "no_hits": sum(
            1 for p in evaluated if (p.get("evaluation") or {}).get("hit_class") == "NO_HIT"
        ),
        "average_candidates": mean(cand_counts) if cand_counts else 0.0,
        "multi_strong_rate": (multi_n / len(locked)) if locked else 0.0,
        "primary_rate": (primary_n / len(locked)) if locked else 0.0,
        "evaluation_completion_rate": (len(evaluated) / len(locked)) if locked else 0.0,
        "median_days_to_exact": median(days_to_exact) if days_to_exact else None,
        "average_days_to_exact": mean(days_to_exact) if days_to_exact else None,
        "results_by_lottery": dict(by_lottery),
        "results_by_position": dict(by_position),
        "results_by_week": dict(by_week),
        "results_by_engine_version": dict(by_engine),
        "results_by_profile": dict(by_profile),
        "results_by_tiebreak_rule": dict(by_tiebreak),
        "hit_primary_rate": _rate(evaluated, "hit_primary_exact"),
        "sample_insufficient": len(evaluated) < 100,
        "production_modified": False,
    }
