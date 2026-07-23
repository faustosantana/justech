"""Timezone helpers for Lottery 3.0 (default America/Santo_Domingo)."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def lottery_tz_name() -> str:
    env = os.environ.get("LOTTERY_SYNC_TIMEZONE")
    if env:
        return env
    try:
        from app.config import settings

        return settings.lottery_sync_timezone or "America/Santo_Domingo"
    except Exception:
        return "America/Santo_Domingo"


def lottery_zone() -> ZoneInfo:
    try:
        return ZoneInfo(lottery_tz_name())
    except Exception:
        return ZoneInfo("America/Santo_Domingo")


def lottery_now() -> datetime:
    return datetime.now(lottery_zone())


def local_today() -> date:
    return lottery_now().date()


def as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
