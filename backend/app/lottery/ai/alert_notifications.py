"""Lottery AI alert notification stubs — DISABLED by default.

Channels: email, webhook, slack, teams, jaios_internal.
Never send externally without explicit enabled flag + recipients/URL.
Deduplicate via fingerprint + throttle window (in-process; unit-testable).

Wire-up: call ``notify_alert`` after detector upsert (or from admin
``run_alert_detector_now``). External delivery is a no-op until flags are on.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger("lottery.ai.alert_notifications")

CHANNELS = ("email", "webhook", "slack", "teams", "jaios_internal")

# fingerprint -> last_sent_monotonic
_THROTTLE_CACHE: dict[str, float] = {}
DEFAULT_THROTTLE_SECONDS = 3600


def _setting_bool(name: str, default: bool = False) -> bool:
    """Read from app.config Settings if present, else env (default false)."""
    attr = name.lower()
    try:
        from app.config import settings

        if hasattr(settings, attr):
            return bool(getattr(settings, attr))
    except Exception:
        pass
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _setting_str(name: str, default: str = "") -> str:
    attr = name.lower()
    try:
        from app.config import settings

        if hasattr(settings, attr):
            val = getattr(settings, attr)
            if val is not None:
                return str(val)
    except Exception:
        pass
    return os.environ.get(name, default) or default


def _setting_int(name: str, default: int) -> int:
    attr = name.lower()
    try:
        from app.config import settings

        if hasattr(settings, attr):
            return int(getattr(settings, attr))
    except Exception:
        pass
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def default_channels_config() -> dict[str, Any]:
    """Build channel config from settings/env — all channels off unless explicitly enabled."""
    return {
        "throttle_seconds": _setting_int("LOTTERY_AI_ALERT_THROTTLE_SECONDS", DEFAULT_THROTTLE_SECONDS),
        "email": {
            "enabled": _setting_bool("LOTTERY_AI_ALERT_EMAIL_ENABLED", False),
            "recipients": [
                x.strip()
                for x in _setting_str("LOTTERY_AI_ALERT_EMAIL_RECIPIENTS", "").split(",")
                if x.strip()
            ],
        },
        "webhook": {
            "enabled": _setting_bool("LOTTERY_AI_ALERT_WEBHOOK_ENABLED", False),
            "url": _setting_str("LOTTERY_AI_ALERT_WEBHOOK_URL", "").strip(),
        },
        "slack": {
            "enabled": _setting_bool("LOTTERY_AI_ALERT_SLACK_ENABLED", False),
            "webhook_url": _setting_str("LOTTERY_AI_ALERT_SLACK_WEBHOOK_URL", "").strip(),
        },
        "teams": {
            "enabled": _setting_bool("LOTTERY_AI_ALERT_TEAMS_ENABLED", False),
            "webhook_url": _setting_str("LOTTERY_AI_ALERT_TEAMS_WEBHOOK_URL", "").strip(),
        },
        "jaios_internal": {
            "enabled": _setting_bool("LOTTERY_AI_ALERT_JAIOS_INTERNAL_ENABLED", False),
        },
    }


def clear_throttle_cache() -> None:
    """Test helper — reset in-process dedupe window."""
    _THROTTLE_CACHE.clear()


def _throttled(fingerprint: str, window: int, *, now: float | None = None) -> bool:
    if not fingerprint or window <= 0:
        return False
    ts = now if now is not None else time.monotonic()
    last = _THROTTLE_CACHE.get(fingerprint)
    if last is not None and (ts - last) < window:
        return True
    return False


def _mark_sent(fingerprint: str, *, now: float | None = None) -> None:
    if fingerprint:
        _THROTTLE_CACHE[fingerprint] = now if now is not None else time.monotonic()


def _send_email(alert: dict[str, Any], cfg: dict[str, Any]) -> str | None:
    """Stub — never opens SMTP. Returns None on success stub, else skip reason."""
    if not cfg.get("enabled"):
        return "email_disabled"
    recipients = cfg.get("recipients") or []
    if not recipients:
        return "email_no_recipients"
    logger.info(
        "alert_notify stub email code=%s recipients=%s (not sent)",
        alert.get("code"),
        len(recipients),
    )
    return None


def _send_webhook(alert: dict[str, Any], cfg: dict[str, Any]) -> str | None:
    if not cfg.get("enabled"):
        return "webhook_disabled"
    if not (cfg.get("url") or "").strip():
        return "webhook_no_url"
    logger.info("alert_notify stub webhook code=%s (not sent)", alert.get("code"))
    return None


def _send_slack(alert: dict[str, Any], cfg: dict[str, Any]) -> str | None:
    if not cfg.get("enabled"):
        return "slack_disabled"
    if not (cfg.get("webhook_url") or "").strip():
        return "slack_no_webhook_url"
    logger.info("alert_notify stub slack code=%s (not sent)", alert.get("code"))
    return None


def _send_teams(alert: dict[str, Any], cfg: dict[str, Any]) -> str | None:
    if not cfg.get("enabled"):
        return "teams_disabled"
    if not (cfg.get("webhook_url") or "").strip():
        return "teams_no_webhook_url"
    logger.info("alert_notify stub teams code=%s (not sent)", alert.get("code"))
    return None


def _send_jaios_internal(alert: dict[str, Any], cfg: dict[str, Any]) -> str | None:
    if not cfg.get("enabled"):
        return "jaios_internal_disabled"
    logger.info("alert_notify stub jaios_internal code=%s (not sent)", alert.get("code"))
    return None


_HANDLERS = {
    "email": _send_email,
    "webhook": _send_webhook,
    "slack": _send_slack,
    "teams": _send_teams,
    "jaios_internal": _send_jaios_internal,
}


def notify_alert(
    alert_dict: dict[str, Any],
    channels_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch alert to configured channels (stubs). Never hits network when disabled.

    Returns ``{sent: [], skipped: [], reasons: []}``.
    """
    cfg = channels_config if channels_config is not None else default_channels_config()
    sent: list[str] = []
    skipped: list[str] = []
    reasons: list[str] = []

    fp = str(alert_dict.get("fingerprint") or alert_dict.get("code") or "")
    window = int(cfg.get("throttle_seconds") or DEFAULT_THROTTLE_SECONDS)
    if _throttled(fp, window):
        return {
            "sent": [],
            "skipped": list(CHANNELS),
            "reasons": [f"throttled:{fp}"],
        }

    any_sent = False
    for channel in CHANNELS:
        channel_cfg = cfg.get(channel) or {}
        if not isinstance(channel_cfg, dict):
            channel_cfg = {}
        handler = _HANDLERS[channel]
        reason = handler(alert_dict, channel_cfg)
        if reason is None:
            sent.append(channel)
            any_sent = True
        else:
            skipped.append(channel)
            reasons.append(reason)

    if any_sent:
        _mark_sent(fp)

    return {"sent": sent, "skipped": skipped, "reasons": reasons}
