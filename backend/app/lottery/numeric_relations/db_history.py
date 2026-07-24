"""Carga asíncrona de ocurrencias históricas (drawn_number = N) desde PostgreSQL.

No duplica el análisis: solo alimenta InMemoryDrawHistory / DrawHistoryPort.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lottery.numeric_relations.models import (
    DrawNumberRef,
    HistoricalOccurrence,
    OccurrenceLimit,
)
from app.models.lottery import Lottery, LotteryDraw, LotteryDrawNumber
from app.services.lottery_repository import LotteryRepository


def _number_variants(n: int) -> list[str]:
    """Formatos típicos de number_value en el histórico (sin ampliar el dominio 1..100)."""
    raw = str(int(n))
    variants = [raw]
    if n <= 99:
        variants.append(raw.zfill(2))
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


async def load_occurrences_from_db(
    db: AsyncSession,
    *,
    observed_number: int,
    lottery_ids: list[UUID | str],
    limit: OccurrenceLimit,
) -> list[HistoricalOccurrence]:
    """Ocurrencias reales donde salió N, más recientes primero; luego recorta por K."""
    n = int(observed_number)
    if n < 1 or n > 100:
        raise ValueError("observed_number must be in [1, 100]")
    if not lottery_ids:
        raise ValueError("lottery_ids must not be empty")

    repo = LotteryRepository(db)
    variants = _number_variants(n)
    # Collect candidate (draw, hit_row) newest-first across lotteries
    collected: list[tuple[LotteryDraw, LotteryDrawNumber, str]] = []

    lot_ids = [UUID(str(x)) for x in lottery_ids]
    name_by_id: dict[str, str] = {}
    lots = (
        await db.execute(select(Lottery).where(Lottery.id.in_(lot_ids)))
    ).scalars().all()
    for lot in lots:
        name_by_id[str(lot.id)] = lot.commercial_name or lot.name or lot.slug

    fetch_limit = 5000 if limit.mode == "all" else max(int(limit.k or 1) * 5, 50)

    for lid in lot_ids:
        for variant in variants:
            rows, _total = await repo.number_occurrences(
                lid,
                variant,
                limit=fetch_limit,
                offset=0,
                order="desc",
            )
            for draw, num_row in rows:
                collected.append((draw, num_row, name_by_id.get(str(lid), str(lid))))

    # Unique draws (same draw may match multiple variants)
    by_draw: dict[str, tuple[LotteryDraw, str]] = {}
    for draw, _hit, lname in collected:
        key = str(draw.id)
        if key not in by_draw:
            by_draw[key] = (draw, lname)

    draws_sorted = sorted(
        by_draw.values(),
        key=lambda pair: (pair[0].draw_date, pair[0].draw_time or "", str(pair[0].id)),
        reverse=True,
    )

    occurrences: list[HistoricalOccurrence] = []
    for draw, lname in draws_sorted:
        nums = (
            await db.execute(
                select(LotteryDrawNumber)
                .where(LotteryDrawNumber.draw_id == draw.id)
                .order_by(LotteryDrawNumber.position.asc())
            )
        ).scalars().all()
        refs: list[DrawNumberRef] = []
        saw_n = False
        for row in nums:
            try:
                val = int(str(row.number_value).lstrip("0") or "0")
            except ValueError:
                continue
            if val == n:
                saw_n = True
            refs.append(
                DrawNumberRef(
                    position=row.position,
                    drawn_number=val,
                    position_label=row.position_label,
                )
            )
        if not saw_n:
            continue
        occurrences.append(
            HistoricalOccurrence(
                lottery_id=draw.lottery_id,
                lottery_name=lname,
                draw_id=draw.id,
                draw_date=draw.draw_date,
                draw_time=draw.draw_time,
                observed_number=n,
                draw_numbers=tuple(refs),
            )
        )

    if limit.mode == "last_k":
        return occurrences[: int(limit.k or 0)]
    return occurrences


async def analyze_from_db(
    db: AsyncSession,
    *,
    observed_number: int,
    lottery_ids: list[UUID | str],
    limit: OccurrenceLimit,
    lottery_names: dict[str, str] | None = None,
):
    """Carga histórico desde DB y ejecuta el motor único (sin duplicar scoring)."""
    from app.lottery.numeric_relations.analysis import analyze_observed_number
    from app.lottery.numeric_relations.history import InMemoryDrawHistory

    all_occs = await load_occurrences_from_db(
        db,
        observed_number=observed_number,
        lottery_ids=list(lottery_ids),
        limit=OccurrenceLimit.all(),
    )
    names = dict(lottery_names or {})
    for occ in all_occs:
        names.setdefault(str(occ.lottery_id), occ.lottery_name)
    hist = InMemoryDrawHistory(all_occs)
    return analyze_observed_number(
        observed_number,
        list(lottery_ids),
        limit,
        history=hist,
        lottery_names=names,
    )
