"""Conversational orchestrator A/B — Hermes vs GPT (structured decisions only)."""

from app.lottery.ai.conversational_orchestrator.conversation_provider import (
    ConversationProvider,
    HuaweiConversationProvider,
    OpenAIConversationProvider,
)
from app.lottery.ai.conversational_orchestrator.conversation_provider_factory import (
    get_conversation_provider,
)
from app.lottery.ai.conversational_orchestrator.gpt_adapter import GptConversationalOrchestrator
from app.lottery.ai.conversational_orchestrator.schema import OrchestratorDecision
from app.lottery.ai.conversational_orchestrator.shadow import (
    maybe_apply_gpt_decision,
    orchestrator_mode,
    run_gpt_shadow,
)

__all__ = [
    "ConversationProvider",
    "HuaweiConversationProvider",
    "OpenAIConversationProvider",
    "get_conversation_provider",
    "GptConversationalOrchestrator",
    "OrchestratorDecision",
    "maybe_apply_gpt_decision",
    "orchestrator_mode",
    "run_gpt_shadow",
]
