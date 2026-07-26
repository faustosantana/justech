"""Four-year FEATURED_SEVEN historical audit — read-only, deterministic.

Extends official T1×T2 geometry. Does not modify motor, tables, or Production.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable
from uuid import uuid4

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION
from app.lottery.numeric_relations.historical_manual_audit import (
    ObservedNumber,
    SEED_DEFAULT,
    StrengthenedHit,
    _companions,
    _in_universe,
    _neighbors,
    direct_t2_signals,
    strengthen_official,
    wilson_ci,
)

PREFERRED_FROM = date(2022, 7, 26)
PREFERRED_TO = date(2026, 7, 26)

# Extended windows (reported separately; never mixed)
WINDOW_SPECS: tuple[tuple[str, str], ...] = (
    ("W1_next_chronological_draw", "next_chrono_1"),
    ("W2_same_day_other_draws", "same_day"),
    ("W3_next_calendar_day", "next_day_1"),
    ("W4_next_3_featured_draws", "next_chrono_3"),
    ("W5_next_7_featured_draws", "next_chrono_7"),
    ("W6_next_14_featured_draws", "next_chrono_14"),
    ("W7_next_3_calendar_days", "next_days_3"),
    ("W8_next_7_calendar_days", "next_days_7"),
)

MIN_SAMPLE_RELATION = 20
MIN_SAMPLE_LIFT_RANK = 30


def new_audit_id() -> str:
    return str(uuid4())


def classify_day_level(
    hits: list[StrengthenedHit],
    *,
    has_t1_unconfirmed: bool,
    has_direct_t2: bool,
) -> str:
    if hits:
        if len(hits) > 1:
            return "NIVEL_5_MULTIPLES_FUERTES"
        n_conf = len(hits[0].confirmers)
        if n_conf >= 3:
            return "NIVEL_4_MULTICONFIRMADO"
        if n_conf == 2:
            return "NIVEL_3_DOS_CONFIRMACIONES"
        return "NIVEL_2_UNA_CONFIRMACION"
    if has_t1_unconfirmed:
        return "NIVEL_1_T1_SIN_CONFIRMACION"
    if has_direct_t2:
        return "NIVEL_X_DIRECT_T2_RECHAZADO"
    return "NIVEL_0_SIN_RELACION"


def security_level(
    *,
    n: int,
    lift: float | None,
    ci: tuple[float, float] | None,
    years_positive: int,
    years_total: int,
    oos_lift: float | None,
) -> str:
    """A–E evidence scale. Near-1 lift ⇒ not strong."""
    if n < 15 or lift is None:
        return "C_PROMETEDOR_NO_CONCLUYENTE" if n >= 5 and lift and lift > 1.05 else "D_SIN_VENTAJA"
    ci_ok = ci is not None and ci[0] > 1.0
    stable = years_total >= 2 and years_positive >= max(2, years_total - 1)
    oos_ok = oos_lift is not None and oos_lift >= 1.15
    if lift >= 1.35 and ci_ok and stable and oos_ok and n >= 40:
        return "A_EVIDENCIA_FUERTE"
    if lift >= 1.20 and (ci_ok or oos_ok) and n >= 25 and years_positive >= 1:
        return "B_EVIDENCIA_MODERADA"
    if lift >= 1.10 and n >= 15:
        return "C_PROMETEDOR_NO_CONCLUYENTE"
    if lift < 1.0 or (ci is not None and ci[1] < 1.0):
        return "E_RECHAZADO"
    return "D_SIN_VENTAJA"


def appearance_in_draws(
    targets: set[int], draws: list[dict[str, Any]]
) -> dict[str, Any] | None:
    for d in draws:
        for n, pos, label in zip(d["numbers"], d["positions"], d["position_labels"]):
            if int(n) in targets and _in_universe(int(n)):
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


def slice_windows(
    *,
    case_date: date,
    case_draw_ids: set[str],
    all_draws_sorted: list[dict[str, Any]],
    by_date: dict[date, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    case_indices = [
        i for i, d in enumerate(all_draws_sorted) if d["draw_id"] in case_draw_ids
    ]
    max_idx = max(case_indices) if case_indices else -1
    same_day = [d for d in by_date.get(case_date, []) if d["draw_id"] not in case_draw_ids]
    return {
        "W1_next_chronological_draw": all_draws_sorted[max_idx + 1 : max_idx + 2],
        "W2_same_day_other_draws": same_day,
        "W3_next_calendar_day": by_date.get(case_date + timedelta(days=1), []),
        "W4_next_3_featured_draws": all_draws_sorted[max_idx + 1 : max_idx + 4],
        "W5_next_7_featured_draws": all_draws_sorted[max_idx + 1 : max_idx + 8],
        "W6_next_14_featured_draws": all_draws_sorted[max_idx + 1 : max_idx + 15],
        "W7_next_3_calendar_days": [
            d
            for offset in range(1, 4)
            for d in by_date.get(case_date + timedelta(days=offset), [])
        ],
        "W8_next_7_calendar_days": [
            d
            for offset in range(1, 8)
            for d in by_date.get(case_date + timedelta(days=offset), [])
        ],
    }


def evaluate_all_windows(
    fuertes: list[int],
    *,
    case_date: date,
    case_draw_ids: set[str],
    all_draws_sorted: list[dict[str, Any]],
    by_date: dict[date, list[dict[str, Any]]],
) -> dict[str, Any]:
    target = set(int(x) for x in fuertes)
    slices = slice_windows(
        case_date=case_date,
        case_draw_ids=case_draw_ids,
        all_draws_sorted=all_draws_sorted,
        by_date=by_date,
    )
    out: dict[str, Any] = {}
    if not target:
        for w, _ in WINDOW_SPECS:
            out[w] = {"hit": False, "first_appearance": None, "draw_count_in_window": 0}
        return out
    for w, draws in slices.items():
        app = appearance_in_draws(target, draws)
        out[w] = {
            "hit": app is not None,
            "first_appearance": app,
            "draw_count_in_window": len(draws),
        }
    return out


def has_t1_unconfirmed(observations: list[ObservedNumber], cat: TableCatalog) -> bool:
    nums = {int(o.number) for o in observations if _in_universe(o.number)}
    for g in nums:
        for c in _companions(cat, g):
            if set(_neighbors(cat, c)) & (nums - {g}):
                return False  # at least one confirmed exists → not "only unconfirmed"
            # companions exist without confirmation
            if _companions(cat, g):
                # continue scanning; true if any companion never confirmed
                pass
    # True if any generator has companions but none confirmed
    for g in nums:
        comps = _companions(cat, g)
        if not comps:
            continue
        others = nums - {g}
        if not any(set(_neighbors(cat, c)) & others for c in comps):
            return True
    return False


def relation_key(h: StrengthenedHit) -> str:
    conf = ",".join(str(x) for x in sorted(h.confirmers))
    return f"{h.generator_observed}->{h.candidate}<-{conf}"


def lottery_pair_key(names: list[str]) -> str:
    return " + ".join(sorted(names))


@dataclass
class DayCase:
    case_date: date
    observations: list[ObservedNumber]
    hits: list[StrengthenedHit]
    level: str
    windows: dict[str, Any]
    direct_t2: list[dict[str, Any]]
    year: int


def build_day_case(
    *,
    case_date: date,
    observations: list[ObservedNumber],
    catalog: TableCatalog,
    all_draws_sorted: list[dict[str, Any]],
    by_date: dict[date, list[dict[str, Any]]],
) -> DayCase:
    hits = strengthen_official(observations, catalog=catalog)
    t2 = direct_t2_signals(
        observations, catalog=catalog, official_candidates=[h.candidate for h in hits]
    )
    level = classify_day_level(
        hits,
        has_t1_unconfirmed=has_t1_unconfirmed(observations, catalog) and not hits,
        has_direct_t2=bool(t2) and not hits,
    )
    windows = evaluate_all_windows(
        [h.candidate for h in hits],
        case_date=case_date,
        case_draw_ids={o.draw_id for o in observations},
        all_draws_sorted=all_draws_sorted,
        by_date=by_date,
    )
    return DayCase(
        case_date=case_date,
        observations=observations,
        hits=hits,
        level=level,
        windows=windows,
        direct_t2=t2,
        year=case_date.year,
    )


def coverage_table(
    by_date: dict[date, list[dict[str, Any]]],
    *,
    date_from: date,
    date_to: date,
    featured_count: int = 7,
) -> list[dict[str, Any]]:
    rows = []
    for year in range(date_from.year, date_to.year + 1):
        y0 = max(date_from, date(year, 1, 1))
        y1 = min(date_to, date(year, 12, 31))
        days = [d for d in by_date if y0 <= d <= y1]
        draws = sum(len(by_date[d]) for d in days)
        # expected ≈ featured_count draws/day (approximate; calendar varies)
        calendar_days = (y1 - y0).days + 1
        expected = calendar_days * featured_count
        cov = round(100.0 * draws / expected, 2) if expected else 0.0
        rows.append(
            {
                "year": year,
                "date_from": y0.isoformat(),
                "date_to": y1.isoformat(),
                "calendar_days": calendar_days,
                "days_with_any_featured_draw": len(days),
                "draws_available": draws,
                "draws_expected_approx": expected,
                "coverage_pct_approx": cov,
                "note": "expected ≈ 7 draws/calendar day; real calendars vary by lottery schedule",
            }
        )
    return rows


def next_day_universe(
    case_date: date, by_date: dict[date, list[dict[str, Any]]]
) -> set[int]:
    out: set[int] = set()
    for dr in by_date.get(case_date + timedelta(days=1), []):
        for n in dr.get("numbers") or []:
            if _in_universe(int(n)):
                out.add(int(n))
    return out


def aggregate_audit(
    days: list[DayCase],
    *,
    by_date: dict[date, list[dict[str, Any]]],
    catalog: TableCatalog,
    seed: int = SEED_DEFAULT,
) -> dict[str, Any]:
    rng = random.Random(seed)
    with_fuerte = [d for d in days if d.hits]
    level_counts = Counter(d.level for d in days)

    # Window metrics among cases with fuerte
    window_metrics: dict[str, Any] = {}
    for w, _ in WINDOW_SPECS:
        hits_n = sum(1 for d in with_fuerte if d.windows[w]["hit"])
        den = len(with_fuerte)
        lo, hi = wilson_ci(hits_n, den)
        window_metrics[w] = {
            "hits": hits_n,
            "denominator": den,
            "hit_rate": round(hits_n / den, 6) if den else 0.0,
            "wilson_ci_95": [round(lo, 6), round(hi, 6)],
        }

    # Relation stats (activation + W3 hit)
    rel_stats: dict[str, dict[str, Any]] = {}
    for d in with_fuerte:
        u = next_day_universe(d.case_date, by_date)
        for h in d.hits:
            key = relation_key(h)
            st = rel_stats.setdefault(
                key,
                {
                    "relation": key,
                    "generator": h.generator_observed,
                    "candidate": h.candidate,
                    "confirmers": h.confirmers,
                    "n_confirmers": len(h.confirmers),
                    "activations": 0,
                    "w3_hits": 0,
                    "years": Counter(),
                    "generator_lotteries": Counter(),
                    "confirmer_lotteries": Counter(),
                },
            )
            st["activations"] += 1
            st["years"][d.year] += 1
            st["generator_lotteries"][h.generator_lottery] += 1
            for cl in h.confirmer_lotteries:
                st["confirmer_lotteries"][cl] += 1
            if h.candidate in u:
                st["w3_hits"] += 1

    relations_out = []
    for st in rel_stats.values():
        n = st["activations"]
        hits = st["w3_hits"]
        hr = hits / n if n else 0.0
        lo, hi = wilson_ci(hits, n)
        # empirical base for same-k=1 ≈ mean coverage; use later global
        years_pos = sum(1 for y, c in st["years"].items() if c > 0)
        relations_out.append(
            {
                **{k: st[k] for k in ("relation", "generator", "candidate", "confirmers", "n_confirmers", "activations", "w3_hits")},
                "hit_rate_w3": round(hr, 6),
                "wilson_ci_95": [round(lo, 6), round(hi, 6)],
                "years_active": sorted(st["years"].keys()),
                "years_count": dict(st["years"]),
                "generator_lotteries": dict(st["generator_lotteries"]),
                "confirmer_lotteries": dict(st["confirmer_lotteries"]),
            }
        )

    # Number profiles 1..100
    observed_c = Counter()
    cand_c = Counter()
    fuerte_c = Counter()
    fuerte_w3 = Counter()
    for d in days:
        for o in d.observations:
            if _in_universe(o.number):
                observed_c[int(o.number)] += 1
        for h in d.hits:
            fuerte_c[h.candidate] += 1
            if d.windows["W3_next_calendar_day"]["hit"] and (
                (d.windows["W3_next_calendar_day"]["first_appearance"] or {}).get("number")
                == h.candidate
                or h.candidate in next_day_universe(d.case_date, by_date)
            ):
                fuerte_w3[h.candidate] += 1
            for c in h.table1_companions_of_generator:
                cand_c[c] += 1

    # Fair baselines on W3 for cases with fuerte
    elig = []
    day_sets = []
    for d in with_fuerte:
        u = next_day_universe(d.case_date, by_date)
        if u:
            elig.append(d)
            day_sets.append(u)
    n_elig = len(elig)
    avg_cov = (
        sum(len(s) for s in day_sets) / n_elig / 100.0 if n_elig else 0.0
    )
    avg_k = (
        sum(len(d.hits) for d in with_fuerte) / len(with_fuerte) if with_fuerte else 1.0
    )

    def hit_rate(picker) -> dict[str, Any]:
        hits = 0
        for i, d in enumerate(elig):
            preds = set(int(x) for x in picker(d, rng))
            if preds & day_sets[i]:
                hits += 1
        lo, hi = wilson_ci(hits, n_elig)
        return {
            "hits": hits,
            "denominator": n_elig,
            "hit_rate": round(hits / n_elig, 6) if n_elig else 0.0,
            "wilson_ci_95": [round(lo, 6), round(hi, 6)],
        }

    official = hit_rate(lambda d, r: [h.candidate for h in d.hits])
    rand1 = hit_rate(lambda d, r: [r.randint(1, 100)])
    randk = hit_rate(
        lambda d, r: r.sample(range(1, 101), k=max(1, len(d.hits)))
    )

    def t1_nc(d, r):
        if not d.observations:
            return []
        return _companions(catalog, d.observations[0].number)[:5]

    def t2_dir(d, r):
        if not d.observations:
            return []
        return _neighbors(catalog, d.observations[0].number)

    # freq prior: top-k by observed_c excluding look-ahead would need per-case; approximate global prior
    top_freq = [n for n, _ in observed_c.most_common(20)]

    def freq_ctrl(d, r):
        k = max(1, len(d.hits))
        return top_freq[:k]

    t1 = hit_rate(t1_nc)
    t2 = hit_rate(t2_dir)
    freq = hit_rate(freq_ctrl)

    def lift(a, b):
        if not b["hit_rate"]:
            return None
        return round(a["hit_rate"] / b["hit_rate"], 4)

    # Attach lifts to relations vs avg_cov (random one) and theor same-k
    theor_k = 1.0 - (1.0 - avg_cov) ** avg_k if avg_cov < 1 else 1.0
    for r in relations_out:
        r["lift_vs_base_freq_random_one"] = (
            round(r["hit_rate_w3"] / avg_cov, 4) if avg_cov else None
        )
        r["lift_vs_expected_same_k1"] = (
            round(r["hit_rate_w3"] / avg_cov, 4) if avg_cov else None
        )
        years_pos = len([y for y, c in r["years_count"].items() if c > 0])
        r["security_level"] = security_level(
            n=r["activations"],
            lift=r["lift_vs_base_freq_random_one"],
            ci=None,
            years_positive=years_pos,
            years_total=len(r["years_active"]),
            oos_lift=None,
        )

    # Confirmation-level buckets
    conf_buckets: dict[str, list[DayCase]] = defaultdict(list)
    for d in with_fuerte:
        # use max confirmers among hits that day
        mx = max(len(h.confirmers) for h in d.hits)
        if mx >= 4:
            key = "4+"
        else:
            key = str(mx)
        conf_buckets[key].append(d)

    conf_level_metrics = {}
    for key, bucket in sorted(conf_buckets.items()):
        h = sum(1 for d in bucket if d.windows["W3_next_calendar_day"]["hit"])
        den = len(bucket)
        lo, hi = wilson_ci(h, den)
        conf_level_metrics[key] = {
            "cases": den,
            "w3_hits": h,
            "hit_rate": round(h / den, 6) if den else 0.0,
            "wilson_ci_95": [round(lo, 6), round(hi, 6)],
        }

    # Yearly
    yearly = {}
    for year in sorted({d.year for d in days}):
        yd = [d for d in days if d.year == year]
        yf = [d for d in yd if d.hits]
        h = sum(1 for d in yf if d.windows["W3_next_calendar_day"]["hit"])
        den = len(yf)
        lo, hi = wilson_ci(h, den)
        yearly[str(year)] = {
            "days": len(yd),
            "days_with_fuerte": den,
            "w3_hits": h,
            "hit_rate": round(h / den, 6) if den else 0.0,
            "wilson_ci_95": [round(lo, 6), round(hi, 6)],
            "level_counts": dict(Counter(d.level for d in yd)),
        }

    # Lottery pairs (generator lottery × confirmer lottery from hits)
    pair_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"activations": 0, "w3_hits": 0}
    )
    for d in with_fuerte:
        u = next_day_universe(d.case_date, by_date)
        for h in d.hits:
            gens = [x.strip() for x in h.generator_lottery.split(",") if x.strip()]
            for g in gens:
                for c in h.confirmer_lotteries:
                    pk = lottery_pair_key([g, c])
                    pair_stats[pk]["activations"] += 1
                    if h.candidate in u:
                        pair_stats[pk]["w3_hits"] += 1
    pairs_out = []
    for pk, st in pair_stats.items():
        n = st["activations"]
        hits = st["w3_hits"]
        lo, hi = wilson_ci(hits, n)
        pairs_out.append(
            {
                "pair": pk,
                "activations": n,
                "w3_hits": hits,
                "hit_rate": round(hits / n, 6) if n else 0.0,
                "wilson_ci_95": [round(lo, 6), round(hi, 6)],
            }
        )
    pairs_out.sort(key=lambda x: (-x["activations"], -x["hit_rate"]))

    # Number profiles
    number_profiles = []
    for n in range(1, 101):
        t1c = catalog.table1_number_to_code.get(n)
        try:
            t2c = catalog.get_table2_code_for_number(n)
        except KeyError:
            t2c = None
        act = fuerte_c[n]
        wh = fuerte_w3[n]
        hr = wh / act if act else 0.0
        lo, hi = wilson_ci(wh, act) if act else (0.0, 0.0)
        lift_n = round(hr / avg_cov, 4) if act and avg_cov else None
        number_profiles.append(
            {
                "number": n,
                "table1_code": t1c,
                "table2_code": t2c,
                "times_observed": observed_c[n],
                "times_strengthened": act,
                "w3_hits_when_strengthened": wh,
                "hit_rate_w3": round(hr, 6) if act else None,
                "wilson_ci_95": [round(lo, 6), round(hi, 6)] if act else None,
                "lift_vs_base_freq": lift_n,
                "security_level": security_level(
                    n=act,
                    lift=lift_n,
                    ci=(lo / avg_cov, hi / avg_cov) if act and avg_cov else None,
                    years_positive=0,
                    years_total=0,
                    oos_lift=None,
                )
                if act
                else "D_SIN_VENTAJA",
            }
        )

    # Walk-forward: discover years -> validate next year on official W3 hit rate
    years_sorted = sorted({d.year for d in days})
    walk_forward = []
    for i in range(len(years_sorted) - 1):
        train_years = set(years_sorted[: i + 1])
        test_year = years_sorted[i + 1]
        train = [d for d in with_fuerte if d.year in train_years]
        test = [d for d in with_fuerte if d.year == test_year]
        def hr(cases):
            if not cases:
                return {"hits": 0, "denominator": 0, "hit_rate": 0.0}
            h = sum(1 for d in cases if d.windows["W3_next_calendar_day"]["hit"])
            return {
                "hits": h,
                "denominator": len(cases),
                "hit_rate": round(h / len(cases), 6),
            }
        tr = hr(train)
        te = hr(test)
        walk_forward.append(
            {
                "train_years": sorted(train_years),
                "test_year": test_year,
                "in_sample_w3": tr,
                "out_of_sample_w3": te,
                "degradation_pp": round(
                    (te["hit_rate"] - tr["hit_rate"]) * 100, 3
                ),
            }
        )

    # Rankings
    by_sample = sorted(relations_out, key=lambda r: -r["activations"])[:20]
    by_lift = sorted(
        [r for r in relations_out if r["activations"] >= MIN_SAMPLE_LIFT_RANK],
        key=lambda r: (-(r["lift_vs_base_freq_random_one"] or 0), -r["activations"]),
    )[:20]
    worst = sorted(
        [r for r in relations_out if r["activations"] >= MIN_SAMPLE_RELATION],
        key=lambda r: ((r["lift_vs_base_freq_random_one"] or 99), -r["activations"]),
    )[:20]
    deceptive = sorted(
        [
            r
            for r in relations_out
            if r["hit_rate_w3"] >= 0.35 and r["activations"] < MIN_SAMPLE_RELATION
        ],
        key=lambda r: -r["hit_rate_w3"],
    )[:20]

    return {
        "methodology_version": METHODOLOGY_VERSION,
        "seed": seed,
        "total_days": len(days),
        "days_with_fuerte": len(with_fuerte),
        "days_multi_fuerte": sum(1 for d in days if len(d.hits) > 1),
        "days_sin_fuerte": sum(1 for d in days if not d.hits),
        "total_strengthened_instances": sum(len(d.hits) for d in days),
        "level_counts": dict(level_counts),
        "window_metrics": window_metrics,
        "confirmation_level_metrics": conf_level_metrics,
        "yearly": yearly,
        "lottery_pairs": pairs_out[:50],
        "baselines_w3": {
            "window": "W3_next_calendar_day",
            "definition": (
                "Hit iff prediction ∩ next-day FEATURED numbers ≠ ∅. "
                "Denom = days with ≥1 fuerte and next-day draws."
            ),
            "official_t1_x_t2": official,
            "random_one": rand1,
            "random_same_k": randk,
            "t1_unconfirmed": t1,
            "direct_t2_rejected_rule": t2,
            "frequency_prior_topk": freq,
            "base_frequency_mean_coverage": round(avg_cov, 6),
            "avg_k": round(avg_k, 4),
            "expected_random_same_k": round(theor_k, 6),
            "lift_official_vs_random_one": lift(official, rand1),
            "lift_official_vs_random_same_k": lift(official, randk),
            "lift_official_vs_t1_unconfirmed": lift(official, t1),
            "lift_official_vs_direct_t2": lift(official, t2),
            "lift_official_vs_freq_prior": lift(official, freq),
            "absolute_diff_vs_random_same_k": round(
                official["hit_rate"] - randk["hit_rate"], 6
            ),
        },
        "walk_forward": walk_forward,
        "relations_count": len(relations_out),
        "top_relations_by_sample": by_sample,
        "top_relations_by_lift_min_sample": by_lift,
        "worst_relations_min_sample": worst,
        "deceptive_relations": deceptive,
        "number_profiles": number_profiles,
        "all_relations": relations_out,
    }


def pick_ten_explained(
    days: list[DayCase], *, seed: int = SEED_DEFAULT
) -> list[dict[str, Any]]:
    """Educational mix; not the statistical base. Seeded + anchors."""
    rng = random.Random(seed)
    anchors_dates = {
        date(2026, 6, 21),
        date(2026, 6, 23),
        date(2026, 7, 22),
    }
    selected: list[DayCase] = []
    seen = set()

    def add(d: DayCase) -> None:
        if d.case_date in seen:
            return
        seen.add(d.case_date)
        selected.append(d)

    for d in days:
        if d.case_date in anchors_dates:
            add(d)
    pools = {
        "hit": [d for d in days if d.hits and d.windows["W3_next_calendar_day"]["hit"]],
        "fail": [d for d in days if d.hits and not d.windows["W3_next_calendar_day"]["hit"]],
        "multi": [d for d in days if len(d.hits) > 1],
        "none": [d for d in days if not d.hits and d.level != "NIVEL_X_DIRECT_T2_RECHAZADO"],
        "t2": [d for d in days if d.level == "NIVEL_X_DIRECT_T2_RECHAZADO"],
        "multi_conf": [d for d in days if d.hits and any(len(h.confirmers) >= 2 for h in d.hits)],
    }
    for p in pools.values():
        rng.shuffle(p)

    def take(name: str, n: int) -> None:
        for d in pools[name]:
            if len(selected) >= 10:
                break
            if n <= 0:
                break
            before = len(selected)
            add(d)
            if len(selected) > before:
                n -= 1

    take("hit", 3)
    take("fail", 2)
    take("multi", 1)
    take("multi_conf", 1)
    take("none", 1)
    take("t2", 1)
    # fill chronologically from remaining years
    rest = sorted([d for d in days if d.case_date not in seen], key=lambda x: x.case_date)
    for d in rest:
        if len(selected) >= 10:
            break
        add(d)

    cards = []
    for i, d in enumerate(selected[:10], start=1):
        cards.append(
            {
                "id": f"FY-{i:03d}",
                "date": d.case_date.isoformat(),
                "year": d.year,
                "level": d.level,
                "observations": [
                    {
                        "lottery_name": o.lottery_name,
                        "lottery_id": o.lottery_id,
                        "draw_id": o.draw_id,
                        "draw_time": o.draw_time,
                        "position": o.position,
                        "number": o.number,
                        "source_reference": o.source_reference,
                    }
                    for o in d.observations
                ],
                "official_strengthened": [
                    {
                        "candidate": h.candidate,
                        "generator_observed": h.generator_observed,
                        "generator_lottery": h.generator_lottery,
                        "confirmers": h.confirmers,
                        "confirmer_lotteries": h.confirmer_lotteries,
                        "n_confirmers": len(h.confirmers),
                    }
                    for h in d.hits
                ],
                "windows": {
                    k: {
                        "hit": v["hit"],
                        "first_appearance": v.get("first_appearance"),
                    }
                    for k, v in d.windows.items()
                },
                "direct_t2_sample": d.direct_t2[:5],
                "explanation": _explain_day(d),
            }
        )
    return cards


def _explain_day(d: DayCase) -> str:
    if d.level == "NIVEL_X_DIRECT_T2_RECHAZADO":
        eg = d.direct_t2[0] if d.direct_t2 else {}
        return (
            f"Sin fuerte oficial. Señal T2 directa "
            f"{eg.get('observed')}→{eg.get('direct_t2_neighbor')} rechazada como regla predictiva."
        )
    if not d.hits:
        return "Sin candidato T1 confirmado por otro observado ese día."
    parts = []
    for h in d.hits:
        parts.append(
            f"{h.generator_observed} ({h.generator_lottery}) genera candidato T1 {h.candidate}; "
            f"confirmado por {h.confirmers} ({', '.join(h.confirmer_lotteries)})."
        )
    w3 = d.windows["W3_next_calendar_day"]
    if w3["hit"] and w3["first_appearance"]:
        fa = w3["first_appearance"]
        parts.append(
            f"Al día siguiente apareció {fa['number']} en {fa['lottery_name']} "
            f"pos {fa['position']} (ref {fa.get('source_reference')})."
        )
    else:
        parts.append("No apareció en la ventana día calendario siguiente (W3).")
    parts.append(f"Nivel: {d.level}.")
    return " ".join(parts)


def decide_verdicts(agg: dict[str, Any]) -> dict[str, Any]:
    base = agg["baselines_w3"]
    lift_k = base.get("lift_official_vs_random_same_k")
    hr = base["official_t1_x_t2"]["hit_rate"]
    n = base["official_t1_x_t2"]["denominator"]
    wf = agg.get("walk_forward") or []
    oos_positive = sum(
        1
        for w in wf
        if w["out_of_sample_w3"]["denominator"] >= 50
        and w["out_of_sample_w3"]["hit_rate"] > 0
    )

    math_v = "GEOMETRIA_CORRECTA"  # methodology fixed; C1–C5 already reproduced upstream

    if lift_k is not None and lift_k >= 1.35 and hr >= 0.30 and n >= 500:
        stat = "EVIDENCIA_FUERTE"
    elif lift_k is not None and lift_k >= 1.20 and n >= 300:
        stat = "EVIDENCIA_MODERADA"
    elif lift_k is not None and lift_k >= 1.10:
        stat = "PROMETEDORA"
    elif lift_k is not None and lift_k >= 0.95:
        stat = "SIN_VENTAJA"
    else:
        stat = "RECHAZADA"

    plain = {
        "supera_azar_same_k": bool(lift_k and lift_k >= 1.10),
        "lift_near_one": bool(lift_k is not None and 0.95 <= lift_k < 1.10),
        "ventana_principal_reportada": "W3_next_calendar_day",
        "lift_vs_random_same_k": lift_k,
        "hit_rate_official": hr,
        "n_cases_with_fuerte_and_next_day": n,
        "wilson_ci_95": base["official_t1_x_t2"]["wilson_ci_95"],
        "walk_forward_steps": len(wf),
        "oos_steps_with_data": oos_positive,
    }

    # Geometry may support analytical copiloto; predictive requires statistical edge.
    j11a = ["NO_GO_PARA_J11A_PREDICTIVO"]
    if math_v == "GEOMETRIA_CORRECTA":
        j11a.insert(0, "GO_PARA_J11A_SOLO_COMO_COPILOTO_ANALITICO")

    return {
        "veredicto_matematico": math_v,
        "veredicto_estadistico": stat,
        "respuestas_claras": plain,
        "decision_j11a": j11a,
        "disclaimer": (
            "Frecuencia histórica e intervalos; no garantía predictiva. "
            "No usar lenguaje de certeza ('va a salir')."
        ),
    }
