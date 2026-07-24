"""Resolución de confirmadores Tabla 2 según confirmation_window."""

from __future__ import annotations

from datetime import timedelta

from app.lottery.numeric_relations.catalog import TableCatalog
from app.lottery.numeric_relations.historical.enums import ConfirmationWindowMode
from app.lottery.numeric_relations.historical.models import (
    ConfirmationWindowConfig,
    ConfirmingHit,
    DrawRef,
    LotteryScope,
)
from app.lottery.numeric_relations.historical.universe import (
    DrawUniversePort,
    session_bucket_for,
)


def _hit(
    *,
    candidate: int,
    confirmer: int,
    draw: DrawRef,
    mode: ConfirmationWindowMode,
    position: int | str | None,
    tz_name: str,
) -> ConfirmingHit:
    return ConfirmingHit(
        confirmer_number=int(confirmer),
        confirmer_lottery_id=str(draw.lottery_id),
        confirmer_lottery_name=draw.lottery_name,
        confirmer_draw_id=str(draw.draw_id),
        confirmer_datetime=draw.local_datetime(tz_name).isoformat(),
        confirmer_position=position,
        relation_mode=mode.value,
        points=1,
        score_delta=1,
        candidate_strengthened=int(candidate),
        dedupe_key=f"{draw.draw_id}|{candidate}|{confirmer}|{position}",
    )


def _positions_for_number(draw: DrawRef, number: int) -> list[int | str]:
    return [p for p, n in draw.numbers if int(n) == int(number)]


def find_confirming_hits(
    *,
    candidate: int,
    neighbors: list[int],
    anchor: DrawRef,
    scope: LotteryScope,
    window: ConfirmationWindowConfig,
    universe: DrawUniversePort,
    observed_number: int,
) -> list[ConfirmingHit]:
    """
    Busca confirmadores V ∈ neighbors en la ventana configurada.
    Fortalece a `candidate` (T1); nunca al confirmador V como score de esta relación.
    No fusiona draws: cada hit conserva su draw_id.
    """
    neighbor_set = {int(x) for x in neighbors}
    tz = window.timezone
    confirming_ids = list(scope.confirming_lottery_ids)
    hits: list[ConfirmingHit] = []
    seen: set[str] = set()

    def accept(draw: DrawRef, confirmer: int) -> None:
        if int(confirmer) == int(observed_number):
            return
        if int(confirmer) not in neighbor_set:
            return
        positions = _positions_for_number(draw, confirmer) or [None]
        for pos in positions:
            h = _hit(
                candidate=candidate,
                confirmer=confirmer,
                draw=draw,
                mode=window.mode,
                position=pos,
                tz_name=tz,
            )
            if h.dedupe_key in seen:
                continue
            seen.add(h.dedupe_key)
            hits.append(h)

    mode = window.mode

    if mode == ConfirmationWindowMode.SAME_DRAW:
        # Solo números del mismo draw_id ancla (multi-number draw)
        for num in anchor.numbers_1_to_100():
            accept(anchor, num)
        return hits

    if mode == ConfirmationWindowMode.SAME_DATE:
        for d in universe.list_draws_on_date(confirming_ids, anchor.draw_date):
            if str(d.draw_id) == str(anchor.draw_id):
                # same draw already covered conceptually; still allow if confirming includes primary
                for num in d.numbers_1_to_100():
                    if str(d.draw_id) == str(anchor.draw_id) and int(num) == int(observed_number):
                        continue
                    accept(d, num)
            else:
                for num in d.numbers_1_to_100():
                    accept(d, num)
        return hits

    if mode == ConfirmationWindowMode.SAME_SESSION:
        anchor_sess = session_bucket_for(anchor.local_datetime(tz))
        if window.session and window.session != anchor_sess:
            return hits
        for d in universe.list_draws_on_date(confirming_ids, anchor.draw_date):
            if session_bucket_for(d.local_datetime(tz)) != anchor_sess:
                continue
            for num in d.numbers_1_to_100():
                if str(d.draw_id) == str(anchor.draw_id) and int(num) == int(observed_number):
                    continue
                accept(d, num)
        return hits

    if mode == ConfirmationWindowMode.HOURS_AFTER:
        start = anchor.local_datetime(tz)
        end = start + timedelta(hours=int(window.hours_after or 0))
        for lid in confirming_ids:
            for d in universe.list_draws_for_lottery(lid):
                dt = d.local_datetime(tz)
                if dt < start or dt > end:
                    continue
                if str(d.draw_id) == str(anchor.draw_id):
                    for num in d.numbers_1_to_100():
                        if int(num) == int(observed_number):
                            continue
                        accept(d, num)
                else:
                    for num in d.numbers_1_to_100():
                        accept(d, num)
        return hits

    if mode == ConfirmationWindowMode.NEXT_DRAW_PER_CONFIRMING_LOTTERY:
        for lid in confirming_ids:
            nxt = universe.draws_after(lid, after=anchor, k=1, tz_name=tz)
            for d in nxt:
                for num in d.numbers_1_to_100():
                    accept(d, num)
        return hits

    if mode == ConfirmationWindowMode.NEXT_K_DRAWS:
        k = int(window.next_k or 1)
        for lid in confirming_ids:
            nxt = universe.draws_after(lid, after=anchor, k=k, tz_name=tz)
            for d in nxt:
                for num in d.numbers_1_to_100():
                    accept(d, num)
        return hits

    raise ValueError(f"unsupported confirmation window mode: {mode}")


def neighbors_for_candidate(catalog: TableCatalog, candidate: int) -> tuple[int, list[int], list[int]]:
    code = catalog.get_table2_code_for_number(candidate)
    group = list(catalog.table2_code_to_numbers.get(code, []))
    neighbors = catalog.get_table2_neighbors(candidate, exclude_self=True)
    return code, group, neighbors
