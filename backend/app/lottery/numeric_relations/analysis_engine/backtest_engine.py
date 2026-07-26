"""Historical backtest for the Complete Analysis Engine."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Callable, Iterable
from statistics import median

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.schemas import (
    ENGINE_VERSION,
    RankProfile,
    new_id,
)


DrawFn = Callable[[date], list[dict[str, Any]]]
# each draw dict: {date, lottery, position, number}


def _window_hits(
    fuerte: int,
    analysis_date: date,
    future_draws: Iterable[dict[str, Any]],
    catalog: TableCatalog,
) -> dict[str, Any]:
    exact = {i: 0 for i in range(1, 8)}
    first_pos = 0
    any_pos = 0
    t1_hits = 0
    t2_hits = 0
    days_exact: list[int] = []
    family = set(catalog.get_table1_companions(fuerte))
    neigh = set(catalog.get_table2_neighbors(fuerte, exclude_self=True))

    by_day: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for d in future_draws:
        dd = d["date"] if isinstance(d["date"], date) else date.fromisoformat(str(d["date"])[:10])
        delta = (dd - analysis_date).days
        if 1 <= delta <= 7:
            by_day[delta].append(d)

    for day, rows in by_day.items():
        nums = [int(r["number"]) for r in rows]
        if fuerte in nums:
            exact[day] = 1
            days_exact.append(day)
            any_pos += 1
            if any(str(r.get("position", "first")) in {"first", "1", "primera"} and int(r["number"]) == fuerte for r in rows):
                first_pos += 1
        if set(nums) & family:
            t1_hits += 1
        if set(nums) & neigh:
            t2_hits += 1

    return {
        "exact_by_day": exact,
        "exact_hits_d1_d3": sum(exact[i] for i in (1, 2, 3)),
        "exact_hits_d1_d7": sum(exact.values()),
        "first_position_hits": first_pos,
        "any_position_hits": any_pos,
        "t1_family_hits": t1_hits,
        "t2_neighbor_hits": t2_hits,
        "days_to_exact": days_exact,
        "miss": sum(exact.values()) == 0,
    }


def run_backtest(
    scenarios: list[dict[str, Any]],
    *,
    get_future_draws: DrawFn | None = None,
    profile: str = RankProfile.MANUAL_RECONSTRUCTED.value,
    catalog: TableCatalog | None = None,
) -> dict[str, Any]:
    """
    scenarios: [{date, numbers, lotteries?, positions?}]
    get_future_draws(analysis_date) -> draw rows in next 7 days
    """
    cat = catalog or build_catalog()
    backtest_id = new_id("bt")
    total_analyses = 0
    total_candidates = 0
    total_strong = 0
    single_winner = 0
    multi_candidate = 0
    ambiguity = 0
    exact = {f"exact_hits_d{i}": 0 for i in range(1, 8)}
    exact_d1_d3 = 0
    exact_d1_d7 = 0
    first_pos = 0
    any_pos = 0
    t1_hits = 0
    t2_hits = 0
    misses = 0
    days_list: list[int] = []
    by_year: dict[str, int] = defaultdict(int)
    by_lottery: dict[str, int] = defaultdict(int)
    reconstructions: list[dict[str, Any]] = []

    for sc in scenarios:
        total_analyses += 1
        d = sc.get("date")
        if isinstance(d, str):
            d = date.fromisoformat(d[:10])
        result = run_complete_analysis(
            {
                "numbers": sc["numbers"],
                "date": d,
                "mode": profile,
                "positions": sc.get("positions") or ["first"],
                "lotteries": sc.get("lotteries") or [],
                "create_signals": False,
                "derivation_depth": sc.get("derivation_depth", 2),
            },
            catalog=cat,
            persist=False,
        )
        ranked = result.ranked_candidates
        total_candidates += len(ranked)
        strong = [c for c in ranked if c["classification"] in {"FUERTE_PRINCIPAL", "FUERTE_SECUNDARIO"}]
        total_strong += len(strong)
        if len(strong) == 1:
            single_winner += 1
        if len(ranked) > 1:
            multi_candidate += 1
        if len(strong) > 1:
            ambiguity += 1

        primary = result.primary_signal
        if d is not None:
            by_year[str(d.year)] += 1
        if primary and get_future_draws and d is not None:
            future = get_future_draws(d)
            hit = _window_hits(int(primary["number"]), d, future, cat)
            for i in range(1, 8):
                exact[f"exact_hits_d{i}"] += hit["exact_by_day"][i]
            exact_d1_d3 += hit["exact_hits_d1_d3"]
            exact_d1_d7 += hit["exact_hits_d1_d7"]
            first_pos += hit["first_position_hits"]
            any_pos += hit["any_position_hits"]
            t1_hits += 1 if hit["t1_family_hits"] else 0
            t2_hits += 1 if hit["t2_neighbor_hits"] else 0
            if hit["miss"]:
                misses += 1
            days_list.extend(hit["days_to_exact"])
            for lot in sc.get("lotteries") or []:
                by_lottery[str(lot)] += 1

        reconstructions.append(
            {
                "inputs": sc["numbers"],
                "primary": primary,
                "ranked": [
                    {"n": c["number"], "cls": c["classification"], "score": c["total_score"]}
                    for c in ranked[:5]
                ],
            }
        )

    metrics = {
        "backtest_id": backtest_id,
        "engine_version": ENGINE_VERSION,
        "profile": profile,
        "total_analyses": total_analyses,
        "total_candidates": total_candidates,
        "total_strong_signals": total_strong,
        "single_winner_rate": (single_winner / total_analyses) if total_analyses else 0.0,
        "multi_candidate_rate": (multi_candidate / total_analyses) if total_analyses else 0.0,
        "ambiguity_rate": (ambiguity / total_analyses) if total_analyses else 0.0,
        "average_candidates_per_analysis": (total_candidates / total_analyses) if total_analyses else 0.0,
        **exact,
        "exact_hits_d1_d3": exact_d1_d3,
        "exact_hits_d1_d7": exact_d1_d7,
        "first_position_hits": first_pos,
        "any_position_hits": any_pos,
        "t1_family_hits": t1_hits,
        "t2_neighbor_hits": t2_hits,
        "misses": misses,
        "median_days_to_exact": float(median(days_list)) if days_list else None,
        "average_days_to_exact": (sum(days_list) / len(days_list)) if days_list else None,
        "year_distribution": dict(by_year),
        "lottery_distribution": dict(by_lottery),
        "limitations": [
            "Las tasas de cumplimiento en ventana D+1..D+7 pueden saturarse por cobertura del universo 1..100.",
            "No afirmar ventaja predictiva sin baseline y tamaño muestral adecuado.",
            "Separar cumplimiento exacto de familia T1 / vecino T2.",
        ],
        "reconstructions": reconstructions,
    }
    return metrics


def manual_case_scenarios() -> list[dict[str, Any]]:
    """Reconstruction fixtures — NOT hardcoded engine branches."""
    return [
        {"date": "2026-06-21", "numbers": [41, 41, 70], "expected": 29, "id": "M1"},
        {"date": "2026-06-21", "numbers": [41, 62], "expected": 75, "id": "M2", "class": "VECINO_T2_DIRECTO"},
        {"date": "2026-06-21", "numbers": [49, 44, 70], "expected": 35, "id": "M3"},
        {"date": "2026-06-23", "numbers": [35, 14], "expected": 54, "id": "M4"},
        {"date": "2026-06-25", "numbers": [39, 58], "expected": 94, "id": "M5"},
    ]
