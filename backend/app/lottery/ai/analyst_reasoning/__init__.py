"""Lottery Analyst 2.1 — Analyst Reasoning Layer.

Huawei analyzes a verified Evidence Package only.
Does NOT choose tools, invent facts, or modify Prompt Maestro / Motor / SQL.
"""

from __future__ import annotations

from app.lottery.ai.analyst_reasoning.evidence_package import (
    EvidencePackage,
    EvidencePackageBuilder,
)
from app.lottery.ai.analyst_reasoning.factual_guard import FactualGuard, GuardResult
from app.lottery.ai.analyst_reasoning.reasoning_layer import AnalystReasoningLayer, ReasoningResult
from app.lottery.ai.analyst_reasoning.reasoning_modes import (
    ReasoningMode,
    ReasoningModeSelector,
    should_invoke_reasoning,
)

__all__ = [
    "AnalystReasoningLayer",
    "EvidencePackage",
    "EvidencePackageBuilder",
    "FactualGuard",
    "GuardResult",
    "ReasoningMode",
    "ReasoningModeSelector",
    "ReasoningResult",
    "should_invoke_reasoning",
]
