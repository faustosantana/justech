"""Lottery IA 4.2 — structured conversation memory extensions."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


IntentName = Literal[
    "result_by_date",
    "last_occurrence",
    "first_occurrence",
    "multi_last_occurrence",
    "last_occurrence_by_position",
    "cross_lottery_last_occurrence",
    "occurrence_in_other_lotteries",
    "multi_number_query",
    "compound_lottery_query",
    "number_history",
    "frequency",
    "hot_numbers",
    "cold_numbers",
    "overdue_numbers",
    "compare_numbers",
    "compare_lotteries",
    "compare_number_periods",
    "repeated_numbers",
    "cross_lottery_matches",
    "draw_sequence",
    "post_occurrence_window",
    "data_coverage",
    "data_quality",
    "data_completeness",
    "missing_results",
    "sync_status",
    "source_health",
    "next_sync",
    "lottery_summary",
    "latest_date",
    "explain_metric",
    "yearly_comparison",
    "monthly_trend",
    "general_domain_question",
    "greeting",
    "general_chat",
    "help",
    "clarification_response",
    "follow_up",
    "out_of_domain",
    "restricted_technical",
    "prediction_request",
    "unsupported",
]


class OccurrenceMemory(BaseModel):
    number: str
    date: str
    position: str | int | None = None
    lottery: str | None = None


class ConversationState(BaseModel):
    """Typed conversational memory for Lottery IA 4.2."""

    model_config = {"extra": "ignore"}

    active_lotteries: list[str] = Field(default_factory=list)
    active_numbers: list[str] = Field(default_factory=list)
    primary_lottery: Optional[str] = None
    date_context: Optional[date] = None
    range_context: Optional[dict[str, Any]] = None
    draw_count_context: Optional[int] = None
    calendar_window: Optional[int] = None
    metric_context: Optional[str] = None
    analysis_scope: Literal["current", "defaults", "all", "custom", "unknown"] = "unknown"
    analysis_depth: Literal["quick", "standard", "deep"] = "standard"
    pending_slots: list[str] = Field(default_factory=list)
    pending_intent: Optional[str] = None
    pending_params: dict[str, Any] = Field(default_factory=dict)
    last_intent: Optional[str] = None
    last_tool: Optional[str] = None
    last_plan: list[str] = Field(default_factory=list)
    clarification_question: Optional[str] = None
    scope: Literal["single", "multiple", "all", "unknown"] = "unknown"
    # Derived tool results — critical for follow-ups
    last_occurrences: dict[str, OccurrenceMemory] = Field(default_factory=dict)
    # Position preference — Fase X.2: default all positions; first is preferred highlight only
    default_number_position_scope: Literal[
        "first_position", "any_position", "specific_position", "ask_each_time"
    ] = "any_position"
    default_primary_position: int = 1
    last_multi_queries: list[dict[str, Any]] = Field(default_factory=list)
    last_position_scope: Optional[str] = None
    last_tool_results: list[dict[str, Any]] = Field(default_factory=list)
    last_analysis: dict[str, Any] = Field(default_factory=dict)
    last_user_reference: Optional[str] = None
    provider_trace: dict[str, Any] = Field(default_factory=dict)
    conversation_summary: Optional[str] = None
    active_date: Optional[str] = None
    active_position: Optional[str] = None
    current_primary_candidate: Optional[int] = None
    current_alternatives: list[int] = Field(default_factory=list)
    historical_summary: Optional[str] = None
    # Fase A — Conversation Brain extensions (additive; ignore if absent in legacy sessions)
    active_pair: list[str] = Field(default_factory=list)
    active_filters: dict[str, Any] = Field(default_factory=dict)
    open_hypotheses: list[str] = Field(default_factory=list)
    current_research: dict[str, Any] = Field(default_factory=dict)
    recent_memory: list[str] = Field(default_factory=list)
    research_mode: Optional[str] = None
    focus_stack: list[str] = Field(default_factory=list)
    # Fase X.2 — compound relation memory
    active_relation: Optional[str] = None  # e.g. same_day
    preferred_position: int = 1
    position_scope: Optional[str] = None  # any_position | first_position | ...
    # v2.4.5 — meta continuity (H.5–H.9): prefer factual template over LLM rewrite
    force_local_template: bool = False
    # Analyst 2.0 — structured Active Investigation Session (10 min TTL)
    active_investigation: dict[str, Any] = Field(default_factory=dict)
    # Investigation Workspace 1.0 — operable assets
    workspace_assets: dict[str, Any] = Field(default_factory=dict)
    active_asset_id: str | None = None

    def to_store(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def occurrence_date_for(self, lottery: str) -> date | None:
        mem = self.last_occurrences.get(lottery)
        if not mem or not mem.date:
            return None
        try:
            return date.fromisoformat(str(mem.date)[:10])
        except ValueError:
            return None

    def remember_occurrence(
        self,
        *,
        lottery: str,
        number: str,
        draw_date: date | str | None,
        position: str | int | None = None,
    ) -> None:
        if not lottery or not draw_date:
            return
        iso = draw_date.isoformat() if isinstance(draw_date, date) else str(draw_date)[:10]
        self.last_occurrences[lottery] = OccurrenceMemory(
            number=str(number),
            date=iso,
            position=position,
            lottery=lottery,
        )
        try:
            self.date_context = date.fromisoformat(iso)
        except ValueError:
            pass
        if lottery not in self.active_lotteries:
            self.active_lotteries.append(lottery)
        # Never collapse a sticky same-day / active investigation pair to one ball.
        if str(self.active_relation or "").lower() == "same_day" and len(self.active_numbers or []) >= 2:
            pass
        elif number and (not self.active_numbers or self.active_numbers[0] != str(number)):
            self.active_numbers = [str(number)]

    @classmethod
    def from_store(cls, data: dict[str, Any] | None) -> "ConversationState":
        if not data:
            return cls()
        mapped = dict(data)
        if "active_lotteries" not in mapped and data.get("last_lottery"):
            mapped["active_lotteries"] = [data["last_lottery"]]
        if "active_numbers" not in mapped and data.get("last_numbers"):
            mapped["active_numbers"] = list(data.get("last_numbers") or [])
        if "date_context" not in mapped and data.get("base_date"):
            mapped["date_context"] = data["base_date"]
        if "draw_count_context" not in mapped and data.get("last_draw_count"):
            mapped["draw_count_context"] = data["last_draw_count"]
        if "last_intent" not in mapped and data.get("last_query_semantics"):
            mapped["last_intent"] = data["last_query_semantics"]
        if "pending_slots" not in mapped and data.get("pending_ambiguity"):
            mapped["pending_slots"] = ["lottery"]
        # Normalize legacy last_occurrences dict[str,str] → OccurrenceMemory
        raw_occ = mapped.get("last_occurrences")
        if isinstance(raw_occ, dict) and raw_occ:
            normalized: dict[str, Any] = {}
            for k, v in raw_occ.items():
                if isinstance(v, dict):
                    item = dict(v)
                    if "date" not in item and item.get("draw_date"):
                        item["date"] = item.pop("draw_date")
                    if "number" not in item:
                        nums = mapped.get("active_numbers") or []
                        item["number"] = nums[0] if nums else ""
                    item.setdefault("lottery", k)
                    normalized[k] = item
                elif isinstance(v, str):
                    nums = mapped.get("active_numbers") or []
                    normalized[k] = {
                        "number": nums[0] if nums else "",
                        "date": v,
                        "lottery": k,
                    }
            mapped["last_occurrences"] = normalized
        if isinstance(mapped.get("active_numbers"), list):
            mapped["active_numbers"] = [
                str(n).zfill(2) if str(n).isdigit() and len(str(n)) <= 2 else str(n)
                for n in mapped["active_numbers"]
            ]
        try:
            return cls.model_validate(mapped)
        except Exception:
            return cls()


class UnderstandingResult(BaseModel):
    intent: Any = "unsupported"
    lotteries: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)
    query_date: Optional[date] = None
    date_range: Optional[dict[str, Any]] = None
    draw_count: Optional[int] = None
    calendar_days: Optional[int] = None
    metric: Optional[str] = None
    scope: Literal["single", "multiple", "all", "unknown"] = "unknown"
    missing_slots: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    confidence: float = 0.0
    tool: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)
    plan: list[str] = Field(default_factory=list)
    source: Literal["rules", "llm", "hybrid", "follow_up", "domain"] = "rules"
    domain_class: Optional[str] = None
    per_lottery_dates: dict[str, str] = Field(default_factory=dict)


def smart_clarify(
    *,
    intent: str,
    number: str | None = None,
    lottery: str | None = None,
    missing: list[str] | None = None,
    known_lotteries: list[str] | None = None,
) -> str:
    """Natural clarification — ONLY material blockers (Fase X.1)."""
    missing = missing or []
    # Never ask lottery/date/position as form fields
    material = [m for m in missing if m in {"number", "compare_with", "query"}]
    if not material:
        return "¿Qué te gustaría investigar en el histórico?"
    if "number" in material:
        if intent in {"last_occurrence", "DATE"} or "última" in intent:
            return "¿La última vez de cuál número?"
        return "¿De qué número?"
    if "compare_with" in material:
        return "¿Con qué número lo comparo?"
    return "¿Qué te gustaría investigar?"
