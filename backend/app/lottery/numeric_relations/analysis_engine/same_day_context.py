"""Same-day cross-lottery confirmation — official socio geometry.

Deterministic evidence:
  X (observed) → Tabla 1 → C
  Y (same day, other lottery/position) → Tabla 2 → C
  ⇒ C strengthened (SAME_DAY_CROSS_LOTTERY_CONFIRMATION)

Does not change Tabla 1 / Tabla 2 formulas.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Iterable, Sequence

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.constants import N_MAX, N_MIN

EVIDENCE_CODE = "SAME_DAY_CROSS_LOTTERY_CONFIRMATION"

_POS_ALIASES = {
    "first": "primera",
    "1": "primera",
    "primera": "primera",
    "second": "segunda",
    "2": "segunda",
    "segunda": "segunda",
    "third": "tercera",
    "3": "tercera",
    "tercera": "tercera",
}


@dataclass
class DayAppearance:
    number: int
    lottery: str
    lottery_id: str | None
    date: str
    position: str  # primera|segunda|tercera
    draw_id: str | None = None
    position_index: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SameDayCrossConfirmation:
    """X → T1 → C  and  Y(same day) → T2 → C."""

    evidence_code: str
    observed_x: int
    companion_c: int
    confirmer_y: int
    date: str
    lottery_x: str | None
    lottery_y: str | None
    position_x: str | None
    position_y: str | None
    draw_id_x: str | None
    draw_id_y: str | None
    table1_route: str
    table2_route: str
    distinct_lotteries: bool
    distinct_draws: bool
    confirmation_level: str
    path: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SameDayContext:
    date: str
    appearances: list[DayAppearance]
    """Numbers used as confirmers (filtered by position policy)."""
    confirmer_numbers: list[int]
    """All numbers drawn that day (1..100), for UI."""
    all_numbers: list[int]
    by_lottery: dict[str, dict[str, Any]]
    position_policy: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "appearances": [a.to_dict() for a in self.appearances],
            "confirmer_numbers": list(self.confirmer_numbers),
            "all_numbers": list(self.all_numbers),
            "by_lottery": self.by_lottery,
            "position_policy": list(self.position_policy),
        }


def _norm_pos(label: str | int | None) -> str | None:
    if label is None:
        return None
    key = str(label).strip().lower()
    return _POS_ALIASES.get(key)


def _parse_number(raw: Any) -> int | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s in {"—", "-"}:
        return None
    try:
        n = int(s)
    except ValueError:
        digits = "".join(ch for ch in s if ch.isdigit())
        if not digits:
            return None
        n = int(digits)
    if not (N_MIN <= n <= N_MAX):
        return None
    return n


def normalize_position_policy(positions: Sequence[str] | None) -> list[str]:
    """Default socio methodology: primeras posiciones across featured lotteries."""
    if not positions:
        return ["primera"]
    out: list[str] = []
    for p in positions:
        n = _norm_pos(p)
        if n and n not in out:
            out.append(n)
    return out or ["primera"]


def appearances_from_result_rows(
    rows: Iterable[dict[str, Any]],
    *,
    draw_date: date | str,
) -> list[DayAppearance]:
    date_s = draw_date.isoformat() if isinstance(draw_date, date) else str(draw_date)[:10]
    out: list[DayAppearance] = []
    for row in rows:
        lot = str(row.get("lottery") or row.get("lottery_name") or "")
        lot_id = str(row.get("lottery_id") or "") or None
        draw_id = str(row.get("draw_id") or "") or None
        d = str(row.get("date") or date_s)[:10]
        for idx, key in enumerate(("primera", "segunda", "tercera"), start=1):
            n = _parse_number(row.get(key))
            if n is None:
                continue
            out.append(
                DayAppearance(
                    number=n,
                    lottery=lot,
                    lottery_id=lot_id,
                    date=d,
                    position=key,
                    draw_id=draw_id,
                    position_index=idx,
                )
            )
    return out


def build_same_day_context(
    rows: Iterable[dict[str, Any]],
    *,
    draw_date: date | str,
    positions: Sequence[str] | None = None,
    exclude_numbers: Sequence[int] | None = None,
) -> SameDayContext:
    date_s = draw_date.isoformat() if isinstance(draw_date, date) else str(draw_date)[:10]
    policy = normalize_position_policy(positions)
    appearances = appearances_from_result_rows(rows, draw_date=date_s)
    exclude = {int(x) for x in (exclude_numbers or [])}

    by_lottery: dict[str, dict[str, Any]] = {}
    for row in rows:
        lot = str(row.get("lottery") or row.get("lottery_name") or "—")
        by_lottery[lot] = {
            "lottery": lot,
            "lottery_id": row.get("lottery_id"),
            "date": str(row.get("date") or date_s)[:10],
            "draw_id": row.get("draw_id"),
            "primera": row.get("primera"),
            "segunda": row.get("segunda"),
            "tercera": row.get("tercera"),
            "hora": row.get("hora"),
        }

    all_numbers: list[int] = []
    seen_all: set[int] = set()
    for a in appearances:
        if a.number not in seen_all:
            seen_all.add(a.number)
            all_numbers.append(a.number)

    confirmer_numbers: list[int] = []
    seen_c: set[int] = set()
    for a in appearances:
        if a.position not in policy:
            continue
        if a.number in exclude:
            continue
        if a.number in seen_c:
            continue
        seen_c.add(a.number)
        confirmer_numbers.append(a.number)

    return SameDayContext(
        date=date_s,
        appearances=appearances,
        confirmer_numbers=confirmer_numbers,
        all_numbers=all_numbers,
        by_lottery=by_lottery,
        position_policy=policy,
    )


def same_day_context_from_dict(payload: dict[str, Any] | None) -> SameDayContext | None:
    """Rebuild SameDayContext from API/engine payload for metadata enrichment."""
    if not payload or not isinstance(payload, dict):
        return None
    apps: list[DayAppearance] = []
    for raw in payload.get("appearances") or []:
        try:
            apps.append(
                DayAppearance(
                    number=int(raw["number"]),
                    lottery=str(raw.get("lottery") or "—"),
                    lottery_id=raw.get("lottery_id"),
                    date=str(raw.get("date") or payload.get("date") or "")[:10],
                    position=str(raw.get("position") or "primera"),
                    draw_id=raw.get("draw_id"),
                    position_index=int(raw.get("position_index") or 0),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    confirmers: list[int] = []
    for n in payload.get("confirmer_numbers") or []:
        try:
            confirmers.append(int(n))
        except (TypeError, ValueError):
            continue
    return SameDayContext(
        date=str(payload.get("date") or "")[:10],
        appearances=apps,
        confirmer_numbers=confirmers,
        all_numbers=[int(x) for x in (payload.get("all_numbers") or []) if str(x).isdigit()],
        by_lottery=dict(payload.get("by_lottery") or {}),
        position_policy=list(payload.get("position_policy") or ["primera"]),
    )


def find_same_day_cross_confirmations(
    seed_numbers: Sequence[int],
    confirmer_numbers: Sequence[int],
    *,
    catalog: TableCatalog | None = None,
    day_context: SameDayContext | None = None,
    date_s: str | None = None,
) -> list[SameDayCrossConfirmation]:
    """Find C strengthened by X∈seeds (T1) and Y∈confirmers (T2)."""
    cat = catalog or build_catalog()
    seeds = [int(x) for x in seed_numbers if N_MIN <= int(x) <= N_MAX]
    confirmers = [
        int(y)
        for y in confirmer_numbers
        if N_MIN <= int(y) <= N_MAX and int(y) not in seeds
    ]
    if not seeds or not confirmers:
        return []

    by_num: dict[int, list[DayAppearance]] = {}
    if day_context:
        for a in day_context.appearances:
            by_num.setdefault(a.number, []).append(a)
        date_s = date_s or day_context.date
    date_s = date_s or ""

    out: list[SameDayCrossConfirmation] = []
    seen: set[tuple[int, int, int]] = set()

    for x in seeds:
        companions = list(cat.get_table1_companions(x))
        ax = (by_num.get(x) or [None])[0]
        for c in companions:
            if c == x:
                continue
            t2 = set(cat.get_table2_neighbors(c, exclude_self=True))
            for y in confirmers:
                if y not in t2:
                    continue
                key = (x, c, y)
                if key in seen:
                    continue
                seen.add(key)
                ay = (by_num.get(y) or [None])[0]
                lot_x = ax.lottery if ax else None
                lot_y = ay.lottery if ay else None
                draw_x = ax.draw_id if ax else None
                draw_y = ay.draw_id if ay else None
                out.append(
                    SameDayCrossConfirmation(
                        evidence_code=EVIDENCE_CODE,
                        observed_x=x,
                        companion_c=c,
                        confirmer_y=y,
                        date=date_s,
                        lottery_x=lot_x,
                        lottery_y=lot_y,
                        position_x=ax.position if ax else None,
                        position_y=ay.position if ay else None,
                        draw_id_x=draw_x,
                        draw_id_y=draw_y,
                        table1_route=f"{x} → Tabla 1 → {c}",
                        table2_route=f"{y} → Tabla 2 → {c}",
                        distinct_lotteries=bool(lot_x and lot_y and lot_x != lot_y),
                        distinct_draws=bool(draw_x and draw_y and draw_x != draw_y)
                        or bool(lot_x and lot_y and lot_x != lot_y),
                        confirmation_level="direct_t1_t2_same_day",
                        path=[x, c, y],
                    )
                )
    # Prefer more specific T2 groups, then more confirmers per C, then lower C
    def _sort_key(ev: SameDayCrossConfirmation) -> tuple:
        try:
            gsize = len(cat.table2_code_to_numbers.get(cat.get_table2_code_for_number(ev.companion_c), []))
        except Exception:
            gsize = 99
        return (gsize, -int(ev.distinct_lotteries), ev.companion_c, ev.confirmer_y)

    return sorted(out, key=_sort_key)


def explain_same_day_cross(ev: SameDayCrossConfirmation) -> str:
    lot_x = ev.lottery_x or "una lotería"
    lot_y = ev.lottery_y or "otra lotería"
    return (
        f"El {ev.observed_x} relaciona al {ev.companion_c} mediante Tabla 1. "
        f"El {ev.confirmer_y}, salido en {lot_y} el mismo día"
        f"{f' que {lot_x}' if ev.lottery_x else ''}, confirma al {ev.companion_c} "
        f"mediante Tabla 2. Por esa coincidencia independiente entre ambas tablas, "
        f"el {ev.companion_c} queda fortalecido."
    )
