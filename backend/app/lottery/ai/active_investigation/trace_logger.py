"""ConversationTraceLogger — safe turn diagnostics (no chain-of-thought)."""

from __future__ import annotations

from typing import Any

from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecision


class ConversationTraceLogger:
    @staticmethod
    def build(
        *,
        decision: HermesDecision | None,
        provider_used: str | None = None,
        model_used: str | None = None,
        prompt_version: str | None = None,
        latency_ms: float | None = None,
        token_usage: dict[str, Any] | None = None,
        fallback_reason: str | None = None,
        investigation_id: str | None = None,
        evidence_reused: bool = False,
        tools_used: list[str] | None = None,
        reasoning_telemetry: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {
            "provider_used": provider_used,
            "model_used": model_used,
            "prompt_version": prompt_version,
            "latency_ms": latency_ms,
            "token_usage": token_usage or {},
            "fallback_reason": fallback_reason,
            "investigation_id": investigation_id,
            "evidence_reused": evidence_reused,
            "tools_used": list(tools_used or [])[:16],
        }
        if decision is not None:
            out["hermes_decision"] = decision.to_trace()
            out["hermes_decision_id"] = decision.hermes_decision_id
        if reasoning_telemetry:
            out["analyst_reasoning"] = reasoning_telemetry
        return {k: v for k, v in out.items() if v is not None and v != {} and v != []}
