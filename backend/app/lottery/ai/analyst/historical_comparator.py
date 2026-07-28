"""Historical Comparator — comparative investigations (Fase B).

Builds multi-subject comparison plans over existing Lottery Tools.
"""

from __future__ import annotations

from typing import Any

from app.lottery.ai.planner import PlanStep
from app.services.lottery_ai_contracts import LotteryToolName


def compare_numbers_steps(
    *,
    a: str,
    b: str,
    lotteries: list[str] | None = None,
    lottery: str | None = None,
    year: int | None = None,
    position: int | None = None,
) -> list[PlanStep]:
    """Primary metrics first so ResearchEngine._bound truncation keeps both subjects.

    A and B always share the same lottery scope, year window, and position filter.
    """
    lots = list(lotteries or [])[:8]
    date_kw: dict[str, Any] = {}
    if year:
        y = int(year)
        date_kw = {
            "year": y,
            "from_date": f"{y}-01-01",
            "to_date": f"{y}-12-31",
        }
    pos_kw: dict[str, Any] = {}
    if position is not None:
        try:
            pos_i = int(position)
        except (TypeError, ValueError):
            pos_i = None
        if pos_i in (1, 2, 3):
            pos_kw = {"position": pos_i}

    steps: list[PlanStep] = []

    # 1–2. Occurrences for both subjects under identical filters
    if lottery:
        for n, tag in ((a, "a"), (b, "b")):
            steps.append(
                PlanStep(
                    tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                    params={"number": n, "lottery": lottery, **date_kw, **pos_kw},
                    purpose=f"compare_{tag}_occurrences",
                )
            )
    elif lots:
        # Unscoped: same multi-lottery last_n for both (never pin A/B to one sticky lot)
        for n, tag in ((a, "a"), (b, "b")):
            steps.append(
                PlanStep(
                    tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                    params={
                        "number": n,
                        "lotteries": lots,
                        "mode": "last_n",
                        "limit": 1,
                        "page_size": 1,
                        "order": "desc",
                        **date_kw,
                        **pos_kw,
                    },
                    purpose=f"compare_{tag}_last",
                )
            )

    # 3–4. Cross-lottery compare when lotteries provided (same lots + filters)
    if lots:
        for n, tag in ((a, "a"), (b, "b")):
            steps.append(
                PlanStep(
                    tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                    params={"number": n, "lotteries": lots, **date_kw, **pos_kw},
                    purpose=f"compare_{tag}_lotteries",
                )
            )

    # 5–6. Position / frequency only when a single lottery is explicit
    if lottery:
        for n, tag in ((a, "a"), (b, "b")):
            steps.append(
                PlanStep(
                    tool=LotteryToolName.GET_POSITION_DISTRIBUTION.value,
                    params={"number": n, "lottery": lottery, **date_kw},
                    purpose=f"compare_{tag}_positions",
                )
            )
        for n, tag in ((a, "a"), (b, "b")):
            steps.append(
                PlanStep(
                    tool=LotteryToolName.CALCULATE_FREQUENCIES.value,
                    params={"lottery": lottery, "number": n, **date_kw},
                    purpose=f"compare_{tag}_frequency",
                )
            )
        for n, tag in ((a, "a"), (b, "b")):
            for days in (1, 3, 7):
                steps.append(
                    PlanStep(
                        tool=LotteryToolName.GET_FOLLOWING_DAYS.value,
                        params={"number": n, "lottery": lottery, "days": days},
                        purpose=f"compare_{tag}_d{days}",
                    )
                )

    # 7. Cross historical pattern compare last
    hist: dict[str, Any] = {}
    if str(a).isdigit():
        hist["origin_x"] = int(a)
    if str(b).isdigit():
        hist["candidate_c"] = int(b)
    hist.update(date_kw)
    hist.update(pos_kw)
    if lottery:
        hist["lottery"] = lottery
    elif lots:
        hist["lotteries"] = lots
    if hist:
        steps.append(
            PlanStep(
                tool=LotteryToolName.COMPARE_HISTORICAL_PATTERNS.value,
                params=hist,
                purpose="compare_historical_patterns",
            )
        )
    return steps


def compare_lotteries_steps(
    *,
    lottery_a: str,
    lottery_b: str,
    number: str | None = None,
) -> list[PlanStep]:
    steps = [
        PlanStep(
            tool=LotteryToolName.COMPARE_LOTTERIES.value,
            params={"lotteries": [lottery_a, lottery_b]},
            purpose="compare_lottery_profiles",
        ),
        PlanStep(
            tool=LotteryToolName.GET_COINCIDENCES.value,
            params={"lotteries": [lottery_a, lottery_b], **({"number": number} if number else {})},
            purpose="compare_lottery_coincidences",
        ),
    ]
    if number:
        steps.append(
            PlanStep(
                tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                params={"number": number, "lotteries": [lottery_a, lottery_b]},
                purpose="compare_number_across_pair",
            )
        )
        for lot, tag in ((lottery_a, "a"), (lottery_b, "b")):
            steps.append(
                PlanStep(
                    tool=LotteryToolName.CALCULATE_FREQUENCIES.value,
                    params={"lottery": lot, "number": number},
                    purpose=f"compare_lot_{tag}_frequency",
                )
            )
    return steps


def compare_positions_steps(
    *,
    number: str,
    lottery: str | None = None,
) -> list[PlanStep]:
    return [
        PlanStep(
            tool=LotteryToolName.GET_POSITION_DISTRIBUTION.value,
            params={"number": number, "lottery": lottery},
            purpose="position_distribution_full",
        ),
        PlanStep(
            tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
            params={"number": number, "lottery": lottery, "position_scope": "first_position"},
            purpose="position_first_only",
        ),
        PlanStep(
            tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
            params={"number": number, "lottery": lottery, "position_scope": "second_position"},
            purpose="position_second_only",
        ),
    ]


def comparison_skeleton(subjects: list[str], dimension: str) -> dict[str, Any]:
    return {
        "subjects": subjects,
        "dimension": dimension,
        "similarities": [],
        "differences": [],
        "statistics": {},
        "note": "Filled from tool evidence only — no invented deltas.",
    }
