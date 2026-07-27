"""Research Engine profesional — Investigación Inteligente (Fase B v2.0).

Builds strategies before answering. Executes via existing Lottery Tools only.
Never invents data. Never mutates motor / ranking / Prompt Maestro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.lottery.ai.analyst.config import AnalystRuntimeConfig
from app.lottery.ai.analyst.dynamic_planner import DynamicResearchPlanner
from app.lottery.ai.analyst.question_classifier import (
    RESEARCH_KINDS,
    QuestionClassifier,
    ResearchQuestion,
)
from app.lottery.ai.analyst.research_planner import ResearchPlan
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.planner import PlanStep, build_plan


@dataclass
class ResearchAuditRecord:
    question: str
    kind: str | None
    plan_steps: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    duration_ms: int | None = None
    tokens: int | None = None
    result_preview: str | None = None
    errors: list[str] = field(default_factory=list)
    confidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "kind": self.kind,
            "plan": self.plan_steps,
            "tools": self.tools,
            "duration_ms": self.duration_ms,
            "tokens": self.tokens,
            "result_preview": self.result_preview,
            "errors": self.errors,
            "confidence": self.confidence,
        }


class ResearchEngine:
    """True investigation engine on top of Fase A architecture."""

    ENABLED = True
    VERSION = "2.0"
    SUPPORTED_KINDS = RESEARCH_KINDS

    def can_handle(self, question: ResearchQuestion) -> bool:
        if not self.ENABLED:
            return False
        if question.requires_discovery:
            return False
        return question.kind in self.SUPPORTED_KINDS

    def prepare(self, question: ResearchQuestion, context: dict[str, Any]) -> dict[str, Any]:
        """Strategy preview (no tool execution)."""
        state = ConversationState()
        if isinstance(context, dict):
            if context.get("active_numbers"):
                state.active_numbers = list(context["active_numbers"])
            if context.get("active_lotteries"):
                state.active_lotteries = list(context["active_lotteries"])
            if context.get("active_pair"):
                state.active_pair = list(context["active_pair"])
            if context.get("current_primary_candidate") is not None:
                try:
                    state.current_primary_candidate = int(context["current_primary_candidate"])
                except (TypeError, ValueError):
                    pass
        steps, meta = DynamicResearchPlanner.build(question, state, max_steps=40)
        return {
            "status": "planned",
            "enabled": True,
            "version": self.VERSION,
            "kind": question.kind,
            "step_count": len(steps),
            "steps": [s.purpose or s.tool for s in steps],
            "meta": meta,
            "message": "Estrategia de investigación lista. Ejecutar vía Tool Orchestrator.",
        }

    def classify(
        self,
        message: str,
        state: ConversationState,
        resolution: dict[str, Any] | None = None,
    ) -> ResearchQuestion | None:
        return QuestionClassifier.classify(message, state, resolution)

    def build_plan(
        self,
        *,
        message: str,
        understanding: UnderstandingResult,
        state: ConversationState,
        config: AnalystRuntimeConfig,
        resolution: dict[str, Any] | None = None,
    ) -> ResearchPlan | None:
        """Return a dynamic ResearchPlan when the message is an open investigation."""
        if not self.ENABLED:
            return None
        if understanding.needs_clarification and not (
            resolution and resolution.get("inherit_active_number")
        ):
            # Still allow research if we can inherit context
            if not (state.active_numbers or state.active_pair):
                return None

        question = self.classify(message, state, resolution)
        if question is None or not self.can_handle(question):
            return None

        # Force research for classified open questions unless admin is quick/light
        if config.research_mode == "quick" or config.analysis_depth == "light":
            return None

        max_steps = config.effective_max_steps()
        max_tools = config.effective_max_tools()
        steps, meta = DynamicResearchPlanner.build(
            question, state, max_steps=max(max_steps, max_tools)
        )
        # If dynamic plan empty, fall back to single understanding tool
        if not steps and understanding.tool:
            base = build_plan(understanding)
            steps = list(base.steps)

        steps = self._bound(steps, max_tools=max_tools, max_steps=max_steps)
        if not steps:
            return None

        return ResearchPlan(
            mode="deep",
            is_research=True,
            steps=steps,
            rationale=f"research_engine:{question.kind}",
            investigating_message=config.investigating_message,
            user_visible_status=config.investigating_message,
            question_kind=question.kind,
            research_meta=meta,
        )

    # Prefer primary answer metrics over satellite windows when truncating.
    _BOUND_PRIORITY_PURPOSES = frozenset(
        {
            "compare_a_occurrences",
            "compare_b_occurrences",
            "compare_a_lotteries",
            "compare_b_lotteries",
            "last_n_occurrences",
            "last_occurrence",
            "last_occurrence_all_lotteries",
            "recent_occurrences",
            "same_day_coincidence",
            "frequency",
            "frequency_across_lotteries",
        }
    )

    @classmethod
    def _bound(cls, steps: list[PlanStep], *, max_tools: int, max_steps: int) -> list[PlanStep]:
        limit = max(1, min(max_tools, max_steps))
        if len(steps) <= limit:
            return list(steps)
        primary = [s for s in steps if str(s.purpose or "") in cls._BOUND_PRIORITY_PURPOSES]
        satellite = [s for s in steps if str(s.purpose or "") not in cls._BOUND_PRIORITY_PURPOSES]
        return (primary + satellite)[:limit]


def get_research_engine() -> ResearchEngine:
    return ResearchEngine()
