#!/usr/bin/env python3
"""Follow-up Q1–Q10 on deep mathematical audit artifacts (read-only)."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.lottery.numeric_relations.catalog import build_catalog  # noqa: E402
from app.lottery.numeric_relations.deep_mathematical_audit import (  # noqa: E402
    position_in_group,
    t1_group_ordered,
)

ART = REPO / "artifacts/deep_mathematical_audit"
DOCS = REPO / "docs/lottery/deep_mathematical_audit"
OUT = ART / "followup_q1_q10"


def pct(a: int, b: int) -> float:
    return round(100.0 * a / b, 2) if b else 0.0


def load_activations():
    rows = []
    with (ART / "all_activations.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def load_appearances_for_keys(keys: set[tuple[str, str]]):
    """Load future appearances only for (case_date, fuerte) keys needed."""
    by = defaultdict(list)
    with (ART / "all_future_appearances.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["case_date"], r["fuerte"])
            if key in keys:
                by[key].append(r)
    return by


def unique_fuerte_activations(acts: list[dict]) -> list[dict]:
    """One row per (case_date, fuerte) — first chain row."""
    seen = set()
    out = []
    for r in acts:
        k = (r["case_date"], r["fuerte"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cat = build_catalog()
    acts_all = load_activations()
    acts = unique_fuerte_activations(acts_all)
    keys = {(r["case_date"], r["fuerte"]) for r in acts}
    apps_by = load_appearances_for_keys(keys)

    # Deduplicate appearances per (case_date,fuerte,result,day,lottery,draw_pos)
    def apps_unique(case_date: str, fuerte: str) -> list[dict]:
        rows = apps_by.get((case_date, fuerte), [])
        # Multiple chains share same fuerte/day — appearances duplicated in CSV.
        # Deduplicate physical appearances.
        seen = set()
        out = []
        for r in rows:
            sig = (
                r["result"],
                r["day_offset"],
                r["result_date"],
                r["result_lottery"],
                r["result_draw_position"],
                r.get("source_reference") or "",
            )
            if sig in seen:
                continue
            seen.add(sig)
            out.append(r)
        out.sort(key=lambda x: (int(x["day_offset"]), x["result_lottery"], int(x["result_draw_position"])))
        return out

    # ------------------------------------------------------------------
    # Q1: opportunities and rates per T1 distance
    # ------------------------------------------------------------------
    opp = Counter()  # distance -> opportunities
    hit = Counter()  # distance -> activations where that relative number appeared in window
    hit_by_day = defaultdict(Counter)  # dist -> day -> hits (first appearance day of that number)
    number_at_dist = defaultdict(Counter)  # dist -> number -> count of opportunities
    hit_number_at_dist = defaultdict(Counter)

    for r in acts:
        f = int(r["fuerte"])
        group = t1_group_ordered(cat, f)
        pf = position_in_group(group, f)
        if pf is None:
            continue
        # map distance -> number
        dist_num = {}
        for n in group:
            pos = position_in_group(group, n)
            if pos is None:
                continue
            d = pos - pf
            dist_num[d] = n
            opp[d] += 1
            number_at_dist[d][n] += 1

        appeared_nums = {int(a["result"]) for a in apps_unique(r["case_date"], r["fuerte"])}
        # first day per number
        first_day = {}
        for a in apps_unique(r["case_date"], r["fuerte"]):
            n = int(a["result"])
            day = int(a["day_offset"])
            if n not in first_day or day < first_day[n]:
                first_day[n] = day

        for d, n in dist_num.items():
            if n in appeared_nums:
                hit[d] += 1
                hit_number_at_dist[d][n] += 1
                hit_by_day[d][first_day[n]] += 1

    q1_rows = []
    for d in sorted(opp.keys()):
        q1_rows.append(
            {
                "t1_distance": d,
                "opportunities": opp[d],
                "appearances_in_window": hit[d],
                "rate_pct": pct(hit[d], opp[d]),
                "top_numbers_at_position": ", ".join(
                    f"{n}:{c}" for n, c in number_at_dist[d].most_common(8)
                ),
            }
        )
    with (OUT / "q1_t1_distance_rates.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(q1_rows[0].keys()))
        w.writeheader()
        w.writerows(q1_rows)

    # ------------------------------------------------------------------
    # Q2: -1,+1,-2,+2 by D+1,D+2,D+3 (first appearance of that relative number)
    # ------------------------------------------------------------------
    focus = (-1, 1, -2, 2)
    q2 = []
    for d in focus:
        row = {"t1_distance": d, "opportunities": opp[d], "hits_any_D1_7": hit[d], "rate_pct": pct(hit[d], opp[d])}
        for day in (1, 2, 3):
            row[f"first_at_D+{day}"] = hit_by_day[d][day]
            row[f"first_at_D+{day}_pct_of_opp"] = pct(hit_by_day[d][day], opp[d])
            row[f"first_at_D+{day}_pct_of_hits"] = pct(hit_by_day[d][day], hit[d])
        # cumulative D1-D3
        cum = sum(hit_by_day[d][x] for x in (1, 2, 3))
        row["first_within_D1_D3"] = cum
        row["first_within_D1_D3_pct_of_opp"] = pct(cum, opp[d])
        q2.append(row)
    with (OUT / "q2_adjacent_by_day.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(q2[0].keys()))
        w.writeheader()
        w.writerows(q2)

    # ------------------------------------------------------------------
    # Q3: exact number at each relative position (global catalog view + per fuerte)
    # ------------------------------------------------------------------
    q3_catalog = []
    for f in range(1, 101):
        group = t1_group_ordered(cat, f)
        pf = position_in_group(group, f)
        if pf is None:
            continue
        entry = {"fuerte": f, "t1_code": cat.table1_number_to_code[f], "t1_group": "|".join(map(str, group)), "t1_pos_fuerte": pf}
        for d in range(-7, 8):
            n = None
            for x in group:
                if position_in_group(group, x) - pf == d:
                    n = x
                    break
            entry[f"dist_{d:+d}".replace("+", "p").replace("-", "m")] = n if n is not None else ""
        q3_catalog.append(entry)
    # simpler explicit columns for focus distances
    q3_focus = []
    for f in range(1, 101):
        group = t1_group_ordered(cat, f)
        pf = position_in_group(group, f)
        if pf is None:
            continue
        def num_at(d):
            for x in group:
                if position_in_group(group, x) - pf == d:
                    return x
            return None
        q3_focus.append(
            {
                "fuerte": f,
                "t1_group": " ".join(map(str, group)),
                "pos_fuerte": pf,
                "number_at_-2": num_at(-2) or "",
                "number_at_-1": num_at(-1) or "",
                "number_at_0": f,
                "number_at_+1": num_at(1) or "",
                "number_at_+2": num_at(2) or "",
            }
        )
    with (OUT / "q3_numbers_at_t1_positions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(q3_focus[0].keys()))
        w.writeheader()
        w.writerows(q3_focus)

    # ------------------------------------------------------------------
    # Q4: 552 misses — first related
    # ------------------------------------------------------------------
    misses = [r for r in acts if r["fuerte_appeared"] in ("False", "false", "")]
    # also check bool-ish
    misses = [r for r in acts if str(r["fuerte_appeared"]).lower() != "true"]
    related_labels = {
        "FUERTE_EXACTO",  # shouldn't appear in misses
        "MISMO_GRUPO_T1",
        "MISMO_CODIGO_T1",
        "POSICION_T1_ADYACENTE",
        "POSICION_T1_CERCANA",
        "POSICION_T1_LEJANA",
        "MISMO_GRUPO_T2",
        "MISMO_CODIGO_T2",
        "POSICION_T2_ADYACENTE",
        "CONFIRMADOR_ORIGINAL",
        "COMPANERO_DEL_CONFIRMADOR",
        "VECINO_DEL_CONFIRMADOR",
        "CANDIDATO_ORIGINAL_ALTERNATIVO",
        "FUERTE_ALTERNATIVO",
        "RELACION_DE_SEGUNDO_NIVEL",
        "RELACION_DE_TERCER_NIVEL",
    }
    q4 = []
    for r in misses:
        apps = apps_unique(r["case_date"], r["fuerte"])
        first_rel = None
        for a in apps:
            labs = set((a.get("labels") or "").split("|"))
            # prefer T1 family, else any non-SIN
            if "SIN_RELACION_DIRECTA_IDENTIFICADA" in labs and len(labs) == 1:
                continue
            if labs & (related_labels - {"FUERTE_EXACTO"}):
                first_rel = a
                break
        if first_rel is None and apps:
            # fallback: first non-SIN or first app
            for a in apps:
                if a.get("primary_relation") != "SIN_RELACION_DIRECTA_IDENTIFICADA":
                    first_rel = a
                    break
            if first_rel is None:
                first_rel = apps[0]
        q4.append(
            {
                "case_date": r["case_date"],
                "fuerte": r["fuerte"],
                "origin": r["origin"],
                "confirmer": r["confirmer"],
                "t1_group": r["t1_group_fuerte"],
                "t1_pos_fuerte": r["t1_pos_fuerte"],
                "first_related": first_rel["result"] if first_rel else "",
                "first_related_primary": first_rel["primary_relation"] if first_rel else "",
                "first_related_labels": first_rel["labels"] if first_rel else "",
                "t1_pos_related": first_rel.get("t1_pos_result") if first_rel else "",
                "t1_dist": first_rel.get("t1_dist") if first_rel else "",
                "day_offset": first_rel["day_offset"] if first_rel else "",
                "lottery": first_rel["result_lottery"] if first_rel else "",
                "draw_position": first_rel["result_draw_position"] if first_rel else "",
                "source_reference": first_rel.get("source_reference") if first_rel else "",
            }
        )
    with (OUT / "q4_misses_first_related.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(q4[0].keys()) if q4 else ["case_date"])
        w.writeheader()
        w.writerows(q4)

    q4_summary = {
        "miss_activations": len(misses),
        "with_first_related": sum(1 for x in q4 if x["first_related"] != ""),
        "by_primary": dict(Counter(x["first_related_primary"] for x in q4)),
        "by_t1_dist": dict(Counter(x["t1_dist"] for x in q4 if x["t1_dist"] != "")),
        "by_day": dict(Counter(x["day_offset"] for x in q4 if x["day_offset"] != "")),
        "by_lottery": dict(Counter(x["lottery"] for x in q4 if x["lottery"]).most_common(15)),
    }

    # ------------------------------------------------------------------
    # Q5: top 20 repeated chains O→F←C→R
    # ------------------------------------------------------------------
    # Count from appearances CSV for chain keys — use activations file + appearances
    chain_app = Counter()
    chain_days = defaultdict(Counter)
    chain_years = defaultdict(set)
    chain_t1dist = defaultdict(Counter)
    chain_acts = Counter()
    # activations per O,F,C
    for r in acts_all:
        chain_acts[(int(r["origin"]), int(r["fuerte"]), int(r["confirmer"]))] += 1

    # For top results need chain→result counts from appearances (dedupe carefully by activation_id)
    with (ART / "origin_confirmator_chains.csv").open(encoding="utf-8") as f:
        chain_rank = list(csv.DictReader(f))
    top20 = chain_rank[:20]

    q5 = []
    for row in top20:
        o, f, c, res = int(row["origin"]), int(row["fuerte"]), int(row["confirmer"]), int(row["result"])
        # gather activation dates for this O,F,C
        act_rows = [
            r
            for r in acts_all
            if int(r["origin"]) == o and int(r["fuerte"]) == f and int(r["confirmer"]) == c
        ]
        years = sorted({int(r["year"]) for r in act_rows})
        # appearances of this exact R after those activations
        app_count = 0
        days = Counter()
        t1ds = Counter()
        draw_pos = Counter()
        lotteries = Counter()
        exceptions = []  # activations where R never appeared
        for ar in act_rows:
            apps = [
                a
                for a in apps_by.get((ar["case_date"], ar["fuerte"]), [])
                if a["activation_id"] == ar["activation_id"] and int(a["result"]) == res
            ]
            # dedupe
            seen = set()
            uniq = []
            for a in apps:
                sig = (a["day_offset"], a["result_lottery"], a["result_draw_position"], a["result_date"])
                if sig in seen:
                    continue
                seen.add(sig)
                uniq.append(a)
            if not uniq:
                exceptions.append(ar["case_date"])
            else:
                app_count += len(uniq)
                for a in uniq:
                    days[int(a["day_offset"])] += 1
                    if a.get("t1_dist") not in ("", None):
                        t1ds[a["t1_dist"]] += 1
                    draw_pos[a["result_draw_position"]] += 1
                    lotteries[a["result_lottery"]] += 1
        q5.append(
            {
                "chain": f"{o}→{f}←{c}→{res}",
                "origin": o,
                "fuerte": f,
                "confirmer": c,
                "result": res,
                "activations": len(act_rows),
                "appearance_rows": app_count,
                "years": years,
                "year_span": len(years),
                "days": dict(days),
                "t1_dist_of_result": dict(t1ds),
                "draw_positions": dict(draw_pos),
                "lotteries": dict(lotteries.most_common(5)),
                "exception_dates_no_result": exceptions[:20],
                "exception_count": len(exceptions),
                "consistency_csv": row.get("consistency"),
            }
        )
    (OUT / "q5_top20_chains.json").write_text(json.dumps(q5, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # Q6: full profile of 42
    # ------------------------------------------------------------------
    f42 = 42
    group42 = t1_group_ordered(cat, f42)
    pf42 = position_in_group(group42, f42)
    acts42 = [r for r in acts if int(r["fuerte"]) == f42]
    origins42 = Counter(int(r["origin"]) for r in acts_all if int(r["fuerte"]) == f42)
    confs42 = Counter(int(r["confirmer"]) for r in acts_all if int(r["fuerte"]) == f42)
    as_origin = [r for r in acts_all if int(r["origin"]) == f42]
    as_conf = [r for r in acts_all if int(r["confirmer"]) == f42]

    # posterior relatives when 42 is fuerte
    rel_counts = Counter()
    rel_dist = Counter()
    first_days_exact = Counter()
    for r in acts42:
        apps = apps_unique(r["case_date"], r["fuerte"])
        exact = [a for a in apps if int(a["result"]) == f42]
        if exact:
            first_days_exact[int(exact[0]["day_offset"])] += 1
        for a in apps:
            if a.get("t1_dist") not in ("", None):
                rel_dist[a["t1_dist"]] += 1
            if "MISMO_GRUPO_T1" in (a.get("labels") or ""):
                rel_counts[int(a["result"])] += 1

    profile42 = {
        "number": 42,
        "t1_code": cat.table1_number_to_code[42],
        "t1_group_ordered": group42,
        "t1_pos": pf42,
        "numbers_by_distance": {
            str(position_in_group(group42, n) - pf42): n for n in group42
        },
        "t2_code": cat.table2_number_to_code[42],
        "t2_group": list(cat.table2_code_to_numbers[cat.table2_number_to_code[42]]),
        "times_fuerte_unique_day": len(acts42),
        "exact_hits": sum(1 for r in acts42 if str(r["fuerte_appeared"]).lower() == "true"),
        "exact_first_day": dict(first_days_exact),
        "top_origins": origins42.most_common(15),
        "top_confirmers": confs42.most_common(15),
        "times_as_origin_chains": len(as_origin),
        "times_as_confirmer_chains": len(as_conf),
        "t1_family_appearance_counts_when_fuerte": rel_counts.most_common(),
        "t1_dist_counts_when_fuerte_all_apps": dict(rel_dist),
        "years_as_fuerte": sorted({int(r["year"]) for r in acts42}),
    }
    (OUT / "q6_profile_42.json").write_text(json.dumps(profile42, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # Q7: profile 39 → 94 ← 84
    # ------------------------------------------------------------------
    o, f, c = 39, 94, 84
    pair_acts = [
        r
        for r in acts_all
        if int(r["origin"]) == o and int(r["fuerte"]) == f and int(r["confirmer"]) == c
    ]
    results = Counter()
    days = Counter()
    years = Counter()
    t1dist_res = Counter()
    lot_res = Counter()
    for ar in pair_acts:
        years[int(ar["year"])] += 1
        apps = [a for a in apps_by.get((ar["case_date"], ar["fuerte"]), []) if a["activation_id"] == ar["activation_id"]]
        seen = set()
        for a in apps:
            sig = (a["result"], a["day_offset"], a["result_lottery"], a["result_draw_position"], a["result_date"])
            if sig in seen:
                continue
            seen.add(sig)
            results[int(a["result"])] += 1
            days[int(a["day_offset"])] += 1
            lot_res[a["result_lottery"]] += 1
            if a.get("t1_dist") not in ("", None):
                t1dist_res[a["t1_dist"]] += 1

    g94 = t1_group_ordered(cat, 94)
    p94 = position_in_group(g94, 94)
    profile_pair = {
        "chain": "39→94←84",
        "activations": len(pair_acts),
        "years": dict(years),
        "year_list": sorted(years),
        "fuerte_t1_group": g94,
        "fuerte_t1_pos": p94,
        "numbers_by_distance": {str(position_in_group(g94, n) - p94): n for n in g94},
        "origin_lottery_top": Counter(r["origin_lottery"] for r in pair_acts).most_common(),
        "confirmer_lottery_top": Counter(r["confirmer_lottery"] for r in pair_acts).most_common(),
        "top_results": results.most_common(20),
        "result_days": dict(days),
        "result_lotteries": lot_res.most_common(10),
        "t1_dist_of_results": dict(t1dist_res),
        "exact_fuerte_rate": pct(
            sum(1 for r in pair_acts if str(r["fuerte_appeared"]).lower() == "true"),
            len(pair_acts),
        ),
        "activation_dates": [r["case_date"] for r in pair_acts],
    }
    (OUT / "q7_profile_39_94_84.json").write_text(
        json.dumps(profile_pair, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ------------------------------------------------------------------
    # Q8: Gana Más → Nacional → Real
    # ------------------------------------------------------------------
    lo, lc, lr = "Gana Mas", "Loteria Nacional", "Quiniela Real"
    # count from appearances where origin_lottery, confirmer_lottery, result_lottery match
    # Need to scan appearances CSV (large) — stream
    n_triple = 0
    by_year = Counter()
    by_day = Counter()
    by_primary = Counter()
    by_fuerte = Counter()
    by_result = Counter()
    exact = 0
    t1_family = 0
    with (ART / "all_future_appearances.csv").open(encoding="utf-8") as f:
        for a in csv.DictReader(f):
            if (
                a["origin_lottery"] == lo
                and a["confirmer_lottery"] == lc
                and a["result_lottery"] == lr
            ):
                n_triple += 1
                by_year[a["year"]] += 1
                by_day[a["day_offset"]] += 1
                by_primary[a["primary_relation"]] += 1
                by_fuerte[a["fuerte"]] += 1
                by_result[a["result"]] += 1
                if "FUERTE_EXACTO" in (a.get("labels") or ""):
                    exact += 1
                if "MISMO_GRUPO_T1" in (a.get("labels") or ""):
                    t1_family += 1

    # activation count for this lottery pair (origin/confirmer)
    act_pair = [
        r
        for r in acts_all
        if r["origin_lottery"] == lo and r["confirmer_lottery"] == lc
    ]
    q8 = {
        "transition": f"{lo} → {lc} → {lr}",
        "appearance_rows": n_triple,
        "activations_origin_confirmer_pair": len(act_pair),
        "unique_days_activations": len({r["case_date"] for r in act_pair}),
        "by_year": dict(by_year),
        "by_day": dict(by_day),
        "by_primary_top": by_primary.most_common(12),
        "top_fuertes": by_fuerte.most_common(10),
        "top_results": by_result.most_common(10),
        "exact_label_rows": exact,
        "mismo_grupo_t1_rows": t1_family,
        "note": (
            "Cuenta filas de aparición (cadena×resultado). "
            "La transición mide lotería del origen, del confirmador y del resultado posterior."
        ),
    }
    (OUT / "q8_lottery_transition.json").write_text(json.dumps(q8, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # Q9: negative T1 direction scope
    # ------------------------------------------------------------------
    # Among opportunities for -1, which years/groups/fuertes hit?
    neg_opp_year = Counter()
    neg_hit_year = Counter()
    neg_opp_fuerte = Counter()
    neg_hit_fuerte = Counter()
    neg_opp_code = Counter()
    neg_hit_code = Counter()
    for r in acts:
        f = int(r["fuerte"])
        y = int(r["year"])
        group = t1_group_ordered(cat, f)
        pf = position_in_group(group, f)
        code = cat.table1_number_to_code[f]
        # number at -1
        n_m1 = None
        for x in group:
            if position_in_group(group, x) - pf == -1:
                n_m1 = x
                break
        if n_m1 is None:
            continue
        neg_opp_year[y] += 1
        neg_opp_fuerte[f] += 1
        neg_opp_code[code] += 1
        appeared = {int(a["result"]) for a in apps_unique(r["case_date"], r["fuerte"])}
        if n_m1 in appeared:
            neg_hit_year[y] += 1
            neg_hit_fuerte[f] += 1
            neg_hit_code[code] += 1

    years_all = sorted(neg_opp_year)
    years_with_hit = sorted(y for y in years_all if neg_hit_year[y] > 0)
    fuertes_with_opp = sorted(neg_opp_fuerte)
    fuertes_with_hit = sorted(f for f in fuertes_with_opp if neg_hit_fuerte[f] > 0)
    codes_with_opp = sorted(neg_opp_code)
    codes_with_hit = sorted(c for c in codes_with_opp if neg_hit_code[c] > 0)

    # rates by fuerte for -1
    rate_by_fuerte = []
    for f in fuertes_with_opp:
        rate_by_fuerte.append(
            {
                "fuerte": f,
                "opportunities": neg_opp_fuerte[f],
                "hits": neg_hit_fuerte[f],
                "rate_pct": pct(neg_hit_fuerte[f], neg_opp_fuerte[f]),
            }
        )
    rate_by_fuerte.sort(key=lambda x: (-x["hits"], -x["rate_pct"]))

    q9 = {
        "distance": -1,
        "total_opportunities": sum(neg_opp_year.values()),
        "total_hits": sum(neg_hit_year.values()),
        "overall_rate_pct": pct(sum(neg_hit_year.values()), sum(neg_opp_year.values())),
        "years_with_opportunity": years_all,
        "years_with_at_least_one_hit": years_with_hit,
        "hits_all_years": years_with_hit == years_all,
        "by_year": {
            str(y): {
                "opp": neg_opp_year[y],
                "hits": neg_hit_year[y],
                "rate_pct": pct(neg_hit_year[y], neg_opp_year[y]),
            }
            for y in years_all
        },
        "t1_codes_with_opportunity": len(codes_with_opp),
        "t1_codes_with_hit": len(codes_with_hit),
        "hits_all_codes_with_opp": codes_with_hit == codes_with_opp,
        "fuertes_with_opportunity": len(fuertes_with_opp),
        "fuertes_with_hit": len(fuertes_with_hit),
        "hits_all_fuertes_with_opp": len(fuertes_with_hit) == len(fuertes_with_opp),
        "fuertes_with_opp_but_zero_hits": [f for f in fuertes_with_opp if neg_hit_fuerte[f] == 0],
        "top_fuertes_by_hits": rate_by_fuerte[:20],
        "bottom_fuertes_with_opp": sorted(rate_by_fuerte, key=lambda x: (x["rate_pct"], x["hits"]))[:15],
    }
    (OUT / "q9_negative_direction_scope.json").write_text(
        json.dumps(q9, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ------------------------------------------------------------------
    # Q10: sequence fuerte → pos -1 → pos -2 (temporal order in window)
    # ------------------------------------------------------------------
    seq_full = 0  # exact then -1 then -2 in that chronological order (not necessarily consecutive days)
    seq_family_rot = 0  # -1 appears before -2 (with or without exact)
    seq_exact_then_m1 = 0
    seq_m1_then_m2 = 0
    examples = []
    for r in acts:
        f = int(r["fuerte"])
        group = t1_group_ordered(cat, f)
        pf = position_in_group(group, f)
        n_m1 = n_m2 = None
        for x in group:
            d = position_in_group(group, x) - pf
            if d == -1:
                n_m1 = x
            elif d == -2:
                n_m2 = x
        if n_m1 is None or n_m2 is None:
            continue
        apps = apps_unique(r["case_date"], r["fuerte"])
        # first time each appears
        first = {}
        for a in apps:
            n = int(a["result"])
            day = int(a["day_offset"])
            if n not in first or day < first[n][0]:
                first[n] = (day, a["result_lottery"], a["result_draw_position"])
        has_f = f in first
        has_m1 = n_m1 in first
        has_m2 = n_m2 in first
        if has_f and has_m1 and first[f][0] < first[n_m1][0]:
            seq_exact_then_m1 += 1
        if has_m1 and has_m2 and first[n_m1][0] < first[n_m2][0]:
            seq_m1_then_m2 += 1
        if has_f and has_m1 and has_m2:
            if first[f][0] < first[n_m1][0] < first[n_m2][0]:
                seq_full += 1
                if len(examples) < 15:
                    examples.append(
                        {
                            "case_date": r["case_date"],
                            "fuerte": f,
                            "number_-1": n_m1,
                            "number_-2": n_m2,
                            "day_fuerte": first[f][0],
                            "day_-1": first[n_m1][0],
                            "day_-2": first[n_m2][0],
                            "lotteries": {
                                "fuerte": first[f][1],
                                "-1": first[n_m1][1],
                                "-2": first[n_m2][1],
                            },
                        }
                    )
        if has_m1 and has_m2 and first[n_m1][0] < first[n_m2][0]:
            seq_family_rot += 1

    # opportunities where -1 and -2 both exist in group
    opp_both = 0
    for r in acts:
        f = int(r["fuerte"])
        group = t1_group_ordered(cat, f)
        pf = position_in_group(group, f)
        dists = {position_in_group(group, x) - pf for x in group}
        if -1 in dists and -2 in dists:
            opp_both += 1

    q10 = {
        "definition": (
            "Secuencia temporal por primera aparición en D+1…D+7: "
            "día(fuerte) < día(número en posición −1) < día(número en posición −2)."
        ),
        "activations_with_-1_and_-2_in_group": opp_both,
        "sequence_fuerte_then_-1_then_-2": seq_full,
        "rate_pct_of_opp_both": pct(seq_full, opp_both),
        "sequence_fuerte_then_-1_only": seq_exact_then_m1,
        "sequence_-1_then_-2_regardless_exact": seq_m1_then_m2,
        "examples": examples,
    }
    (OUT / "q10_sequence_minus1_minus2.json").write_text(
        json.dumps(q10, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary = {
        "unique_fuerte_activations": len(acts),
        "misses": len(misses),
        "q1_top_distances": q1_rows[:15],
        "q2": q2,
        "q4_summary": q4_summary,
        "q5_top5": [
            {
                "chain": x["chain"],
                "activations": x["activations"],
                "appearances": x["appearance_rows"],
                "years": x["years"],
                "exceptions": x["exception_count"],
            }
            for x in q5[:5]
        ],
        "q6_times_fuerte": profile42["times_fuerte_unique_day"],
        "q7_activations": profile_pair["activations"],
        "q8_rows": q8["appearance_rows"],
        "q9": {
            "all_years": q9["hits_all_years"],
            "fuertes_hit": q9["fuertes_with_hit"],
            "fuertes_opp": q9["fuertes_with_opportunity"],
            "rate": q9["overall_rate_pct"],
        },
        "q10": {
            "full_seq": q10["sequence_fuerte_then_-1_then_-2"],
            "opp_both": q10["activations_with_-1_and_-2_in_group"],
            "rate": q10["rate_pct_of_opp_both"],
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
