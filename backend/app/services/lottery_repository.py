"""Repositorio de consultas históricas (SQLAlchemy parametrizado, sin raw_payload)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lottery import LotteryDraw, LotteryDrawNumber


def number_value_match_forms(number: str) -> list[str]:
    """Match both padded and unpadded ball forms stored in number_value.

    Historical rows are inconsistent (e.g. Leidsa ``7`` vs NY ``07``). Exact
    equality on the conversational subject ``07`` skips newer unpadded rows and
    returns a stale last-occurrence (Cert200 LONG_30.T29 / G01.T04).
    """
    raw = str(number or "").strip()
    if not raw:
        return []
    forms: list[str] = [raw]
    if raw.isdigit() and len(raw) <= 2:
        forms.append(str(int(raw)))
        forms.append(str(int(raw)).zfill(2))
    seen: set[str] = set()
    out: list[str] = []
    for v in forms:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


class LotteryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _draw_query(self, lottery_id: uuid.UUID, *, game: str | None = None):
        q = (
            select(LotteryDraw)
            .options(selectinload(LotteryDraw.numbers))
            .where(LotteryDraw.lottery_id == lottery_id)
        )
        if game:
            q = q.where(LotteryDraw.game_name == game)
        return q

    async def draws_by_date(
        self,
        lottery_id: uuid.UUID,
        draw_date: date,
        *,
        game: str | None = None,
    ) -> list[LotteryDraw]:
        q = self._draw_query(lottery_id, game=game).where(LotteryDraw.draw_date == draw_date)
        q = q.order_by(asc(LotteryDraw.draw_time).nullsfirst(), asc(LotteryDraw.id))
        return list((await self.db.execute(q)).scalars().unique().all())

    async def draws_in_range(
        self,
        lottery_id: uuid.UUID,
        from_date: date,
        to_date: date,
        *,
        game: str | None = None,
        number: str | None = None,
        position: int | None = None,
        sort: str = "asc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LotteryDraw], int]:
        base = select(LotteryDraw.id).where(
            LotteryDraw.lottery_id == lottery_id,
            LotteryDraw.draw_date >= from_date,
            LotteryDraw.draw_date <= to_date,
        )
        if game:
            base = base.where(LotteryDraw.game_name == game)
        if number is not None or position is not None:
            base = base.join(LotteryDrawNumber, LotteryDrawNumber.draw_id == LotteryDraw.id)
            if number is not None:
                base = base.where(
                    LotteryDrawNumber.number_value.in_(number_value_match_forms(number))
                )
            if position is not None:
                base = base.where(LotteryDrawNumber.position == position)
            base = base.distinct()

        total = int(
            (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        )

        order = asc(LotteryDraw.draw_date) if sort == "asc" else desc(LotteryDraw.draw_date)
        q = (
            select(LotteryDraw)
            .options(selectinload(LotteryDraw.numbers))
            .where(LotteryDraw.id.in_(base))
            .order_by(order, asc(LotteryDraw.draw_time).nullsfirst(), asc(LotteryDraw.id))
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.db.execute(q)).scalars().unique().all())
        return rows, total

    async def draws_in_calendar_window(
        self,
        lottery_id: uuid.UUID,
        from_date: date,
        to_date: date,
        *,
        game: str | None = None,
    ) -> list[LotteryDraw]:
        q = self._draw_query(lottery_id, game=game).where(
            LotteryDraw.draw_date >= from_date,
            LotteryDraw.draw_date <= to_date,
        )
        q = q.order_by(asc(LotteryDraw.draw_date), asc(LotteryDraw.draw_time).nullsfirst(), asc(LotteryDraw.id))
        return list((await self.db.execute(q)).scalars().unique().all())

    async def following_draws(
        self,
        lottery_id: uuid.UUID,
        base_date: date,
        count: int,
        *,
        include_base_date: bool = False,
        game: str | None = None,
    ) -> list[LotteryDraw]:
        q = self._draw_query(lottery_id, game=game)
        if include_base_date:
            q = q.where(LotteryDraw.draw_date >= base_date)
        else:
            q = q.where(LotteryDraw.draw_date > base_date)
        q = q.order_by(
            asc(LotteryDraw.draw_date),
            asc(LotteryDraw.draw_time).nullsfirst(),
            asc(LotteryDraw.id),
        ).limit(count)
        return list((await self.db.execute(q)).scalars().unique().all())

    async def previous_draws(
        self,
        lottery_id: uuid.UUID,
        base_date: date,
        count: int,
        *,
        include_base_date: bool = False,
        game: str | None = None,
    ) -> list[LotteryDraw]:
        q = self._draw_query(lottery_id, game=game)
        if include_base_date:
            q = q.where(LotteryDraw.draw_date <= base_date)
        else:
            q = q.where(LotteryDraw.draw_date < base_date)
        q = q.order_by(
            desc(LotteryDraw.draw_date),
            desc(LotteryDraw.draw_time).nullslast(),
            desc(LotteryDraw.id),
        ).limit(count)
        rows = list((await self.db.execute(q)).scalars().unique().all())
        # Return chronological
        return list(reversed(rows))

    async def number_occurrences(
        self,
        lottery_id: uuid.UUID,
        number: str,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        position: int | None = None,
        number_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
        order: str = "asc",
    ) -> tuple[list[tuple[LotteryDraw, LotteryDrawNumber]], int]:
        filters = [
            LotteryDraw.lottery_id == lottery_id,
            LotteryDrawNumber.number_value.in_(number_value_match_forms(number)),
        ]
        if from_date:
            filters.append(LotteryDraw.draw_date >= from_date)
        if to_date:
            filters.append(LotteryDraw.draw_date <= to_date)
        if position is not None:
            filters.append(LotteryDrawNumber.position == position)
        if number_type:
            filters.append(LotteryDrawNumber.number_type == number_type)

        count_q = (
            select(func.count())
            .select_from(LotteryDrawNumber)
            .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
            .where(and_(*filters))
        )
        total = int((await self.db.execute(count_q)).scalar_one())

        if (order or "asc").lower() == "desc":
            order_by = (
                desc(LotteryDraw.draw_date),
                desc(LotteryDraw.draw_time).nullslast(),
            )
        else:
            order_by = (
                asc(LotteryDraw.draw_date),
                asc(LotteryDraw.draw_time).nullsfirst(),
            )

        q = (
            select(LotteryDraw, LotteryDrawNumber)
            .join(LotteryDrawNumber, LotteryDrawNumber.draw_id == LotteryDraw.id)
            .where(and_(*filters))
            .order_by(*order_by)
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.db.execute(q)).all())
        return rows, total

    async def frequencies(
        self,
        lottery_id: uuid.UUID,
        from_date: date,
        to_date: date,
        *,
        position: int | None = None,
        number_type: str | None = None,
        limit: int = 20,
        order: str = "desc",
    ) -> tuple[list[tuple[str, int]], int]:
        filters = [
            LotteryDraw.lottery_id == lottery_id,
            LotteryDraw.draw_date >= from_date,
            LotteryDraw.draw_date <= to_date,
        ]
        if position is not None:
            filters.append(LotteryDrawNumber.position == position)
        if number_type:
            filters.append(LotteryDrawNumber.number_type == number_type)

        total_q = (
            select(func.count())
            .select_from(LotteryDrawNumber)
            .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
            .where(and_(*filters))
        )
        total = int((await self.db.execute(total_q)).scalar_one())

        ord_fn = desc if order == "desc" else asc
        q = (
            select(LotteryDrawNumber.number_value, func.count().label("cnt"))
            .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
            .where(and_(*filters))
            .group_by(LotteryDrawNumber.number_value)
            .order_by(ord_fn("cnt"), asc(LotteryDrawNumber.number_value))
            .limit(limit)
        )
        rows = [(r[0], int(r[1])) for r in (await self.db.execute(q)).all()]
        return rows, total

    async def repetitions(
        self,
        lottery_id: uuid.UUID,
        from_date: date,
        to_date: date,
        *,
        min_count: int = 2,
        position: int | None = None,
        number_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        filters = [
            LotteryDraw.lottery_id == lottery_id,
            LotteryDraw.draw_date >= from_date,
            LotteryDraw.draw_date <= to_date,
        ]
        if position is not None:
            filters.append(LotteryDrawNumber.position == position)
        if number_type:
            filters.append(LotteryDrawNumber.number_type == number_type)

        # First get numbers meeting min_count
        grouped = (
            select(
                LotteryDrawNumber.number_value.label("num"),
                func.count().label("cnt"),
                func.min(LotteryDraw.draw_date).label("first_d"),
                func.max(LotteryDraw.draw_date).label("last_d"),
            )
            .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
            .where(and_(*filters))
            .group_by(LotteryDrawNumber.number_value)
            .having(func.count() >= min_count)
            .order_by(desc("cnt"), asc(LotteryDrawNumber.number_value))
            .limit(limit)
        )
        groups = (await self.db.execute(grouped)).all()
        if not groups:
            return []

        numbers = [g.num for g in groups]
        detail_q = (
            select(
                LotteryDrawNumber.number_value,
                LotteryDraw.draw_date,
                LotteryDrawNumber.position,
            )
            .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
            .where(and_(*filters, LotteryDrawNumber.number_value.in_(numbers)))
            .order_by(asc(LotteryDraw.draw_date))
        )
        details = (await self.db.execute(detail_q)).all()
        by_num: dict[str, dict] = {
            g.num: {
                "number": g.num,
                "count": int(g.cnt),
                "first_date": g.first_d,
                "last_date": g.last_d,
                "dates": [],
                "positions": set(),
            }
            for g in groups
        }
        for num, ddate, pos in details:
            item = by_num[num]
            if ddate not in item["dates"]:
                item["dates"].append(ddate)
            item["positions"].add(pos)

        result = []
        for g in groups:
            item = by_num[g.num]
            result.append(
                {
                    "number": item["number"],
                    "count": item["count"],
                    "first_date": item["first_date"],
                    "last_date": item["last_date"],
                    "dates": item["dates"][:100],
                    "positions": sorted(item["positions"]),
                }
            )
        return result

    async def next_occurrences(
        self,
        lottery_id: uuid.UUID,
        number: str,
        after_date: date,
        *,
        limit: int = 10,
        position: int | None = None,
    ) -> list[tuple[LotteryDraw, LotteryDrawNumber]]:
        filters = [
            LotteryDraw.lottery_id == lottery_id,
            LotteryDrawNumber.number_value.in_(number_value_match_forms(number)),
            LotteryDraw.draw_date > after_date,
        ]
        if position is not None:
            filters.append(LotteryDrawNumber.position == position)
        q = (
            select(LotteryDraw, LotteryDrawNumber)
            .join(LotteryDrawNumber, LotteryDrawNumber.draw_id == LotteryDraw.id)
            .where(and_(*filters))
            .order_by(asc(LotteryDraw.draw_date), asc(LotteryDraw.draw_time).nullsfirst())
            .limit(limit)
        )
        return list((await self.db.execute(q)).all())

    async def numbers_by_lottery_dates(
        self,
        lottery_ids: list[uuid.UUID],
        from_date: date,
        to_date: date,
        *,
        position: int | None = None,
        number_type: str | None = None,
    ) -> list[tuple[uuid.UUID, date, str, int]]:
        """Returns (lottery_id, draw_date, number_value, position)."""
        filters = [
            LotteryDraw.lottery_id.in_(lottery_ids),
            LotteryDraw.draw_date >= from_date,
            LotteryDraw.draw_date <= to_date,
        ]
        if position is not None:
            filters.append(LotteryDrawNumber.position == position)
        if number_type:
            filters.append(LotteryDrawNumber.number_type == number_type)
        q = (
            select(
                LotteryDraw.lottery_id,
                LotteryDraw.draw_date,
                LotteryDrawNumber.number_value,
                LotteryDrawNumber.position,
            )
            .join(LotteryDrawNumber, LotteryDrawNumber.draw_id == LotteryDraw.id)
            .where(and_(*filters))
        )
        return list((await self.db.execute(q)).all())

    async def same_day_number_coincidences(
        self,
        numbers: list[str],
        *,
        lottery_ids: list[uuid.UUID] | None = None,
        position: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit_dates: int = 200,
    ) -> list[tuple[date, str, str, int, str | None]]:
        """
        Rows of (draw_date, number_value, lottery_name, position, position_label)
        for dates where ALL requested numbers appear at least once (any lottery
        unless lottery_ids is set). Caller aggregates by date.
        """
        from app.models.lottery import LotteryLottery

        nums = [str(n).zfill(2) if len(str(n)) <= 2 else str(n) for n in numbers]
        if len(nums) < 2:
            return []

        filters = [LotteryDrawNumber.number_value.in_(nums)]
        if lottery_ids:
            filters.append(LotteryDraw.lottery_id.in_(lottery_ids))
        if position is not None:
            filters.append(LotteryDrawNumber.position == int(position))
        if from_date:
            filters.append(LotteryDraw.draw_date >= from_date)
        if to_date:
            filters.append(LotteryDraw.draw_date <= to_date)

        # Dates that contain every number (across all matching draws that day)
        date_counts = (
            select(
                LotteryDraw.draw_date.label("dd"),
                func.count(func.distinct(LotteryDrawNumber.number_value)).label("nuniq"),
            )
            .join(LotteryDrawNumber, LotteryDrawNumber.draw_id == LotteryDraw.id)
            .where(and_(*filters))
            .group_by(LotteryDraw.draw_date)
            .having(func.count(func.distinct(LotteryDrawNumber.number_value)) >= len(set(nums)))
            .order_by(desc(LotteryDraw.draw_date))
            .limit(limit_dates)
        )
        date_rows = list((await self.db.execute(date_counts)).all())
        if not date_rows:
            return []
        dates = [r.dd for r in date_rows]

        detail_filters = [
            LotteryDrawNumber.number_value.in_(nums),
            LotteryDraw.draw_date.in_(dates),
        ]
        if lottery_ids:
            detail_filters.append(LotteryDraw.lottery_id.in_(lottery_ids))
        if position is not None:
            detail_filters.append(LotteryDrawNumber.position == int(position))

        detail_q = (
            select(
                LotteryDraw.draw_date,
                LotteryDrawNumber.number_value,
                LotteryLottery.name,
                LotteryDrawNumber.position,
                LotteryDrawNumber.position_label,
            )
            .join(LotteryDrawNumber, LotteryDrawNumber.draw_id == LotteryDraw.id)
            .join(LotteryLottery, LotteryLottery.id == LotteryDraw.lottery_id)
            .where(and_(*detail_filters))
            .order_by(desc(LotteryDraw.draw_date), asc(LotteryDrawNumber.number_value))
        )
        return list((await self.db.execute(detail_q)).all())
