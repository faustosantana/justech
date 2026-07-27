"""Discovery Engine — architecture stub only (Fase B §15).

NOT implemented. Reserved extension points for a future phase:
automatic discovery, findings, observations, hypotheses, auto-reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class DiscoveryRequest:
    kind: str
    # Reserved future kinds:
    # - auto_discovery
    # - findings_digest
    # - observation
    # - hypothesis
    # - auto_report
    params: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryResult:
    status: str = "not_implemented"
    enabled: bool = False
    kind: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class DiscoveryEngine(Protocol):
    def can_discover(self, request: DiscoveryRequest) -> bool: ...

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult: ...


class DiscoveryEngineStub:
    """Placeholder — automatic discovery intentionally disabled."""

    ENABLED = False
    SUPPORTED_KINDS = (
        "auto_discovery",
        "findings_digest",
        "observation",
        "hypothesis",
        "auto_report",
    )

    def can_discover(self, request: DiscoveryRequest) -> bool:
        return False

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        return DiscoveryResult(
            status="not_implemented",
            enabled=False,
            kind=request.kind,
            payload={
                "message": (
                    "Discovery Engine preparado arquitectónicamente. "
                    "El descubrimiento automático aún no está activo."
                ),
                "supported_kinds": list(self.SUPPORTED_KINDS),
            },
        )


def get_discovery_engine() -> DiscoveryEngineStub:
    return DiscoveryEngineStub()
