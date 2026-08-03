"""Conversation settings — form test vs active, public mask, activation cache."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.lottery.ai.conversational_orchestrator.conversation_provider import (
    ProviderDecisionResult,
)
from app.lottery.ai.conversational_orchestrator.conversation_provider_factory import (
    get_lottery_conversation_provider,
    get_runtime_settings,
    set_runtime_settings_cache,
)
from app.services.lottery_ai_conversation_settings_service import (
    SUGGESTED_MODELS,
    LotteryAiConversationSettingsService,
    _mask_openai_key,
    _public_dict,
)


def _row(**kwargs):
    base = dict(
        id=uuid4(),
        conversation_provider="huawei",
        conversation_model="deepseek-v4-flash",
        temperature=0.0,
        max_tokens=700,
        timeout_seconds=45,
        is_active=True,
        openai_api_key_encrypted=None,
        openai_base_url="https://api.openai.com/v1",
        openai_organization=None,
        openai_project=None,
        credential_updated_at=None,
        credential_updated_by=None,
        last_test_at=None,
        last_test_ok=None,
        last_test_latency_ms=None,
        last_test_model=None,
        last_test_error=None,
        last_test_message=None,
        updated_by=None,
        updated_at=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_mask_never_full_key():
    masked = _mask_openai_key("sk-abcdefghijklmnopqrstuvwxyz")
    assert masked is not None
    assert "abcdefghijklmnopqrstuvwxyz" not in masked
    assert masked.startswith("sk-")
    assert "••••" in masked


def test_public_dict_excludes_secrets():
    row = _row(
        conversation_provider="openai",
        conversation_model="gpt-4o-mini",
        openai_api_key_encrypted="cipher-blob",
    )
    with patch(
        "app.services.lottery_ai_conversation_settings_service.decrypt_secret",
        return_value="sk-live-secret-key-9999",
    ):
        pub = _public_dict(row)  # type: ignore[arg-type]
    blob = str(pub)
    assert "sk-live-secret-key-9999" not in blob
    assert "cipher-blob" not in blob
    assert pub["openai_key_configured"] is True
    assert pub["key_configured"] is True
    assert pub["credential_source"] == "database"
    assert "openai_api_key" not in pub
    assert "openai_api_key_encrypted" not in pub
    assert pub["models_for_provider"]["huawei"] == SUGGESTED_MODELS["huawei"]
    assert "gpt-4o-mini" in pub["models_for_provider"]["openai"]
    assert "deepseek-v4-flash" not in pub["models_for_provider"]["openai"]


@pytest.mark.asyncio
async def test_connection_uses_form_provider_not_active():
    """Active=Huawei; form=OpenAI → probe.provider must be openai."""
    row = _row()
    db = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    svc = LotteryAiConversationSettingsService(db=db, user_id=uuid4())
    svc._active_row = AsyncMock(return_value=row)  # type: ignore[method-assign]

    fake = ProviderDecisionResult(
        content='{"turn_type":"social_chitchat","subjects":[],"intent":"chitchat","confidence":1}',
        model="gpt-4o-mini",
        provider_name="openai",
        latency_ms=11.0,
    )
    fake_provider = MagicMock()
    fake_provider.available.return_value = True
    fake_provider.decide.return_value = fake
    fake_provider.credential_source = "form"
    fake_provider.name = "openai"

    set_runtime_settings_cache(
        {"conversation_provider": "huawei", "conversation_model": "deepseek-v4-flash"}
    )

    with patch.object(svc, "_build_for_test", return_value=fake_provider) as build:
        result = await svc.test_connection(
            {
                "conversation_provider": "openai",
                "conversation_model": "gpt-4o-mini",
                "openai_api_key": "sk-test-form-key",
                "temperature": 0,
                "max_tokens": 400,
                "timeout_seconds": 45,
            }
        )

    assert build.call_args[0][0]["conversation_provider"] == "openai"
    assert build.call_args[0][0]["conversation_model"] == "gpt-4o-mini"
    assert result["provider"] == "openai"
    assert result["model"] == "gpt-4o-mini"
    assert result["tested_from"] == "form"
    assert result["active_provider"] == "huawei"
    assert result["credential_source"] == "form"
    # Live chat cache must remain Huawei after a draft OpenAI test
    rt = get_runtime_settings()
    assert rt["conversation_provider"] == "huawei"


@pytest.mark.asyncio
async def test_save_activates_openai_and_updates_cache():
    row_prev = _row()
    db = MagicMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    svc = LotteryAiConversationSettingsService(db=db, user_id=uuid4())
    svc._active_row = AsyncMock(return_value=row_prev)  # type: ignore[method-assign]

    probe_ok = {
        "ok": True,
        "provider": "openai",
        "model": "gpt-4o-mini",
        "latency_ms": 9,
        "message_received": "{}",
        "credential_source": "form",
    }
    with patch.object(svc, "test_connection", AsyncMock(return_value=probe_ok)):
        with patch(
            "app.services.lottery_ai_conversation_settings_service.encrypt_secret",
            return_value="enc-blob",
        ):
            async def _refresh(obj):
                obj.updated_at = None
                if not hasattr(obj, "last_test_message"):
                    obj.last_test_message = None

            db.refresh = AsyncMock(side_effect=_refresh)
            out = await svc.save(
                {
                    "conversation_provider": "openai",
                    "conversation_model": "gpt-4o-mini",
                    "openai_api_key": "sk-new-key-xxxx",
                    "temperature": 0,
                    "max_tokens": 700,
                    "timeout_seconds": 45,
                },
                require_test_ok=True,
            )

    settings = out["settings"]
    assert settings["conversation_provider"] == "openai"
    assert settings["conversation_model"] == "gpt-4o-mini"
    assert "sk-new-key" not in str(settings)
    rt = get_runtime_settings()
    assert rt["conversation_provider"] == "openai"
    assert rt["conversation_model"] == "gpt-4o-mini"
    assert rt["openai_key_configured"] is True

    with patch(
        "app.lottery.ai.conversational_orchestrator.conversation_provider_factory.decrypt_secret",
        return_value="sk-new-key-xxxx",
    ):
        provider, meta = get_lottery_conversation_provider(allow_fallback=False)
    assert provider.name == "openai"
    assert meta["provider_used"] == "openai"
    assert meta.get("fallback_used") is False


@pytest.mark.asyncio
async def test_list_openai_models_never_returns_huawei():
    row = _row(openai_api_key_encrypted="enc")
    svc = LotteryAiConversationSettingsService(db=MagicMock(), user_id=uuid4())
    svc._active_row = AsyncMock(return_value=row)  # type: ignore[method-assign]

    fake_provider = MagicMock()
    fake_provider.available.return_value = True
    fake_provider._api_key = "sk-x"
    fake_provider.credential_source = "database"

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {"id": "gpt-4o-mini"},
                    {"id": "gpt-4o"},
                    {"id": "whisper-1"},
                ]
            }

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **k):
            return _Resp()

    with patch(
        "app.services.lottery_ai_conversation_settings_service.build_provider",
        return_value=fake_provider,
    ):
        with patch(
            "app.services.lottery_ai_conversation_settings_service.httpx.Client",
            _Client,
        ):
            data = await svc.list_openai_models({})

    assert data["provider"] == "openai"
    assert all("deepseek" not in m.lower() for m in data["models"])
    assert "gpt-4o-mini" in data["models"]
