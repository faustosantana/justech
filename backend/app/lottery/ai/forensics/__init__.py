"""Lottery chat forensic tracing (opt-in; default off)."""

from app.lottery.ai.forensics.context import (
    get_correlation_id,
    new_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)
from app.lottery.ai.forensics.service import ForensicTraceService

__all__ = [
    "ForensicTraceService",
    "get_correlation_id",
    "new_correlation_id",
    "reset_correlation_id",
    "set_correlation_id",
]
