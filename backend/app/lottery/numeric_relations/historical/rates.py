"""Tasas históricas por horizonte (excluye censurados del denominador)."""

from __future__ import annotations

from statistics import mean, median, pstdev
from typing import Iterable

from app.lottery.numeric_relations.historical.enums import Horizon, HORIZON_OFFSETS
from app.lottery.numeric_relations.historical.models import (
    CycleStats,
    HorizonRate,
    PosteriorOutcome,
)
from app.lottery.numeric_relations.historical.sample import classify_sample, sample_warning


def _flag_for_horizon(p: PosteriorOutcome, horizon: Horizon) -> bool | None:
    mapping = {
        Horizon.NEXT_1: p.responded_next_draw,
        Horizon.WITHIN_2: p.responded_within_2,
        Horizon.WITHIN_3: p.responded_within_3,
        Horizon.WITHIN_5: p.responded_within_5,
        Horizon.WITHIN_10: p.responded_within_10,
    }
    return mapping[horizon]


def compute_horizon_rates(posteriors: Iterable[PosteriorOutcome | None]) -> dict[str, HorizonRate]:
    rows = [p for p in posteriors if p is not None]
    out: dict[str, HorizonRate] = {}
    for horizon in Horizon:
        numer = 0
        denom = 0
        censored = 0
        for p in rows:
            flag = _flag_for_horizon(p, horizon)
            if flag is None:
                censored += 1
                continue
            denom += 1
            if flag:
                numer += 1
        rate = (numer / denom) if denom > 0 else None
        sample = denom  # evaluable sample for this horizon
        out[horizon.value] = HorizonRate(
            horizon=horizon.value,
            numerator=numer,
            denominator=denom,
            rate=rate,
            sample_size=sample,
            censored_count=censored,
            sample_tier=classify_sample(sample),
            sample_warning=sample_warning(sample),
        )
    return out


def compute_cycle_stats(posteriors: Iterable[PosteriorOutcome | None]) -> CycleStats:
    rows = [p for p in posteriors if p is not None]
    observed: list[int] = []
    no_response = 0
    censored = 0
    for p in rows:
        if p.draws_until_response is not None:
            observed.append(int(p.draws_until_response))
        elif p.censored:
            censored += 1
        else:
            no_response += 1

    dist: dict[str, int] = {}
    for c in observed:
        key = str(c)
        dist[key] = dist.get(key, 0) + 1

    percentiles: dict[str, float] = {}
    if observed:
        s = sorted(observed)
        def pct(q: float) -> float:
            if not s:
                return 0.0
            idx = min(len(s) - 1, max(0, int(round((q / 100.0) * (len(s) - 1)))))
            return float(s[idx])

        percentiles = {
            "p25": pct(25),
            "p50": pct(50),
            "p75": pct(75),
            "p90": pct(90),
        }

    return CycleStats(
        min=float(min(observed)) if observed else None,
        max=float(max(observed)) if observed else None,
        mean=float(mean(observed)) if observed else None,
        median=float(median(observed)) if observed else None,
        stdev=float(pstdev(observed)) if len(observed) >= 2 else (0.0 if observed else None),
        percentiles=percentiles,
        distribution=dist,
        events_with_response=len(observed),
        events_without_response_in_window=no_response,
        events_censored=censored,
        observed_cycles=observed,
    )


def rates_payload(posteriors: Iterable[PosteriorOutcome | None]) -> dict:
    rates = compute_horizon_rates(posteriors)
    cycles = compute_cycle_stats(posteriors)
    return {
        "response_rates": {k: v.to_dict() for k, v in rates.items()},
        "aliases": {
            "response_rate_next_draw": rates[Horizon.NEXT_1.value].to_dict(),
            "response_rate_within_2": rates[Horizon.WITHIN_2.value].to_dict(),
            "response_rate_within_3": rates[Horizon.WITHIN_3.value].to_dict(),
            "response_rate_within_5": rates[Horizon.WITHIN_5.value].to_dict(),
            "response_rate_within_10": rates[Horizon.WITHIN_10.value].to_dict(),
        },
        "cycles": cycles.to_dict(),
        "terminology": {
            "uses": [
                "tasa_historica",
                "respuesta_observada",
                "frecuencia_de_repeticion",
                "soporte_historico",
            ],
            "forbidden": ["probabilidad_de_ganar"],
        },
    }
