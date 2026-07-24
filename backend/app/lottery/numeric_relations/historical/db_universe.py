"""Carga de DrawRef desde PostgreSQL para el analizador histórico (solo lectura)."""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.lottery.numeric_relations.historical.models import DrawRef
from app.lottery.numeric_relations.historical.universe import InMemoryDrawUniverse
from app.models.lottery import LotteryDraw, LotteryDrawNumber, LotteryLottery


def _parse_number(raw: str | int | None) -> int | None:
    if raw is None:
        return None
    try:
        n = int(str(raw).lstrip("0") or "0")
    except ValueError:
        return None
    if 1 <= n <= 100:
        return n
    return None


async def load_universe_from_db(
    db: AsyncSession,
    *,
    lottery_ids: list[str | UUID],
    date_from: date | None = None,
    date_to: date | None = None,
    max_draws: int = 20000,
) -> tuple[InMemoryDrawUniverse, dict[str, str]]:
    """
    Carga draws + numbers 1..100 para loterías dadas.
    No muta histórico. Identidad = draw_id.
    """
    lids = [UUID(str(x)) for x in lottery_ids]
    if not lids:
        raise ValueError("lottery_ids must not be empty")

    lots = (
        await db.execute(
            select(
                LotteryLottery.id,
                LotteryLottery.name,
                LotteryLottery.commercial_name,
                LotteryLottery.slug,
            ).where(LotteryLottery.id.in_(lids))
        )
    ).all()
    names = {
        str(r.id): (r.commercial_name or r.name or r.slug or str(r.id)) for r in lots
    }

    filters = [LotteryDraw.lottery_id.in_(lids)]
    if date_from is not None:
        filters.append(LotteryDraw.draw_date >= date_from)
    if date_to is not None:
        filters.append(LotteryDraw.draw_date <= date_to)

    q = (
        select(LotteryDraw)
        .where(and_(*filters))
        .options(selectinload(LotteryDraw.numbers))
        .order_by(LotteryDraw.draw_date.asc(), LotteryDraw.id.asc())
        .limit(int(max_draws))
    )
    draws = (await db.execute(q)).scalars().unique().all()

    universe = InMemoryDrawUniverse()
    for d in draws:
        nums: list[tuple[int | str, int]] = []
        for row in d.numbers or []:
            # LotteryDrawNumber typically has position + number_value
            val = _parse_number(getattr(row, "number_value", None) or getattr(row, "drawn_number", None))
            if val is None:
                continue
            pos = getattr(row, "position", None) or getattr(row, "slot", None) or len(nums) + 1
            nums.append((pos, val))
        universe.add(
            DrawRef(
                draw_id=str(d.id),
                lottery_id=str(d.lottery_id),
                lottery_name=names.get(str(d.lottery_id), str(d.lottery_id)),
                draw_date=d.draw_date,
                draw_time=d.draw_time if isinstance(d.draw_time, time) else None,
                numbers=tuple(nums),
            )
        )
    return universe, names
