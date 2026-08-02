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
    _resolve_openai_credentials,
    build_provider,
    configured_provider_name,
    get_conversation_provider,
    get_runtime_settings,
    set_runtime_settings_cache,
)
from app.lottery.ai.conversational_orchestrator.gpt_adapter import GptConversationalOrchestrator


def test_interface_and_implementations():
    assert issubclass(HuaweiConversationProvider, ConversationProvider)
    assert issubclass(OpenAIConversationProvider, ConversationProvider)
    assert hasattr(ConversationProvider, "decide")


def test_factory_reads_runtime_cache_not_env():
    set_runtime_settings_cache(
        {
            "conversation_provider": "huawei",
            "conversation_model": "deepseek-v4-flash",
            "temperature": 0.0,
            "max_tokens": 700,
            "timeout_seconds": 45,
        }
    )
    assert configured_provider_name() == "huawei"
    p, meta = get_conversation_provider()
    assert p.name == "huawei"
    assert meta["requested_provider"] == "huawei"
    assert meta["source"] == "lottery_ai_settings"
    assert meta["model"] == "deepseek-v4-flash"


def test_openai_unavailable_falls_back_to_huawei():
    set_runtime_settings_cache(
        {
            "conversation_provider": "openai",
            "conversation_model": "gpt-4o",
            "temperature": 0.0,
            "max_tokens": 700,
            "timeout_seconds": 45,
        }
    )
    with patch.object(OpenAIConversationProvider, "available", return_value=False):
        with patch.object(HuaweiConversationProvider, "available", return_value=True):
            p, meta = get_conversation_provider()
    assert p.name == "huawei"
    assert meta["provider_unavailable"] is True
    assert meta["fallback"] == "huawei"
    assert meta["requested_provider"] == "openai"


def test_orchestrator_calls_provider_decide_only():
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
        return_value=(
            _Fake(),
            {
                "provider": "huawei",
                "requested_provider": "huawei",
                "provider_unavailable": False,
                "fallback": None,
                "temperature": 0.0,
                "max_tokens": 700,
            },
        ),
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


def test_runtime_settings_never_exposes_encrypted_key():
    set_runtime_settings_cache(
        {
            "conversation_provider": "openai",
            "conversation_model": "gpt-4o",
            "openai_api_key_encrypted": "gAAAA_fake_ciphertext",
            "openai_base_url": "https://api.openai.com/v1",
        }
    )
    pub = get_runtime_settings()
    assert "openai_api_key_encrypted" not in pub
    assert pub["openai_key_configured"] is True


def test_resolve_openai_credentials_prefers_form_then_db_then_env():
    set_runtime_settings_cache(
        {
            "openai_api_key_encrypted": None,
            "openai_base_url": "https://api.openai.com/v1",
        }
    )
    key, _, _, _, source = _resolve_openai_credentials(api_key_override="sk-form-key")
    assert key == "sk-form-key"
    assert source == "form"

    with patch(
        "app.lottery.ai.conversational_orchestrator.conversation_provider_factory.decrypt_secret",
        return_value="sk-db-key",
    ):
        set_runtime_settings_cache({"openai_api_key_encrypted": "enc-blob"})
        key, _, _, _, source = _resolve_openai_credentials()
        assert key == "sk-db-key"
        assert source == "database"

    set_runtime_settings_cache({"openai_api_key_encrypted": None})
    with patch(
        "app.lottery.ai.conversational_orchestrator.conversation_provider_factory.settings"
    ) as mock_settings:
        mock_settings.openai_api_key = "sk-env-key"
        mock_settings.openai_base_url = "https://api.openai.com/v1"
        key, _, _, _, source = _resolve_openai_credentials()
        assert key == "sk-env-key"
        assert source == "environment"
