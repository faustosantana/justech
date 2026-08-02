"""Live chat must honor Lottery AI Settings provider (single factory)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.lottery.ai.conversational_orchestrator.conversation_provider_factory import (
    complete_with_lottery_provider,
    get_lottery_conversation_provider,
    get_runtime_settings,
    invalidate_provider_cache,
    set_runtime_settings_cache,
)
from app.lottery.ai.conversational_orchestrator.conversation_provider import (
    OpenAIConversationProvider,
    ProviderDecisionResult,
)


def test_openai_active_in_db_selects_openai_provider():
    set_runtime_settings_cache(
        {
            "conversation_provider": "openai",
            "conversation_model": "gpt-4o-mini",
            "openai_api_key_encrypted": "enc",
            "timeout_seconds": 45,
        }
    )
    with patch(
        "app.lottery.ai.conversational_orchestrator.conversation_provider_factory.decrypt_secret",
        return_value="sk-test",
    ):
        provider, meta = get_lottery_conversation_provider(allow_fallback=False)
    assert provider.name == "openai"
    assert meta["selected_provider"] == "openai"
    assert meta["provider_used"] == "openai"
    assert meta["selected_model"] == "gpt-4o-mini"
    assert meta["provider_config_source"] == "database"
    assert meta["credential_source"] == "database"


def test_huawei_active_in_db_selects_huawei_provider():
    set_runtime_settings_cache(
        {
            "conversation_provider": "huawei",
            "conversation_model": "deepseek-v4-flash",
            "timeout_seconds": 45,
        }
    )
    provider, meta = get_lottery_conversation_provider(allow_fallback=False)
    assert provider.name == "huawei"
    assert meta["selected_provider"] == "huawei"
    assert meta["provider_used"] == "huawei_modelarts"


def test_provider_change_invalidates_cache_version():
    set_runtime_settings_cache(
        {"conversation_provider": "huawei", "conversation_model": "deepseek-v4-flash"}
    )
    v1 = get_runtime_settings()["cache_version"]
    invalidate_provider_cache()
    v2 = get_runtime_settings()["cache_version"]
    assert v2 > v1
    set_runtime_settings_cache(
        {
            "conversation_provider": "openai",
            "conversation_model": "gpt-4o-mini",
            "openai_api_key_encrypted": "enc",
        }
    )
    v3 = get_runtime_settings()["cache_version"]
    assert v3 > v2


def test_without_db_config_compatible_default_is_huawei():
    # Fresh-ish defaults via explicit huawei cache (simulates no openai row)
    set_runtime_settings_cache(
        {"conversation_provider": "huawei", "conversation_model": "deepseek-v4-flash"}
    )
    provider, meta = get_lottery_conversation_provider(allow_fallback=True)
    assert provider.name == "huawei"
    assert meta["selected_provider"] == "huawei"


def test_selected_provider_matches_provider_used_label():
    set_runtime_settings_cache(
        {
            "conversation_provider": "openai",
            "conversation_model": "gpt-4o-mini",
            "openai_api_key_encrypted": "enc",
        }
    )
    with patch(
        "app.lottery.ai.conversational_orchestrator.conversation_provider_factory.decrypt_secret",
        return_value="sk-test",
    ):
        provider, meta = get_lottery_conversation_provider(allow_fallback=False)
    assert meta["selected_provider"] == "openai"
    assert meta["provider_used"] == provider.name == "openai"


def test_no_silent_fallback_when_openai_available():
    set_runtime_settings_cache(
        {
            "conversation_provider": "openai",
            "conversation_model": "gpt-4o-mini",
            "openai_api_key_encrypted": "enc",
        }
    )
    with patch(
        "app.lottery.ai.conversational_orchestrator.conversation_provider_factory.decrypt_secret",
        return_value="sk-test",
    ):
        provider, meta = get_lottery_conversation_provider(allow_fallback=False)
    assert provider.name == "openai"
    assert meta.get("fallback_used") is False
    assert meta.get("fallback") is None


def test_ui_and_chat_share_same_factory_entrypoint():
    from app.lottery.ai.conversational_orchestrator import (
        complete_with_lottery_provider as exported_complete,
        get_lottery_conversation_provider as exported_get,
    )
    from app.lottery.ai.conversational_orchestrator.conversation_provider_factory import (
        complete_with_lottery_provider as factory_complete,
        get_lottery_conversation_provider as factory_get,
    )

    assert exported_get is factory_get
    assert exported_complete is factory_complete


def test_complete_with_lottery_provider_uses_openai_decide():
    set_runtime_settings_cache(
        {
            "conversation_provider": "openai",
            "conversation_model": "gpt-4o-mini",
            "openai_api_key_encrypted": "enc",
            "temperature": 0.0,
            "max_tokens": 200,
        }
    )
    fake = ProviderDecisionResult(
        content="respuesta de prueba suficientemente larga para pasar filtros",
        model="gpt-4o-mini",
        usage={"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        provider_name="openai",
        latency_ms=12.0,
    )
    with patch(
        "app.lottery.ai.conversational_orchestrator.conversation_provider_factory.decrypt_secret",
        return_value="sk-test",
    ):
        with patch.object(OpenAIConversationProvider, "decide", return_value=fake) as decide:
            text, model, usage, meta = complete_with_lottery_provider(
                [{"role": "user", "content": "Hola"}],
                max_tokens=200,
                allow_fallback=False,
            )
    assert text and "prueba" in text
    assert model == "gpt-4o-mini"
    assert meta["provider_used"] == "openai"
    assert meta["credential_source"] == "database"
    assert decide.called
