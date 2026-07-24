"""Puerto de universo de draws para confirmación y seguimiento (sin mutar histórico)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from app.lottery.numeric_relations.historical.enums import SessionBucket
from app.lottery.numeric_relations.historical.models import DrawRef


def session_bucket_for(dt: datetime) -> SessionBucket:
    h = dt.hour
    if h < 12:
        return SessionBucket.MORNING
    if h < 18:
        return SessionBucket.AFTERNOON
    return SessionBucket.NIGHT


class DrawUniversePort(Protocol):
    def get_draw(self, draw_id: str) -> DrawRef | None: ...

    def list_draws_for_lottery(self, lottery_id: str) -> list[DrawRef]:
        """Orden cronológico ascendente (más antiguo primero)."""
        ...

    def list_draws_on_date(self, lottery_ids: list[str], on_date: date) -> list[DrawRef]: ...

    def draws_after(
        self,
        lottery_id: str,
        *,
        after: DrawRef,
        k: int,
        tz_name: str = "America/Santo_Domingo",
    ) -> list[DrawRef]: ...


class InMemoryDrawUniverse:
    """Universo en memoria para tests controlados — identidad siempre por draw_id."""

    def __init__(self, draws: list[DrawRef] | None = None) -> None:
        self._by_id: dict[str, DrawRef] = {}
        self._all: list[DrawRef] = []
        for d in draws or []:
            self.add(d)

    def add(self, draw: DrawRef) -> None:
        self._by_id[str(draw.draw_id)] = draw
        self._all.append(draw)

    def get_draw(self, draw_id: str) -> DrawRef | None:
        return self._by_id.get(str(draw_id))

    def list_draws_for_lottery(self, lottery_id: str) -> list[DrawRef]:
        lid = str(lottery_id)
        rows = [d for d in self._all if str(d.lottery_id) == lid]
        rows.sort(key=lambda d: (d.draw_date, d.draw_time or time(0, 0), str(d.draw_id)))
        return rows

    def list_draws_on_date(self, lottery_ids: list[str], on_date: date) -> list[DrawRef]:
        wanted = {str(x) for x in lottery_ids}
        rows = [
            d
            for d in self._all
            if str(d.lottery_id) in wanted and d.draw_date == on_date
        ]
        rows.sort(key=lambda d: (d.draw_time or time(0, 0), str(d.draw_id)))
        return rows

    def draws_after(
        self,
        lottery_id: str,
        *,
        after: DrawRef,
        k: int,
        tz_name: str = "America/Santo_Domingo",
    ) -> list[DrawRef]:
        """Próximos k sorteos estrictamente posteriores al ancla (misma lotería)."""
        seq = self.list_draws_for_lottery(lottery_id)
        after_dt = after.local_datetime(tz_name)
        after_id = str(after.draw_id)
        out: list[DrawRef] = []
        for d in seq:
            if str(d.draw_id) == after_id:
                continue
            if d.local_datetime(tz_name) > after_dt or (
                d.local_datetime(tz_name) == after_dt and str(d.draw_id) > after_id
            ):
                # Prefer datetime comparison; if equal datetime, use draw_id tie-break
                if d.local_datetime(tz_name) < after_dt:
                    continue
                if d.local_datetime(tz_name) == after_dt and str(d.draw_id) <= after_id:
                    continue
                out.append(d)
                if len(out) >= k:
                    break
        return out


def effective_window_bounds(
    anchor: DrawRef,
    *,
    mode: str,
    tz_name: str,
    hours_after: int | None = None,
) -> tuple[str, str | None, str | None]:
    """Devuelve (timezone, start_iso, end_iso) para auditoría."""
    start = anchor.local_datetime(tz_name)
    end: datetime | None = None
    if mode == "HOURS_AFTER" and hours_after:
        end = start + timedelta(hours=int(hours_after))
    elif mode == "SAME_DATE":
        end = datetime(
            anchor.draw_date.year,
            anchor.draw_date.month,
            anchor.draw_date.day,
            23,
            59,
            59,
            tzinfo=ZoneInfo(tz_name),
        )
    return tz_name, start.isoformat(), end.isoformat() if end else None
