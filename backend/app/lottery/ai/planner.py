"""Lottery IA 4.0 — query planner (multi-tool, bounded)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.lottery.ai.conversation_state import UnderstandingResult


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

    if tool == "lottery_compare_last_occurrence_all" or (
        understanding.intent == "last_occurrence" and understanding.scope == "all"
    ):
        number = params.get("number") or (
            understanding.numbers[0] if understanding.numbers else None
        )
        return QueryPlan(
            steps=[
                PlanStep(
                    tool="lottery_list_lotteries",
                    params={"limit": 50, "searchable_only": True},
                    purpose="list_ai_enabled_lotteries",
                ),
                PlanStep(
                    tool="lottery_get_last_occurrence",
                    params={"number": number, "scope": "all"},
                    purpose="search_last_occurrence_per_lottery",
                ),
            ],
            rationale="compare_last_occurrence_across_lotteries",
        ).bounded()

    if understanding.intent == "compare_numbers" and understanding.numbers:
        lots = list(understanding.lotteries)
        number = understanding.numbers[0]
        steps = [
            PlanStep(
                tool="lottery_get_last_occurrence",
                params={"lottery": lot, "number": number},
                purpose=f"last_occurrence_{lot}",
            )
            for lot in lots[:MAX_TOOLS_PER_TURN]
        ]
        if steps:
            return QueryPlan(
                steps=steps,
                rationale="compare_number_across_named_lotteries",
            ).bounded()

    # Default single-tool plan
    return QueryPlan(
        steps=[PlanStep(tool=tool, params=params, purpose=understanding.intent)],
        rationale="single_tool",
    ).bounded()
