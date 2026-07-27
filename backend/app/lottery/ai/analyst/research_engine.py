"""Research Engine — architecture stub for future automatic discovery (Fase A.1).

NOT implemented yet. This module only declares the future contract so planners
and docs can reference stable extension points without changing the motor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ResearchQuestion:
    """Future high-level research question (discovery layer — not active)."""

    kind: str
    # Examples of future kinds (reserved):
    # - what_usually_happens_after
    # - which_lottery_confirms_first
    # - which_confirms_most
    # - most_frequent_pattern
    # - best_historical_group
    params: dict[str, Any] = field(default_factory=dict)
    requires_discovery: bool = True


class ResearchEngine(Protocol):
    """Future protocol — do not call from production chat yet."""

    def can_handle(self, question: ResearchQuestion) -> bool: ...

    def prepare(self, question: ResearchQuestion, context: dict[str, Any]) -> dict[str, Any]: ...


class ResearchEngineStub:
    """Placeholder. Automatic discovery is intentionally disabled."""

    ENABLED = False
    SUPPORTED_KINDS = (
        "what_usually_happens_after",
        "which_lottery_confirms_first",
        "which_confirms_most",
        "most_frequent_pattern",
        "best_historical_group",
    )

    def can_handle(self, question: ResearchQuestion) -> bool:
        return False

    def prepare(self, question: ResearchQuestion, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "not_implemented",
            "enabled": False,
            "kind": question.kind,
            "message": (
                "Research Engine preparado arquitectónicamente. "
                "El descubrimiento automático aún no está activo."
            ),
            "supported_kinds": list(self.SUPPORTED_KINDS),
            "context_keys": list((context or {}).keys())[:20],
        }


def get_research_engine() -> ResearchEngineStub:
    return ResearchEngineStub()
