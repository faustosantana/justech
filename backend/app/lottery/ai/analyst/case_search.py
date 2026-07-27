"""Case Search Engine — equivalent / similar / related cases (Fase B).

Uses existing historical Lottery Tools only. Always records the criterion.
"""

from __future__ import annotations

from typing import Any

from app.lottery.ai.planner import PlanStep
from app.services.lottery_ai_contracts import LotteryToolName


CASE_CRITERIA = {
    "equivalent": "same origin/confirmer relation conditions (exact historical match)",
    "similar": "shared confirmer combinations / pattern detail",
    "partial": "partial pattern overlap via compare_historical_patterns",
    "related": "related numbers / cross confirmations",
}


def case_search_steps(
    *,
    observed: str | None,
    confirmer: str | None = None,
    candidate: int | None = None,
    lottery: str | None = None,
    mode: str = "all",  # all | equivalent | similar | partial | related | recent
) -> list[PlanStep]:
    steps: list[PlanStep] = []
    if not observed:
        return steps

    hist: dict[str, Any] = {
        "origin_x": int(observed) if str(observed).isdigit() else observed,
    }
    if confirmer is not None:
        hist["confirmer_y"] = int(confirmer) if str(confirmer).isdigit() else confirmer
    if candidate is not None:
        hist["candidate_c"] = int(candidate)

    if mode in {"all", "equivalent", "recent"}:
        steps.append(
            PlanStep(
                tool=LotteryToolName.HISTORICAL_RELATION_CONDITIONS.value,
                params=hist,
                purpose="cases_equivalent",
            )
        )
    if mode in {"all", "similar", "related"} and confirmer is not None:
        steps.append(
            PlanStep(
                tool=LotteryToolName.CONFIRMER_COMBINATIONS.value,
                params=hist,
                purpose="cases_related_confirmations",
            )
        )
    if mode in {"all", "similar", "partial"}:
        steps.append(
            PlanStep(
                tool=LotteryToolName.COMPARE_HISTORICAL_PATTERNS.value,
                params=hist,
                purpose="cases_similar_partial",
            )
        )
        steps.append(
            PlanStep(
                tool=LotteryToolName.RELATION_PATTERN_DETAIL.value,
                params=hist,
                purpose="cases_pattern_detail",
            )
        )
    if candidate is not None and mode in {"all", "equivalent", "similar"}:
        steps.append(
            PlanStep(
                tool=LotteryToolName.CANDIDATE_RESPONSE_SUMMARY.value,
                params={**hist, "candidate_c": int(candidate)},
                purpose="cases_d1_d3_d7_summary",
            )
        )
    if mode == "recent" and observed:
        steps.append(
            PlanStep(
                tool=LotteryToolName.GET_NUMBER_OCCURRENCES.value,
                params={"number": observed, "lottery": lottery, "occurrence_mode": "recent"},
                purpose="cases_recent_occurrences",
            )
        )
    return steps


def describe_case_criteria(mode: str = "all") -> list[dict[str, str]]:
    if mode == "all":
        return [{"code": k, "criterion": v} for k, v in CASE_CRITERIA.items()]
    if mode in CASE_CRITERIA:
        return [{"code": mode, "criterion": CASE_CRITERIA[mode]}]
    return [{"code": mode, "criterion": CASE_CRITERIA.get("equivalent", mode)}]
