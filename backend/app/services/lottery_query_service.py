"""Servicios de consulta histórica del módulo lottery."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.lottery import LotteryDraw, LotteryLottery
from app.schemas.lottery import (
    CalendarWindowResponse,
    ComparisonResponse,
    CrossLotteryResponse,
    DateQueryResponse,
    DrawNumberResult,
    DrawResult,
    DrawsWindowResponse,
    FrequencyItem,
    FrequencyResponse,
    LotteryLotteryResponse,
    NextOccurrenceItem,
    NextOccurrencesResponse,
    NumberOccurrence,
    NumberSearchResponse,
    PaginationMeta,
    QueryMeta,
    RangeQueryResponse,
    RepetitionItem,
    RepetitionResponse,
    WarningMessage,
)
from app.services.lottery_aliases import LotteryResolver
from app.services.lottery_exceptions import LotteryQueryError
from app.services.lottery_repository import LotteryRepository


def _lottery_resp(lot: LotteryLottery) -> LotteryLotteryResponse:
    return LotteryLotteryResponse.model_validate(lot)


def _draw_result(draw: LotteryDraw, *, include_numbers: bool = True) -> DrawResult:
    numbers: list[DrawNumberResult] = []
    if include_numbers:
        ordered = sorted(draw.numbers, key=lambda n: (n.position, n.number_type))
        numbers = [
            DrawNumberResult(
                position=n.position,
                position_label=n.position_label,
                number_value=n.number_value,
                number_raw=n.number_raw,
                number_type=n.number_type,
            )
            for n in ordered
        ]
    return DrawResult(
        id=draw.id,
        draw_date=draw.draw_date,
        draw_time=draw.draw_time,
        game_name=draw.game_name,
        source_reference=draw.source_reference,
        numbers=numbers,
    )


def _meta(
    query: dict[str, Any],
    lottery: LotteryLottery | None,
    *,
    filters: dict | None = None,
    warnings: list[WarningMessage] | None = None,
) -> QueryMeta:
    return QueryMeta(
        query=query,
        resolved_lottery=_lottery_resp(lottery) if lottery else None,
        filters=filters or {},
        warnings=warnings or [],
        generated_at=datetime.now(timezone.utc),
    )


def _validate_range(from_date: date, to_date: date) -> None:
    if from_date > to_date:
        raise LotteryQueryError("RANGE_INVALID", "from debe ser <= to")
    days = (to_date - from_date).days + 1
    if days > settings.lottery_max_range_days:
        raise LotteryQueryError(
            "RANGE_TOO_LARGE",
            f"Rango máximo {settings.lottery_max_range_days} días",
            details={"days": days},
        )


def _page_size(page_size: int | None) -> int:
    size = page_size or settings.lottery_default_page_size
    if size < 1 or size > settings.lottery_max_page_size:
        raise LotteryQueryError(
            "COUNT_INVALID",
            f"page_size debe estar entre 1 y {settings.lottery_max_page_size}",
        )
    return size


def _validate_number(number: str) -> str:
    value = (number or "").strip()
    if not value or len(value) > 32:
        raise LotteryQueryError("NUMBER_INVALID", "Número inválido")
    # Preserve leading zeros — do not coerce to int
    if not all(ch.isalnum() or ch in "-+" for ch in value):
        raise LotteryQueryError("NUMBER_INVALID", "Caracteres no permitidos en número")
    return value


class LotteryQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.resolver = LotteryResolver(db)
        self.repo = LotteryRepository(db)

    async def by_date(
        self,
        lottery: str,
        draw_date: date,
        *,
        game: str | None = None,
        include_numbers: bool = True,
    ) -> DateQueryResponse:
        lot = await self.resolver.resolve_or_raise(lottery)
        draws = await self.repo.draws_by_date(lot.id, draw_date, game=game)
        warnings: list[WarningMessage] = []
        if len(draws) > 1:
            warnings.append(
                WarningMessage(
                    code="MULTIPLE_DRAWS_SAME_DAY",
                    message=f"Se encontraron {len(draws)} sorteos en la misma fecha.",
                )
            )
        return DateQueryResponse(
            meta=_meta(
                {"lottery": lottery, "date": str(draw_date), "game": game},
                lot,
                filters={"game": game},
                warnings=warnings,
            ),
            date=draw_date,
            total=len(draws),
            draws=[_draw_result(d, include_numbers=include_numbers) for d in draws],
        )

    async def range(
        self,
        lottery: str,
        from_date: date,
        to_date: date,
        *,
        game: str | None = None,
        number: str | None = None,
        position: int | None = None,
        page: int = 1,
        page_size: int | None = None,
        sort: str = "asc",
    ) -> RangeQueryResponse:
        _validate_range(from_date, to_date)
        if page < 1:
            raise LotteryQueryError("COUNT_INVALID", "page debe ser >= 1")
        size = _page_size(page_size)
        if sort not in ("asc", "desc"):
            raise LotteryQueryError("RANGE_INVALID", "sort debe ser asc|desc")
        lot = await self.resolver.resolve_or_raise(lottery)
        num = _validate_number(number) if number is not None else None
        offset = (page - 1) * size
        draws, total = await self.repo.draws_in_range(
            lot.id,
            from_date,
            to_date,
            game=game,
            number=num,
            position=position,
            sort=sort,
            limit=size,
            offset=offset,
        )
        pages = max(1, math.ceil(total / size)) if total else 0
        return RangeQueryResponse(
            meta=_meta(
                {
                    "lottery": lottery,
                    "from": str(from_date),
                    "to": str(to_date),
                    "game": game,
                    "number": num,
                    "position": position,
                },
                lot,
            ),
            from_date=from_date,
            to_date=to_date,
            pagination=PaginationMeta(
                page=page, page_size=size, total=total, total_pages=pages
            ),
            draws=[_draw_result(d) for d in draws],
        )

    async def following_days(
        self,
        lottery: str,
        base_date: date,
        days: int,
        *,
        include_base_date: bool = False,
        game: str | None = None,
    ) -> CalendarWindowResponse:
        if days < 1 or days > settings.lottery_max_days_window:
            raise LotteryQueryError(
                "COUNT_INVALID",
                f"days debe estar entre 1 y {settings.lottery_max_days_window}",
            )
        lot = await self.resolver.resolve_or_raise(lottery)
        if include_base_date:
            calendar_from = base_date
            calendar_to = base_date + timedelta(days=days - 1)
        else:
            calendar_from = base_date + timedelta(days=1)
            calendar_to = base_date + timedelta(days=days)
        draws = await self.repo.draws_in_calendar_window(
            lot.id, calendar_from, calendar_to, game=game
        )
        with_draws = sorted({d.draw_date for d in draws})
        all_days = [
            calendar_from + timedelta(days=i)
            for i in range((calendar_to - calendar_from).days + 1)
        ]
        without = [d for d in all_days if d not in set(with_draws)]
        return CalendarWindowResponse(
            meta=_meta(
                {
                    "lottery": lottery,
                    "date": str(base_date),
                    "days": days,
                    "include_base_date": include_base_date,
                    "semantics": "calendar_days",
                },
                lot,
                warnings=[
                    WarningMessage(
                        code="CALENDAR_DAYS",
                        message="Consulta por días calendario, no por cantidad de sorteos.",
                    )
                ],
            ),
            days_requested=days,
            include_base_date=include_base_date,
            calendar_from=calendar_from,
            calendar_to=calendar_to,
            days_with_draws=with_draws,
            days_without_draws=without,
            total_draws=len(draws),
            draws=[_draw_result(d) for d in draws],
        )

    async def previous_days(
        self,
        lottery: str,
        base_date: date,
        days: int,
        *,
        include_base_date: bool = False,
        game: str | None = None,
    ) -> CalendarWindowResponse:
        if days < 1 or days > settings.lottery_max_days_window:
            raise LotteryQueryError(
                "COUNT_INVALID",
                f"days debe estar entre 1 y {settings.lottery_max_days_window}",
            )
        lot = await self.resolver.resolve_or_raise(lottery)
        if include_base_date:
            calendar_to = base_date
            calendar_from = base_date - timedelta(days=days - 1)
        else:
            calendar_to = base_date - timedelta(days=1)
            calendar_from = base_date - timedelta(days=days)
        draws = await self.repo.draws_in_calendar_window(
            lot.id, calendar_from, calendar_to, game=game
        )
        with_draws = sorted({d.draw_date for d in draws})
        all_days = [
            calendar_from + timedelta(days=i)
            for i in range((calendar_to - calendar_from).days + 1)
        ]
        without = [d for d in all_days if d not in set(with_draws)]
        return CalendarWindowResponse(
            meta=_meta(
                {
                    "lottery": lottery,
                    "date": str(base_date),
                    "days": days,
                    "include_base_date": include_base_date,
                    "semantics": "calendar_days",
                },
                lot,
            ),
            days_requested=days,
            include_base_date=include_base_date,
            calendar_from=calendar_from,
            calendar_to=calendar_to,
            days_with_draws=with_draws,
            days_without_draws=without,
            total_draws=len(draws),
            draws=[_draw_result(d) for d in draws],
        )

    async def following_draws(
        self,
        lottery: str,
        base_date: date,
        count: int,
        *,
        include_base_date: bool = False,
        game: str | None = None,
    ) -> DrawsWindowResponse:
        if count < 1 or count > settings.lottery_max_draw_count:
            raise LotteryQueryError(
                "COUNT_INVALID",
                f"count debe estar entre 1 y {settings.lottery_max_draw_count}",
            )
        lot = await self.resolver.resolve_or_raise(lottery)
        draws = await self.repo.following_draws(
            lot.id, base_date, count, include_base_date=include_base_date, game=game
        )
        return DrawsWindowResponse(
            meta=_meta(
                {
                    "lottery": lottery,
                    "date": str(base_date),
                    "count": count,
                    "include_base_date": include_base_date,
                    "semantics": "next_n_draws",
                },
                lot,
                warnings=[
                    WarningMessage(
                        code="DRAW_COUNT",
                        message="Consulta por N sorteos existentes, no por N días calendario.",
                    )
                ],
            ),
            count_requested=count,
            include_base_date=include_base_date,
            total=len(draws),
            draws=[_draw_result(d) for d in draws],
            chronological=True,
        )

    async def previous_draws(
        self,
        lottery: str,
        base_date: date,
        count: int,
        *,
        include_base_date: bool = False,
        game: str | None = None,
    ) -> DrawsWindowResponse:
        if count < 1 or count > settings.lottery_max_draw_count:
            raise LotteryQueryError(
                "COUNT_INVALID",
                f"count debe estar entre 1 y {settings.lottery_max_draw_count}",
            )
        lot = await self.resolver.resolve_or_raise(lottery)
        draws = await self.repo.previous_draws(
            lot.id, base_date, count, include_base_date=include_base_date, game=game
        )
        return DrawsWindowResponse(
            meta=_meta(
                {
                    "lottery": lottery,
                    "date": str(base_date),
                    "count": count,
                    "include_base_date": include_base_date,
                    "semantics": "previous_n_draws",
                },
                lot,
            ),
            count_requested=count,
            include_base_date=include_base_date,
            total=len(draws),
            draws=[_draw_result(d) for d in draws],
            chronological=True,
        )

    async def by_number(
        self,
        lottery: str,
        number: str,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        position: int | None = None,
        number_type: str | None = None,
        page: int = 1,
        page_size: int | None = None,
        order: str = "asc",
    ) -> NumberSearchResponse:
        num = _validate_number(number)
        if from_date and to_date:
            _validate_range(from_date, to_date)
        if page < 1:
            raise LotteryQueryError("COUNT_INVALID", "page debe ser >= 1")
        size = _page_size(page_size)
        lot = await self.resolver.resolve_or_raise(lottery)
        rows, total = await self.repo.number_occurrences(
            lot.id,
            num,
            from_date=from_date,
            to_date=to_date,
            position=position,
            number_type=number_type,
            limit=size,
            offset=(page - 1) * size,
            order=order,
        )
        pages = max(1, math.ceil(total / size)) if total else 0
        occ = [
            NumberOccurrence(
                draw_id=draw.id,
                draw_date=draw.draw_date,
                draw_time=draw.draw_time,
                game_name=draw.game_name,
                position=n.position,
                position_label=n.position_label,
                number_value=n.number_value,
                number_type=n.number_type,
            )
            for draw, n in rows
        ]
        return NumberSearchResponse(
            meta=_meta({"lottery": lottery, "number": num}, lot),
            number=num,
            pagination=PaginationMeta(page=page, page_size=size, total=total, total_pages=pages),
            occurrences=occ,
        )

    async def frequencies(
        self,
        lottery: str,
        from_date: date,
        to_date: date,
        *,
        position: int | None = None,
        number_type: str | None = None,
        limit: int = 20,
        order: str = "desc",
    ) -> FrequencyResponse:
        _validate_range(from_date, to_date)
        if limit < 1 or limit > settings.lottery_max_stats_limit:
            raise LotteryQueryError("COUNT_INVALID", "limit inválido")
        lot = await self.resolver.resolve_or_raise(lottery)
        rows, total = await self.repo.frequencies(
            lot.id,
            from_date,
            to_date,
            position=position,
            number_type=number_type,
            limit=limit,
            order=order,
        )
        items = [
            FrequencyItem(
                number=num,
                count=cnt,
                percentage=round((cnt / total) * 100, 4) if total else 0.0,
            )
            for num, cnt in rows
        ]
        return FrequencyResponse(
            meta=_meta(
                {"lottery": lottery, "from": str(from_date), "to": str(to_date)},
                lot,
                warnings=[
                    WarningMessage(
                        code="INFORMATIVE_ONLY",
                        message="Frecuencia histórica — no es predicción ni probabilidad de ganar.",
                    )
                ],
            ),
            from_date=from_date,
            to_date=to_date,
            total_observations=total,
            items=items,
        )

    async def repetitions(
        self,
        lottery: str,
        from_date: date,
        to_date: date,
        *,
        min_count: int = 2,
        position: int | None = None,
        number_type: str | None = None,
        limit: int = 50,
    ) -> RepetitionResponse:
        _validate_range(from_date, to_date)
        if min_count < 2:
            raise LotteryQueryError("COUNT_INVALID", "min_count debe ser >= 2")
        lot = await self.resolver.resolve_or_raise(lottery)
        rows = await self.repo.repetitions(
            lot.id,
            from_date,
            to_date,
            min_count=min_count,
            position=position,
            number_type=number_type,
            limit=min(limit, settings.lottery_max_stats_limit),
        )
        items = [RepetitionItem(**r) for r in rows]
        return RepetitionResponse(
            meta=_meta({"lottery": lottery}, lot),
            from_date=from_date,
            to_date=to_date,
            min_count=min_count,
            items=items,
        )

    async def next_occurrences(
        self,
        lottery: str,
        number: str,
        after_date: date,
        *,
        limit: int = 10,
        position: int | None = None,
    ) -> NextOccurrencesResponse:
        num = _validate_number(number)
        if limit < 1 or limit > settings.lottery_max_stats_limit:
            raise LotteryQueryError("COUNT_INVALID", "limit inválido")
        lot = await self.resolver.resolve_or_raise(lottery)
        rows = await self.repo.next_occurrences(
            lot.id, num, after_date, limit=limit, position=position
        )
        items = [
            NextOccurrenceItem(
                draw_id=draw.id,
                draw_date=draw.draw_date,
                draw_time=draw.draw_time,
                position=n.position,
                position_label=n.position_label,
                number_value=n.number_value,
                number_type=n.number_type,
            )
            for draw, n in rows
        ]
        return NextOccurrencesResponse(
            meta=_meta(
                {"lottery": lottery, "number": num, "after_date": str(after_date)},
                lot,
                warnings=[
                    WarningMessage(
                        code="HISTORICAL_ONLY",
                        message="Próxima aparición histórica — no predice resultados futuros.",
                    )
                ],
            ),
            number=num,
            after_date=after_date,
            items=items,
        )

    async def compare(
        self,
        lotteries: list[str],
        from_date: date,
        to_date: date,
        mode: str,
        *,
        position: int | None = None,
        number_type: str | None = None,
        include_draws: bool = False,
        limit: int = 50,
        intersection_scope: str = "within_range",
    ) -> ComparisonResponse:
        _validate_range(from_date, to_date)
        if len(lotteries) < 2 or len(lotteries) > settings.lottery_max_compare_lotteries:
            raise LotteryQueryError("COUNT_INVALID", "Se requieren entre 2 y 10 loterías")
        resolved = [await self.resolver.resolve_or_raise(x) for x in lotteries]
        ids = [r.id for r in resolved]
        rows = await self.repo.numbers_by_lottery_dates(
            ids, from_date, to_date, position=position, number_type=number_type
        )
        # Map lottery id → name
        id_to_lot = {r.id: r for r in resolved}

        data: dict[str, Any] = {}
        if mode == "same_date":
            by_date: dict[date, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
            for lid, ddate, num, _pos in rows:
                by_date[ddate][id_to_lot[lid].name].add(num)
            items = []
            for ddate, per_lot in sorted(by_date.items()):
                if len(per_lot) < 2:
                    continue
                sets = list(per_lot.values())
                inter = set.intersection(*sets) if sets else set()
                items.append(
                    {
                        "date": str(ddate),
                        "lotteries": {k: sorted(v) for k, v in per_lot.items()},
                        "common_numbers": sorted(inter),
                    }
                )
                if len(items) >= limit:
                    break
            data = {"items": items, "total": len(items)}

        elif mode == "repeated_numbers":
            by_num: dict[str, dict[str, Any]] = {}
            for lid, ddate, num, _pos in rows:
                name = id_to_lot[lid].name
                entry = by_num.setdefault(
                    num, {"number": num, "lotteries": set(), "counts": defaultdict(int), "dates": set()}
                )
                entry["lotteries"].add(name)
                entry["counts"][name] += 1
                entry["dates"].add(ddate)
            items = []
            for num, entry in by_num.items():
                if len(entry["lotteries"]) < 2:
                    continue
                items.append(
                    {
                        "number": num,
                        "lotteries": sorted(entry["lotteries"]),
                        "counts": dict(entry["counts"]),
                        "dates": sorted(str(d) for d in entry["dates"])[:50],
                        "total": sum(entry["counts"].values()),
                    }
                )
            items.sort(key=lambda x: (-x["total"], x["number"]))
            data = {"items": items[:limit], "total": len(items)}

        elif mode == "frequencies":
            # Per lottery top frequencies
            per = {}
            for lot in resolved:
                freq_rows, total = await self.repo.frequencies(
                    lot.id, from_date, to_date, position=position, number_type=number_type, limit=limit
                )
                per[lot.name] = {
                    "total_observations": total,
                    "items": [{"number": n, "count": c} for n, c in freq_rows],
                }
            data = {"by_lottery": per}

        elif mode == "intersections":
            if intersection_scope == "same_day":
                by_date_nums: dict[date, dict[uuid.UUID, set[str]]] = defaultdict(lambda: defaultdict(set))
                for lid, ddate, num, _pos in rows:
                    by_date_nums[ddate][lid].add(num)
                items = []
                for ddate, per_lid in sorted(by_date_nums.items()):
                    if len(per_lid) < len(ids):
                        continue
                    sets = [per_lid[i] for i in ids if i in per_lid]
                    if len(sets) < 2:
                        continue
                    inter = set.intersection(*sets)
                    if inter:
                        items.append({"date": str(ddate), "numbers": sorted(inter)})
                    if len(items) >= limit:
                        break
                data = {"scope": "same_day", "items": items}
            else:
                per_lid: dict[uuid.UUID, set[str]] = defaultdict(set)
                for lid, _ddate, num, _pos in rows:
                    per_lid[lid].add(num)
                sets = [per_lid[i] for i in ids]
                inter = set.intersection(*sets) if sets else set()
                data = {
                    "scope": "within_range",
                    "numbers": sorted(inter)[:limit],
                    "total": len(inter),
                }

        elif mode == "timeline":
            by_date: dict[date, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
            for lid, ddate, num, _pos in rows:
                name = id_to_lot[lid].name
                if num not in by_date[ddate][name]:
                    by_date[ddate][name].append(num)
            items = [
                {"date": str(ddate), "lotteries": dict(per)}
                for ddate, per in sorted(by_date.items())[:limit]
            ]
            data = {"items": items, "total": len(by_date)}
        else:
            raise LotteryQueryError("RANGE_INVALID", f"mode no soportado: {mode}")

        if include_draws and mode == "timeline":
            data["note"] = "include_draws limitado; use endpoints de resultados para detalle."

        return ComparisonResponse(
            meta=_meta(
                {"lotteries": lotteries, "mode": mode, "from": str(from_date), "to": str(to_date)},
                None,
                warnings=[
                    WarningMessage(
                        code="INFORMATIVE_ONLY",
                        message="Comparación histórica — no garantiza resultados futuros.",
                    )
                ],
            ),
            mode=mode,
            lotteries=[_lottery_resp(r) for r in resolved],
            from_date=from_date,
            to_date=to_date,
            data=data,
        )

    async def cross_lottery(
        self,
        lotteries: list[str],
        from_date: date,
        to_date: date,
        mode: str,
        *,
        number: str | None = None,
    ) -> CrossLotteryResponse:
        _validate_range(from_date, to_date)
        if len(lotteries) < 2:
            raise LotteryQueryError("COUNT_INVALID", "Se requieren al menos 2 loterías")
        days = (to_date - from_date).days + 1
        if days > 366:
            raise LotteryQueryError("RANGE_TOO_LARGE", "cross-lottery máximo 366 días")
        resolved = [await self.resolver.resolve_or_raise(x) for x in lotteries]
        ids = [r.id for r in resolved]
        rows = await self.repo.numbers_by_lottery_dates(ids, from_date, to_date)
        id_to_name = {r.id: r.name for r in resolved}
        data: dict[str, Any] = {}

        if mode == "same_day":
            cmp = await self.compare(
                lotteries, from_date, to_date, "intersections", intersection_scope="same_day"
            )
            data = cmp.data
        elif mode == "within_range":
            cmp = await self.compare(
                lotteries, from_date, to_date, "intersections", intersection_scope="within_range"
            )
            data = cmp.data
        elif mode == "after_occurrence":
            if not number:
                raise LotteryQueryError("NUMBER_INVALID", "number requerido para after_occurrence")
            num = _validate_number(number)
            # Find occurrences in first lottery, then see if number appears later in others
            primary = resolved[0]
            primary_dates = sorted(
                {ddate for lid, ddate, n, _p in rows if lid == primary.id and n == num}
            )
            followups = []
            for d0 in primary_dates[:20]:
                later = [
                    {"lottery": id_to_name[lid], "date": str(ddate)}
                    for lid, ddate, n, _p in rows
                    if lid != primary.id and n == num and ddate > d0
                ]
                if later:
                    followups.append({"after": str(d0), "primary": primary.name, "later": later[:20]})
            data = {"number": num, "items": followups[:50]}
        else:
            raise LotteryQueryError("RANGE_INVALID", f"mode no soportado: {mode}")

        return CrossLotteryResponse(
            meta=_meta({"lotteries": lotteries, "mode": mode}, None),
            mode=mode,
            lotteries=[_lottery_resp(r) for r in resolved],
            from_date=from_date,
            to_date=to_date,
            data=data,
        )

    async def same_day_number_coincidences(
        self,
        numbers: list[str],
        *,
        lotteries: list[str] | None = None,
        position: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit_dates: int = 200,
        also_all_positions_totals: bool = True,
    ) -> dict[str, Any]:
        """
        Dates where all numbers appear the same calendar day (any lottery by default).
        Position filter is optional; when set, only that position counts.
        """
        nums = []
        for n in numbers:
            s = str(n).strip()
            if not s:
                continue
            nums.append(s.zfill(2) if len(s) <= 2 and s.isdigit() else s)
        nums = list(dict.fromkeys(nums))
        if len(nums) < 2:
            raise LotteryQueryError("VALIDATION", "Se requieren al menos 2 números")

        lottery_ids: list[Any] | None = None
        resolved_names: list[str] = []
        if lotteries:
            resolved = []
            for name in lotteries:
                try:
                    resolved.append(await self.resolver.resolve_or_raise(str(name)))
                except Exception:  # noqa: BLE001
                    continue
            lottery_ids = [r.id for r in resolved]
            resolved_names = [r.name for r in resolved]

        rows = await self.repo.same_day_number_coincidences(
            nums,
            lottery_ids=lottery_ids,
            position=position,
            from_date=from_date,
            to_date=to_date,
            limit_dates=limit_dates,
        )
        by_date: dict[date, list[dict[str, Any]]] = defaultdict(list)
        seen_key: set[tuple[Any, ...]] = set()
        for ddate, num, lot_name, pos, pos_label in rows:
            key = (ddate, num, lot_name, pos)
            if key in seen_key:
                continue
            seen_key.add(key)
            by_date[ddate].append(
                {
                    "number": str(num).zfill(2) if len(str(num)) <= 2 else str(num),
                    "lottery": lot_name,
                    "position": int(pos) if pos is not None else None,
                    "position_label": pos_label or (str(pos) if pos is not None else None),
                }
            )

        items = []
        for ddate in sorted(by_date.keys(), reverse=True):
            appearances = by_date[ddate]
            # Ensure all numbers present (guard)
            present = {a["number"] for a in appearances}
            if not set(nums).issubset(present):
                continue
            items.append({"date": str(ddate), "appearances": appearances})

        total_all = None
        if also_all_positions_totals and position is not None:
            rows_all = await self.repo.same_day_number_coincidences(
                nums,
                lottery_ids=lottery_ids,
                position=None,
                from_date=from_date,
                to_date=to_date,
                limit_dates=limit_dates,
            )
            dates_all = {r[0] for r in rows_all}
            # Re-check containment per date
            tmp: dict[date, set[str]] = defaultdict(set)
            for ddate, num, *_rest in rows_all:
                tmp[ddate].add(str(num).zfill(2) if len(str(num)) <= 2 else str(num))
            total_all = sum(1 for d, s in tmp.items() if set(nums).issubset(s))

        return {
            "relation": "same_day",
            "numbers": nums,
            "position_filter": position,
            "preferred_position": 1,
            "all_lotteries": not bool(lottery_ids),
            "lotteries": resolved_names,
            "total": len(items),
            "total_all_positions": total_all,
            "items": items,
            "from_date": str(from_date) if from_date else None,
            "to_date": str(to_date) if to_date else None,
        }
