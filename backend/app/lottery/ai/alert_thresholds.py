"""Versioned alert-detector thresholds for Lottery IA (not scattered constants)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_ALERT_THRESHOLDS: dict[str, Any] = {
    "provider_down_minutes": 15,
    "fallback_rate_warning": 0.25,
    "fallback_rate_critical": 0.45,
    "error_rate_warning": 0.20,
    "error_rate_critical": 0.40,
    "p95_latency_ms_warning": 8000,
    "p95_latency_ms_critical": 20000,
    "context_loss_rate": 0.15,
    "unnecessary_clarification_rate": 0.30,
    "tool_failure_rate": 0.20,
    "token_daily_limit": 500_000,
    "benchmark_min_score": 0.95,
    "max_p0": 0,
    "max_p1": 0,
    "no_successful_call_minutes": 60,
    "window_days": 7,
    "min_queries_for_rates": 10,
}


def merge_thresholds(payload: dict[str, Any] | None) -> dict[str, Any]:
    out = deepcopy(DEFAULT_ALERT_THRESHOLDS)
    if payload:
        for k, v in payload.items():
            if k in out and v is not None:
                out[k] = v
    return out
