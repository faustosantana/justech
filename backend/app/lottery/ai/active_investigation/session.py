"""Structured Active Investigation Session (10-minute TTL)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

TTL_SECONDS = 600  # 10 minutes from last interaction


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ActiveInvestigationSession(BaseModel):
    """Structured investigation memory — not LLM chat text."""

    model_config = {"extra": "ignore"}

    investigation_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    conversation_id: str | None = None
    topic: str | None = None
    subjects: list[str] = Field(default_factory=list)
    relation: str | None = None  # e.g. same_day
    event_type: str | None = None
    metric: str | None = None
    lotteries: list[str] = Field(default_factory=list)
    positions: list[str] = Field(default_factory=list)
    date_anchor: str | None = None
    time_window: dict[str, Any] = Field(default_factory=dict)
    limit: int | None = None
    results: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    tools_used: list[str] = Field(default_factory=list)
    summary: str | None = None
    last_user_question: str | None = None
    last_answer: str | None = None
    last_intent: str | None = None
    follow_up_kind: str | None = None
    last_event: dict[str, Any] = Field(default_factory=dict)
    pending_questions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: _utcnow() + timedelta(seconds=TTL_SECONDS)
    )
    status: Literal["active", "expired", "closed"] = "active"

    def touch(self, *, ttl_seconds: int = TTL_SECONDS) -> "ActiveInvestigationSession":
        now = _utcnow()
        self.updated_at = now
        self.expires_at = now + timedelta(seconds=ttl_seconds)
        if self.status == "expired":
            self.status = "active"
        return self

    def is_expired(self, *, now: datetime | None = None) -> bool:
        ts = now or _utcnow()
        if self.status in {"expired", "closed"}:
            return True
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return ts >= exp

    def mark_expired(self) -> "ActiveInvestigationSession":
        self.status = "expired"
        return self

    def to_store(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_store(cls, data: dict[str, Any] | None) -> "ActiveInvestigationSession | None":
        if not data or not isinstance(data, dict):
            return None
        try:
            return cls.model_validate(data)
        except Exception:  # noqa: BLE001
            return None
