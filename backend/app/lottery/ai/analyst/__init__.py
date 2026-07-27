"""Fase A / A.1 / B — Analista IA + Research Engine (capa sobre el motor).

No modifica Tabla 1/2, ranking, tiebreak, histórico matemático ni Prompt Maestro v5.
"""

from app.lottery.ai.analyst.config import AnalystRuntimeConfig, load_analyst_config_from_payload
from app.lottery.ai.analyst.conversation_brain import ConversationBrain
from app.lottery.ai.analyst.discovery_engine import DiscoveryEngineStub, get_discovery_engine
from app.lottery.ai.analyst.evidence_engine import EvidenceEngine, EvidencePackage
from app.lottery.ai.analyst.guardrails import AnalystGuardrails
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.question_classifier import QuestionClassifier, ResearchQuestion
from app.lottery.ai.analyst.research_engine import ResearchEngine, get_research_engine
from app.lottery.ai.analyst.research_planner import ResearchPlan, ResearchPlanner
from app.lottery.ai.analyst.research_trace import ResearchTrace
from app.lottery.ai.analyst.response_formatter import format_analyst_response, format_research_response
from app.lottery.ai.analyst.tool_orchestrator import ToolOrchestrator

__all__ = [
    "AnalystGuardrails",
    "AnalystRuntimeConfig",
    "ConversationBrain",
    "DiscoveryEngineStub",
    "EvidenceEngine",
    "EvidencePackage",
    "IntentResolver",
    "QuestionClassifier",
    "ResearchEngine",
    "ResearchPlan",
    "ResearchPlanner",
    "ResearchQuestion",
    "ResearchTrace",
    "ToolOrchestrator",
    "format_analyst_response",
    "format_research_response",
    "get_discovery_engine",
    "get_research_engine",
    "load_analyst_config_from_payload",
]
