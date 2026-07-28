"""Lottery Analyst 2.0 — Active Investigation Session (conversation layer only).

Does NOT modify Mathematical Motor, Prompt Maestro, Tabla 1/2, Ranking,
deterministic history tables, or Huawei credentials.
"""

from __future__ import annotations

from app.lottery.ai.active_investigation.evidence_aggregator import EvidenceAggregator
from app.lottery.ai.active_investigation.hermes_decision_engine import (
    HermesDecision,
    HermesDecisionEngine,
)
from app.lottery.ai.active_investigation.natural_response import NaturalResponseGenerator
from app.lottery.ai.active_investigation.session import ActiveInvestigationSession
from app.lottery.ai.active_investigation.session_expiration import SessionExpirationManager
from app.lottery.ai.active_investigation.state_manager import InvestigationStateManager
from app.lottery.ai.active_investigation.trace_logger import ConversationTraceLogger

__all__ = [
    "ActiveInvestigationSession",
    "ConversationTraceLogger",
    "EvidenceAggregator",
    "HermesDecision",
    "HermesDecisionEngine",
    "InvestigationStateManager",
    "NaturalResponseGenerator",
    "SessionExpirationManager",
]
