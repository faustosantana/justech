"""J-2 — Agregados atómicos N-C-V y combinaciones N-C-{V} (sin explosión)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from itertools import combinations
from typing import Any, Iterable

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.historical.conditions import build_historical_events
from app.lottery.numeric_relations.historical.models import (
    AtomicRelationEvent,
    CombinationRelationEvent,
    ConfirmationWindowConfig,
    LotteryScope,
)
from app.lottery.numeric_relations.historical.rates import rates_payload
from app.lottery.numeric_relations.historical.sample import classify_sample, sample_warning
from app.lottery.numeric_relations.historical.universe import InMemoryDrawUniverse
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION


def _year_of(ev: AtomicRelationEvent | CombinationRelationEvent) -> int:
    return int(ev.anchor.draw_date.year)


def _posteriors_of(events: Iterable[Any]) -> list:
    return [e.posterior for e in events]


def aggregate_atomic_patterns(
    atomics: list[AtomicRelationEvent],
) -> list[dict[str, Any]]:
    """Nivel A: agregados por (N, C, V)."""
    groups: dict[tuple[int, int, int], list[AtomicRelationEvent]] = defaultdict(list)
    for e in atomics:
        groups[(e.observed_number, e.candidate, e.confirmer)].append(e)

    rows: list[dict[str, Any]] = []
    for (n, c, v), evs in sorted(groups.items()):
        stats = rates_payload(_posteriors_of(evs))
        by_year: dict[str, int] = defaultdict(int)
        by_primary: dict[str, int] = defaultdict(int)
        by_confirming: dict[str, int] = defaultdict(int)
        for e in evs:
            by_year[str(_year_of(e))] += 1
            by_primary[str(e.anchor.lottery_id)] += 1
            by_confirming[str(e.hit.confirmer_lottery_id)] += 1
        sample = len(evs)
        rows.append(
            {
                "level": "atomic",
                "observed_number": n,
                "candidate": c,
                "confirmer": v,
                "pattern_key": f"{n}->{c}->{v}",
                "event_count": sample,
                "sample_tier": classify_sample(sample).value,
                "sample_warning": sample_warning(sample),
                "by_year": dict(by_year),
                "by_primary_lottery": dict(by_primary),
                "by_confirming_lottery": dict(by_confirming),
                "statistics": stats,
                "event_ids": [e.event_id for e in evs],
            }
        )
    rows.sort(key=lambda r: (-r["event_count"], r["pattern_key"]))
    return rows


def _subset_keys(confirmers: list[int], *, max_pair_triple: bool = True) -> list[tuple[str, list[int]]]:
    """
    Por defecto: individuales (ya en atomic), pares, tríos y conjunto completo.
    Evita explosión: no genera k>3 salvo el conjunto completo observado.
    """
    confs = sorted({int(x) for x in confirmers})
    out: list[tuple[str, list[int]]] = []
    if not confs:
        return out
    # full set
    full_key = ",".join(str(x) for x in confs)
    out.append((full_key, confs))
    if not max_pair_triple:
        return out
    if len(confs) >= 2:
        for pair in combinations(confs, 2):
            key = ",".join(str(x) for x in pair)
            out.append((key, list(pair)))
    if len(confs) >= 3:
        for trip in combinations(confs, 3):
            key = ",".join(str(x) for x in trip)
            # skip if same as full when len==3 (already added)
            if list(trip) != confs:
                out.append((key, list(trip)))
    # dedupe preserving order
    seen: set[str] = set()
    uniq: list[tuple[str, list[int]]] = []
    for k, vals in out:
        if k in seen:
            continue
        seen.add(k)
        uniq.append((k, vals))
    return uniq


def aggregate_combination_patterns(
    combos: list[CombinationRelationEvent],
    *,
    include_pairs_triples: bool = True,
) -> list[dict[str, Any]]:
    """
    Nivel B: agregados por (N, C, confirmers_key).
    También indexa pares/tríos como subconjuntos (consultas por subconjunto).
    """
    # Exact full-set aggregates
    exact: dict[tuple[int, int, str], list[CombinationRelationEvent]] = defaultdict(list)
    # Subset index: (N,C,subset_key) -> list of combo events that contain the subset
    subset_hits: dict[tuple[int, int, str], list[CombinationRelationEvent]] = defaultdict(list)

    for e in combos:
        exact[(e.observed_number, e.candidate, e.confirmers_key)].append(e)
        for key, vals in _subset_keys(e.confirmers, max_pair_triple=include_pairs_triples):
            # subset containment: vals ⊆ e.confirmers
            if set(vals).issubset(set(e.confirmers)):
                subset_hits[(e.observed_number, e.candidate, key)].append(e)

    rows: list[dict[str, Any]] = []

    def build_row(
        n: int,
        c: int,
        key: str,
        evs: list[CombinationRelationEvent],
        *,
        match_type: str,
    ) -> dict[str, Any]:
        stats = rates_payload(_posteriors_of(evs))
        by_year: dict[str, int] = defaultdict(int)
        by_primary: dict[str, int] = defaultdict(int)
        for e in evs:
            by_year[str(_year_of(e))] += 1
            by_primary[str(e.anchor.lottery_id)] += 1
        sample = len(evs)
        confs = [int(x) for x in key.split(",") if x]
        return {
            "level": "combination",
            "match_type": match_type,  # exact | subset
            "observed_number": n,
            "candidate": c,
            "confirmers": confs,
            "confirmers_key": key,
            "pattern_key": f"{n}->{c}->{{{key}}}",
            "event_count": sample,
            "sample_tier": classify_sample(sample).value,
            "sample_warning": sample_warning(sample),
            "by_year": dict(by_year),
            "by_primary_lottery": dict(by_primary),
            "statistics": stats,
            "event_ids": [e.event_id for e in evs],
            "atomic_event_ids": sorted({aid for e in evs for aid in e.atomic_event_ids}),
        }

    for (n, c, key), evs in exact.items():
        rows.append(build_row(n, c, key, evs, match_type="exact"))

    for (n, c, key), evs in subset_hits.items():
        parts = [p for p in key.split(",") if p]
        # singles belong to atomic Nivel A
        if len(parts) < 2:
            continue
        # full-set exact already covered; still emit subset when containment count differs
        # or when key is a proper pair/triple view for queries
        if (n, c, key) in exact and len(evs) == len(exact[(n, c, key)]) and set(parts) == set(
            exact[(n, c, key)][0].confirmers
        ):
            # identical to exact full set — skip duplicate
            continue
        rows.append(build_row(n, c, key, evs, match_type="subset"))

    rows.sort(key=lambda r: (-r["event_count"], r["pattern_key"]))
    return rows


def build_candidate_confirmer_matrix(
    atomics: list[AtomicRelationEvent],
    *,
    candidates: list[int] | None = None,
    confirmers: list[int] | None = None,
) -> dict[str, Any]:
    """Matriz filas=C, columnas=V con eventos y tasas."""
    patterns = aggregate_atomic_patterns(atomics)
    by_cell = {(p["candidate"], p["confirmer"]): p for p in patterns}
    cand_set = sorted({p["candidate"] for p in patterns} | set(candidates or []))
    conf_set = sorted({p["confirmer"] for p in patterns} | set(confirmers or []))
    cells = []
    for c in cand_set:
        for v in conf_set:
            p = by_cell.get((c, v))
            if not p:
                cells.append(
                    {
                        "candidate": c,
                        "confirmer": v,
                        "event_count": 0,
                        "response_rate_next_draw": None,
                        "response_rate_within_3": None,
                        "response_rate_within_5": None,
                        "median_cycle": None,
                        "sample_size": 0,
                        "sample_tier": classify_sample(0).value,
                    }
                )
                continue
            aliases = p["statistics"]["aliases"]
            cycles = p["statistics"]["cycles"]
            cells.append(
                {
                    "candidate": c,
                    "confirmer": v,
                    "event_count": p["event_count"],
                    "response_rate_next_draw": aliases["response_rate_next_draw"],
                    "response_rate_within_3": aliases["response_rate_within_3"],
                    "response_rate_within_5": aliases["response_rate_within_5"],
                    "median_cycle": cycles.get("median"),
                    "sample_size": p["event_count"],
                    "sample_tier": p["sample_tier"],
                    "sample_warning": p["sample_warning"],
                    "pattern_key": p["pattern_key"],
                }
            )
    return {
        "methodology_version": METHODOLOGY_VERSION,
        "rows_candidates": cand_set,
        "columns_confirmers": conf_set,
        "cells": cells,
    }


class HistoricalAggregatesService:
    def __init__(
        self,
        *,
        universe: InMemoryDrawUniverse,
        catalog: TableCatalog | None = None,
    ) -> None:
        self.universe = universe
        self.catalog = catalog or build_catalog()

    def compute(
        self,
        *,
        observed_number: int,
        scope: LotteryScope,
        window: ConfirmationWindowConfig,
        date_from: date | None = None,
        date_to: date | None = None,
        candidate: int | None = None,
        confirmer: int | None = None,
        include_pairs_triples: bool = True,
        max_horizon: int = 10,
    ) -> dict[str, Any]:
        raw = build_historical_events(
            observed_number=observed_number,
            scope=scope,
            window=window,
            universe=self.universe,
            catalog=self.catalog,
            date_from=date_from,
            date_to=date_to,
            candidate_filter=candidate,
            confirmer_filter=confirmer,
            max_horizon=max_horizon,
        )
        atomics: list[AtomicRelationEvent] = raw["atomic_events"]
        combos: list[CombinationRelationEvent] = raw["combination_events"]
        atomic_agg = aggregate_atomic_patterns(atomics)
        combo_agg = aggregate_combination_patterns(
            combos, include_pairs_triples=include_pairs_triples
        )
        matrix = build_candidate_confirmer_matrix(
            atomics,
            candidates=self.catalog.get_table1_companions(int(observed_number)),
        )
        return {
            "methodology_version": METHODOLOGY_VERSION,
            "effective_parameters": {
                "observed_number": int(observed_number),
                "mother_code": int(observed_number),
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "candidate_filter": candidate,
                "confirmer_filter": confirmer,
                "include_pairs_triples": include_pairs_triples,
                "confirmation_window": window.to_dict(),
                "lottery_scope": scope.to_dict(),
            },
            "atomic_patterns": atomic_agg,
            "combination_patterns": combo_agg,
            "matrix": matrix,
            "totals": {
                "atomic_events": len(atomics),
                "combination_events": len(combos),
                "atomic_patterns": len(atomic_agg),
                "combination_patterns": len(combo_agg),
            },
        }
