"""Conversation LLM providers — transport only. Orchestrator never branches on vendor."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings


@dataclass
class ProviderDecisionResult:
    """Raw completion from a conversation provider (text + usage)."""

    content: str = ""
    model: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    provider_name: str = ""
    provider_unavailable: bool = False
    error: str | None = None
    latency_ms: float = 0.0


class ConversationProvider(ABC):
    """Vendor-agnostic interface for structured orchestrator completions."""

    name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """True when credentials/endpoint are configured."""

    @abstractmethod
    def decide(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | str | None,
        temperature: float,
        max_tokens: int,
    ) -> ProviderDecisionResult:
        """Return model text. Must not invent tooling / SQL / evidence."""


def _chat_completions_url(base_or_full: str) -> str:
    url = (base_or_full or "").rstrip("/")
    if not url:
        return ""
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return url + "/chat/completions"
    if "/chat/completions" in url:
        return url
    return url + "/v1/chat/completions"


def _post_chat_completions(
    *,
    url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    provider_name: str,
    timeout_sec: float = 45.0,
) -> ProviderDecisionResult:
    import time

    if not url or not api_key:
        return ProviderDecisionResult(
            provider_name=provider_name,
            provider_unavailable=True,
            error="provider_unavailable",
        )
    t0 = time.perf_counter()
    # Merge system + messages (OpenAI-compatible chat format)
    chat_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for m in messages or []:
        role = str(m.get("role") or "user")
        content = str(m.get("content") or "")
        if role == "system":
            # already set — append as user context to avoid double-system edge cases
            chat_messages.append({"role": "user", "content": content})
        else:
            chat_messages.append({"role": role, "content": content})
    body: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": chat_messages,
    }
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        content = (
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        )
        usage = data.get("usage") or {}
        return ProviderDecisionResult(
            content=str(content),
            model=model,
            usage={
                "prompt_tokens": usage.get("prompt_tokens") or usage.get("input_tokens") or 0,
                "completion_tokens": usage.get("completion_tokens")
                or usage.get("output_tokens")
                or 0,
                "total_tokens": usage.get("total_tokens") or 0,
            },
            provider_name=provider_name,
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
        )
    except Exception as e:  # noqa: BLE001
        return ProviderDecisionResult(
            provider_name=provider_name,
            error=f"llm_call_failed:{type(e).__name__}:{str(e)[:180]}",
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
        )


class HuaweiConversationProvider(ConversationProvider):
    name = "huawei"

    def __init__(self, model: str | None = None, timeout_sec: float = 45.0) -> None:
        self.model = (model or "").strip() or None
        self.timeout_sec = float(timeout_sec or 45.0)

    def available(self) -> bool:
        url = (getattr(settings, "hermes_model_api_url", None) or "").strip()
        key = (getattr(settings, "hermes_model_api_key", None) or "").strip()
        return bool(url and key)

    def decide(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | str | None,
        temperature: float,
        max_tokens: int,
    ) -> ProviderDecisionResult:
        # schema reserved for future JSON-mode / response_format wiring
        _ = schema
        if not self.available():
            return ProviderDecisionResult(
                provider_name=self.name,
                provider_unavailable=True,
                error="provider_unavailable",
            )
        url = _chat_completions_url(settings.hermes_model_api_url)
        model = self.model or (
            getattr(settings, "hermes_analysis_model", None)
            or getattr(settings, "hermes_default_model", None)
            or "DeepSeek-V3.2"
        )
        return _post_chat_completions(
            url=url,
            api_key=(settings.hermes_model_api_key or "").strip(),
            model=str(model),
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            provider_name=self.name,
            timeout_sec=self.timeout_sec,
        )


class OpenAIConversationProvider(ConversationProvider):
    name = "openai"

    def __init__(self, model: str | None = None, timeout_sec: float = 45.0) -> None:
        self.model = (model or "").strip() or None
        self.timeout_sec = float(timeout_sec or 45.0)

    def available(self) -> bool:
        return bool((settings.openai_api_key or "").strip())

    def decide(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | str | None,
        temperature: float,
        max_tokens: int,
    ) -> ProviderDecisionResult:
        _ = schema
        if not self.available():
            return ProviderDecisionResult(
                provider_name=self.name,
                provider_unavailable=True,
                error="provider_unavailable",
            )
        base = (settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        url = _chat_completions_url(base)
        model = self.model or settings.openai_default_model or "gpt-4o"
        return _post_chat_completions(
            url=url,
            api_key=settings.openai_api_key.strip(),
            model=str(model),
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            provider_name=self.name,
            timeout_sec=self.timeout_sec,
        )
