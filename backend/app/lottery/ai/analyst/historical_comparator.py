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
) -> list[PlanStep]:
    lots = list(lotteries or [])[:6]
    steps: list[PlanStep] = []
    for n, tag in ((a, "a"), (b, "b")):
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                params={"number": n, "lottery": lottery, **({"year": year} if year else {})},
                purpose=f"compare_{tag}_occurrences",
            )
        )
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_POSITION_DISTRIBUTION.value,
                params={"number": n, "lottery": lottery, **({"year": year} if year else {})},
                purpose=f"compare_{tag}_positions",
            )
        )
        if lottery:
            steps.append(
                PlanStep(
                    tool=LotteryToolName.CALCULATE_FREQUENCIES.value,
                    params={"lottery": lottery, "number": n, **({"year": year} if year else {})},
                    purpose=f"compare_{tag}_frequency",
                )
            )
        if lots:
            steps.append(
                PlanStep(
                    tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                    params={"number": n, "lotteries": lots},
                    purpose=f"compare_{tag}_lotteries",
                )
            )
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_FOLLOWING_DAYS.value,
                params={"number": n, "lottery": lottery, "days": 1},
                purpose=f"compare_{tag}_d1",
            )
        )
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_FOLLOWING_DAYS.value,
                params={"number": n, "lottery": lottery, "days": 3},
                purpose=f"compare_{tag}_d3",
            )
        )
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_FOLLOWING_DAYS.value,
                params={"number": n, "lottery": lottery, "days": 7},
                purpose=f"compare_{tag}_d7",
            )
        )
    # Cross historical pattern compare when both look numeric
    hist: dict[str, Any] = {}
    if str(a).isdigit():
        hist["origin_x"] = int(a)
    if str(b).isdigit():
        hist["candidate_c"] = int(b)
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
