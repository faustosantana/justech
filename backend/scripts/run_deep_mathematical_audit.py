#!/usr/bin/env python3
"""Run deep mathematical relations audit over 2019-07-23 → 2026-07-16."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.lottery.numeric_relations.catalog import build_catalog  # noqa: E402
from app.lottery.numeric_relations.deep_mathematical_audit import (  # noqa: E402
    PERIOD_FROM,
    PERIOD_TO,
    accumulate_first_hit_days,
    chain_hop_closures,
    classify_appearance,
    collect_future,
    consistency_level,
    enumerate_official_chains,
    matrix_with_margins,
    new_audit_id,
    pct,
    position_in_group,
    strengthen_official,
    t1_candidates_from_observed,
    t1_group_ordered,
    t1_group_ordered as _t1g,
    t2_group_ordered,
)
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION  # noqa: E402
from app.lottery.numeric_relations.historical_audit_runner import (  # noqa: E402
    DEFAULT_DEV_DSN,
    first_obs_for_date,
    load_featured_draws,
)

DOCS = REPO / "docs/lottery/deep_mathematical_audit"
ART = REPO / "artifacts/deep_mathematical_audit"
ASSETS = DOCS / "assets"


def bar_svg(values: dict[str, float], title: str, path: Path) -> None:
    items = list(values.items())
    w, h, pad = 820, 300, 48
    max_v = max(values.values()) if items else 1
    max_v = max_v or 1
    bw = (w - 2 * pad) / max(len(items), 1)
    bars = []
    for i, (label, val) in enumerate(items):
        bh = (h - 2 * pad - 36) * (val / max_v)
        x = pad + i * bw + 4
        y = h - pad - bh
        bars.append(
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{bw-8:.1f}' height='{bh:.1f}' fill='#1d4ed8'/>"
            f"<text x='{x+bw/2:.1f}' y='{h-16}' text-anchor='middle' font-size='10' "
            f"font-family='system-ui'>{label}</text>"
            f"<text x='{x+bw/2:.1f}' y='{y-4:.1f}' text-anchor='middle' font-size='10' "
            f"font-family='system-ui'>{val:g}</text>"
        )
    path.write_text(
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}'>"
        f"<rect width='100%' height='100%' fill='#fafafa'/>"
        f"<text x='{pad}' y='26' font-size='14' font-family='system-ui' font-weight='600'>{title}</text>"
        + "".join(bars)
        + "</svg>",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


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
        featured = [
            dict(r)
            for r in await conn.fetch(
                """
                select id::text as id, name, source_id, is_featured
                from lottery_lotteries where is_featured = true
                order by display_order, name
                """
            )
        ]
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

    date_from = PERIOD_FROM
    # analysis_to is period end; need draws through period_to+7 for windows
    window_end = PERIOD_TO + timedelta(days=7)
    by_date: dict[date, list[dict]] = defaultdict(list)
    for dr in draws:
        dd = dr["draw_date"]
        if dd < date_from or dd > window_end:
            continue
        by_date[dd].append(dr)

    # Coverage
    cal_days = (PERIOD_TO - PERIOD_FROM).days + 1
    days_with_data = sorted(d for d in by_date if date_from <= d <= PERIOD_TO)
    coverage = {
        "period_from": date_from.isoformat(),
        "period_to": PERIOD_TO.isoformat(),
        "calendar_days": cal_days,
        "days_with_featured_draws": len(days_with_data),
        "days_missing": cal_days - len(days_with_data),
        "featured_draws_in_period": sum(
            len(by_date[d]) for d in days_with_data
        ),
        "db_featured_min": mm["dmin"].isoformat() if mm["dmin"] else None,
        "db_featured_max": mm["dmax"].isoformat() if mm["dmax"] else None,
        "db_draw_count": draw_count,
        "featured_seven": featured,
    }

    activation_rows: list[dict] = []
    appearance_rows: list[dict] = []
    strong_exact_rows: list[dict] = []
    t1_pos_rows: list[dict] = []
    t2_pos_rows: list[dict] = []
    chain_result_counter: Counter = Counter()
    pair_stats: dict[tuple[int, int, int], dict] = {}
    first_hit_offsets: list[int | None] = []
    fuerte_activation_keys: list[tuple[date, int]] = []

    # Counters for matrices
    m_fuerte_result = Counter()
    m_fuerte_t1pos = Counter()
    m_fuerte_t2pos = Counter()
    m_origin_fuerte = Counter()
    m_conf_fuerte = Counter()
    m_oc_result_rel = Counter()
    m_lot_origin_result = Counter()
    m_pos_origin_result = Counter()
    m_day_relation = Counter()
    m_year_relation = Counter()
    m_t1_pos_fuerte_x_appeared = Counter()
    m_t1_dist = Counter()
    m_t2_dist = Counter()
    label_counter = Counter()
    day_label_any = Counter()  # (day, label) any appearance
    lottery_triple = Counter()
    conf_count_stats = defaultdict(lambda: {"activations": 0, "exact": 0, "first_days": []})
    yearly = defaultdict(lambda: defaultdict(int))
    by_fuerte_num = defaultdict(lambda: defaultdict(int))
    by_origin_num = defaultdict(lambda: defaultdict(int))
    by_conf_num = defaultdict(lambda: defaultdict(int))
    graph_edges = defaultdict(lambda: {"count": 0, "days": [], "lotteries": Counter()})

    days_ge2 = 0
    days_with_fuerte = 0
    explained_pool: list[dict] = []

    for d in sorted(days_with_data):
        if d > PERIOD_TO:
            continue
        obs = first_obs_for_date(by_date[d], d)
        if len(obs) < 2:
            continue
        days_ge2 += 1
        hits = strengthen_official(obs, catalog=cat)
        if not hits:
            continue
        days_with_fuerte += 1
        chains = enumerate_official_chains(d, obs, catalog=cat)
        future = collect_future(d, by_date)
        futuros_by_num = defaultdict(list)
        for fa in future:
            futuros_by_num[fa.number].append(fa)

        # Unique fuerte activations (one per fuerte/day)
        seen_fuerte: set[int] = set()
        for chain in chains:
            f = chain.fuerte
            act_id = f"{d.isoformat()}|{chain.origin}|{f}|{chain.confirmer}"
            fuerte_apps = futuros_by_num.get(f, [])
            first = min(fuerte_apps, key=lambda a: (a.day_offset, a.lottery_name, a.position)) if fuerte_apps else None
            if f not in seen_fuerte:
                seen_fuerte.add(f)
                fuerte_activation_keys.append((d, f))
                first_hit_offsets.append(first.day_offset if first else None)
                ck = str(chain.n_confirmers_for_fuerte if chain.n_confirmers_for_fuerte < 4 else "4+")
                conf_count_stats[ck]["activations"] += 1
                if first:
                    conf_count_stats[ck]["exact"] += 1
                    conf_count_stats[ck]["first_days"].append(first.day_offset)
                by_fuerte_num[f]["times_fuerte"] += 1
                if first:
                    by_fuerte_num[f][f"exact_D+{first.day_offset}"] += 1
                    by_fuerte_num[f]["exact_any"] += 1
                yearly[str(d.year)]["fuerte_activations"] += 1
                if first:
                    yearly[str(d.year)]["exact_hits"] += 1

            by_origin_num[chain.origin]["times_origin"] += 1
            by_conf_num[chain.confirmer]["times_confirmer"] += 1
            m_origin_fuerte[(chain.origin, f)] += 1
            m_conf_fuerte[(chain.confirmer, f)] += 1

            activation_rows.append(
                {
                    "activation_id": act_id,
                    "case_date": d.isoformat(),
                    "year": d.year,
                    "origin": chain.origin,
                    "origin_lottery": chain.origin_lottery,
                    "origin_draw_position": chain.origin_position,
                    "origin_source": chain.origin_source,
                    "fuerte": f,
                    "confirmer": chain.confirmer,
                    "confirmer_lottery": chain.confirmer_lottery,
                    "confirmer_draw_position": chain.confirmer_position,
                    "confirmer_source": chain.confirmer_source,
                    "t1_candidates": "|".join(map(str, chain.t1_candidates)),
                    "t1_group_fuerte": "|".join(map(str, chain.t1_group_of_fuerte)),
                    "t1_pos_fuerte": chain.t1_pos_fuerte,
                    "t2_group_fuerte": "|".join(map(str, chain.t2_group_of_fuerte)),
                    "t2_pos_fuerte": chain.t2_pos_fuerte,
                    "t2_pos_confirmer": chain.t2_pos_confirmer,
                    "n_confirmers": chain.n_confirmers_for_fuerte,
                    "n_fuertes_same_day": chain.n_fuertes_same_day,
                    "other_fuertes": "|".join(map(str, chain.other_fuertes_same_day)),
                    "fuerte_appeared": bool(fuerte_apps),
                    "first_day_offset": first.day_offset if first else "",
                    "first_lottery": first.lottery_name if first else "",
                    "first_draw_position": first.position if first else "",
                    "fuerte_appearance_count": len(fuerte_apps),
                    "methodology": METHODOLOGY_VERSION,
                }
            )

            if first:
                strong_exact_rows.append(
                    {
                        "case_date": d.isoformat(),
                        "fuerte": f,
                        "origin": chain.origin,
                        "confirmer": chain.confirmer,
                        "first_day_offset": first.day_offset,
                        "first_date": first.draw_date.isoformat(),
                        "first_lottery": first.lottery_name,
                        "first_draw_position": first.position,
                        "first_position_label": first.position_label,
                        "total_appearances": len(fuerte_apps),
                        "distinct_days": len({a.day_offset for a in fuerte_apps}),
                        "distinct_lotteries": len({a.lottery_name for a in fuerte_apps}),
                        "source_reference": first.source_reference,
                    }
                )

            # Classify every future appearance against this chain
            hop1, hop2 = chain_hop_closures(cat, chain)
            conf_t1 = _t1g(cat, chain.confirmer)
            conf_t2 = set(cat.get_table2_neighbors(chain.confirmer, exclude_self=True))
            related_first = None
            for fa in future:
                clf = classify_appearance(
                    cat=cat,
                    chain=chain,
                    app=fa,
                    hop1=hop1,
                    hop2=hop2,
                    conf_t1=conf_t1,
                    conf_t2=conf_t2,
                )
                labels = clf["labels"]
                for lab in labels:
                    label_counter[lab] += 1
                    day_label_any[(fa.day_offset, lab)] += 1
                    m_day_relation[(f"D+{fa.day_offset}", lab)] += 1
                    m_year_relation[(str(d.year), lab)] += 1

                primary = clf["primary_relation"]
                m_fuerte_result[(f, fa.number)] += 1
                m_oc_result_rel[(f"{chain.origin}>{f}<{chain.confirmer}", primary)] += 1
                m_lot_origin_result[(chain.origin_lottery, fa.lottery_name)] += 1
                m_pos_origin_result[(chain.origin_position, fa.position)] += 1
                lottery_triple[(chain.origin_lottery, chain.confirmer_lottery, fa.lottery_name)] += 1

                if clf["t1_pos"] is not None:
                    m_fuerte_t1pos[(f, clf["t1_pos"])] += 1
                    m_t1_pos_fuerte_x_appeared[(chain.t1_pos_fuerte, clf["t1_pos"])] += 1
                    t1_pos_rows.append(
                        {
                            "case_date": d.isoformat(),
                            "fuerte": f,
                            "result": fa.number,
                            "day_offset": fa.day_offset,
                            "t1_pos_fuerte": chain.t1_pos_fuerte,
                            "t1_pos_result": clf["t1_pos"],
                            "t1_dist": clf["t1_dist"],
                            "t1_direction": clf["t1_direction"],
                            "lottery": fa.lottery_name,
                            "draw_position": fa.position,
                            "labels": "|".join(labels),
                        }
                    )
                    if clf["t1_dist"] is not None:
                        m_t1_dist[clf["t1_dist"]] += 1

                if clf["t2_pos"] is not None:
                    m_fuerte_t2pos[(f, clf["t2_pos"])] += 1
                    t2_pos_rows.append(
                        {
                            "case_date": d.isoformat(),
                            "fuerte": f,
                            "result": fa.number,
                            "day_offset": fa.day_offset,
                            "t2_pos_fuerte": chain.t2_pos_fuerte,
                            "t2_pos_result": clf["t2_pos"],
                            "t2_dist": clf["t2_dist"],
                            "lottery": fa.lottery_name,
                            "draw_position": fa.position,
                            "labels": "|".join(labels),
                        }
                    )
                    if clf["t2_dist"] is not None:
                        m_t2_dist[clf["t2_dist"]] += 1

                key_chain = (chain.origin, f, chain.confirmer, fa.number)
                chain_result_counter[key_chain] += 1
                pk = (chain.origin, f, chain.confirmer)
                st = pair_stats.setdefault(
                    pk,
                    {
                        "count": 0,
                        "years": set(),
                        "results": Counter(),
                        "primaries": Counter(),
                        "days": Counter(),
                    },
                )
                # count activation once per chain later; results here
                st["results"][fa.number] += 1
                st["primaries"][primary] += 1
                st["days"][fa.day_offset] += 1
                st["years"].add(d.year)

                # graph edges fuerte → result (observed posterior)
                ek = ("fuerte_result", f, fa.number)
                graph_edges[ek]["count"] += 1
                graph_edges[ek]["days"].append(fa.day_offset)
                graph_edges[ek]["lotteries"][fa.lottery_name] += 1

                row = {
                    "activation_id": act_id,
                    "case_date": d.isoformat(),
                    "year": d.year,
                    "origin": chain.origin,
                    "origin_lottery": chain.origin_lottery,
                    "confirmer": chain.confirmer,
                    "confirmer_lottery": chain.confirmer_lottery,
                    "fuerte": f,
                    "result": fa.number,
                    "day_offset": fa.day_offset,
                    "result_date": fa.draw_date.isoformat(),
                    "result_lottery": fa.lottery_name,
                    "result_draw_position": fa.position,
                    "result_position_label": fa.position_label,
                    "source_reference": fa.source_reference,
                    "t1_code": clf["t1_code"],
                    "t2_code": clf["t2_code"],
                    "t1_pos_fuerte": chain.t1_pos_fuerte,
                    "t1_pos_result": clf["t1_pos"],
                    "t1_dist": clf["t1_dist"],
                    "t1_direction": clf["t1_direction"],
                    "t2_pos_fuerte": chain.t2_pos_fuerte,
                    "t2_pos_result": clf["t2_pos"],
                    "t2_dist": clf["t2_dist"],
                    "labels": "|".join(labels),
                    "primary_relation": primary,
                }
                appearance_rows.append(row)

                if related_first is None and "SIN_RELACION_DIRECTA_IDENTIFICADA" not in labels:
                    related_first = row

            # pair activation count
            pk = (chain.origin, f, chain.confirmer)
            pair_stats[pk]["count"] += 1
            pair_stats[pk]["years"].add(d.year)

            # graph structural edges
            for et, a, b in (
                ("origin_fuerte", chain.origin, f),
                ("confirmer_fuerte", chain.confirmer, f),
                ("t1_geometry", chain.origin, f),  # origin-as-code → candidate
            ):
                ek = (et, a, b)
                graph_edges[ek]["count"] += 1

            # explained pool sample
            explained_pool.append(
                {
                    "case_date": d.isoformat(),
                    "origin": chain.origin,
                    "fuerte": f,
                    "confirmer": chain.confirmer,
                    "t1_group": chain.t1_group_of_fuerte,
                    "t2_group": chain.t2_group_of_fuerte,
                    "t1_pos_fuerte": chain.t1_pos_fuerte,
                    "fuerte_appeared": bool(fuerte_apps),
                    "first_day": first.day_offset if first else None,
                    "first_lottery": first.lottery_name if first else None,
                    "n_confirmers": chain.n_confirmers_for_fuerte,
                    "n_fuertes": chain.n_fuertes_same_day,
                    "related_first": related_first,
                    "appearance_sample": [
                        r
                        for r in appearance_rows[-len(future) :]
                        if r["activation_id"] == act_id
                        and r["primary_relation"] != "SIN_RELACION_DIRECTA_IDENTIFICADA"
                    ][:12],
                }
            )

    coverage["days_ge2_observed"] = days_ge2
    coverage["days_with_fuerte"] = days_with_fuerte

    n_chain_act = len(activation_rows)
    n_fuerte_act = len(fuerte_activation_keys)
    first_stats = accumulate_first_hit_days(first_hit_offsets)

    # Top chains O→F←C→R
    top_chains = [
        {
            "origin": o,
            "fuerte": f,
            "confirmer": c,
            "result": r,
            "count": n,
            "consistency": consistency_level(n),
        }
        for (o, f, c, r), n in chain_result_counter.most_common(100)
    ]

    # Pair ranking with sample buckets
    pair_rank = []
    for (o, f, c), st in pair_stats.items():
        n = st["count"]
        top_res = st["results"].most_common(3)
        pair_rank.append(
            {
                "origin": o,
                "fuerte": f,
                "confirmer": c,
                "activations": n,
                "years": sorted(st["years"]),
                "year_span": len(st["years"]),
                "consistency": consistency_level(n),
                "sample_bucket": (
                    "1-4"
                    if n < 5
                    else "5-9"
                    if n < 10
                    else "10-24"
                    if n < 25
                    else "25-49"
                    if n < 50
                    else "50-99"
                    if n < 100
                    else "100+"
                ),
                "top_results": [{"number": a, "count": b} for a, b in top_res],
                "top_primary": st["primaries"].most_common(3),
                "top_days": st["days"].most_common(3),
            }
        )
    pair_rank.sort(key=lambda x: (-x["activations"], x["origin"], x["fuerte"], x["confirmer"]))

    # Number profiles 1..100
    number_profiles = []
    for num in range(1, 101):
        bf = by_fuerte_num[num]
        bo = by_origin_num[num]
        bc = by_conf_num[num]
        t1g = t1_group_ordered(cat, num)
        t2g = t2_group_ordered(cat, num)
        number_profiles.append(
            {
                "number": num,
                "t1_code": cat.table1_number_to_code.get(num),
                "t1_group": "|".join(map(str, t1g)),
                "t1_pos": position_in_group(t1g, num),
                "t1_group_size": len(t1g),
                "t2_code": cat.table2_number_to_code.get(num),
                "t2_group": "|".join(map(str, t2g)),
                "t2_pos": position_in_group(t2g, num),
                "t2_group_size": len(t2g),
                "times_fuerte": bf.get("times_fuerte", 0),
                "exact_any": bf.get("exact_any", 0),
                **{f"exact_D+{i}": bf.get(f"exact_D+{i}", 0) for i in range(1, 8)},
                "times_origin": bo.get("times_origin", 0),
                "times_confirmer": bc.get("times_confirmer", 0),
                "candidates_as_origin": "|".join(
                    map(str, t1_candidates_from_observed(cat, num))
                ),
            }
        )

    # Pick 50 explained cases
    explained = []
    def take(pred, n, tag):
        nonlocal explained
        for p in explained_pool:
            if len(explained) >= 50:
                return
            if any(e.get("_tag") == tag and e["case_date"] == p["case_date"] and e["fuerte"] == p["fuerte"] for e in explained):
                continue
            if pred(p):
                item = dict(p)
                item["_tag"] = tag
                explained.append(item)
                n -= 1
                if n <= 0:
                    return

    take(lambda p: p["first_day"] == 1, 6, "exact_D1")
    take(lambda p: p["first_day"] == 2, 4, "exact_D2")
    take(lambda p: p["first_day"] == 3, 4, "exact_D3")
    take(lambda p: p["first_day"] is not None and p["first_day"] >= 4, 4, "exact_D4_7")
    take(lambda p: not p["fuerte_appeared"], 6, "no_exact")
    take(lambda p: p["n_confirmers"] >= 2, 4, "multi_conf")
    take(lambda p: p["n_fuertes"] >= 2, 4, "multi_fuerte")
    take(lambda p: True, 50, "fill")

    for i, e in enumerate(explained, 1):
        e["case_id"] = f"DM-{i:03d}"
        e.pop("_tag", None)

    manual = explained[:20]

    # Matrices
    matrices = {
        "fuerte_x_result_top": [
            {"fuerte": a, "result": b, "count": n}
            for (a, b), n in m_fuerte_result.most_common(200)
        ],
        "t1_pos_fuerte_x_appeared": matrix_with_margins(m_t1_pos_fuerte_x_appeared),
        "t1_dist": dict(sorted(m_t1_dist.items())),
        "t2_dist": dict(sorted(m_t2_dist.items())),
        "origin_x_fuerte_top": [
            {"origin": a, "fuerte": b, "count": n}
            for (a, b), n in m_origin_fuerte.most_common(100)
        ],
        "confirmer_x_fuerte_top": [
            {"confirmer": a, "fuerte": b, "count": n}
            for (a, b), n in m_conf_fuerte.most_common(100)
        ],
        "day_x_relation": matrix_with_margins(m_day_relation),
        "year_x_relation": matrix_with_margins(m_year_relation),
        "origin_pos_x_result_pos": matrix_with_margins(m_pos_origin_result),
        "lottery_origin_x_result": [
            {"origin_lottery": a, "result_lottery": b, "count": n}
            for (a, b), n in m_lot_origin_result.most_common(50)
        ],
        "lottery_triples_top": [
            {
                "origin_lottery": a,
                "confirmer_lottery": b,
                "result_lottery": c,
                "count": n,
            }
            for (a, b, c), n in lottery_triple.most_common(40)
        ],
    }

    # Confirmation count summary
    conf_summary = {}
    for k, st in conf_count_stats.items():
        days = st["first_days"]
        conf_summary[k] = {
            "activations": st["activations"],
            "exact": st["exact"],
            "exact_pct": pct(st["exact"], st["activations"]),
            "median_first_day": sorted(days)[len(days) // 2] if days else None,
            "mean_first_day": round(sum(days) / len(days), 2) if days else None,
        }

    # Graph JSON (top edges)
    graph = {
        "nodes": [{"id": n, **{k: number_profiles[n - 1][k] for k in ("t1_code", "t2_code", "times_fuerte")}} for n in range(1, 101)],
        "edges": [],
    }
    for (et, a, b), st in sorted(graph_edges.items(), key=lambda kv: -kv[1]["count"])[:500]:
        days = st["days"]
        graph["edges"].append(
            {
                "type": et,
                "from": a,
                "to": b,
                "count": st["count"],
                "mean_day": round(sum(days) / len(days), 2) if days else None,
                "top_lottery": st["lotteries"].most_common(1)[0][0] if st["lotteries"] else None,
            }
        )

    # Label summary (appearance-level)
    label_summary = [
        {"label": lab, "count": label_counter[lab], "pct_of_label_hits": pct(label_counter[lab], sum(label_counter.values()))}
        for lab in sorted(label_counter, key=lambda x: -label_counter[x])
    ]

    # T1 distance ranking (among related T1 appearances)
    t1_dist_rank = [
        {"distance": k, "count": v, "pct": pct(v, sum(m_t1_dist.values()))}
        for k, v in sorted(m_t1_dist.items(), key=lambda kv: -kv[1])
    ]
    t2_dist_rank = [
        {"distance": k, "count": v, "pct": pct(v, sum(m_t2_dist.values()))}
        for k, v in sorted(m_t2_dist.items(), key=lambda kv: -kv[1])
    ]

    yearly_rows = []
    for y in sorted(yearly):
        ya = yearly[y]
        yearly_rows.append(
            {
                "year": y,
                "fuerte_activations": ya.get("fuerte_activations", 0),
                "exact_hits": ya.get("exact_hits", 0),
                "exact_pct": pct(ya.get("exact_hits", 0), ya.get("fuerte_activations", 0)),
            }
        )

    summary = {
        "audit_id": audit_id,
        "branch": "feature/nr-deep-mathematical-relations-audit",
        "phase_commit": "2a19579",
        "worktree": str(REPO),
        "methodology_version": METHODOLOGY_VERSION,
        "production_forbidden": True,
        "motor_modified": False,
        "tables_modified": False,
        "j11a_started": False,
        "random_baseline_used": False,
        "coverage": coverage,
        "totals": {
            "chain_activations": n_chain_act,
            "fuerte_activations_unique_per_day": n_fuerte_act,
            "distinct_fuertes": len({f for _, f in fuerte_activation_keys}),
            "future_appearance_rows": len(appearance_rows),
            "days_ge2": days_ge2,
            "days_with_fuerte": days_with_fuerte,
        },
        "first_hit_stats": first_stats,
        "label_summary": label_summary,
        "t1_distance_rank": t1_dist_rank,
        "t2_distance_rank": t2_dist_rank,
        "confirmation_count": conf_summary,
        "yearly": yearly_rows,
        "top_chains": top_chains[:40],
        "top_pairs": pair_rank[:40],
        "matrices": matrices,
        "answers_preview": {
            "chain_activations": n_chain_act,
            "fuerte_activations": n_fuerte_act,
            "distinct_fuertes": len({f for _, f in fuerte_activation_keys}),
            "exact_by_day": first_stats["by_day"],
            "cumulative": first_stats["cumulative"],
            "top_t1_dist": t1_dist_rank[:8],
            "top_t2_dist": t2_dist_rank[:8],
            "top_label": label_summary[:10],
            "top_lottery_triple": matrices["lottery_triples_top"][:10],
            "top_pair": pair_rank[:10],
        },
    }

    # Exports
    (ART / "full_statistics.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (ART / "relationship_graph.json").write_text(
        json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (ART / "explained_cases.json").write_text(
        json.dumps(explained, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (DOCS / "evidence_full_statistics.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    write_csv(ART / "all_activations.csv", activation_rows)
    write_csv(ART / "all_future_appearances.csv", appearance_rows)
    write_csv(ART / "strong_exact_results.csv", strong_exact_rows)
    write_csv(ART / "table1_position_results.csv", t1_pos_rows)
    write_csv(ART / "table2_position_results.csv", t2_pos_rows)
    write_csv(
        ART / "origin_confirmator_chains.csv",
        [
            {
                "origin": o,
                "fuerte": f,
                "confirmer": c,
                "result": r,
                "count": n,
                "consistency": consistency_level(n),
            }
            for (o, f, c, r), n in chain_result_counter.most_common()
        ],
    )
    write_csv(ART / "number_profiles.csv", number_profiles)
    write_csv(ART / "lottery_transitions.csv", matrices["lottery_triples_top"])
    write_csv(ART / "yearly_results.csv", yearly_rows)
    # Flatten a compact relationship matrix day x primary-ish labels
    rel_mat_rows = []
    day_rel = matrices["day_x_relation"]
    for r in day_rel["rows"]:
        for c in day_rel["cols"]:
            rel_mat_rows.append(
                {
                    "day": r,
                    "relation": c,
                    "count": day_rel["counts"][r][c],
                    "row_pct": day_rel["row_pct"][r][c],
                    "col_pct": day_rel["col_pct"][r][c],
                }
            )
    write_csv(ART / "relationship_matrix.csv", rel_mat_rows)
    write_csv(
        ART / "repeated_sequences.csv",
        [
            {
                "origin": x["origin"],
                "fuerte": x["fuerte"],
                "confirmer": x["confirmer"],
                "result": x["result"],
                "count": x["count"],
                "consistency": x["consistency"],
            }
            for x in top_chains
        ],
    )

    # Charts
    bar_svg(
        {y["year"]: float(y["fuerte_activations"]) for y in yearly_rows},
        "Activaciones de fuerte (únicas/día) por año",
        ASSETS / "activations_by_year.svg",
    )
    bar_svg(
        {k: float(v) for k, v in first_stats["by_day"].items()},
        "Primera aparición del fuerte exacto por D+n",
        ASSETS / "exact_by_day.svg",
    )
    bar_svg(
        {str(x["distance"]): float(x["count"]) for x in t1_dist_rank[:15]},
        "Distancias posicionales T1 (result−fuerte)",
        ASSETS / "t1_distances.svg",
    )
    bar_svg(
        {str(x["distance"]): float(x["count"]) for x in t2_dist_rank[:15]},
        "Distancias posicionales T2 (result−fuerte)",
        ASSETS / "t2_distances.svg",
    )
    bar_svg(
        {f"{a}->{b}": float(n) for (a, b), n in list(m_origin_fuerte.most_common(12))},
        "Top origen → fuerte",
        ASSETS / "origin_to_fuerte.svg",
    )
    bar_svg(
        {f"{a}->{b}": float(n) for (a, b), n in list(m_conf_fuerte.most_common(12))},
        "Top confirmador → fuerte",
        ASSETS / "confirmer_to_fuerte.svg",
    )
    bar_svg(
        {
            f"{x['origin']}>{x['fuerte']}<{x['confirmer']}→{x['result']}": float(x["count"])
            for x in top_chains[:10]
        },
        "Top cadenas O→F←C→R",
        ASSETS / "top_chains.svg",
    )
    bar_svg(
        {f"{a[:8]}→{b[:8]}": float(n) for (a, b), n in list(m_lot_origin_result.most_common(10))},
        "Transiciones lotería origen → resultado",
        ASSETS / "lottery_transitions.svg",
    )
    bar_svg(
        {k: float(v["activations"]) for k, v in sorted(conf_summary.items())},
        "Activaciones por cantidad de confirmadores",
        ASSETS / "confirmation_counts.svg",
    )
    bar_svg(
        {
            str(p["number"]): float(p["times_fuerte"])
            for p in sorted(number_profiles, key=lambda x: -x["times_fuerte"])[:15]
        },
        "Números más frecuentes como fuerte",
        ASSETS / "fuerte_repetition.svg",
    )
    # Placeholder aliases requested
    for name in (
        "t1_positions.svg",
        "t2_positions.svg",
        "fuerte_to_result.svg",
        "draw_positions.svg",
        "relations_by_year.svg",
    ):
        if name == "t1_positions.svg":
            # position of appeared within T1 among MISMO_GRUPO rows
            pos_c = Counter(r["t1_pos_result"] for r in t1_pos_rows if r.get("t1_pos_result"))
            bar_svg({str(k): float(v) for k, v in sorted(pos_c.items())[:12]}, "Posiciones T1 del resultado", ASSETS / name)
        elif name == "t2_positions.svg":
            pos_c = Counter(r["t2_pos_result"] for r in t2_pos_rows if r.get("t2_pos_result"))
            bar_svg({str(k): float(v) for k, v in sorted(pos_c.items())[:12]}, "Posiciones T2 del resultado", ASSETS / name)
        elif name == "fuerte_to_result.svg":
            bar_svg(
                {f"{a}→{b}": float(n) for (a, b), n in m_fuerte_result.most_common(12)},
                "Top fuerte → resultado",
                ASSETS / name,
            )
        elif name == "draw_positions.svg":
            pos_c = Counter(r["result_draw_position"] for r in appearance_rows)
            bar_svg({str(k): float(v) for k, v in sorted(pos_c.items())}, "Posición del sorteo (resultados)", ASSETS / name)
        else:
            bar_svg(
                {y["year"]: float(y["exact_pct"]) for y in yearly_rows},
                "Exacto % por año (activaciones fuerte)",
                ASSETS / name,
            )

    # Book
    from write_deep_mathematical_book import write_book

    write_book(summary, explained, manual, number_profiles, pair_rank)

    print(
        json.dumps(
            {
                "audit_id": audit_id,
                "coverage": coverage,
                "chain_activations": n_chain_act,
                "fuerte_activations": n_fuerte_act,
                "appearance_rows": len(appearance_rows),
                "first_hit_by_day": first_stats["by_day"],
                "top_t1_dist": t1_dist_rank[:5],
                "top_chain": top_chains[:3],
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
