"""AnalystReasoningLayer — Huawei over Evidence Package + Factual Guard."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage
from app.lottery.ai.analyst_reasoning.factual_guard import FactualGuard, GuardResult
from app.lottery.ai.analyst_reasoning.reasoning_modes import (
    ReasoningMode,
    should_invoke_reasoning,
)
from app.lottery.ai.analyst_reasoning.reasoning_prompt import (
    REASONING_PROMPT_VERSION,
    build_reasoning_messages,
)

# Callable: messages, max_tokens -> (text, model_name, usage_dict)
HuaweiCaller = Callable[
    [list[dict[str, str]], int],
    Awaitable[tuple[str | None, str | None, dict[str, Any]]],
]


@dataclass
class ReasoningResult:
    text: str
    used_reasoning: bool
    mode: ReasoningMode
    provider_used: str
    model_used: str | None = None
    guard_passed: bool = True
    rejection_reason: str | None = None
    fallback_used: bool = False
    latency_ms: float | None = None
    evidence_hash: str | None = None
    prompt_version: str = REASONING_PROMPT_VERSION
    input_tokens: int | None = None
    output_tokens: int | None = None
    telemetry: dict[str, Any] = field(default_factory=dict)

    def to_telemetry(self) -> dict[str, Any]:
        return {
            "reasoning_mode": self.mode,
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "evidence_hash": self.evidence_hash,
            "prompt_version": self.prompt_version,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "guard_passed": self.guard_passed,
            "rejection_reason": self.rejection_reason,
            "fallback_used": self.fallback_used,
            "used_reasoning": self.used_reasoning,
        }


class AnalystReasoningLayer:
    """Run selective Huawei analysis over verified evidence."""

    def __init__(self, *, huawei_caller: HuaweiCaller | None = None):
        self.huawei_caller = huawei_caller

    async def run(
        self,
        *,
        package: EvidencePackage,
        mode: ReasoningMode,
        factual_fallback: str,
        max_tokens: int = 1200,
    ) -> ReasoningResult:
        ehash = package.evidence_hash()
        rich_fallback = package.safe_interpretive_text(base_factual=factual_fallback)

        if not should_invoke_reasoning(mode):
            # Skip: keep short template for attribute asks; use rich text only for
            # modes that would have analyzed (handled above). Pure skip stays factual.
            return ReasoningResult(
                text=factual_fallback,
                used_reasoning=False,
                mode=mode or "skip",
                provider_used="local_template",
                guard_passed=True,
                fallback_used=False,
                evidence_hash=ehash,
                telemetry={"skip_reason": "mode_skip_or_factual"},
            )

        if self.huawei_caller is None:
            return ReasoningResult(
                text=rich_fallback,
                used_reasoning=False,
                mode=mode,
                provider_used="local_template",
                fallback_used=True,
                rejection_reason="no_huawei_caller",
                evidence_hash=ehash,
            )

        messages = build_reasoning_messages(package=package, mode=mode)
        t0 = time.perf_counter()
        text, model, usage = await self.huawei_caller(messages, max_tokens)
        latency = (time.perf_counter() - t0) * 1000.0

        if not text:
            return ReasoningResult(
                text=rich_fallback,
                used_reasoning=False,
                mode=mode,
                provider_used="local_template",
                model_used=model,
                fallback_used=True,
                rejection_reason="empty_huawei_response",
                latency_ms=latency,
                evidence_hash=ehash,
                input_tokens=(usage or {}).get("input_tokens"),
                output_tokens=(usage or {}).get("output_tokens"),
            )

        guard: GuardResult = FactualGuard.validate(text, package)
        if not guard.passed:
            return ReasoningResult(
                text=rich_fallback,
                used_reasoning=True,
                mode=mode,
                provider_used="huawei_modelarts",
                model_used=model,
                guard_passed=False,
                rejection_reason=guard.rejection_reason,
                fallback_used=True,
                latency_ms=latency,
                evidence_hash=ehash,
                input_tokens=(usage or {}).get("input_tokens"),
                output_tokens=(usage or {}).get("output_tokens"),
                telemetry={"violations": guard.violations},
            )

        return ReasoningResult(
            text=guard.text,
            used_reasoning=True,
            mode=mode,
            provider_used="huawei_modelarts",
            model_used=model,
            guard_passed=True,
            latency_ms=latency,
            evidence_hash=ehash,
            input_tokens=(usage or {}).get("input_tokens"),
            output_tokens=(usage or {}).get("output_tokens"),
        )
