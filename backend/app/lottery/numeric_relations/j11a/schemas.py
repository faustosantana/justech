"""J-11A schemas — Copiloto Analítico (explains; never calculates tables)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.lottery.numeric_relations.analysis_engine.schemas import ExplanationLevel


J11A_VERSION = "j11a-analytical-copilot-1.0.0"


INTENTS = (
    "RUN_ANALYSIS",
    "EXPLAIN_SIGNAL",
    "EXPLAIN_CANDIDATE",
    "COMPARE_CANDIDATES",
    "SHOW_RELATIONSHIP_GRAPH",
    "SHOW_TABLE1_RELATIONS",
    "SHOW_TABLE2_RELATIONS",
    "SHOW_DERIVATIONS",
    "SHOW_ACTIVE_SIGNALS",
    "SHOW_FULFILLED_SIGNALS",
    "CHECK_HISTORICAL_APPEARANCE",
    "COMPARE_HISTORICAL_CASES",
    "RUN_BACKTEST",
    "SHOW_CHAIN",
    "SHOW_PREDICTIONS",
    "EXPLAIN_CONFIDENCE",
    "EXPLAIN_REJECTION",
    "FOLLOW_UP_CONTEXT",
    "CLARIFY",
    "UNKNOWN",
)


@dataclass
class SessionMemory:
    conversation_id: str
    analysis_id: str | None = None
    observed_numbers: list[int] = field(default_factory=list)
    analysis_date: str | None = None
    lotteries: list[str] = field(default_factory=list)
    positions: list[str] = field(default_factory=list)
    mode: str | None = None
    derivation_depth: int = 2
    primary_signal: dict[str, Any] | None = None
    secondary_signals: list[dict[str, Any]] = field(default_factory=list)
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    last_candidate: int | None = None
    last_signal: str | None = None
    last_question: str | None = None
    active_chain: str | None = None
    explanation_level: str = ExplanationLevel.ANALYTICAL.value
    last_ranked: list[dict[str, Any]] = field(default_factory=list)
    last_result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IntentResult:
    intent: str
    numbers: list[int] = field(default_factory=list)
    candidate: int | None = None
    raw: str = ""
    needs_clarification: bool = False
    clarification_prompt: str | None = None
    explanation_level: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlanStep:
    step: int
    action: str
    tool: str | None = None
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    intent: str
    steps: list[PlanStep]
    notes: str = "Planner is deterministic; LLM must not compute tables."

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "steps": [asdict(s) for s in self.steps],
            "notes": self.notes,
        }
