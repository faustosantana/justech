"""Quick tests — ConversationProvider factory + orchestrator decoupling."""
from __future__ import annotations

from unittest.mock import patch

from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.conversational_orchestrator.conversation_provider import (
    ConversationProvider,
    HuaweiConversationProvider,
    OpenAIConversationProvider,
    ProviderDecisionResult,
)
from app.lottery.ai.conversational_orchestrator.conversation_provider_factory import (
    build_provider,
    configured_provider_name,
    get_conversation_provider,
)
from app.lottery.ai.conversational_orchestrator.gpt_adapter import GptConversationalOrchestrator


def test_interface_and_implementations():
    assert issubclass(HuaweiConversationProvider, ConversationProvider)
    assert issubclass(OpenAIConversationProvider, ConversationProvider)
    assert hasattr(ConversationProvider, "decide")


def test_factory_default_huawei():
    with patch(
        "app.lottery.ai.conversational_orchestrator.conversation_provider_factory.settings"
    ) as s:
        s.lottery_conversation_provider = "huawei"
        assert configured_provider_name() == "huawei"
        p, meta = get_conversation_provider()
        assert p.name == "huawei"
        assert meta["requested_provider"] == "huawei"


def test_openai_unavailable_falls_back_to_huawei():
    with patch(
        "app.lottery.ai.conversational_orchestrator.conversation_provider_factory.settings"
    ) as s:
        s.lottery_conversation_provider = "openai"
        with patch.object(OpenAIConversationProvider, "available", return_value=False):
            with patch.object(HuaweiConversationProvider, "available", return_value=True):
                p, meta = get_conversation_provider()
    assert p.name == "huawei"
    assert meta["provider_unavailable"] is True
    assert meta["fallback"] == "huawei"
    assert meta["requested_provider"] == "openai"


def test_orchestrator_calls_provider_decide_only():
    """Orchestrator must use provider.decide — no vendor branching in adapter source."""
    from pathlib import Path

    import app.lottery.ai.conversational_orchestrator.gpt_adapter as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "if provider ==" not in src
    assert "huawei_modelarts" not in src
    assert "openai_api_key" not in src
    assert "get_conversation_provider" in src
    assert "provider.decide(" in src


def test_orchestrator_with_mock_provider_decision_ok():
    fake = ProviderDecisionResult(
        content='{"turn_type":"new_investigation","intent":"same_day","subjects":["35","54"],'
        '"relation":"same_day","lottery_scope":[],"position_scope":[],"period_scope":{},'
        '"reuse_asset":false,"asset_id":null,"workspace_action":null,"tool_plan":[],'
        '"needs_clarification":false,"clarification_slot":null,"confidence":0.9,'
        '"reason_codes":["test"]}',
        model="mock",
        usage={"total_tokens": 10},
        provider_name="huawei",
    )

    class _Fake:
        name = "huawei"

        def decide(self, **kwargs):
            return fake

    with patch(
        "app.lottery.ai.conversational_orchestrator.gpt_adapter.get_conversation_provider",
        return_value=(_Fake(), {"provider": "huawei", "requested_provider": "huawei",
                                 "provider_unavailable": False, "fallback": None}),
    ):
        out = GptConversationalOrchestrator.decide(
            "¿Cuándo coincidieron el 35 y el 54?",
            state=ConversationState(),
            investigation=None,
        )
    assert out["schema_valid"] is True
    assert out["decision"]["subjects"] == ["35", "54"]
    assert out["provider"] == "huawei"


def test_build_provider_names():
    assert build_provider("openai").name == "openai"
    assert build_provider("huawei").name == "huawei"
    assert build_provider("unknown").name == "huawei"
