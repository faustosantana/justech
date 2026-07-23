"""Smart sync windows — Lottery 3.0 Sync Engine planner.

Phases:
  idle     — outside draw window (normal interval)
  pre      — before draw (faster poll)
  live     — around draw time (fastest poll)
  post     — after draw until result validated (fast poll)
  paused   — result validated for today's slot (no poll until next slot)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from app.lottery.core.timeutil import lottery_now, lottery_zone


class SyncWindowPhase(str, Enum):
    IDLE = "idle"
    PRE = "pre"
    LIVE = "live"
    POST = "post"
    PAUSED = "paused"


@dataclass(frozen=True)
class WindowDecision:
    lottery_id: str
    source_id: int
    phase: SyncWindowPhase
    interval_minutes: int
    next_draw_at: datetime | None
    reason: str
    should_poll: bool
    priority: int


def _parse_times(raw: str | None) -> list[time]:
    if not raw:
        return []
    out: list[time] = []
    for part in raw.replace(";", ",").split(","):
        p = part.strip()
        if not p:
            continue
        try:
            hh, mm = p.split(":")[:2]
            out.append(time(int(hh), int(mm)))
        except Exception:
            continue
    return out


def _parse_days(raw: str | None) -> set[int] | None:
    """Return set of weekday ints (0=Mon) or None = every day."""
    if not raw or raw.strip().lower() in {"*", "all", "daily", "7"}:
        return None
    mapping = {
        "mon": 0,
        "tue": 1,
        "wed": 2,
        "thu": 3,
        "fri": 4,
        "sat": 5,
        "sun": 6,
        "lun": 0,
        "mar": 1,
        "mie": 2,
        "jue": 3,
        "vie": 4,
        "sab": 5,
        "dom": 6,
    }
    days: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        p = part.strip().lower()
        if not p:
            continue
        if p.isdigit():
            days.add(int(p) % 7)
        elif p[:3] in mapping:
            days.add(mapping[p[:3]])
    return days or None


def _next_slots(
    *,
    now: datetime,
    tz: ZoneInfo,
    draw_times: list[time],
    draw_days: set[int] | None,
    horizon_days: int = 7,
) -> list[datetime]:
    if not draw_times:
        # Default evening slot for RD quinielas when unset
        draw_times = [time(20, 55)]
    slots: list[datetime] = []
    local_now = now.astimezone(tz)
    for d in range(0, horizon_days + 1):
        day = (local_now.date() + timedelta(days=d))
        if draw_days is not None and day.weekday() not in draw_days:
            continue
        for t in draw_times:
            slot = datetime.combine(day, t, tzinfo=tz)
            slots.append(slot)
    slots.sort()
    return slots


def plan_lottery_window(
    lot: Any,
    *,
    now: datetime | None = None,
    result_validated_for_date: date | None = None,
    pre_minutes: int | None = None,
    live_minutes: int | None = None,
    post_minutes: int | None = None,
) -> WindowDecision:
    """Decide poll phase/interval for one lottery."""
    tz_name = lot.timezone or "America/Santo_Domingo"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = lottery_zone()
    now = now or lottery_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)

    pre_m = pre_minutes if pre_minutes is not None else int(getattr(lot, "sync_pre_window_minutes", None) or 15)
    live_m = live_minutes if live_minutes is not None else int(getattr(lot, "sync_live_window_minutes", None) or 10)
    post_m = post_minutes if post_minutes is not None else int(
        lot.sync_post_draw_delay_minutes or getattr(lot, "sync_post_window_minutes", None) or 45
    )
    idle_interval = int(lot.sync_interval_minutes or 60)
    pre_interval = int(getattr(lot, "sync_pre_interval_minutes", None) or 5)
    live_interval = int(getattr(lot, "sync_live_interval_minutes", None) or 1)
    post_interval = int(getattr(lot, "sync_post_interval_minutes", None) or 1)
    priority = int(getattr(lot, "sync_priority", None) or 100)

    times = _parse_times(lot.draw_times)
    days = _parse_days(lot.draw_days)
    slots = _next_slots(now=now, tz=tz, draw_times=times, draw_days=days)
    upcoming = [s for s in slots if s >= now - timedelta(minutes=post_m)]
    next_draw = upcoming[0] if upcoming else (slots[0] if slots else None)

    # Pause if today's draw already validated
    if result_validated_for_date and next_draw and result_validated_for_date == next_draw.date():
        # only pause if we're past that slot
        if now >= next_draw:
            return WindowDecision(
                lottery_id=str(lot.id),
                source_id=lot.source_id,
                phase=SyncWindowPhase.PAUSED,
                interval_minutes=idle_interval,
                next_draw_at=next_draw,
                reason="result_validated_for_slot",
                should_poll=False,
                priority=priority,
            )

    if next_draw is None:
        return WindowDecision(
            lottery_id=str(lot.id),
            source_id=lot.source_id,
            phase=SyncWindowPhase.IDLE,
            interval_minutes=idle_interval,
            next_draw_at=None,
            reason="no_schedule",
            should_poll=True,
            priority=priority,
        )

    delta_pre = (next_draw - now).total_seconds() / 60
    delta_post = (now - next_draw).total_seconds() / 60

    if 0 <= delta_post <= post_m:
        return WindowDecision(
            lottery_id=str(lot.id),
            source_id=lot.source_id,
            phase=SyncWindowPhase.POST,
            interval_minutes=post_interval,
            next_draw_at=next_draw,
            reason="post_draw_awaiting_result",
            should_poll=True,
            priority=priority - 20,
        )
    if -live_m <= delta_pre <= 0 or (0 < delta_pre <= live_m / 2):
        # near or at draw
        return WindowDecision(
            lottery_id=str(lot.id),
            source_id=lot.source_id,
            phase=SyncWindowPhase.LIVE,
            interval_minutes=live_interval,
            next_draw_at=next_draw,
            reason="live_draw_window",
            should_poll=True,
            priority=priority - 40,
        )
    if 0 < delta_pre <= pre_m:
        return WindowDecision(
            lottery_id=str(lot.id),
            source_id=lot.source_id,
            phase=SyncWindowPhase.PRE,
            interval_minutes=pre_interval,
            next_draw_at=next_draw,
            reason="pre_draw_window",
            should_poll=True,
            priority=priority - 10,
        )

    return WindowDecision(
        lottery_id=str(lot.id),
        source_id=lot.source_id,
        phase=SyncWindowPhase.IDLE,
        interval_minutes=idle_interval,
        next_draw_at=next_draw,
        reason="outside_window",
        should_poll=True,
        priority=priority,
    )


def plan_many(
    lotteries: list[Any],
    *,
    validated_dates: dict[str, date] | None = None,
    now: datetime | None = None,
) -> list[WindowDecision]:
    validated_dates = validated_dates or {}
    decisions = [
        plan_lottery_window(
            lot,
            now=now,
            result_validated_for_date=validated_dates.get(str(lot.id)),
        )
        for lot in lotteries
    ]
    decisions.sort(key=lambda d: (d.priority, d.interval_minutes))
    return decisions
