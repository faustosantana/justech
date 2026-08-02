"""Structured conversational orchestrator decision schema (no free-text answers)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

TurnType = Literal[
    "new_investigation",
    "contextual_follow_up",
    "attribute_of_last_event",
    "filter_refine",
    "topic_switch",
    "clarify",
    "meta",
    "reuse_evidence",
    "asset_action",
    "social_chitchat",
]

ORCHESTRATOR_JSON_SCHEMA_HINT = """{
  "turn_type": "new_investigation|contextual_follow_up|attribute_of_last_event|filter_refine|topic_switch|clarify|meta|reuse_evidence|asset_action|social_chitchat",
  "intent": "string",
  "subjects": ["NN", "..."],
  "relation": "same_day|null|string",
  "lottery_scope": ["..."],
  "position_scope": ["..."],
  "period_scope": {},
  "reuse_asset": false,
  "asset_id": null,
  "workspace_action": null,
  "tool_plan": [],
  "needs_clarification": false,
  "clarification_slot": null,
  "confidence": 0.0,
  "reason_codes": ["..."]
}"""


class OrchestratorDecision(BaseModel):
    """Mandatory decision object — never a free-text user answer."""

    model_config = {"extra": "forbid"}

    turn_type: TurnType
    intent: str = ""
    subjects: list[str] = Field(default_factory=list)
    relation: str | None = None
    lottery_scope: list[str] = Field(default_factory=list)
    position_scope: list[str] = Field(default_factory=list)
    period_scope: dict[str, Any] = Field(default_factory=dict)
    reuse_asset: bool = False
    asset_id: str | None = None
    workspace_action: str | None = None
    tool_plan: list[Any] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_slot: str | None = None
    confidence: float = 0.0
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("subjects", "lottery_scope", "position_scope", "reason_codes", "tool_plan", mode="before")
    @classmethod
    def _listify(cls, v: Any) -> list:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]

    @field_validator("period_scope", mode="before")
    @classmethod
    def _dictify(cls, v: Any) -> dict:
        return v if isinstance(v, dict) else {}

    @field_validator("confidence", mode="before")
    @classmethod
    def _conf(cls, v: Any) -> float:
        try:
            return float(v)
        except Exception:  # noqa: BLE001
            return 0.0

    @field_validator("subjects")
    @classmethod
    def _norm_subjects(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for s in v or []:
            t = str(s).strip()
            if t.isdigit():
                t = t.zfill(2) if len(t) <= 2 else t
            if t and t not in out:
                out.append(t)
        return out[:8]


def parse_orchestrator_decision(raw: Any) -> tuple[OrchestratorDecision | None, str | None]:
    """Strict parse. Returns (decision, error)."""
    if isinstance(raw, OrchestratorDecision):
        return raw, None
    if not isinstance(raw, dict):
        return None, "not_an_object"
    try:
        return OrchestratorDecision.model_validate(raw), None
    except ValidationError as e:
        return None, f"schema_invalid:{e.error_count()}"
