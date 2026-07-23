"""Per-lottery sync dispatcher — evaluates windows; writes only auto-write lotteries."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.lottery.sync.window_planner import WindowDecision, plan_many
from app.models.lottery import LotteryDraw, LotteryLottery

logger = logging.getLogger(__name__)


async def validated_dates_map(db: AsyncSession, lottery_ids: list) -> dict[str, date]:
    """Map lottery_id -> max draw_date present in DB (used as validated slot marker)."""
    if not lottery_ids:
        return {}
    rows = (
        await db.execute(
            select(LotteryDraw.lottery_id, func.max(LotteryDraw.draw_date))
            .where(LotteryDraw.lottery_id.in_(lottery_ids))
            .group_by(LotteryDraw.lottery_id)
        )
    ).all()
    return {str(lid): d for lid, d in rows if d is not None}


async def plan_due_lotteries(
    db: AsyncSession,
    *,
    only_sync_enabled: bool = True,
) -> list[WindowDecision]:
    stmt = select(LotteryLottery).where(LotteryLottery.is_aggregate.is_(False))
    if only_sync_enabled:
        stmt = stmt.where(LotteryLottery.is_sync_enabled.is_(True))
    lots = (await db.execute(stmt.order_by(LotteryLottery.display_order.asc()))).scalars().all()
    validated = await validated_dates_map(db, [lot.id for lot in lots])
    return plan_many(list(lots), validated_dates=validated)


async def dispatch_status(db: AsyncSession) -> dict[str, Any]:
    decisions = await plan_due_lotteries(db, only_sync_enabled=False)
    sync_enabled = await plan_due_lotteries(db, only_sync_enabled=True)
    auto = (
        await db.execute(
            select(LotteryLottery.source_id, LotteryLottery.name).where(
                LotteryLottery.is_auto_write_enabled.is_(True)
            )
        )
    ).all()
    return {
        "timezone": settings.lottery_sync_timezone,
        "evaluated": len(decisions),
        "sync_enabled_due": [
            {
                "source_id": d.source_id,
                "phase": d.phase.value,
                "interval_minutes": d.interval_minutes,
                "should_poll": d.should_poll,
                "next_draw_at": d.next_draw_at.isoformat() if d.next_draw_at else None,
                "reason": d.reason,
                "priority": d.priority,
            }
            for d in sync_enabled
            if d.should_poll
        ],
        "phases": {
            phase: sum(1 for d in decisions if d.phase.value == phase)
            for phase in ("idle", "pre", "live", "post", "paused")
        },
        "auto_write_lotteries": [{"source_id": s, "name": n} for s, n in auto],
        "write_scope": "only_is_auto_write_enabled",
    }
