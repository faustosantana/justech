"""Select ConversationProvider from Lottery AI Settings (DB/cache) — never ENV."""
from __future__ import annotations

from typing import Any

from app.lottery.ai.conversational_orchestrator.conversation_provider import (
    ConversationProvider,
    HuaweiConversationProvider,
    OpenAIConversationProvider,
)

_VALID = frozenset({"huawei", "openai"})

# Process-local cache refreshed on get/save/test — no service restart needed.
_RUNTIME_SETTINGS: dict[str, Any] = {
    "conversation_provider": "huawei",
    "conversation_model": "deepseek-v4-flash",
    "temperature": 0.0,
    "max_tokens": 700,
    "timeout_seconds": 45,
}


def set_runtime_settings_cache(data: dict[str, Any] | None) -> None:
    if not data:
        return
    _RUNTIME_SETTINGS["conversation_provider"] = str(
        data.get("conversation_provider") or "huawei"
    ).strip().lower()
    _RUNTIME_SETTINGS["conversation_model"] = str(
        data.get("conversation_model") or "deepseek-v4-flash"
    ).strip()
    try:
        _RUNTIME_SETTINGS["temperature"] = float(data.get("temperature", 0.0))
    except (TypeError, ValueError):
        _RUNTIME_SETTINGS["temperature"] = 0.0
    try:
        _RUNTIME_SETTINGS["max_tokens"] = int(data.get("max_tokens", 700))
    except (TypeError, ValueError):
        _RUNTIME_SETTINGS["max_tokens"] = 700
    try:
        _RUNTIME_SETTINGS["timeout_seconds"] = int(data.get("timeout_seconds", 45))
    except (TypeError, ValueError):
        _RUNTIME_SETTINGS["timeout_seconds"] = 45


def get_runtime_settings() -> dict[str, Any]:
    return dict(_RUNTIME_SETTINGS)


def configured_provider_name() -> str:
    name = str(_RUNTIME_SETTINGS.get("conversation_provider") or "huawei").strip().lower()
    return name if name in _VALID else "huawei"


def build_provider(
    name: str,
    *,
    model: str | None = None,
    timeout_sec: float | None = None,
) -> ConversationProvider:
    model_s = model or str(_RUNTIME_SETTINGS.get("conversation_model") or "")
    timeout = float(
        timeout_sec
        if timeout_sec is not None
        else _RUNTIME_SETTINGS.get("timeout_seconds") or 45
    )
    if name == "openai":
        return OpenAIConversationProvider(model=model_s or None, timeout_sec=timeout)
    return HuaweiConversationProvider(model=model_s or None, timeout_sec=timeout)


def get_conversation_provider() -> tuple[ConversationProvider, dict[str, Any]]:
    """Return (provider, meta) from DB-backed runtime cache.

    If configured provider is openai but unavailable → Huawei with
    provider_unavailable=true and fallback=huawei (conversation stays up).
    """
    requested = configured_provider_name()
    model = str(_RUNTIME_SETTINGS.get("conversation_model") or "")
    timeout = float(_RUNTIME_SETTINGS.get("timeout_seconds") or 45)
    primary = build_provider(requested, model=model, timeout_sec=timeout)
    meta: dict[str, Any] = {
        "requested_provider": requested,
        "provider": primary.name,
        "model": model,
        "temperature": float(_RUNTIME_SETTINGS.get("temperature") or 0),
        "max_tokens": int(_RUNTIME_SETTINGS.get("max_tokens") or 700),
        "timeout_seconds": int(timeout),
        "provider_unavailable": False,
        "fallback": None,
        "source": "lottery_ai_settings",
    }
    if primary.available():
        return primary, meta

    meta["provider_unavailable"] = True
    if requested == "openai":
        fallback = build_provider("huawei", model=None, timeout_sec=timeout)
        meta["fallback"] = "huawei"
        meta["provider"] = fallback.name
        return fallback, meta

    meta["fallback"] = None
    return primary, meta
