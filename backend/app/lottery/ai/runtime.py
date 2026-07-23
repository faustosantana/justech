"""Lottery IA 4.0 — sanitized runtime observability (no secrets)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.lottery.ai.prompts.lottery_assistant_system_v1 import (
    get_active_prompt,
    list_prompt_versions,
)


# Process-local last-call traces (sanitized). Reset on restart.
_LAST_SUCCESS: dict[str, Any] | None = None
_LAST_FALLBACK: dict[str, Any] | None = None


def record_runtime_trace(trace: dict[str, Any], *, success: bool) -> None:
    global _LAST_SUCCESS, _LAST_FALLBACK
    sanitized = {
        k: v
        for k, v in trace.items()
        if k
        not in {
            "api_key",
            "token",
            "authorization",
            "password",
            "secret",
            "hermes_model_api_key",
            "huawei_modelarts_api_key",
        }
    }
    sanitized["recorded_at"] = datetime.now(timezone.utc).isoformat()
    if success:
        _LAST_SUCCESS = sanitized
    else:
        _LAST_FALLBACK = sanitized


def runtime_snapshot() -> dict[str, Any]:
    prompt = get_active_prompt()
    hermes_url = bool((getattr(settings, "hermes_model_api_url", None) or "").strip())
    hermes_key = bool((getattr(settings, "hermes_model_api_key", None) or "").strip())
    huawei_url = bool(
        (getattr(settings, "huawei_modelarts_api_url", None) or "").strip()
        or hermes_url
    )
    huawei_key = bool(
        (getattr(settings, "huawei_modelarts_api_key", None) or "").strip()
        or hermes_key
    )
    synthesis_provider = getattr(settings, "assistant_synthesis_provider", None) or None
    configured_model = (
        getattr(settings, "hermes_default_model", None)
        or getattr(settings, "hermes_model", None)
        or getattr(settings, "huawei_modelarts_model", None)
        or "DeepSeek-V3.2"
    )

    # Honest status: hermes-service is NOT the lottery planner; ModelArts HTTP is synthesis-only.
    hermes_service_in_lottery_path = False
    hermes_synthesis_configured = bool(
        getattr(settings, "hermes_enabled", True) and hermes_url and hermes_key
    )

    return {
        "prompt_name": prompt.name,
        "prompt_version": prompt.version,
        "prompt_status": prompt.status,
        "prompt_versions": list_prompt_versions(),
        "provider_configured": synthesis_provider
        or getattr(settings, "hermes_provider", None)
        or getattr(settings, "hermes_default_provider", None)
        or "huawei_modelarts",
        "provider_active": (_LAST_SUCCESS or {}).get("provider_used"),
        "model_configured": configured_model,
        "model_active": (_LAST_SUCCESS or {}).get("model_used"),
        "huawei_modelarts": {
            "credentials_present": huawei_key,
            "endpoint_configured": huawei_url,
            "role_in_lottery": "optional_synthesis_via_HERMES_MODEL_API_*_or_LLMRouter",
            "used_for_planning": False,
        },
        "hermes": {
            "hermes_enabled_flag": bool(getattr(settings, "hermes_enabled", True)),
            "hermes_service_url_configured": bool(
                (getattr(settings, "hermes_service_url", None) or "").strip()
            ),
            "model_api_configured": hermes_synthesis_configured,
            "participates_in_lottery_planning": False,
            "participates_in_lottery_memory": False,
            "participates_in_lottery_tools": False,
            "participates_in_lottery_synthesis": hermes_synthesis_configured,
            "hermes_service_on_lottery_chat_path": hermes_service_in_lottery_path,
            "note": (
                "Lottery IA uses typed tools + Conversation Manager. "
                "Hermes ModelArts HTTP is an optional synthesis fallback only; "
                "hermes-service microservice is not on the lottery chat path."
            ),
        },
        "memory_backend": "lottery_chat_session.context (typed ConversationState v4)",
        "planner_mode": "deterministic_bounded_multi_tool",
        "synthesis_enabled": bool(getattr(settings, "assistant_synthesis_enabled", True)),
        "last_successful_call": _LAST_SUCCESS,
        "last_fallback": _LAST_FALLBACK,
        "health": {
            "ok": True,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "synthesis_credentials_ok": hermes_synthesis_configured or huawei_key,
        },
    }
