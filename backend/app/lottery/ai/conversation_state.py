"""Lottery IA 4.0 — conversation state, slot filling, understanding schema."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


IntentName = Literal[
    "result_by_date",
    "last_occurrence",
    "first_occurrence",
    "number_history",
    "frequency",
    "hot_numbers",
    "cold_numbers",
    "overdue_numbers",
    "compare_numbers",
    "compare_lotteries",
    "repeated_numbers",
    "cross_lottery_matches",
    "draw_sequence",
    "data_coverage",
    "data_quality",
    "missing_results",
    "sync_status",
    "source_health",
    "next_sync",
    "general_domain_question",
    "clarification_response",
    "follow_up",
    "unsupported",
]


class ConversationState(BaseModel):
    """Typed conversational memory for Lottery IA 4.0."""

    model_config = {"extra": "ignore"}

    active_lotteries: list[str] = Field(default_factory=list)
    active_numbers: list[str] = Field(default_factory=list)
    date_context: Optional[date] = None
    range_context: Optional[dict[str, Any]] = None
    draw_count_context: Optional[int] = None
    metric_context: Optional[str] = None
    pending_slots: list[str] = Field(default_factory=list)
    pending_intent: Optional[str] = None
    pending_params: dict[str, Any] = Field(default_factory=dict)
    last_intent: Optional[str] = None
    last_tool: Optional[str] = None
    last_plan: list[str] = Field(default_factory=list)
    clarification_question: Optional[str] = None
    scope: Literal["single", "multiple", "all", "unknown"] = "unknown"
    provider_trace: dict[str, Any] = Field(default_factory=dict)

    def to_store(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_store(cls, data: dict[str, Any] | None) -> "ConversationState":
        if not data:
            return cls()
        # Accept legacy LotterySessionContext keys
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
        try:
            return cls.model_validate(mapped)
        except Exception:
            return cls()


class UnderstandingResult(BaseModel):
    intent: Any = "unsupported"
    lotteries: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)
    date: Optional[date] = None
    date_range: Optional[dict[str, Any]] = None
    draw_count: Optional[int] = None
    metric: Optional[str] = None
    scope: Literal["single", "multiple", "all", "unknown"] = "unknown"
    missing_slots: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    confidence: float = 0.0
    tool: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)
    plan: list[str] = Field(default_factory=list)
    source: Literal["rules", "llm", "hybrid", "follow_up"] = "rules"


def smart_clarify(
    *,
    intent: str,
    number: str | None = None,
    lottery: str | None = None,
    missing: list[str] | None = None,
) -> str:
    """Natural clarification — only ask for missing slots."""
    missing = missing or []
    if intent == "last_occurrence" and number and "lottery" in missing:
        return (
            f"¿En cuál lotería quieres que busque la última aparición del {number}? "
            "Puedo revisarlo en una específica o compararlo entre todas las loterías disponibles."
        )
    if intent == "number_history" and number and "lottery" in missing:
        return (
            f"¿En cuál lotería quieres el historial del {number}? "
            "También puedo compararlo entre varias."
        )
    if intent in {"frequency", "hot_numbers", "cold_numbers", "overdue_numbers"}:
        bits = []
        if "lottery" in missing:
            bits.append("¿en alguna lotería específica o en todas?")
        if "period" in missing or "draw_count" in missing:
            bits.append("¿prefieres los últimos 30 sorteos, el último año o todo el historial?")
        if bits:
            return " ".join(
                [
                    "Para ese análisis necesito un poco más de detalle.",
                    *bits,
                ]
            )
    if intent == "compare_numbers" and number and "lottery" in missing:
        return (
            f"¿Entre qué loterías quieres comparar el {number}? "
            "Puedo usar las que ya mencionaste o todas las sincronizadas."
        )
    if "lottery" in missing and "date" in missing:
        return "¿Qué lotería y qué fecha exacta quieres consultar?"
    if "lottery" in missing:
        return "¿En cuál lotería quieres que lo consulte?"
    if "date" in missing:
        return "¿Qué fecha exacta quieres consultar?"
    if "number" in missing:
        return "¿Qué número quieres analizar?"
    return "¿Puedes precisar un poco más la consulta?"
