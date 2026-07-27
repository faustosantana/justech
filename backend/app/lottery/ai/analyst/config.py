"""Runtime configuration for Analista IA research modes (Admin Center → runtime)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


ResearchMode = Literal["quick", "deep", "auto"]
AnalysisDepth = Literal["light", "standard", "deep"]


@dataclass
class AnalystRuntimeConfig:
    max_tools_per_research: int = 6
    max_research_steps: int = 8
    max_tokens: int = 1200
    timeout_seconds: int = 45
    research_mode: ResearchMode = "auto"
    analysis_depth: AnalysisDepth = "standard"
    investigating_message: str = "Estoy investigando…"
    # Hard guardrails — never overridable to False from UI for motor safety
    allow_motor_mutation: bool = False
    allow_ranking_override: bool = False
    allow_invented_stats: bool = False

    def effective_max_tools(self) -> int:
        if self.analysis_depth == "light" or self.research_mode == "quick":
            return min(self.max_tools_per_research, 3)
        if self.analysis_depth == "deep" or self.research_mode == "deep":
            return self.max_tools_per_research
        return self.max_tools_per_research

    def effective_max_steps(self) -> int:
        if self.analysis_depth == "light" or self.research_mode == "quick":
            return min(self.max_research_steps, 3)
        return self.max_research_steps


def load_analyst_config_from_payload(payload: dict[str, Any] | None) -> AnalystRuntimeConfig:
    raw = payload or {}
    research = raw.get("research") if isinstance(raw.get("research"), dict) else {}
    models = raw.get("models") if isinstance(raw.get("models"), dict) else {}

    mode = str(
        research.get("mode")
        or raw.get("research_mode")
        or raw.get("investigation_mode")
        or "auto"
    ).lower()
    if mode in {"investigation", "investigacion"}:
        mode = "deep"
    if mode not in {"quick", "deep", "auto"}:
        mode = "auto"

    depth = str(raw.get("analysis_depth") or research.get("analysis_depth") or "standard").lower()
    if depth in {"light", "ligera", "quick"}:
        depth = "light"
    elif depth in {"deep", "profunda"}:
        depth = "deep"
    else:
        depth = "standard"

    max_tools = int(
        research.get("max_tools_per_research")
        or raw.get("max_tools")
        or raw.get("max_tools_per_query")
        or 6
    )
    max_steps = int(
        research.get("max_research_steps")
        or raw.get("max_steps")
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
        or raw.get("timeout")
        or 45
    )

    return AnalystRuntimeConfig(
        max_tools_per_research=max(1, min(max_tools, 12)),
        max_research_steps=max(1, min(max_steps, 16)),
        max_tokens=max(200, min(max_tokens, 4000)),
        timeout_seconds=max(10, min(timeout, 120)),
        research_mode=mode,  # type: ignore[arg-type]
        analysis_depth=depth,  # type: ignore[arg-type]
        investigating_message=str(
            research.get("investigating_message") or "Estoy investigando…"
        ),
        allow_motor_mutation=False,
        allow_ranking_override=False,
        allow_invented_stats=False,
    )
