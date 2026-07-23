"""Recompute denormalized lottery metadata from lottery_draws (fixes Real 2099, etc.)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lottery import LotteryDraw, LotteryDrawNumber, LotteryLottery


async def recompute_lottery_metadata(
    db: AsyncSession,
    lottery_id: uuid.UUID,
    *,
    touch_updated_at: bool = True,
) -> dict[str, Any]:
    """Derive draw_count / first_draw_date / last_draw_date / last_result_at from draws."""
    lot = await db.get(LotteryLottery, lottery_id)
    if not lot:
        return {"ok": False, "error": "lottery_not_found"}

    before = {
        "draw_count": lot.draw_count,
        "first_draw_date": lot.first_draw_date.isoformat() if lot.first_draw_date else None,
        "last_draw_date": lot.last_draw_date.isoformat() if lot.last_draw_date else None,
    }

    stats = (
        await db.execute(
            select(
                func.count().label("cnt"),
                func.min(LotteryDraw.draw_date).label("min_d"),
                func.max(LotteryDraw.draw_date).label("max_d"),
                func.max(func.coalesce(LotteryDraw.updated_at, LotteryDraw.created_at)).label("last_touch"),
            ).where(LotteryDraw.lottery_id == lottery_id)
        )
    ).one()

    numbers = int(
        (
            await db.execute(
                select(func.count())
                .select_from(LotteryDrawNumber)
                .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
                .where(LotteryDraw.lottery_id == lottery_id)
            )
        ).scalar_one()
    )

    lot.draw_count = int(stats.cnt or 0)
    lot.first_draw_date = stats.min_d
    lot.last_draw_date = stats.max_d
    lot.numbers_count = numbers
    if stats.last_touch is not None:
        lot.last_result_at = stats.last_touch
    if touch_updated_at:
        lot.updated_at = datetime.now(timezone.utc)
    await db.flush()

    after = {
        "draw_count": lot.draw_count,
        "first_draw_date": lot.first_draw_date.isoformat() if lot.first_draw_date else None,
        "last_draw_date": lot.last_draw_date.isoformat() if lot.last_draw_date else None,
        "numbers_count": numbers,
    }
    return {
        "ok": True,
        "lottery_id": str(lottery_id),
        "source_id": lot.source_id,
        "name": lot.name,
        "before": before,
        "after": after,
        "changed": before != {k: after[k] for k in before},
    }


async def recompute_all_lottery_metadata(db: AsyncSession) -> dict[str, Any]:
    ids = (await db.execute(select(LotteryLottery.id))).scalars().all()
    results = []
    changed = 0
    for lid in ids:
        row = await recompute_lottery_metadata(db, lid)
        results.append(row)
        if row.get("changed"):
            changed += 1
    return {"ok": True, "lotteries": len(ids), "changed": changed, "results": results}
