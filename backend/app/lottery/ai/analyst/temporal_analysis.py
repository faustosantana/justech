"""Temporal analysis helpers for Research Engine (Fase B).

Builds tool steps for before/after and D+N windows using existing Lottery Tools.
Does not invent dates or mutate history.
"""

from __future__ import annotations

from typing import Any

from app.lottery.ai.planner import PlanStep
from app.services.lottery_ai_contracts import LotteryToolName

SUPPORTED_WINDOWS = (1, 3, 7, 15, 30)


def normalize_windows(windows: list[int] | None) -> list[int]:
    raw = [int(w) for w in (windows or []) if int(w) in SUPPORTED_WINDOWS]
    return raw or [1, 3, 7]


def temporal_after_steps(
    *,
    number: str,
    lottery: str | None = None,
    base_date: str | None = None,
    windows: list[int] | None = None,
    year: int | None = None,
    anchors: list[dict[str, Any]] | None = None,
) -> list[PlanStep]:
    """Build following-days steps from known occurrence anchors only.

    Never invents base dates — uses last_analysis items / explicit base_date.
    """
    wins = normalize_windows(windows)
    # «tres días siguientes» → single window of 3 calendar days
    if windows and len(windows) == 1:
        wins = normalize_windows(windows)

    steps: list[PlanStep] = []
    anchor_rows: list[dict[str, Any]] = []
    for row in anchors or []:
        if not isinstance(row, dict):
            continue
        d = row.get("date") or row.get("draw_date") or row.get("base_date")
        if not d:
            continue
        lot = row.get("lottery") or lottery
        if not lot:
            continue
        anchor_rows.append({"date": str(d)[:10], "lottery": str(lot)})

    if not anchor_rows and base_date and lottery:
        anchor_rows = [{"date": str(base_date)[:10], "lottery": str(lottery)}]

    if not anchor_rows:
        # Cannot invent dates — return empty so orchestrator can soft-fail clearly
        return steps

    # Preserve occurrence order (already newest-first from last_n)
    day_span = max(wins) if wins else 3
    for i, anc in enumerate(anchor_rows[:10]):
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_FOLLOWING_DAYS.value,
                params={
                    "number": number,
                    "lottery": anc["lottery"],
                    "days": day_span,
                    "base_date": anc["date"],
                    "date": anc["date"],
                    "anchor_index": i + 1,
                },
                purpose=f"after_window_{i + 1}",
            )
        )
    return steps


def temporal_before_steps(
    *,
    number: str,
    lottery: str | None = None,
    base_date: str | None = None,
    windows: list[int] | None = None,
) -> list[PlanStep]:
    steps: list[PlanStep] = []
    for w in normalize_windows(windows)[:3]:
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_PREVIOUS_DAYS.value,
                params={
                    "number": number,
                    "lottery": lottery,
                    "days": w,
                    "base_date": base_date,
                },
                purpose=f"d_minus_{w}",
            )
        )
    return steps


def period_compare_steps(
    *,
    number: str,
    lottery: str | None,
    years: list[int],
) -> list[PlanStep]:
    steps: list[PlanStep] = []
    if lottery and len(years) >= 2:
        steps.append(
            PlanStep(
                tool=LotteryToolName.COMPARE_NUMBER_PERIODS.value,
                params={
                    "lottery": lottery,
                    "number": number,
                    "period_a": str(years[0]),
                    "period_b": str(years[1]),
                },
                purpose="period_year_compare",
            )
        )
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_YEARLY_COMPARISON.value,
                params={"lottery": lottery, "number": number, "years": years[:4]},
                purpose="yearly_comparison",
            )
        )
    elif lottery:
        steps.append(
            PlanStep(
                tool=LotteryToolName.COMPARE_NUMBER_PERIODS.value,
                params={
                    "lottery": lottery,
                    "number": number,
                    "period_a": "current_year",
                    "period_b": "previous_year",
                },
                purpose="period_default_compare",
            )
        )
    return steps


def temporal_summary(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    windows_hit = [
        e.get("purpose")
        for e in evidence
        if str(e.get("purpose") or "").startswith(("d_plus_", "d_minus_"))
    ]
    return {
        "criterion": "calendar_windows_via_lottery_tools",
        "windows_consulted": windows_hit,
        "supported_windows": list(SUPPORTED_WINDOWS),
    }
