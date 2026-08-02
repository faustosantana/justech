"""Select ConversationProvider from Lottery AI Settings (DB/cache) — never ENV for active provider."""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.lottery.ai.conversational_orchestrator.conversation_provider import (
    ConversationProvider,
    HuaweiConversationProvider,
    OpenAIConversationProvider,
    ProviderDecisionResult,
)
from app.services.credential_vault import decrypt_secret

_VALID = frozenset({"huawei", "openai"})

# Process-local cache — secrets stay encrypted; decrypted only when building provider.
_RUNTIME_SETTINGS: dict[str, Any] = {
    "conversation_provider": "huawei",
    "conversation_model": "deepseek-v4-flash",
    "temperature": 0.0,
    "max_tokens": 700,
    "timeout_seconds": 45,
    "openai_api_key_encrypted": None,
    "openai_base_url": None,
    "openai_organization": None,
    "openai_project": None,
}
_CACHE_VERSION: int = 0
_CACHE_LOADED_FROM_DB: bool = False
_LAST_CACHE_HIT: bool = False


def set_runtime_settings_cache(data: dict[str, Any] | None) -> None:
    global _CACHE_VERSION, _CACHE_LOADED_FROM_DB, _LAST_CACHE_HIT
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
    # Encrypted blob only (never plaintext API key in cache public view)
    if "openai_api_key_encrypted" in data:
        _RUNTIME_SETTINGS["openai_api_key_encrypted"] = data.get("openai_api_key_encrypted")
    if "openai_base_url" in data:
        _RUNTIME_SETTINGS["openai_base_url"] = data.get("openai_base_url")
    if "openai_organization" in data:
        _RUNTIME_SETTINGS["openai_organization"] = data.get("openai_organization")
    if "openai_project" in data:
        _RUNTIME_SETTINGS["openai_project"] = data.get("openai_project")
    _CACHE_VERSION += 1
    _CACHE_LOADED_FROM_DB = True
    _LAST_CACHE_HIT = False


def get_runtime_settings() -> dict[str, Any]:
    """Safe copy — strips encrypted material from returned dict."""
    out = {
        k: v
        for k, v in _RUNTIME_SETTINGS.items()
        if k != "openai_api_key_encrypted"
    }
    out["openai_key_configured"] = bool(_RUNTIME_SETTINGS.get("openai_api_key_encrypted"))
    out["cache_version"] = _CACHE_VERSION
    out["cache_loaded_from_db"] = _CACHE_LOADED_FROM_DB
    return out


def invalidate_provider_cache() -> None:
    """Bump cache version after save/delete so live chat rebuilds the provider."""
    global _CACHE_VERSION, _LAST_CACHE_HIT
    _CACHE_VERSION += 1
    _LAST_CACHE_HIT = False


def configured_provider_name() -> str:
    name = str(_RUNTIME_SETTINGS.get("conversation_provider") or "huawei").strip().lower()
    return name if name in _VALID else "huawei"


def runtime_provider_label(name: str) -> str:
    """Telemetry label used by live chat runtime_trace."""
    n = (name or "").strip().lower()
    if n == "openai":
        return "openai"
    if n in {"huawei", "huawei_modelarts"}:
        return "huawei_modelarts"
    return n or "huawei_modelarts"


def _resolve_openai_credentials(
    *,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
    organization_override: str | None = None,
    project_override: str | None = None,
) -> tuple[str | None, str | None, str | None, str | None, str]:
    """Return (api_key, base_url, org, project, credential_source)."""
    if (api_key_override or "").strip():
        return (
            api_key_override.strip(),
            (base_url_override or _RUNTIME_SETTINGS.get("openai_base_url") or "").strip()
            or None,
            (organization_override or _RUNTIME_SETTINGS.get("openai_organization") or "").strip()
            or None,
            (project_override or _RUNTIME_SETTINGS.get("openai_project") or "").strip() or None,
            "form" if api_key_override else "database",
        )

    enc = _RUNTIME_SETTINGS.get("openai_api_key_encrypted")
    if enc:
        try:
            plain = decrypt_secret(str(enc))
        except Exception:  # noqa: BLE001
            plain = None
        if plain:
            return (
                plain,
                (base_url_override or _RUNTIME_SETTINGS.get("openai_base_url") or "").strip()
                or None,
                (
                    organization_override or _RUNTIME_SETTINGS.get("openai_organization") or ""
                ).strip()
                or None,
                (project_override or _RUNTIME_SETTINGS.get("openai_project") or "").strip()
                or None,
                "database",
            )

    env_key = (settings.openai_api_key or "").strip()
    if env_key:
        return (
            env_key,
            (base_url_override or settings.openai_base_url or "").strip() or None,
            (organization_override or "").strip() or None,
            (project_override or "").strip() or None,
            "environment",
        )
    return (None, None, None, None, "none")


def build_provider(
    name: str,
    *,
    model: str | None = None,
    timeout_sec: float | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    organization: str | None = None,
    project: str | None = None,
) -> ConversationProvider:
    model_s = model or str(_RUNTIME_SETTINGS.get("conversation_model") or "")
    timeout = float(
        timeout_sec
        if timeout_sec is not None
        else _RUNTIME_SETTINGS.get("timeout_seconds") or 45
    )
    if name == "openai":
        key, buri, org, proj, source = _resolve_openai_credentials(
            api_key_override=api_key,
            base_url_override=base_url,
            organization_override=organization,
            project_override=project,
        )
        # form override reported as database when persisted path uses same helper with key
        if api_key and source == "form":
            pass
        return OpenAIConversationProvider(
            model=model_s or None,
            timeout_sec=timeout,
            api_key=key,
            base_url=buri,
            organization=org,
            project=proj,
            credential_source=source if key else "none",
        )
    return HuaweiConversationProvider(model=model_s or None, timeout_sec=timeout)


def get_conversation_provider(
    *,
    allow_fallback: bool = True,
) -> tuple[ConversationProvider, dict[str, Any]]:
    """Return (provider, meta) from DB-backed runtime cache."""
    global _LAST_CACHE_HIT
    cache_hit = bool(_CACHE_LOADED_FROM_DB and _CACHE_VERSION > 0)
    _LAST_CACHE_HIT = cache_hit
    requested = configured_provider_name()
    model = str(_RUNTIME_SETTINGS.get("conversation_model") or "")
    timeout = float(_RUNTIME_SETTINGS.get("timeout_seconds") or 45)
    primary = build_provider(requested, model=model, timeout_sec=timeout)
    cred_source = getattr(primary, "credential_source", None) or (
        "none" if requested == "openai" else "n/a"
    )
    meta: dict[str, Any] = {
        "requested_provider": requested,
        "selected_provider": requested,
        "provider": primary.name,
        "provider_used": runtime_provider_label(primary.name),
        "model": model,
        "selected_model": model,
        "temperature": float(_RUNTIME_SETTINGS.get("temperature") or 0),
        "max_tokens": int(_RUNTIME_SETTINGS.get("max_tokens") or 700),
        "timeout_seconds": int(timeout),
        "provider_unavailable": False,
        "fallback": None,
        "fallback_used": False,
        "fallback_reason": None,
        "source": "lottery_ai_settings",
        "provider_config_source": "database" if _CACHE_LOADED_FROM_DB else "default",
        "credential_source": cred_source,
        "cache_hit": cache_hit,
        "cache_version": _CACHE_VERSION,
    }
    if primary.available():
        return primary, meta

    meta["provider_unavailable"] = True
    if allow_fallback and requested == "openai":
        fallback = build_provider("huawei", model=None, timeout_sec=timeout)
        meta["fallback"] = "huawei"
        meta["fallback_used"] = True
        meta["fallback_reason"] = "openai_unavailable"
        meta["provider"] = fallback.name
        meta["provider_used"] = runtime_provider_label(fallback.name)
        return fallback, meta

    meta["fallback"] = None
    meta["fallback_reason"] = "provider_unavailable"
    return primary, meta


def get_lottery_conversation_provider(
    *,
    allow_fallback: bool = False,
) -> tuple[ConversationProvider, dict[str, Any]]:
    """Single source of truth for Lottery IA live chat + UI connection tests.

    Reads active Lottery AI Settings (process cache hydrated from DB). ENV is only
    used inside OpenAI credential resolution when no DB ciphertext exists.
    """
    return get_conversation_provider(allow_fallback=allow_fallback)


def complete_with_lottery_provider(
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float | None = None,
    allow_fallback: bool = False,
) -> tuple[str | None, str | None, dict[str, Any], dict[str, Any]]:
    """Run a free-form completion via the active Lottery AI Settings provider.

    Returns (text, model, usage, meta).
    """
    provider, meta = get_lottery_conversation_provider(allow_fallback=allow_fallback)
    if not provider.available():
        meta = {
            **meta,
            "provider_unavailable": True,
            "fallback_used": False,
            "fallback_reason": "provider_unavailable",
        }
        return None, None, {}, meta

    system = ""
    rest: list[dict[str, str]] = []
    for m in messages or []:
        role = str(m.get("role") or "user")
        content = str(m.get("content") or "")
        if role == "system" and not system:
            system = content
        else:
            rest.append({"role": role, "content": content})
    if not rest:
        rest = [{"role": "user", "content": " "}]

    temp = (
        float(temperature)
        if temperature is not None
        else float(meta.get("temperature") or 0.0)
    )
    result: ProviderDecisionResult = provider.decide(
        system_prompt=system or "Eres el analista de Lottery IA.",
        messages=rest,
        schema=None,
        temperature=temp,
        max_tokens=int(max_tokens or meta.get("max_tokens") or 700),
    )
    meta = {
        **meta,
        "provider": provider.name,
        "provider_used": runtime_provider_label(provider.name),
        "selected_provider": meta.get("selected_provider") or configured_provider_name(),
        "selected_model": meta.get("selected_model") or meta.get("model"),
        "credential_source": getattr(provider, "credential_source", meta.get("credential_source")),
        "latency_ms": result.latency_ms,
        "fallback_used": False,
        "fallback_reason": None,
    }
    if result.provider_unavailable or (result.error and not result.content):
        meta["provider_unavailable"] = True
        meta["fallback_reason"] = result.error or "provider_call_failed"
        return None, result.model or meta.get("model"), result.usage or {}, meta

    text = (result.content or "").strip() or None
    return text, result.model or meta.get("model"), result.usage or {}, meta
