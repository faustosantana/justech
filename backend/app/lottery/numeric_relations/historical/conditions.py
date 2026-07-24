"""Emisión de eventos Nivel A (atómicos) y Nivel B (combinaciones)."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import date
from typing import Iterable

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.historical.confirmation import (
    find_confirming_hits,
    neighbors_for_candidate,
)
from app.lottery.numeric_relations.historical.models import (
    AtomicRelationEvent,
    CombinationRelationEvent,
    ConfirmationWindowConfig,
    DrawRef,
    LotteryScope,
)
from app.lottery.numeric_relations.historical.posterior import compute_posterior
from app.lottery.numeric_relations.historical.universe import (
    InMemoryDrawUniverse,
    effective_window_bounds,
)
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION


def _event_id(*parts: object) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def normalize_confirmers(confirmers: Iterable[int]) -> list[int]:
    return sorted({int(x) for x in confirmers})


def confirmers_key(confirmers: Iterable[int]) -> str:
    return ",".join(str(x) for x in normalize_confirmers(confirmers))


def build_events_for_anchor(
    *,
    observed_number: int,
    anchor: DrawRef,
    scope: LotteryScope,
    window: ConfirmationWindowConfig,
    universe: InMemoryDrawUniverse,
    catalog: TableCatalog | None = None,
    candidate_filter: int | None = None,
    confirmer_filter: int | None = None,
    compute_posterior_flag: bool = True,
    max_horizon: int = 10,
) -> tuple[list[AtomicRelationEvent], list[CombinationRelationEvent]]:
    """
    mother_code = observed_number.
    Por cada candidato T1: busca confirmadores T2; emite atómicos y combinación.
    """
    cat = catalog or build_catalog()
    n = int(observed_number)
    mother_code = n
    candidates = cat.get_table1_companions(mother_code)
    if candidate_filter is not None:
        candidates = [c for c in candidates if int(c) == int(candidate_filter)]

    tz, start_iso, end_iso = effective_window_bounds(
        anchor,
        mode=window.mode.value,
        tz_name=window.timezone,
        hours_after=window.hours_after,
    )
    window_meta = {
        **window.to_dict(),
        "timezone": tz,
        "window_start": start_iso,
        "window_end": end_iso,
        "anchor_draw_id": str(anchor.draw_id),
        "confirming_lottery_ids": list(scope.confirming_lottery_ids),
    }
    scope_meta = scope.to_dict()

    atomics: list[AtomicRelationEvent] = []
    combinations: list[CombinationRelationEvent] = []

    for candidate in candidates:
        t2_code, t2_group, neighbors = neighbors_for_candidate(cat, int(candidate))
        hits = find_confirming_hits(
            candidate=int(candidate),
            neighbors=neighbors,
            anchor=anchor,
            scope=scope,
            window=window,
            universe=universe,
            observed_number=n,
        )
        if confirmer_filter is not None:
            hits = [h for h in hits if int(h.confirmer_number) == int(confirmer_filter)]
        if not hits:
            continue

        # Dedupe confirmers for combination while keeping individual evidence
        by_confirmer: dict[int, list] = defaultdict(list)
        for h in hits:
            by_confirmer[int(h.confirmer_number)].append(h)

        conf_ids = sorted({h.confirmer_draw_id for h in hits})
        posterior = None
        if compute_posterior_flag:
            posterior = compute_posterior(
                candidate=int(candidate),
                anchor=anchor,
                confirmation_draw_ids=list(conf_ids),
                scope=scope,
                universe=universe,
                max_horizon=max_horizon,
                tz_name=window.timezone,
            )

        atomic_ids: list[str] = []
        unique_hits = []
        for confirmer, hlist in sorted(by_confirmer.items()):
            # one atomic event per confirmer (first hit evidence; all hits retained in combination)
            h0 = hlist[0]
            eid = _event_id(
                "atomic",
                n,
                candidate,
                confirmer,
                anchor.draw_id,
                h0.confirmer_draw_id,
                window.mode.value,
            )
            atomic_ids.append(eid)
            unique_hits.append(h0)
            atomics.append(
                AtomicRelationEvent(
                    event_id=eid,
                    observed_number=n,
                    mother_code=mother_code,
                    candidate=int(candidate),
                    confirmer=int(confirmer),
                    table1_candidates=list(cat.get_table1_companions(mother_code)),
                    candidate_table2_code=t2_code,
                    candidate_table2_group=t2_group,
                    anchor=anchor,
                    hit=h0,
                    posterior=posterior,
                    confirmation_window=window_meta,
                    lottery_scope=scope_meta,
                    methodology_version=METHODOLOGY_VERSION,
                )
            )

        confs = normalize_confirmers(by_confirmer.keys())
        ckey = confirmers_key(confs)
        cid = _event_id("combo", n, candidate, ckey, anchor.draw_id, window.mode.value)
        combinations.append(
            CombinationRelationEvent(
                event_id=cid,
                observed_number=n,
                mother_code=mother_code,
                candidate=int(candidate),
                confirmers=confs,
                confirmers_key=ckey,
                atomic_event_ids=atomic_ids,
                hits=hits,
                score_raw=len(confs),
                anchor=anchor,
                posterior=posterior,
                confirmation_window=window_meta,
                lottery_scope=scope_meta,
                methodology_version=METHODOLOGY_VERSION,
            )
        )

    return atomics, combinations


def collect_anchor_draws(
    universe: InMemoryDrawUniverse,
    *,
    observed_number: int,
    primary_lottery_ids: list[str],
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[DrawRef]:
    """Draws where observed_number appeared in primary lotteries (chronological asc)."""
    n = int(observed_number)
    out: list[DrawRef] = []
    for lid in primary_lottery_ids:
        for d in universe.list_draws_for_lottery(lid):
            if date_from and d.draw_date < date_from:
                continue
            if date_to and d.draw_date > date_to:
                continue
            if n in d.numbers_1_to_100():
                out.append(d)
    out.sort(key=lambda d: (d.draw_date, d.draw_time or "", str(d.draw_id)))
    return out


def build_historical_events(
    *,
    observed_number: int,
    scope: LotteryScope,
    window: ConfirmationWindowConfig,
    universe: InMemoryDrawUniverse,
    catalog: TableCatalog | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    candidate_filter: int | None = None,
    confirmer_filter: int | None = None,
    max_horizon: int = 10,
) -> dict:
    anchors = collect_anchor_draws(
        universe,
        observed_number=observed_number,
        primary_lottery_ids=list(scope.primary_lottery_ids),
        date_from=date_from,
        date_to=date_to,
    )
    all_atomics: list[AtomicRelationEvent] = []
    all_combos: list[CombinationRelationEvent] = []
    for anchor in anchors:
        a, c = build_events_for_anchor(
            observed_number=observed_number,
            anchor=anchor,
            scope=scope,
            window=window,
            universe=universe,
            catalog=catalog,
            candidate_filter=candidate_filter,
            confirmer_filter=confirmer_filter,
            max_horizon=max_horizon,
        )
        all_atomics.extend(a)
        all_combos.extend(c)

    return {
        "methodology_version": METHODOLOGY_VERSION,
        "observed_number": int(observed_number),
        "mother_code": int(observed_number),
        "anchors_examined": len(anchors),
        "atomic_events": all_atomics,
        "combination_events": all_combos,
        "confirmation_window": window.to_dict(),
        "lottery_scope": scope.to_dict(),
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
    }
