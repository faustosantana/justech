"""Research Trace — full investigation audit trail (Fase A.1)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchTrace:
    """Complete debug trace for one Analista IA investigation turn."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent: str | None = None
    context_used: dict[str, Any] = field(default_factory=dict)
    filters_applied: dict[str, Any] = field(default_factory=dict)
    tools_used: list[str] = field(default_factory=list)
    steps_executed: list[dict[str, Any]] = field(default_factory=list)
    evidence_found: list[dict[str, Any]] = field(default_factory=list)
    response_preview: str | None = None
    investigating: bool = False
    research_mode: str | None = None
    analysis_depth: str | None = None
    config_snapshot: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.monotonic)
    finished_at: float | None = None
    duration_ms: int | None = None
    error: str | None = None

    def mark_step(
        self,
        *,
        tool: str,
        purpose: str | None = None,
        status: str = "success",
        duration_ms: int | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        self.steps_executed.append(
            {
                "tool": tool,
                "purpose": purpose,
                "status": status,
                "duration_ms": duration_ms,
            }
        )
        if status == "success" and tool not in self.tools_used:
            self.tools_used.append(tool)
        if summary:
            self.evidence_found.append(
                {
                    "tool": tool,
                    "purpose": purpose,
                    "summary_keys": list(summary.keys())[:12],
                }
            )

    def finish(self, *, response: str | None = None, error: str | None = None) -> "ResearchTrace":
        self.finished_at = time.monotonic()
        self.duration_ms = int((self.finished_at - self.started_at) * 1000)
        if response is not None:
            self.response_preview = (response or "")[:400]
        if error:
            self.error = error
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "intent": self.intent,
            "context_used": self.context_used,
            "filters_applied": self.filters_applied,
            "tools_used": self.tools_used,
            "steps_executed": self.steps_executed,
            "evidence_found": self.evidence_found[-12:],
            "response_preview": self.response_preview,
            "investigating": self.investigating,
            "research_mode": self.research_mode,
            "analysis_depth": self.analysis_depth,
            "config_snapshot": self.config_snapshot,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }
