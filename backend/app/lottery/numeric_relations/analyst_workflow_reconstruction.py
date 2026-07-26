"""Analyst workflow reconstruction — PRE-J11A read-only.

Models how the manual analyst selected combinations, closed fulfilled
fuertes, and started new chains. Does not modify motor/tables/Production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from typing import Any
from uuid import uuid4

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.deep_mathematical_audit import (
    t1_candidates_from_observed,
    t1_group_ordered,
    t2_group_ordered,
)
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION
from app.lottery.numeric_relations.historical_manual_audit import (
    ObservedNumber,
    strengthen_official,
)

ANALYST_STATES = (
    "RESULTADOS_NUEVOS",
    "EXPLORACION_T1",
    "CONFIRMACION_T2",
    "FUERTE_ACTIVO",
    "ESPERA_DE_CUMPLIMIENTO",
    "FUERTE_CUMPLIDO",
    "CASO_CERRADO",
    "NUEVO_ANALISIS",
    "FUERTE_NO_CUMPLIDO",
    "ROTACION_DE_FAMILIA",
)

DISCARD_REASONS = (
    "NO_GENERA_CANDIDATO",
    "CANDIDATO_NO_CONFIRMADO",
    "CONFIRMADOR",
    "FUERTE_OFICIAL",
    "FUERTE_ALTERNATIVO",
    "FUERTE_CUMPLIDO",
    "CASO_CERRADO",
    "COMBINACION_REDUNDANTE",
    "REGLA_MANUAL_DESCONOCIDA",
)


def new_audit_id() -> str:
    return str(uuid4())


def pct(a: int, b: int) -> float:
    return round(100.0 * a / b, 2) if b else 0.0


def parse_time(t: str | None) -> time | None:
    if not t:
        return None
    try:
        parts = str(t).split(":")
        return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except Exception:
        return None


def observations_from_draws(
    draws: list[dict],
    *,
    d: date,
    mode: str,
) -> list[ObservedNumber]:
    """Build observations under selection modalities.

    mode:
      first_pos — first in-universe number per lottery (position order)
      first_second — first two in-universe numbers
      all_pos — all in-universe numbers
    """
    obs: list[ObservedNumber] = []
    for dr in draws:
        nums = list(dr.get("numbers") or [])
        poss = list(dr.get("positions") or [])
        labs = list(dr.get("position_labels") or [])
        # normalize lengths
        while len(poss) < len(nums):
            poss.append(len(poss) + 1)
        while len(labs) < len(nums):
            labs.append(str(len(labs) + 1))
        picked = []
        for n, pos, lab in zip(nums, poss, labs):
            try:
                ni = int(n)
            except Exception:
                continue
            if not (1 <= ni <= 100):
                continue
            picked.append((ni, int(pos), str(lab)))
        if mode == "first_pos":
            picked = picked[:1]
        elif mode == "first_second":
            picked = picked[:2]
        # all_pos keeps all
        for ni, pos, lab in picked:
            obs.append(
                ObservedNumber(
                    lottery_id=str(dr.get("lottery_id") or dr.get("lottery_name")),
                    lottery_name=str(dr.get("lottery_name")),
                    draw_id=str(dr.get("draw_id")),
                    draw_date=d,
                    draw_time=dr.get("draw_time"),
                    position=pos,
                    position_label=lab,
                    number=ni,
                    source_reference=dr.get("source_reference"),
                )
            )
    return obs


def enumerate_combinations(obs: list[ObservedNumber], cat: TableCatalog) -> list[dict[str, Any]]:
    hits = strengthen_official(obs, catalog=cat)
    return [
        {
            "fuerte": h.candidate,
            "origin": h.generator_observed,
            "confirmers": list(h.confirmers),
            "n_confirmers": len(h.confirmers),
            "origin_lotteries": sorted(
                {o.lottery_name for o in obs if o.number == h.generator_observed}
            ),
            "confirmer_lotteries": list(h.confirmer_lotteries),
        }
        for h in hits
    ]


def classify_number_role(
    *,
    number: int,
    obs: list[ObservedNumber],
    combinations: list[dict[str, Any]],
    pending_fuerte: int | None,
    written_by_analyst: set[int],
    fulfilled_today: set[int],
) -> dict[str, Any]:
    as_origin = [c for c in combinations if c["origin"] == number]
    as_conf = [c for c in combinations if number in c["confirmers"]]
    as_fuerte = [c for c in combinations if c["fuerte"] == number]
    cands = t1_candidates_from_observed(build_catalog(), number) if any(
        o.number == number for o in obs
    ) else []

    reasons = []
    analyzed = any(o.number == number for o in obs)
    if not analyzed:
        reasons.append("NO_EN_MODALIDAD")
    elif not cands and not as_conf and number not in fulfilled_today:
        reasons.append("NO_GENERA_CANDIDATO")
    if cands and not as_origin and not as_conf and number not in fulfilled_today:
        # has candidates but none confirmed from this origin in day's combos
        if not as_origin:
            reasons.append("CANDIDATO_NO_CONFIRMADO")
    if as_conf:
        reasons.append("CONFIRMADOR")
    if as_origin:
        reasons.append("FUERTE_OFICIAL" if as_origin else "FUERTE_ALTERNATIVO")
        # mark each produced fuerte
        for c in as_origin:
            reasons.append(f"PRODUCE_{c['fuerte']}")
    if as_fuerte:
        reasons.append("ES_FUERTE_PRODUCIDO")
    if pending_fuerte is not None and number == pending_fuerte and number in fulfilled_today:
        reasons.append("FUERTE_CUMPLIDO")
        reasons.append("CASO_CERRADO")
    if number in written_by_analyst:
        written = True
    else:
        written = False
        if analyzed and not as_origin and not as_conf and number not in fulfilled_today:
            if "CANDIDATO_NO_CONFIRMADO" in reasons or "NO_GENERA_CANDIDATO" in reasons:
                pass
            elif not reasons:
                reasons.append("COMBINACION_REDUNDANTE")

    discarded = analyzed and not written and number not in fulfilled_today
    return {
        "number": number,
        "analyzed": analyzed,
        "generated_candidates": bool(cands),
        "candidates": cands,
        "was_confirmer": bool(as_conf),
        "produced_fuerte": bool(as_origin),
        "fuertes_produced": [c["fuerte"] for c in as_origin],
        "written_by_analyst": written,
        "discarded": discarded,
        "reasons": sorted(set(reasons)) or (["REGLA_MANUAL_DESCONOCIDA"] if discarded else []),
        "fulfilled_pending": number in fulfilled_today,
    }


@dataclass
class PendingCase:
    fuerte: int
    activation_date: date
    origin: int
    confirmers: list[int]
    status: str = "ESPERA_DE_CUMPLIMIENTO"


def simulate_day_flow(
    *,
    day: date,
    draws: list[dict],
    pending: PendingCase | None,
    mode: str = "first_pos",
    featured_only: bool = True,
) -> dict[str, Any]:
    cat = build_catalog()
    use = [d for d in draws if (d.get("is_featured") if featured_only else True)]
    # chronological order
    use_sorted = sorted(
        use,
        key=lambda d: (
            parse_time(d.get("draw_time")) or time(23, 59, 59),
            str(d.get("lottery_name")),
        ),
    )
    timeline = []
    cumulative: list[dict] = []
    for dr in use_sorted:
        cumulative.append(dr)
        obs = observations_from_draws(cumulative, d=day, mode=mode)
        combos = enumerate_combinations(obs, cat)
        timeline.append(
            {
                "after_lottery": dr.get("lottery_name"),
                "after_time": dr.get("draw_time"),
                "n_draws": len(cumulative),
                "observed_numbers": sorted({o.number for o in obs}),
                "combinations": combos,
                "has_35_14_54": any(
                    c["fuerte"] == 54 and c["origin"] == 35 and 14 in c["confirmers"]
                    for c in combos
                ),
                "has_29": any(c["fuerte"] == 29 for c in combos),
            }
        )

    obs_final = observations_from_draws(use_sorted, d=day, mode=mode)
    combos_final = enumerate_combinations(obs_final, cat)
    numbers_today = {o.number for o in obs_final}

    fulfilled = pending is not None and pending.fuerte in numbers_today
    states = ["RESULTADOS_NUEVOS", "EXPLORACION_T1", "CONFIRMACION_T2"]
    if combos_final:
        states.append("FUERTE_ACTIVO")
    if fulfilled:
        states.extend(["FUERTE_CUMPLIDO", "CASO_CERRADO", "NUEVO_ANALISIS"])
    elif pending is not None:
        states.append("ESPERA_DE_CUMPLIMIENTO")

    new_pending = None
    closed = None
    if fulfilled and pending is not None:
        closed = {
            "fuerte": pending.fuerte,
            "activation_date": pending.activation_date.isoformat(),
            "fulfillment_date": day.isoformat(),
            "day_offset": (day - pending.activation_date).days,
            "status": "CASO_CUMPLIDO",
        }
    # New analysis fuertes excluding the just-fulfilled number as a "pending reuse"
    active_fuertes = [c for c in combos_final]
    if fulfilled and pending is not None:
        # model R7: fulfilled number not immediately reused as pending fuerte
        active_fuertes = [c for c in combos_final if c["fuerte"] != pending.fuerte]

    if active_fuertes:
        # pick primary: max confirmers then lower fuerte id
        primary = sorted(active_fuertes, key=lambda c: (-c["n_confirmers"], c["fuerte"]))[0]
        new_pending = PendingCase(
            fuerte=primary["fuerte"],
            activation_date=day,
            origin=primary["origin"],
            confirmers=primary["confirmers"],
        )
        states.append("FUERTE_ACTIVO")

    return {
        "date": day.isoformat(),
        "mode": mode,
        "featured_only": featured_only,
        "states": states,
        "observations": [
            {
                "number": o.number,
                "lottery": o.lottery_name,
                "time": o.draw_time,
                "position": o.position,
                "position_label": o.position_label,
                "source_reference": o.source_reference,
            }
            for o in obs_final
        ],
        "combinations": combos_final,
        "timeline": timeline,
        "pending_before": None
        if pending is None
        else {
            "fuerte": pending.fuerte,
            "activation_date": pending.activation_date.isoformat(),
        },
        "fulfilled": fulfilled,
        "closed_case": closed,
        "new_pending": None
        if new_pending is None
        else {
            "fuerte": new_pending.fuerte,
            "origin": new_pending.origin,
            "confirmers": new_pending.confirmers,
        },
        "methodology_version": METHODOLOGY_VERSION,
    }


__all__ = [
    "ANALYST_STATES",
    "DISCARD_REASONS",
    "METHODOLOGY_VERSION",
    "PendingCase",
    "new_audit_id",
    "pct",
    "parse_time",
    "observations_from_draws",
    "enumerate_combinations",
    "classify_number_role",
    "simulate_day_flow",
    "strengthen_official",
    "build_catalog",
    "t1_candidates_from_observed",
]
