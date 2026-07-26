"""Historical profiler stub — attach optional stats without inventing dates."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.schemas import CandidateEvidence


def profile_from_activation_rows(
    candidate: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    rows: historical activation/outcome rows already sourced from DB/artifacts.
    Does not invent dates. Empty rows → empty profile.
    """
    if not rows:
        return {}
    exact = sum(1 for r in rows if r.get("exact"))
    d = {f"d{i}_hits": 0 for i in range(1, 8)}
    days: list[int] = []
    for r in rows:
        day = r.get("days_to_exact")
        if day and 1 <= int(day) <= 7:
            d[f"d{int(day)}_hits"] += 1
            days.append(int(day))
    return {
        "historical_activations": len(rows),
        "historical_exact_hits": exact,
        "historical_first_position_hits": sum(1 for r in rows if r.get("first_position")),
        "historical_any_position_hits": sum(1 for r in rows if r.get("any_position")),
        "historical_t1_family_hits": sum(1 for r in rows if r.get("t1_family")),
        "historical_t2_neighbor_hits": sum(1 for r in rows if r.get("t2_neighbor")),
        **d,
        "median_days_to_exact": sorted(days)[len(days) // 2] if days else None,
        "average_days_to_exact": (sum(days) / len(days)) if days else None,
        "lottery_distribution": {},
        "position_distribution": {},
        "year_distribution": {},
        "recent_equivalent_cases": rows[:5],
    }


def apply_profile(ev: CandidateEvidence, profile: dict[str, Any]) -> CandidateEvidence:
    for k, v in profile.items():
        if hasattr(ev, k):
            setattr(ev, k, v)
    return ev
