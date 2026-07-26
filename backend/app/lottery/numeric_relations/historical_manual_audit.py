"""Historical Manual Logic Audit — official T1×T2 same-day strengthening only.

Read-only. Does NOT modify motor, tables, draws, or Production.
DIRECT_T2_NEIGHBOR_SIGNAL is detected for rejection labeling, never as fuerte.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Iterable
from uuid import uuid4

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION

SEED_DEFAULT = 20260726
WINDOWS = (
    "next_chronological_draw",
    "same_day_other_draws",
    "next_calendar_day",
    "next_7_featured_draws",
)


@dataclass
class ObservedNumber:
    lottery_id: str
    lottery_name: str
    draw_id: str
    draw_date: date
    draw_time: str | None
    position: int
    position_label: str
    number: int
    source_reference: str | None


@dataclass
class StrengthenedHit:
    candidate: int
    generator_observed: int
    generator_lottery: str
    confirmers: list[int]
    confirmer_lotteries: list[str]
    table1_companions_of_generator: list[int]
    table2_group_of_candidate: list[int]


def _in_universe(n: int) -> bool:
    return 1 <= int(n) <= 100


def _companions(cat: TableCatalog, n: int) -> list[int]:
    if not _in_universe(n):
        return []
    try:
        return list(cat.get_table1_companions(int(n)))
    except KeyError:
        return []


def _neighbors(cat: TableCatalog, n: int) -> list[int]:
    if not _in_universe(n):
        return []
    try:
        return list(cat.get_table2_neighbors(int(n), exclude_self=True))
    except KeyError:
        return []


def strengthen_official(
    observations: list[ObservedNumber],
    *,
    catalog: TableCatalog | None = None,
) -> list[StrengthenedHit]:
    """Official geometry only. Confirmers never strengthened."""
    cat = catalog or build_catalog()
    by_num: dict[int, list[ObservedNumber]] = {}
    for o in observations:
        if not _in_universe(o.number):
            continue
        by_num.setdefault(int(o.number), []).append(o)
    uniq = list(by_num.keys())
    hits: dict[int, StrengthenedHit] = {}
    for gen_n in uniq:
        others = set(uniq) - {gen_n}
        comps = _companions(cat, gen_n)
        for cand in comps:
            conf = sorted(set(_neighbors(cat, cand)) & others)
            if not conf:
                continue
            conf_lots: list[str] = []
            for c in conf:
                conf_lots.extend(sorted({x.lottery_name for x in by_num[c]}))
            gen_lots = sorted({x.lottery_name for x in by_num[gen_n]})
            t2 = list(
                cat.table2_code_to_numbers.get(cat.get_table2_code_for_number(cand), [])
            )
            prev = hits.get(cand)
            if prev is None:
                hits[cand] = StrengthenedHit(
                    candidate=cand,
                    generator_observed=gen_n,
                    generator_lottery=",".join(gen_lots),
                    confirmers=conf,
                    confirmer_lotteries=sorted(set(conf_lots)),
                    table1_companions_of_generator=comps,
                    table2_group_of_candidate=t2,
                )
            else:
                # merge confirmers if multiple generators strengthen same cand
                merged = sorted(set(prev.confirmers) | set(conf))
                prev.confirmers = merged
                prev.confirmer_lotteries = sorted(
                    set(prev.confirmer_lotteries) | set(conf_lots)
                )
    return sorted(hits.values(), key=lambda h: (-len(h.confirmers), h.candidate))


def direct_t2_signals(
    observations: list[ObservedNumber],
    *,
    catalog: TableCatalog | None = None,
    official_candidates: Iterable[int] = (),
) -> list[dict[str, Any]]:
    cat = catalog or build_catalog()
    official = set(int(x) for x in official_candidates)
    out: list[dict[str, Any]] = []
    for o in observations:
        if not _in_universe(o.number):
            continue
        for v in _neighbors(cat, int(o.number)):
            if v in official:
                continue
            # secondary only — reject as fuerte
            out.append(
                {
                    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
                    "observed": int(o.number),
                    "lottery": o.lottery_name,
                    "direct_t2_neighbor": v,
                    "is_official_fuerte": False,
                    "rejected_as_predictive_rule": True,
                }
            )
    # dedupe
    seen = set()
    uniq = []
    for row in out:
        key = (row["observed"], row["direct_t2_neighbor"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(row)
    return uniq


def appearance_in_universe(numbers: set[int], draws: list[dict[str, Any]]) -> dict[str, Any] | None:
    for d in draws:
        for n, pos, label in zip(d["numbers"], d["positions"], d["position_labels"]):
            if int(n) in numbers:
                return {
                    "date": d["draw_date"].isoformat()
                    if hasattr(d["draw_date"], "isoformat")
                    else str(d["draw_date"]),
                    "lottery_name": d["lottery_name"],
                    "lottery_id": d["lottery_id"],
                    "draw_id": d["draw_id"],
                    "source_reference": d.get("source_reference"),
                    "draw_time": d.get("draw_time"),
                    "position": int(pos),
                    "position_label": label,
                    "number": int(n),
                }
    return None


def evaluate_windows(
    *,
    fuertes: list[int],
    case_date: date,
    case_draw_ids: set[str],
    all_draws_sorted: list[dict[str, Any]],
    by_date: dict[date, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Windows are mutually exclusive in reporting (each evaluated independently)."""
    target = set(int(x) for x in fuertes)
    if not target:
        return {w: {"hit": False, "first_appearance": None} for w in WINDOWS}

    # chronological index
    # next chronological draw = first draw strictly after max case draw time/date
    # Use date-based then draw order in all_draws_sorted
    case_indices = [
        i for i, d in enumerate(all_draws_sorted) if d["draw_id"] in case_draw_ids
    ]
    max_idx = max(case_indices) if case_indices else -1

    next_chrono = all_draws_sorted[max_idx + 1 : max_idx + 2]
    same_day = [
        d
        for d in by_date.get(case_date, [])
        if d["draw_id"] not in case_draw_ids
    ]
    next_day = by_date.get(case_date + timedelta(days=1), [])
    next7 = all_draws_sorted[max_idx + 1 : max_idx + 8]

    def pack(draws: list[dict[str, Any]]) -> dict[str, Any]:
        app = appearance_in_universe(target, draws)
        return {"hit": app is not None, "first_appearance": app}

    return {
        "next_chronological_draw": pack(next_chrono),
        "same_day_other_draws": pack(same_day),
        "next_calendar_day": pack(next_day),
        "next_7_featured_draws": pack(next7),
    }


def case_verdict(
    hits: list[StrengthenedHit],
    windows: dict[str, Any],
    *,
    direct_t2_only: bool = False,
) -> str:
    if direct_t2_only and not hits:
        return "DIRECT_T2_RECHAZADO"
    if not hits:
        return "SIN_CONFIRMACION"
    any_hit = any(windows[w]["hit"] for w in WINDOWS)
    unique = len(hits) == 1
    if any_hit and unique:
        return "ACIERTO_EXACTO"
    if any_hit and not unique:
        return "ACIERTO_NO_UNICO"
    if not any_hit:
        return "FALLO"
    return "DATOS_INSUFICIENTES"


def build_case_card(
    *,
    case_id: str,
    case_date: date,
    observations: list[ObservedNumber],
    catalog: TableCatalog | None = None,
    all_draws_sorted: list[dict[str, Any]],
    by_date: dict[date, list[dict[str, Any]]],
    label: str | None = None,
    known_manual_fuerte: int | None = None,
) -> dict[str, Any]:
    cat = catalog or build_catalog()
    hits = strengthen_official(observations, catalog=cat)
    fuertes = [h.candidate for h in hits]
    t2 = direct_t2_signals(observations, catalog=cat, official_candidates=fuertes)
    windows = evaluate_windows(
        fuertes=fuertes,
        case_date=case_date,
        case_draw_ids={o.draw_id for o in observations},
        all_draws_sorted=all_draws_sorted,
        by_date=by_date,
    )
    # C2-style: no official hit but direct t2 present
    direct_only = (not hits) and bool(t2)
    verdict = case_verdict(hits, windows, direct_t2_only=direct_only)

    # look-ahead guard metadata: windows only use dates >= case_date for same_day/next*
    # (never used to select candidates)
    obs_payload = []
    for o in observations:
        if not _in_universe(o.number):
            continue
        obs_payload.append(
            {
                "lottery_id": o.lottery_id,
                "lottery_name": o.lottery_name,
                "draw_id": o.draw_id,
                "draw_date": o.draw_date.isoformat(),
                "draw_time": o.draw_time,
                "position": o.position,
                "position_label": o.position_label,
                "number": o.number,
                "source_reference": o.source_reference,
                "table1_code_mother": o.number,
                "table1_companions": _companions(cat, o.number),
                "table2_neighbors": _neighbors(cat, o.number),
            }
        )

    strengthened = []
    for h in hits:
        strengthened.append(
            {
                "candidate": h.candidate,
                "generator_observed": h.generator_observed,
                "generator_lottery": h.generator_lottery,
                "confirmers": h.confirmers,
                "confirmer_lotteries": h.confirmer_lotteries,
                "confirmation_level": len(h.confirmers),
                "table1_companions_of_generator": h.table1_companions_of_generator,
                "table2_group_of_candidate": h.table2_group_of_candidate,
                "confirmer_never_strengthened": True,
            }
        )

    primary = fuertes[0] if len(fuertes) == 1 else fuertes
    explanation = _explain(hits, windows, verdict, t2)

    return {
        "id": case_id,
        "label": label,
        "date": case_date.isoformat(),
        "methodology_version": METHODOLOGY_VERSION,
        "look_ahead_blocked": True,
        "known_manual_fuerte": known_manual_fuerte,
        "manual_used_only_for_final_compare": True,
        "observations": obs_payload,
        "official_strengthened": strengthened,
        "fuerte_oficial": primary if primary else None,
        "resultado_unico": len(fuertes) == 1,
        "otros_candidatos": fuertes[1:] if len(fuertes) > 1 else [],
        "direct_t2_neighbor_signals": t2,
        "windows": windows,
        "verdict": verdict,
        "explanation": explanation,
        "modifies_motor": False,
    }


def _explain(
    hits: list[StrengthenedHit],
    windows: dict[str, Any],
    verdict: str,
    t2: list[dict[str, Any]],
) -> str:
    if verdict == "DIRECT_T2_RECHAZADO":
        eg = t2[0] if t2 else {}
        return (
            f"No hay candidato T1 confirmado. Señal T2 directa rechazada "
            f"({eg.get('observed')}→{eg.get('direct_t2_neighbor')}). "
            "No es fuerte oficial."
        )
    if not hits:
        return "Sin confirmación oficial: ningún compañero T1 fue confirmado por otro observado."
    parts = []
    for h in hits:
        parts.append(
            f"{h.generator_observed} ({h.generator_lottery}) genera candidato T1 {h.candidate}; "
            f"confirmado por {h.confirmers} vía Tabla2 "
            f"({', '.join(h.confirmer_lotteries)})."
        )
    first_app = None
    for w in WINDOWS:
        if windows[w]["hit"]:
            first_app = windows[w]["first_appearance"]
            break
    if first_app:
        parts.append(
            f"Aparición posterior: {first_app['date']} {first_app['lottery_name']} "
            f"pos {first_app['position']} = {first_app['number']} "
            f"(ref {first_app.get('source_reference')})."
        )
    else:
        parts.append("No apareció en ninguna ventana declarada.")
    parts.append(f"Veredicto: {verdict}.")
    return " ".join(parts)


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    import math

    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return ((centre - margin) / denom, (centre + margin) / denom)


def summarize_population(cases: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(cases)
    with_fuerte = [c for c in cases if c.get("official_strengthened")]
    multi = [c for c in with_fuerte if not c.get("resultado_unico")]
    none = [c for c in cases if not c.get("official_strengthened")]
    t2_rej = [c for c in cases if c.get("verdict") == "DIRECT_T2_RECHAZADO"]

    def window_hits(w: str) -> tuple[int, int]:
        denom = len(with_fuerte)
        num = sum(1 for c in with_fuerte if c["windows"][w]["hit"])
        return num, denom

    metrics = {}
    for w in WINDOWS:
        num, den = window_hits(w)
        lo, hi = wilson_ci(num, den)
        metrics[w] = {
            "hits": num,
            "denominator_cases_with_fuerte": den,
            "precision": round(num / den, 6) if den else 0.0,
            "wilson_ci_95": [round(lo, 6), round(hi, 6)],
        }

    avg_cands = (
        sum(len(c.get("official_strengthened") or []) for c in cases) / n if n else 0
    )
    return {
        "total_cases": n,
        "cases_with_fuerte": len(with_fuerte),
        "cases_multi_fuerte": len(multi),
        "cases_sin_fuerte": len(none),
        "cases_direct_t2_rechazado": len(t2_rej),
        "avg_candidates_per_case": round(avg_cands, 4),
        "windows": metrics,
        "verdict_counts": _count_by(cases, "verdict"),
    }


def _count_by(cases: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in cases:
        k = str(c.get(key))
        out[k] = out.get(k, 0) + 1
    return out


def select_ten_cases(
    population: list[dict[str, Any]],
    *,
    anchors: list[dict[str, Any]],
    seed: int = SEED_DEFAULT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reproducible selection: fixed anchors + seeded stratified fill.

    Quotas (minimum):
    - 5 hits (any window)
    - 3 fails (has fuerte but no window hit)
    - 1 multi-candidate
    - 1 sin confirmación
    - 1 DIRECT_T2_RECHAZADO
    """
    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    selected_keys: set[str] = set()

    def key(c: dict[str, Any]) -> str:
        return f"{c['date']}|{c.get('label')}|{','.join(sorted(str(o['number'])+o['lottery_name'] for o in c['observations']))}"

    for a in anchors:
        selected.append(a)
        selected_keys.add(key(a))

    def is_hit(c: dict[str, Any]) -> bool:
        return any(c["windows"][w]["hit"] for w in WINDOWS) and bool(
            c.get("official_strengthened")
        )

    def is_fail(c: dict[str, Any]) -> bool:
        return bool(c.get("official_strengthened")) and not any(
            c["windows"][w]["hit"] for w in WINDOWS
        )

    pools = {
        "hit": [c for c in population if is_hit(c) and key(c) not in selected_keys],
        "fail": [c for c in population if is_fail(c) and key(c) not in selected_keys],
        "multi": [
            c
            for c in population
            if c.get("official_strengthened")
            and not c.get("resultado_unico")
            and key(c) not in selected_keys
        ],
        "none": [
            c
            for c in population
            if not c.get("official_strengthened")
            and c.get("verdict") != "DIRECT_T2_RECHAZADO"
            and key(c) not in selected_keys
        ],
        "t2": [
            c
            for c in population
            if c.get("verdict") == "DIRECT_T2_RECHAZADO" and key(c) not in selected_keys
        ],
    }
    for p in pools.values():
        rng.shuffle(p)

    def take(pool_name: str, n: int) -> None:
        pool = pools[pool_name]
        while n > 0 and pool:
            c = pool.pop()
            k = key(c)
            if k in selected_keys:
                continue
            selected.append(c)
            selected_keys.add(k)
            n -= 1

    # Ensure quotas counting anchors already selected
    def count_hit() -> int:
        return sum(1 for c in selected if is_hit(c))

    def count_fail() -> int:
        return sum(1 for c in selected if is_fail(c))

    def count_multi() -> int:
        return sum(
            1
            for c in selected
            if c.get("official_strengthened") and not c.get("resultado_unico")
        )

    def count_none() -> int:
        return sum(1 for c in selected if not c.get("official_strengthened"))

    def count_t2() -> int:
        return sum(1 for c in selected if c.get("verdict") == "DIRECT_T2_RECHAZADO")

    take("hit", max(0, 5 - count_hit()))
    take("fail", max(0, 3 - count_fail()))
    take("multi", max(0, 1 - count_multi()))
    take("none", max(0, 1 - count_none()))
    take("t2", max(0, 1 - count_t2()))

    # fill to at least 10 with chronological earliest remaining from mixed pool
    if len(selected) < 10:
        rest = [c for c in population if key(c) not in selected_keys]
        rest.sort(key=lambda c: c["date"])
        for c in rest:
            if len(selected) >= 10:
                break
            selected.append(c)
            selected_keys.add(key(c))

    # renumber ids HIST-001...
    out = []
    for i, c in enumerate(selected, start=1):
        cc = dict(c)
        cc["id"] = f"HIST-{i:03d}"
        out.append(cc)

    meta = {
        "seed": seed,
        "selection_criterion": (
            "Anchors C1/C3/C4/C5 fixed; then seeded shuffle fill by quota "
            "(5 hits / 3 fails / 1 multi / 1 none / 1 DIRECT_T2); "
            "remainder chronological. No success-based reordering after windows."
        ),
        "quotas_achieved": {
            "hits": count_hit(),
            "fails": count_fail(),
            "multi": count_multi(),
            "sin_confirmacion_or_none": count_none(),
            "direct_t2": count_t2(),
            "total": len(out),
        },
    }
    # recount after renumber - need recount on out
    meta["quotas_achieved"] = {
        "hits": sum(1 for c in out if is_hit(c)),
        "fails": sum(1 for c in out if is_fail(c)),
        "multi": sum(
            1
            for c in out
            if c.get("official_strengthened") and not c.get("resultado_unico")
        ),
        "sin_fuerte": sum(1 for c in out if not c.get("official_strengthened")),
        "direct_t2": sum(1 for c in out if c.get("verdict") == "DIRECT_T2_RECHAZADO"),
        "total": len(out),
    }
    return out, meta


def next_calendar_day_numbers(
    case_date: date, by_date: dict[date, list[dict[str, Any]]]
) -> set[int]:
    """All in-universe numbers drawn in FEATURED_SEVEN on the next calendar day."""
    out: set[int] = set()
    for dr in by_date.get(case_date + timedelta(days=1), []):
        for n in dr.get("numbers") or []:
            if _in_universe(int(n)):
                out.add(int(n))
    return out


def random_baselines(
    population: list[dict[str, Any]],
    *,
    by_date: dict[date, list[dict[str, Any]]],
    seed: int = SEED_DEFAULT,
) -> dict[str, Any]:
    """Fair next_calendar_day hit-rate: prediction ∩ next-day universe (not look-ahead)."""
    rng = random.Random(seed)
    with_f = [c for c in population if c.get("official_strengthened")]
    if not with_f:
        return {"error": "no cases with fuerte"}

    # Precompute next-day universes (look-ahead only for scoring, never for candidate selection)
    day_sets: list[set[int]] = []
    for c in with_f:
        day_sets.append(next_calendar_day_numbers(date.fromisoformat(c["date"]), by_date))

    eligible_idx = [i for i, s in enumerate(day_sets) if s]
    n_elig = len(eligible_idx)
    avg_coverage = (
        sum(len(day_sets[i]) for i in eligible_idx) / n_elig / 100.0 if n_elig else 0.0
    )

    def hit_rate(picker) -> dict[str, Any]:
        hits = 0
        for i in eligible_idx:
            c = with_f[i]
            preds = set(int(x) for x in picker(c, rng))
            if preds & day_sets[i]:
                hits += 1
        lo, hi = wilson_ci(hits, n_elig)
        return {
            "hits": hits,
            "denominator": n_elig,
            "hit_rate": round(hits / n_elig, 6) if n_elig else 0.0,
            "wilson_ci_95": [round(lo, 6), round(hi, 6)],
            "cases_with_fuerte_total": len(with_f),
            "cases_excluded_no_next_day_draws": len(with_f) - n_elig,
        }

    official = hit_rate(
        lambda c, r: [h["candidate"] for h in c["official_strengthened"]]
    )
    rand1 = hit_rate(lambda c, r: [r.randint(1, 100)])
    randk = hit_rate(
        lambda c, r: r.sample(
            range(1, 101), k=max(1, len(c.get("official_strengthened") or [1]))
        )
    )

    def t1_unconfirmed(c, r):
        obs = c["observations"]
        if not obs:
            return []
        return list(obs[0].get("table1_companions") or [])[:5]

    def t2_direct(c, r):
        obs = c["observations"]
        if not obs:
            return []
        return list(obs[0].get("table2_neighbors") or [])

    t1_nc = hit_rate(t1_unconfirmed)
    t2 = hit_rate(t2_direct)

    # Theoretical base: P(random one hits) ≈ mean(|U|/100)
    base_rate = round(avg_coverage, 6)
    # Theoretical for same-k: 1 - (1-p)^k using average k
    avg_k = (
        sum(len(c.get("official_strengthened") or []) for c in with_f) / len(with_f)
        if with_f
        else 1.0
    )
    theor_k = round(1.0 - (1.0 - avg_coverage) ** avg_k, 6) if avg_coverage < 1 else 1.0

    def lift(a: dict[str, Any], b: dict[str, Any]) -> float | None:
        if not b["hit_rate"]:
            return None
        return round(a["hit_rate"] / b["hit_rate"], 4)

    return {
        "window": "next_calendar_day",
        "definition": (
            "Hit iff prediction_set ∩ next_calendar_day FEATURED_SEVEN numbers ≠ ∅. "
            "Denominator = cases with ≥1 official fuerte AND at least one next-day featured draw. "
            "Candidates never selected using future draws (look-ahead blocked for selection)."
        ),
        "official_t1_x_t2": official,
        "random_one_number": rand1,
        "random_same_k": randk,
        "t1_companions_no_confirmation": t1_nc,
        "direct_t2_neighbors_rejected_rule": t2,
        "base_frequency_empirical_mean_coverage": {
            "mean_next_day_unique_numbers_over_100": base_rate,
            "expected_hit_rate_random_one": base_rate,
            "avg_k_official": round(avg_k, 4),
            "expected_hit_rate_random_same_k": theor_k,
            "numerator_definition": "mean(|unique next-day numbers|)/100 over eligible cases",
            "denominator": n_elig,
        },
        "lift_official_vs_random_one": lift(official, rand1),
        "lift_official_vs_random_same_k": lift(official, randk),
        "lift_official_vs_t1_unconfirmed": lift(official, t1_nc),
        "lift_official_vs_direct_t2": lift(official, t2),
        "lift_official_vs_base_frequency_random_one": (
            round(official["hit_rate"] / base_rate, 4) if base_rate else None
        ),
        "absolute_diff_vs_random_same_k": round(
            official["hit_rate"] - randk["hit_rate"], 6
        ),
        "seed": seed,
        "bias_note": (
            "Prior biased baseline that scored random against official first_appearance "
            "only is retired; this version uses the full next-day number universe."
        ),
    }


def new_audit_id() -> str:
    return str(uuid4())


def content_fingerprint(payload: dict[str, Any]) -> str:
    raw = repr(sorted(payload.items())).encode()
    return hashlib.sha256(raw).hexdigest()[:16]
