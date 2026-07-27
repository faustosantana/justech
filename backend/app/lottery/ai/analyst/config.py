"""Runtime configuration for Analista IA research modes (Admin Center)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


ResearchMode = Literal["quick", "deep", "auto"]


@dataclass
class AnalystRuntimeConfig:
    max_tools_per_research: int = 6
    max_research_steps: int = 8
    max_tokens: int = 1200
    timeout_seconds: int = 45
    research_mode: ResearchMode = "auto"
    investigating_message: str = "Estoy investigando…"
    # Hard guardrails — never overridable to False from UI for motor safety
    allow_motor_mutation: bool = False
    allow_ranking_override: bool = False
    allow_invented_stats: bool = False


def load_analyst_config_from_payload(payload: dict[str, Any] | None) -> AnalystRuntimeConfig:
    raw = payload or {}
    research = raw.get("research") if isinstance(raw.get("research"), dict) else {}
    models = raw.get("models") if isinstance(raw.get("models"), dict) else {}

    mode = str(research.get("mode") or raw.get("research_mode") or "auto").lower()
    if mode not in {"quick", "deep", "auto"}:
        mode = "auto"

    max_tools = int(
        research.get("max_tools_per_research")
        or raw.get("max_tools_per_query")
        or 6
    )
    max_steps = int(
        research.get("max_research_steps")
        or raw.get("max_planner_steps")
        or 8
    )
    max_tokens = int(
        research.get("max_tokens")
        or models.get("max_tokens")
        or raw.get("max_tokens")
        or 1200
    )
    timeout = int(
        research.get("timeout_seconds")
        or models.get("timeout_seconds")
        or raw.get("timeout_seconds")
        or 45
    )

    return AnalystRuntimeConfig(
        max_tools_per_research=max(1, min(max_tools, 12)),
        max_research_steps=max(1, min(max_steps, 16)),
        max_tokens=max(200, min(max_tokens, 4000)),
        timeout_seconds=max(10, min(timeout, 120)),
        research_mode=mode,  # type: ignore[arg-type]
        investigating_message=str(
            research.get("investigating_message") or "Estoy investigando…"
        ),
        allow_motor_mutation=False,
        allow_ranking_override=False,
        allow_invented_stats=False,
    )
