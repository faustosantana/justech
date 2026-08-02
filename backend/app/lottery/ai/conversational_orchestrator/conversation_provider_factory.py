"""Select ConversationProvider from ENV — orchestrator never branches on vendor."""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.lottery.ai.conversational_orchestrator.conversation_provider import (
    ConversationProvider,
    HuaweiConversationProvider,
    OpenAIConversationProvider,
)

_VALID = frozenset({"huawei", "openai"})


def configured_provider_name() -> str:
    raw = (
        getattr(settings, "lottery_conversation_provider", None)
        or "huawei"
    )
    name = str(raw).strip().lower()
    return name if name in _VALID else "huawei"


def build_provider(name: str) -> ConversationProvider:
    if name == "openai":
        return OpenAIConversationProvider()
    return HuaweiConversationProvider()


def get_conversation_provider() -> tuple[ConversationProvider, dict[str, Any]]:
    """Return (provider, meta).

    If configured provider is openai but unavailable → Huawei with
    provider_unavailable=true and fallback=huawei.
    """
    requested = configured_provider_name()
    primary = build_provider(requested)
    meta: dict[str, Any] = {
        "requested_provider": requested,
        "provider": primary.name,
        "provider_unavailable": False,
        "fallback": None,
    }
    if primary.available():
        return primary, meta

    # Requested provider missing credentials
    meta["provider_unavailable"] = True
    if requested == "openai":
        fallback = HuaweiConversationProvider()
        meta["fallback"] = "huawei"
        meta["provider"] = fallback.name
        return fallback, meta

    # Huawei itself unavailable — return it anyway; decide() will report unavailable
    meta["fallback"] = None
    return primary, meta
