"""Lottery IA 4.1 — query planner (multi-tool, bounded, period/cross-lottery)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.lottery.ai.conversation_state import UnderstandingResult
from app.services.lottery_ai_contracts import LotteryToolName


MAX_TOOLS_PER_TURN = 8


class PlanStep(BaseModel):
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)
    purpose: str = ""


class QueryPlan(BaseModel):
    steps: list[PlanStep] = Field(default_factory=list)
    rationale: str = ""
    max_tools: int = MAX_TOOLS_PER_TURN

    def bounded(self) -> QueryPlan:
        return QueryPlan(
            steps=self.steps[: self.max_tools],
            rationale=self.rationale,
            max_tools=self.max_tools,
        )


def build_plan(understanding: UnderstandingResult) -> QueryPlan:
    """Build a validated multi-tool plan from understanding."""
    if understanding.needs_clarification or not understanding.tool:
        return QueryPlan(steps=[], rationale="awaiting_clarification")

    tool = understanding.tool
    params = dict(understanding.params or {})
    intent = str(understanding.intent or "")

    if intent == "post_occurrence_window" or tool == "lottery_analyze_post_occurrence_window":
        return QueryPlan(
            steps=[
                PlanStep(
                    tool="lottery_analyze_post_occurrence_window",
                    params=params,
                    purpose="post_occurrence_per_lottery_windows",
                )
            ],
            rationale="post_occurrence_window_from_memory",
        ).bounded()

    if tool == "lottery_compare_last_occurrence_all" or (
        intent == "last_occurrence" and understanding.scope == "all"
    ):
        number = params.get("number") or (
            understanding.numbers[0] if understanding.numbers else None
        )
        return QueryPlan(
            steps=[
                PlanStep(
                    tool=LotteryToolName.LIST_LOTTERIES.value,
                    params={"limit": 50, "searchable_only": True},
                    purpose="list_ai_enabled_lotteries",
                ),
                PlanStep(
                    tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                    params={"number": number, "lotteries": understanding.lotteries},
                    purpose="last_occurrence_all_or_named",
                ),
            ],
            rationale="compare_last_occurrence_across_lotteries",
        ).bounded()

    if intent in {"compare_numbers", "compare_lotteries"} and understanding.numbers:
        lots = list(understanding.lotteries)
        number = understanding.numbers[0]
        if lots:
            return QueryPlan(
                steps=[
                    PlanStep(
                        tool=LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES.value,
                        params={"lotteries": lots[:8], "number": number},
                        purpose="compare_number_across_named_lotteries",
                    )
                ],
                rationale="compare_number_across_lotteries",
            ).bounded()

    if intent in {"compare_number_periods", "yearly_comparison"} or tool in {
        LotteryToolName.COMPARE_NUMBER_PERIODS.value,
        LotteryToolName.GET_YEARLY_COMPARISON.value,
    }:
        return QueryPlan(
            steps=[
                PlanStep(
                    tool=LotteryToolName.RESOLVE_LOTTERY.value,
                    params={"lottery": params.get("lottery")},
                    purpose="resolve_lottery",
                ),
                PlanStep(
                    tool=LotteryToolName.COMPARE_NUMBER_PERIODS.value,
                    params={
                        "lottery": params.get("lottery"),
                        "number": params.get("number")
                        or (understanding.numbers[0] if understanding.numbers else None),
                        "period_a": params.get("period_a") or "current_year",
                        "period_b": params.get("period_b") or "previous_year",
                    },
                    purpose="compare_relative_frequency_periods",
                ),
            ],
            rationale="compare_number_periods",
        ).bounded()

    if intent == "lottery_summary" or tool == LotteryToolName.GET_LOTTERY_SUMMARY.value:
        return QueryPlan(
            steps=[
                PlanStep(
                    tool=LotteryToolName.GET_LOTTERY_SUMMARY.value,
                    params=params,
                    purpose="lottery_summary",
                ),
                PlanStep(
                    tool=LotteryToolName.GET_LATEST_AVAILABLE_DATE.value,
                    params={"lottery": params.get("lottery")},
                    purpose="latest_date",
                ),
            ],
            rationale="lottery_summary_pack",
        ).bounded()

    # Default single-tool plan
    return QueryPlan(
        steps=[PlanStep(tool=tool, params=params, purpose=intent or "tool")],
        rationale="single_tool",
    ).bounded()
