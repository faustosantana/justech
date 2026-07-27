"""Fase A / A.1 — Analista IA profesional (capa conversacional sobre el motor).

No modifica Tabla 1/2, ranking, tiebreak, histórico matemático ni Prompt Maestro v5.
"""

from app.lottery.ai.analyst.config import AnalystRuntimeConfig, load_analyst_config_from_payload
from app.lottery.ai.analyst.conversation_brain import ConversationBrain
from app.lottery.ai.analyst.guardrails import AnalystGuardrails
from app.lottery.ai.analyst.intent_resolver import IntentResolver
from app.lottery.ai.analyst.research_engine import ResearchEngineStub, get_research_engine
from app.lottery.ai.analyst.research_planner import ResearchPlan, ResearchPlanner
from app.lottery.ai.analyst.research_trace import ResearchTrace
from app.lottery.ai.analyst.response_formatter import format_analyst_response
from app.lottery.ai.analyst.tool_orchestrator import ToolOrchestrator

__all__ = [
    "AnalystGuardrails",
    "AnalystRuntimeConfig",
    "ConversationBrain",
    "IntentResolver",
    "ResearchEngineStub",
    "ResearchPlan",
    "ResearchPlanner",
    "ResearchTrace",
    "ToolOrchestrator",
    "format_analyst_response",
    "get_research_engine",
    "load_analyst_config_from_payload",
]
