#!/usr/bin/env python3
"""Backtest DIRECT_T2_NEIGHBOR_SIGNAL vs official F and random baselines.

Read-only against DEV. Does not modify motor/tables/production.
"""

from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.lottery.numeric_relations.catalog import build_catalog  # noqa: E402

DEV_DSN = "postgresql://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev"
OUT = Path(__file__).resolve().parents[2] / "docs/lottery/validation/evidence"
SPLIT = date(2023, 1, 1)  # discovery < SPLIT; validation >= SPLIT
RNG = random.Random(20260725)


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return ((centre - margin) / denom, (centre + margin) / denom)


@dataclass
class WindowStats:
    activations: int = 0
    hits: int = 0

    def add(self, hit: bool) -> None:
        self.activations += 1
        if hit:
            self.hits += 1

    def as_dict(self) -> dict:
        n, h = self.activations, self.hits
        lo, hi = wilson_ci(h, n)
        prec = h / n if n else 0.0
        return {
            "activations": n,
            "hits": h,
            "misses": n - h,
            "precision": round(prec, 6),
            "wilson_ci_95": [round(lo, 6), round(hi, 6)],
        }


def neighbors_map(cat) -> dict[int, list[int]]:
    return {n: list(cat.get_table2_neighbors(n, exclude_self=True)) for n in range(1, 101)}


def companions_map(cat) -> dict[int, list[int]]:
    return {n: list(cat.get_table1_companions(n)) for n in range(1, 101)}


async def load_draws(conn) -> list[dict]:
    rows = await conn.fetch(
        """
        select l.id::text as lottery_id, l.name as lottery_name,
               d.id::text as draw_id, d.draw_date,
               array_agg(dn.number_value::int order by dn.position) as numbers
        from lottery_draws d
        join lottery_lotteries l on l.id = d.lottery_id
        join lottery_draw_numbers dn on dn.draw_id = d.id
        where l.is_featured = true
        group by l.id, l.name, d.id, d.draw_date
        order by d.draw_date, l.name
        """
    )
    return [dict(r) for r in rows]


def run_backtest(draws: list[dict], cat) -> dict:
    neigh = neighbors_map(cat)
    comps = companions_map(cat)

    by_lottery: dict[str, list[dict]] = defaultdict(list)
    by_date: dict[date, list[dict]] = defaultdict(list)
    for d in draws:
        by_lottery[d["lottery_id"]].append(d)
        by_date[d["draw_date"]].append(d)
    for lid in by_lottery:
        by_lottery[lid].sort(key=lambda x: (x["draw_date"], x["draw_id"]))

    # index next draws per lottery
    next_idx: dict[str, dict[str, int]] = {}
    for lid, seq in by_lottery.items():
        next_idx[lid] = {seq[i]["draw_id"]: i for i in range(len(seq))}

    windows = [
        "same_draw",
        "next_draw_same_lottery",
        "same_day_other_lottery",
        "next_calendar_day",
        "next_7_draws_same_lottery",
    ]

    def empty_bucket():
        return {w: WindowStats() for w in windows}

    # strategies: t2_direct, random_same_k, official_f_same_day (special)
    results = {
        "discovery": {"t2_direct": empty_bucket(), "random_same_k": empty_bucket()},
        "validation": {"t2_direct": empty_bucket(), "random_same_k": empty_bucket()},
        "global": {"t2_direct": empty_bucket(), "random_same_k": empty_bucket()},
    }
    per_lottery = defaultdict(lambda: {"t2_direct": empty_bucket(), "random_same_k": empty_bucket()})

    # base frequency: how often each number appears as ANY position in featured draws
    appear_counts = defaultdict(int)
    total_number_slots = 0
    for d in draws:
        for n in d["numbers"]:
            if 1 <= int(n) <= 100:
                appear_counts[int(n)] += 1
                total_number_slots += 1

    # Official F same-day activations (multi-lottery day)
    f_stats = {
        "discovery": WindowStats(),
        "validation": WindowStats(),
        "global": WindowStats(),
    }
    # For each date with >=2 featured draws: compute F candidates; hit if any appears next calendar day any featured
    dates_sorted = sorted(by_date.keys())
    for d in dates_sorted:
        day_draws = by_date[d]
        if len(day_draws) < 2:
            continue
        obs = []
        for dr in day_draws:
            if not dr["numbers"]:
                continue
            n0 = int(dr["numbers"][0])
            if 1 <= n0 <= 100:
                obs.append(n0)
        uniq = list(dict.fromkeys(obs))
        if len(uniq) < 2:
            continue
        strengthened: set[int] = set()
        for a in uniq:
            others = set(uniq) - {a}
            for cand in comps[a]:
                if set(neigh[cand]) & others:
                    strengthened.add(cand)
        if not strengthened:
            # still count activation with miss? Only activations where F fires
            continue
        nxt = by_date.get(d + timedelta(days=1), [])
        nxt_nums = {int(x) for dr in nxt for x in dr["numbers"] if 1 <= int(x) <= 100}
        hit = bool(strengthened & nxt_nums)
        split = "discovery" if d < SPLIT else "validation"
        f_stats[split].add(hit)
        f_stats["global"].add(hit)

    # T2 direct activations: each draw's first number N
    for d in draws:
        nums = [int(x) for x in d["numbers"] if 1 <= int(x) <= 100]
        if not nums:
            continue
        n = nums[0]
        t2 = neigh[n]
        if not t2:
            continue
        split = "discovery" if d["draw_date"] < SPLIT else "validation"
        k = len(t2)
        rand_set = RNG.sample(range(1, 101), k=k)

        # window evaluators
        def hit_in(candidates: list[int], universe: set[int]) -> bool:
            return bool(set(candidates) & universe)

        same_draw_others = set(nums[1:])
        # next draw same lottery
        seq = by_lottery[d["lottery_id"]]
        i = next_idx[d["lottery_id"]][d["draw_id"]]
        next_draw_nums: set[int] = set()
        if i + 1 < len(seq):
            next_draw_nums = {int(x) for x in seq[i + 1]["numbers"] if 1 <= int(x) <= 100}
        next7: set[int] = set()
        for j in range(1, 8):
            if i + j < len(seq):
                next7 |= {int(x) for x in seq[i + j]["numbers"] if 1 <= int(x) <= 100}
        same_day_other: set[int] = set()
        for od in by_date[d["draw_date"]]:
            if od["draw_id"] == d["draw_id"]:
                continue
            same_day_other |= {int(x) for x in od["numbers"] if 1 <= int(x) <= 100}
        next_day_nums: set[int] = set()
        for od in by_date.get(d["draw_date"] + timedelta(days=1), []):
            next_day_nums |= {int(x) for x in od["numbers"] if 1 <= int(x) <= 100}

        universes = {
            "same_draw": same_draw_others,
            "next_draw_same_lottery": next_draw_nums,
            "same_day_other_lottery": same_day_other,
            "next_calendar_day": next_day_nums,
            "next_7_draws_same_lottery": next7,
        }

        for w, uni in universes.items():
            for bucket in (results[split], results["global"], per_lottery[d["lottery_name"]]):
                bucket["t2_direct"][w].add(hit_in(t2, uni))
                bucket["random_same_k"][w].add(hit_in(rand_set, uni))

    def serialize_bucket(b):
        return {strat: {w: st.as_dict() for w, st in windows_map.items()} for strat, windows_map in b.items()}

    # base rate for a single random number appearing in next_calendar_day universe size ~ avg
    # Approximate: P(specific number in a day) ≈ appearances/days — compute empirically
    days = len(by_date)
    day_presence = defaultdict(int)
    for d0, lst in by_date.items():
        present = {int(x) for dr in lst for x in dr["numbers"] if 1 <= int(x) <= 100}
        for n in present:
            day_presence[n] += 1
    avg_base_next_day = sum(day_presence.values()) / (100 * days) if days else 0

    # lift for next_calendar_day t2_direct validation
    def lift_for(split: str, window: str) -> dict:
        t2 = results[split]["t2_direct"][window]
        rnd = results[split]["random_same_k"][window]
        t2d = t2.as_dict()
        rndd = rnd.as_dict()
        base = avg_base_next_day if window == "next_calendar_day" else rndd["precision"]
        lift_vs_random = (t2d["precision"] / rndd["precision"]) if rndd["precision"] else None
        # expected if each of k neighbors hits independently at base — rough
        return {
            "t2_precision": t2d["precision"],
            "random_same_k_precision": rndd["precision"],
            "lift_vs_random_same_k": round(lift_vs_random, 4) if lift_vs_random is not None else None,
            "approx_single_number_day_base_rate": round(avg_base_next_day, 6),
            "t2_wilson": t2d["wilson_ci_95"],
            "random_wilson": rndd["wilson_ci_95"],
        }

    out = {
        "methodology_note": "DIRECT_T2_NEIGHBOR_SIGNAL backtest — not official strengthening",
        "split_date": SPLIT.isoformat(),
        "featured_draws": len(draws),
        "total_number_slots": total_number_slots,
        "windows": windows,
        "global": serialize_bucket(results["global"]),
        "discovery": serialize_bucket(results["discovery"]),
        "validation": serialize_bucket(results["validation"]),
        "per_lottery_global": {k: serialize_bucket(v) for k, v in sorted(per_lottery.items())},
        "official_f_same_day_then_next_day": {
            k: v.as_dict() for k, v in f_stats.items()
        },
        "lifts_next_calendar_day": {
            "discovery": lift_for("discovery", "next_calendar_day"),
            "validation": lift_for("validation", "next_calendar_day"),
            "global": lift_for("global", "next_calendar_day"),
        },
        "lifts_next_7_draws": {
            "discovery": lift_for("discovery", "next_7_draws_same_lottery"),
            "validation": lift_for("validation", "next_7_draws_same_lottery"),
            "global": lift_for("global", "next_7_draws_same_lottery"),
        },
    }
    return out


def verdict_from(stats: dict) -> str:
    """A/B/C/D classification for C2 pattern."""
    val = stats["lifts_next_calendar_day"]["validation"]
    t2 = val["t2_precision"]
    rnd = val["random_same_k_precision"]
    lift = val["lift_vs_random_same_k"] or 0
    ci = stats["validation"]["t2_direct"]["next_calendar_day"]["wilson_ci_95"]
    # Require validation lift clearly > 1.15 and CI lower bound > random precision
    if lift >= 1.5 and ci[0] > rnd * 1.05 and t2 >= 0.15:
        return "C_SENAL_SECUNDARIA_VALIDADA"
    if lift >= 1.15 and ci[0] >= rnd:
        return "B_SENAL_SECUNDARIA_EXPERIMENTAL"
    if lift < 1.05 or ci[1] <= rnd:
        return "A_RECHAZADO"
    return "B_SENAL_SECUNDARIA_EXPERIMENTAL"


async def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cat = build_catalog()
    conn = await asyncpg.connect(DEV_DSN)
    try:
        draws = await load_draws(conn)
    finally:
        await conn.close()
    stats = run_backtest(draws, cat)
    verdict = verdict_from(stats)
    stats["c2_pattern_verdict"] = verdict
    stats["c2_classification"] = "DIRECT_T2_NEIGHBOR_SIGNAL"
    stats["not_official_fuerte"] = True
    path = OUT / "c2_direct_t2_backtest.json"
    path.write_text(json.dumps(stats, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({
        "verdict": verdict,
        "validation_next_day": stats["lifts_next_calendar_day"]["validation"],
        "validation_next_7": stats["lifts_next_7_draws"]["validation"],
        "official_f_validation": stats["official_f_same_day_then_next_day"]["validation"],
        "draws": stats["featured_draws"],
    }, indent=2))
    print("wrote", path)
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
