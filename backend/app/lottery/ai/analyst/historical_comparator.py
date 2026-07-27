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
    """Primary metrics first so ResearchEngine._bound truncation keeps both subjects."""
    lots = list(lotteries or [])[:6]
    year_kw = {"year": year} if year else {}
    steps: list[PlanStep] = []

    # 1–2. Occurrences for both subjects (survive truncation)
    for n, tag in ((a, "a"), (b, "b")):
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                params={"number": n, "lottery": lottery, **year_kw},
                purpose=f"compare_{tag}_occurrences",
            )
        )

    # 3–4. Cross-lottery compare when lotteries provided
    if lots:
        for n, tag in ((a, "a"), (b, "b")):
            steps.append(
                PlanStep(
                    tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                    params={"number": n, "lotteries": lots, **year_kw},
                    purpose=f"compare_{tag}_lotteries",
                )
            )

    # 5. Position distribution a/b
    for n, tag in ((a, "a"), (b, "b")):
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_POSITION_DISTRIBUTION.value,
                params={"number": n, "lottery": lottery, **year_kw},
                purpose=f"compare_{tag}_positions",
            )
        )

    # 6. Frequencies a/b when a lottery is set
    if lottery:
        for n, tag in ((a, "a"), (b, "b")):
            steps.append(
                PlanStep(
                    tool=LotteryToolName.CALCULATE_FREQUENCIES.value,
                    params={"lottery": lottery, "number": n, **year_kw},
                    purpose=f"compare_{tag}_frequency",
                )
            )

    # 7. Optional D+1/D+3/D+7 windows last (satellite; may be truncated)
    for n, tag in ((a, "a"), (b, "b")):
        for days in (1, 3, 7):
            steps.append(
                PlanStep(
                    tool=LotteryToolName.GET_FOLLOWING_DAYS.value,
                    params={"number": n, "lottery": lottery, "days": days},
                    purpose=f"compare_{tag}_d{days}",
                )
            )

    # 8. Cross historical pattern compare last
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
