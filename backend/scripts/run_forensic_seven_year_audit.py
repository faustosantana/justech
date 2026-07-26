#!/usr/bin/env python3
"""Impartial forensic audit — full FEATURED_SEVEN history, next-7-day window only."""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.lottery.numeric_relations.catalog import build_catalog  # noqa: E402
from app.lottery.numeric_relations.forensic_audit import (  # noqa: E402
    aggregate_forensic,
    analyze_fuerte,
    collect_window_appearances,
    new_audit_id,
    pick_case_studies,
    t1_companions,
)
from app.lottery.numeric_relations.historical_audit_runner import (  # noqa: E402
    DEFAULT_DEV_DSN,
    first_obs_for_date,
    load_featured_draws,
)
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION  # noqa: E402
from app.lottery.numeric_relations.historical_manual_audit import strengthen_official  # noqa: E402

DOCS = REPO / "docs/lottery/forensic_audit"
ART = REPO / "artifacts/forensic_audit"
ASSETS = DOCS / "assets"


def bar_svg(values: dict[str, float], title: str, path: Path) -> None:
    """Minimal SVG bar chart without external deps."""
    items = list(values.items())
    if not items:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
        return
    w, h, pad = 720, 280, 40
    max_v = max(values.values()) or 1
    bw = (w - 2 * pad) / max(len(items), 1)
    bars = []
    for i, (label, val) in enumerate(items):
        bh = (h - 2 * pad - 30) * (val / max_v)
        x = pad + i * bw + 8
        y = h - pad - bh
        bars.append(
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{bw-16:.1f}' height='{bh:.1f}' fill='#2563eb'/>"
            f"<text x='{x+bw/2:.1f}' y='{h-12}' text-anchor='middle' font-size='10'>{label[:12]}</text>"
            f"<text x='{x+bw/2:.1f}' y='{y-4:.1f}' text-anchor='middle' font-size='10'>{val:.1f}</text>"
        )
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}'>"
        f"<rect width='100%' height='100%' fill='#fff'/>"
        f"<text x='{pad}' y='24' font-size='14' font-family='system-ui'>{title}</text>"
        + "".join(bars)
        + "</svg>"
    )
    path.write_text(svg, encoding="utf-8")


def write_md(name: str, body: str) -> None:
    (DOCS / name).write_text(body.strip() + "\n", encoding="utf-8")


async def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    if "jaios_lottery_dev" not in DEFAULT_DEV_DSN:
        raise SystemExit("production_forbidden")

    audit_id = new_audit_id()
    cat = build_catalog()
    conn = await asyncpg.connect(DEFAULT_DEV_DSN)
    try:
        featured = await conn.fetch(
            """
            select id::text as id, name, source_id
            from lottery_lotteries where is_featured = true
            order by display_order, name
            """
        )
        featured = [dict(r) for r in featured]
        draw_count = int(await conn.fetchval("select count(*) from lottery_draws"))
        mm = await conn.fetchrow(
            """
            select min(d.draw_date) as dmin, max(d.draw_date) as dmax, count(*)::int as n
            from lottery_draws d
            join lottery_lotteries l on l.id = d.lottery_id
            where l.is_featured = true
            """
        )
        draws = await load_featured_draws(conn)
    finally:
        await conn.close()

    if len(featured) != 7:
        raise SystemExit(f"FEATURED_SEVEN broken: {len(featured)}")

    dmin, dmax = mm["dmin"], mm["dmax"]
    # Prefer last 7 years if available
    target_from = dmax - timedelta(days=365 * 7 + 2) if dmax else dmin
    date_from = max(dmin, target_from) if dmin and target_from else dmin
    date_to = dmax

    by_date: dict[date, list[dict]] = defaultdict(list)
    draws_f = []
    for dr in draws:
        dd = dr["draw_date"]
        if date_from and dd < date_from:
            continue
        if date_to and dd > date_to:
            continue
        by_date[dd].append(dr)
        draws_f.append(dr)

    # Need trailing 7 days after last analysis day → stop analysis 7 days before max
    analysis_to = date_to - timedelta(days=7) if date_to else date_to

    outcomes = []
    days_analyzed = 0
    days_with_fuerte = 0
    for d in sorted(by_date.keys()):
        if analysis_to and d > analysis_to:
            continue
        obs = first_obs_for_date(by_date[d], d)
        if len(obs) < 2:
            continue
        days_analyzed += 1
        hits = strengthen_official(obs, catalog=cat)
        if not hits:
            continue
        days_with_fuerte += 1
        apps = collect_window_appearances(case_date=d, by_date=by_date)
        for h in hits:
            outcomes.append(
                analyze_fuerte(case_date=d, hit=h, apps=apps, catalog=cat)
            )

    agg = aggregate_forensic(outcomes)
    cases = pick_case_studies(outcomes)

    # Impartial random baseline (same windows, random fuerte 1..100)
    rng = random.Random(20260726)
    rand_exact = 0
    rand_fam = 0
    window_sizes: list[int] = []
    for o in outcomes:
        apps = collect_window_appearances(case_date=o.case_date, by_date=by_date)
        window_nums = {a.number for a in apps}
        window_sizes.append(len(window_nums))
        r = rng.randint(1, 100)
        rc = t1_companions(cat, r)
        if r in window_nums:
            rand_exact += 1
        if r in window_nums or (rc & window_nums):
            rand_fam += 1
    n_act = len(outcomes) or 1
    ws_sorted = sorted(window_sizes)
    baseline_random = {
        "seed": 20260726,
        "activations": len(outcomes),
        "median_unique_numbers_in_7d_window": ws_sorted[len(ws_sorted) // 2] if ws_sorted else 0,
        "mean_unique": round(sum(window_sizes) / len(window_sizes), 1) if window_sizes else 0,
        "fuerte_exact_rate": agg["fuerte_exact_rate_pct"],
        "random_number_exact_rate": round(100.0 * rand_exact / n_act, 2),
        "lift_exact": round(agg["fuerte_exact_hits"] / rand_exact, 4) if rand_exact else None,
        "fuerte_family_rate": agg["family_exact_or_companion_pct"],
        "random_family_rate": round(100.0 * rand_fam / n_act, 2),
        "lift_family": round(
            (agg["family_exact_or_companion_pct"] / 100.0 * n_act) / rand_fam, 4
        )
        if rand_fam
        else None,
    }

    # Coverage by year
    coverage = []
    for y in range(date_from.year, date_to.year + 1):
        y0 = max(date_from, date(y, 1, 1))
        y1 = min(date_to, date(y, 12, 31))
        days = [dd for dd in by_date if y0 <= dd <= y1]
        coverage.append(
            {
                "year": y,
                "from": y0.isoformat(),
                "to": y1.isoformat(),
                "days_with_draws": len(days),
                "draws": sum(len(by_date[dd]) for dd in days),
            }
        )

    summary = {
        "audit_id": audit_id,
        "production_forbidden": True,
        "motor_modified": False,
        "tables_modified": False,
        "methodology_version": METHODOLOGY_VERSION,
        "featured_seven": featured,
        "db_draw_count": draw_count,
        "featured_draws_loaded": int(mm["n"]),
        "range": {
            "db_min": dmin.isoformat() if dmin else None,
            "db_max": dmax.isoformat() if dmax else None,
            "analysis_from": date_from.isoformat() if date_from else None,
            "analysis_to": analysis_to.isoformat() if analysis_to else None,
            "validation_window": "next_7_calendar_days_exclusive_of_case_day",
        },
        "days_analyzed_ge2_obs": days_analyzed,
        "days_with_fuerte": days_with_fuerte,
        "coverage_by_year": coverage,
        "aggregates": agg,
        "baseline_random": baseline_random,
        "case_studies": cases,
    }

    (ART / "statistics.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (DOCS / "evidence_statistics.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (ART / "cases.json").write_text(
        json.dumps(cases, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    # CSV outcomes sample (all activations would be large — write compact)
    with (ART / "outcomes_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "fuerte",
                "generator",
                "n_confirmers",
                "fuerte_hit",
                "first_day_offset",
                "outcome_bucket",
                "closest_distance",
                "closest_number",
            ],
        )
        w.writeheader()
        for o in outcomes:
            w.writerow(
                {
                    "date": o.case_date.isoformat(),
                    "fuerte": o.fuerte,
                    "generator": o.generator,
                    "n_confirmers": o.n_confirmers,
                    "fuerte_hit": o.fuerte_hit,
                    "first_day_offset": o.first_day_offset,
                    "outcome_bucket": o.outcome_bucket,
                    "closest_distance": o.closest_distance,
                    "closest_number": o.closest_number,
                }
            )

    with (ART / "by_number.csv").open("w", newline="", encoding="utf-8") as f:
        fields = list(agg["by_number_all"][0].keys()) if agg["by_number_all"] else ["number"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in agg["by_number_all"]:
            w.writerow(row)

    # Book + dashboard (rich chapters with baseline)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from write_forensic_book import main as write_book

    write_book()

    ap = agg["answers_preview"]
    print(
        json.dumps(
            {
                "audit_id": audit_id,
                "range": [str(date_from), str(analysis_to)],
                "days_analyzed": days_analyzed,
                "activations": agg["total_fuerte_activations"],
                "exact_rate_pct": agg["fuerte_exact_rate_pct"],
                "family_pct": agg["family_exact_or_companion_pct"],
                "miss_companion_pct": ap["cuando_no_sale_companero_pct_of_misses"],
                "baseline_random": baseline_random,
                "featured": len(featured),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
