"""Fase A / A.1 / B / C / D / E — Analista IA + Research + Discovery + Knowledge.

No modifica Tabla 1/2, ranking, tiebreak, histórico matemático ni Prompt Maestro v5.
"""

from app.lottery.ai.analyst.config import AnalystRuntimeConfig, load_analyst_config_from_payload
from app.lottery.ai.analyst.conversation_brain import ConversationBrain
from app.lottery.ai.analyst.discovery_engine import (
    DiscoveryEngine,
    DiscoveryEngineStub,
    DiscoveryFinding,
    DiscoveryRequest,
    DiscoveryResult,
    FindingValidator,
    get_discovery_engine,
)
from app.lottery.ai.analyst.discovery_store import get_discovery_store
from app.lottery.ai.analyst.evidence_engine import EvidenceEngine, EvidencePackage
from app.lottery.ai.analyst.guardrails import AnalystGuardrails
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.knowledge_engine import (
    KnowledgeEngine,
    KnowledgeSaveRequest,
    KnowledgeSearchQuery,
    get_knowledge_engine,
)
from app.lottery.ai.analyst.knowledge_store import KnowledgeRecord, get_knowledge_store
from app.lottery.ai.analyst.question_classifier import QuestionClassifier, ResearchQuestion
from app.lottery.ai.analyst.research_engine import ResearchEngine, get_research_engine
from app.lottery.ai.analyst.research_planner import ResearchPlan, ResearchPlanner
from app.lottery.ai.analyst.research_trace import ResearchTrace
from app.lottery.ai.analyst.response_formatter import (
    format_analyst_response,
    format_research_response,
    render_bar,
    render_ranking_bars,
    select_response_mode,
)
from app.lottery.ai.analyst.tool_orchestrator import ToolOrchestrator

__all__ = [
    "AnalystGuardrails",
    "AnalystRuntimeConfig",
    "ConversationBrain",
    "DiscoveryEngine",
    "DiscoveryEngineStub",
    "DiscoveryFinding",
    "DiscoveryRequest",
    "DiscoveryResult",
    "EvidenceEngine",
    "EvidencePackage",
    "FindingValidator",
    "IntentResolver",
    "KnowledgeEngine",
    "KnowledgeRecord",
    "KnowledgeSaveRequest",
    "KnowledgeSearchQuery",
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
    "get_discovery_store",
    "get_knowledge_engine",
    "get_knowledge_store",
    "render_bar",
    "render_ranking_bars",
    "select_response_mode",
    "get_research_engine",
    "load_analyst_config_from_payload",
]
