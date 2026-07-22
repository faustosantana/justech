"""Circuit breaker for lottery scheduler / source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.config import settings

CircuitState = Literal["closed", "open", "half_open"]


@dataclass
class CircuitDecision:
    state: CircuitState
    allow_tick: bool
    allow_write: bool
    reason: str | None = None


def evaluate_circuit(
    *,
    state: str,
    consecutive_failures: int,
    opened_at: datetime | None = None,
) -> CircuitDecision:
    st = (state or "closed").lower()
    threshold = settings.lottery_sync_circuit_failure_threshold
    if st == "open":
        # Half-open probe after 10 minutes
        if opened_at and (datetime.now(timezone.utc) - opened_at).total_seconds() >= 600:
            return CircuitDecision("half_open", True, False, "half_open_probe")
        return CircuitDecision("open", False, False, "circuit_open")
    if st == "half_open":
        return CircuitDecision("half_open", True, False, "half_open_observe_only")
    if consecutive_failures >= threshold:
        return CircuitDecision("open", False, False, "failure_threshold")
    return CircuitDecision("closed", True, True, None)


def next_state_after_success(current: str) -> str:
    return "closed"


def next_state_after_failure(current: str, consecutive_failures: int) -> str:
    if consecutive_failures >= settings.lottery_sync_circuit_failure_threshold:
        return "open"
    if (current or "").lower() == "half_open":
        return "open"
    return "closed"
