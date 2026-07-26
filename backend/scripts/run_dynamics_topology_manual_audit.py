#!/usr/bin/env python3
"""PRE-J11A dynamics / topology / manual-rules audit runner."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.lottery.numeric_relations.catalog import build_catalog  # noqa: E402
from app.lottery.numeric_relations.dynamics_topology_manual_audit import (  # noqa: E402
    MANUAL_CASES,
    ManualCaseSpec,
    detect_sequence_flags,
    new_audit_id,
    pct,
    relative_number,
    reproduce_manual_case,
)
from app.lottery.numeric_relations.deep_mathematical_audit import (  # noqa: E402
    position_in_group,
    t1_group_ordered,
    t2_group_ordered,
)
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION  # noqa: E402

DEEP = REPO / "artifacts/deep_mathematical_audit"
ART = REPO / "artifacts/dynamics_topology_manual_audit"
DOCS = REPO / "docs/lottery/dynamics_topology_manual_audit"
ASSETS = DOCS / "assets"


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


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
            f"<text x='{x+bw/2:.1f}' y='{h-14}' text-anchor='middle' font-size='9' "
            f"font-family='system-ui'>{label[:14]}</text>"
            f"<text x='{x+bw/2:.1f}' y='{y-3:.1f}' text-anchor='middle' font-size='9'>{val:g}</text>"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}'>"
        f"<rect width='100%' height='100%' fill='#fafafa'/>"
        f"<text x='{pad}' y='24' font-size='13' font-family='system-ui' font-weight='600'>{title}</text>"
        + "".join(bars)
        + "</svg>",
        encoding="utf-8",
    )


def network_svg(edges: list[tuple[int, int, int]], title: str, path: Path, *, max_edges: int = 80) -> None:
    """Simple circular layout network SVG."""
    edges = sorted(edges, key=lambda e: -e[2])[:max_edges]
    nodes = sorted({a for a, _, _ in edges} | {b for _, b, _ in edges})
    if not nodes:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        return
    import math

    W, H, R = 900, 900, 380
    cx, cy = W / 2, H / 2
    pos = {}
    for i, n in enumerate(nodes):
        ang = 2 * math.pi * i / len(nodes) - math.pi / 2
        pos[n] = (cx + R * math.cos(ang), cy + R * math.sin(ang))
    max_w = max(e[2] for e in edges) or 1
    lines = []
    for a, b, c in edges:
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        sw = 0.5 + 4.5 * (c / max_w)
        lines.append(
            f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' "
            f"stroke='#2563eb' stroke-opacity='0.45' stroke-width='{sw:.2f}'/>"
        )
    dots = []
    for n, (x, y) in pos.items():
        dots.append(
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='10' fill='#0f172a'/>"
            f"<text x='{x:.1f}' y='{y+4:.1f}' text-anchor='middle' fill='#fff' font-size='9' "
            f"font-family='system-ui'>{n}</text>"
        )
    path.write_text(
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}'>"
        f"<rect width='100%' height='100%' fill='#fff'/>"
        f"<text x='20' y='28' font-size='14' font-family='system-ui' font-weight='600'>{title}</text>"
        + "".join(lines)
        + "".join(dots)
        + "</svg>",
        encoding="utf-8",
    )


def load_unique_activations() -> list[dict]:
    rows = []
    seen = set()
    with (DEEP / "all_activations.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            k = (r["case_date"], r["fuerte"])
            if k in seen:
                continue
            seen.add(k)
            rows.append(r)
    return rows


def load_apps_for_keys(keys: set[tuple[str, str]]) -> dict[tuple[str, str], list[dict]]:
    by = defaultdict(list)
    with (DEEP / "all_future_appearances.csv").open(encoding="utf-8") as f:
        for a in csv.DictReader(f):
            k = (a["case_date"], a["fuerte"])
            if k in keys:
                by[k].append(a)
    # dedupe physical
    out = {}
    for k, rows in by.items():
        seen = set()
        uniq = []
        for a in sorted(rows, key=lambda x: (int(x["day_offset"]), x["result_lottery"], int(x["result_draw_position"]))):
            sig = (
                a["result"],
                a["day_offset"],
                a["result_date"],
                a["result_lottery"],
                a["result_draw_position"],
                a.get("source_reference") or "",
            )
            if sig in seen:
                continue
            seen.add(sig)
            uniq.append(a)
        out[k] = uniq
    return out


def chain_history(acts_all: list[dict], apps_by_act: dict, origin: int, fuerte: int, confirmer: int) -> dict:
    rows = [
        r
        for r in acts_all
        if int(r["origin"]) == origin and int(r["fuerte"]) == fuerte and int(r["confirmer"]) == confirmer
    ]
    dossier = []
    for r in rows:
        apps = apps_by_act.get(r["activation_id"], [])
        exact = [a for a in apps if int(a["result"]) == fuerte]
        first = exact[0] if exact else None
        # T1 relatives first days
        cat_rel = {}
        dossier.append(
            {
                "case_date": r["case_date"],
                "year": r["year"],
                "origin_lottery": r["origin_lottery"],
                "origin_draw_position": r["origin_draw_position"],
                "confirmer_lottery": r["confirmer_lottery"],
                "confirmer_draw_position": r["confirmer_draw_position"],
                "fuerte_appeared": r["fuerte_appeared"],
                "first_day_offset": r.get("first_day_offset"),
                "first_lottery": r.get("first_lottery"),
                "first_draw_position": r.get("first_draw_position"),
                "fuerte_appearance_count": r.get("fuerte_appearance_count"),
            }
        )
    return {
        "origin": origin,
        "fuerte": fuerte,
        "confirmer": confirmer,
        "activations": len(rows),
        "years": sorted({int(r["year"]) for r in rows}),
        "exact_count": sum(1 for r in rows if str(r["fuerte_appeared"]).lower() == "true"),
        "exact_rate_pct": pct(
            sum(1 for r in rows if str(r["fuerte_appeared"]).lower() == "true"), len(rows)
        ),
        "rows": dossier,
    }


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    if not (DEEP / "all_activations.csv").exists():
        raise SystemExit("deep audit artifacts missing; run deep audit first")

    audit_id = new_audit_id()
    cat = build_catalog()

    # ---- Manual cases ----
    manual_repros = [reproduce_manual_case(s, catalog=cat) for s in MANUAL_CASES]
    # Also reproduce M5 with 84 explicitly
    m5_84 = reproduce_manual_case(
        ManualCaseSpec(
            "M5b",
            [39, 84],
            94,
            "Par alterno 39+84→94",
            ["deep audit"],
        ),
        catalog=cat,
    )

    write_csv(
        ART / "manual_cases.csv",
        [
            {
                "case_id": m["case_id"],
                "observed": "|".join(map(str, m["observed"])),
                "manual_fuerte": m["manual_fuerte"],
                "official_fuertes": "|".join(map(str, m["official_fuertes"])),
                "classification": m["classification"],
                "certainty": m["certainty"],
                "evidence": m["evidence"],
            }
            for m in manual_repros
        ],
    )
    write_csv(
        ART / "rule_classifications.csv",
        [
            {
                "case_id": m["case_id"],
                "classification": m["classification"],
                "certainty": m["certainty"],
                "evidence": m["evidence"],
            }
            for m in manual_repros
        ],
    )
    (ART / "manual_case_reproductions.json").write_text(
        json.dumps({"cases": manual_repros, "m5b_39_84": m5_84}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ---- Load deep history ----
    acts_unique = load_unique_activations()
    acts_all = list(csv.DictReader((DEEP / "all_activations.csv").open(encoding="utf-8")))
    keys = {(r["case_date"], r["fuerte"]) for r in acts_unique}
    apps_by = load_apps_for_keys(keys)

    # apps by activation_id for chain dossiers (stream once more lightly from memory keys)
    apps_by_act: dict[str, list[dict]] = defaultdict(list)
    with (DEEP / "all_future_appearances.csv").open(encoding="utf-8") as f:
        for a in csv.DictReader(f):
            # only keep for chain of interest later — store all is heavy; filter origins
            if (a["case_date"], a["fuerte"]) in keys:
                apps_by_act[a["activation_id"]].append(a)

    # ---- Historical dossiers for key chains ----
    hist_35_54_14 = chain_history(acts_all, apps_by_act, 35, 54, 14)
    hist_39_94_84 = chain_history(acts_all, apps_by_act, 39, 94, 84)
    hist_39_94_58 = chain_history(acts_all, apps_by_act, 39, 94, 58)
    hist_41_62_days = [
        r for r in acts_all if {int(r["origin"]), int(r["confirmer"])} == {41, 62} or (
            int(r["origin"]) in (41, 62) and int(r["confirmer"]) in (41, 62)
        )
    ]
    # Days where 41 and 62 co-observed as origin/confirmer roles — also scan unique days from activations mentioning both
    # Broader: from all_activations where origin/confirmer pair involves — for DIRECT_T2 look for days in deep data
    # Use appearances? Better: scan activations for origin=41 any, and check same day had 62 — approximate via chain absence
    direct_t2_41_62 = {
        "note": "41+62 no produce fuerte oficial; 75 es vecino T2 de 62",
        "geometry": manual_repros[1]["direct_t2_links"],
        "official_hits_on_pair": [],
        "historical_chains_with_41_and_62_roles": len(hist_41_62_days),
    }

    # Enrich M4 dossier with relative positions when miss
    m4_rows = []
    for r in hist_35_54_14["rows"]:
        apps = apps_by.get((r["case_date"], "54"), [])
        first_days = {}
        for a in apps:
            n = int(a["result"])
            d = int(a["day_offset"])
            if n not in first_days or d < first_days[n]:
                first_days[n] = d
        rel = {}
        for dist in (-2, -1, 1, 2):
            num = relative_number(cat, 54, dist)
            rel[f"dist_{dist}"] = {
                "number": num,
                "appeared": bool(num and num in first_days),
                "first_day": first_days.get(num) if num else None,
            }
        m4_rows.append({**r, "relatives": rel, "first_days_sample": dict(list(first_days.items())[:12])})
    hist_35_54_14["detailed_rows"] = m4_rows

    (ART / "manual_case_reproductions.csv").write_text("", encoding="utf-8")
    write_csv(
        ART / "manual_case_reproductions.csv",
        [
            {
                "case_id": m["case_id"],
                "observed": "|".join(map(str, m["observed"])),
                "manual_fuerte": m["manual_fuerte"],
                "official": "|".join(map(str, m["official_fuertes"])),
                "classification": m["classification"],
                "certainty": m["certainty"],
            }
            for m in manual_repros + [m5_84]
        ],
    )

    # ---- Multiple strong / tie-break ----
    multi = [r for r in acts_unique if int(r.get("n_fuertes_same_day") or 0) >= 2]
    # Expand: days with >=2 unique fuertes
    day_fuertes = defaultdict(set)
    for r in acts_unique:
        day_fuertes[r["case_date"]].add(int(r["fuerte"]))
    multi_days = {d: sorted(fs) for d, fs in day_fuertes.items() if len(fs) >= 2}
    multi_rows = []
    for d, fs in sorted(multi_days.items()):
        day_acts = [r for r in acts_all if r["case_date"] == d]
        for f in fs:
            fa = [r for r in day_acts if int(r["fuerte"]) == f]
            if not fa:
                continue
            # pick max confirmers row
            best = max(fa, key=lambda r: int(r["n_confirmers"]))
            multi_rows.append(
                {
                    "case_date": d,
                    "fuerte": f,
                    "origin": best["origin"],
                    "confirmer": best["confirmer"],
                    "n_confirmers": best["n_confirmers"],
                    "n_fuertes_same_day": len(fs),
                    "all_fuertes": "|".join(map(str, fs)),
                    "t1_pos_fuerte": best["t1_pos_fuerte"],
                    "fuerte_appeared": best["fuerte_appeared"],
                    "first_day_offset": best.get("first_day_offset"),
                }
            )
    write_csv(ART / "multiple_strong_cases.csv", multi_rows)

    # Tie-break candidate: more confirmers wins among same-day fuertes
    # Evaluate on days with multi fuertes: does the fuerte with max confirmers have better exact rate?
    tb_cases = []
    for d, fs in multi_days.items():
        stats = []
        for f in fs:
            rows = [r for r in acts_all if r["case_date"] == d and int(r["fuerte"]) == f]
            nc = max(int(r["n_confirmers"]) for r in rows)
            exact = any(str(r["fuerte_appeared"]).lower() == "true" for r in rows)
            stats.append({"fuerte": f, "n_confirmers": nc, "exact": exact})
        winner = max(stats, key=lambda x: x["n_confirmers"])
        tb_cases.append(
            {
                "case_date": d,
                "fuertes": "|".join(map(str, fs)),
                "max_confirmers_fuerte": winner["fuerte"],
                "max_confirmers": winner["n_confirmers"],
                "max_confirmers_exact": winner["exact"],
                "any_exact": any(s["exact"] for s in stats),
            }
        )
    # M3 alignment
    m3 = next(m for m in manual_repros if m["case_id"] == "M3")
    tie_break_candidates = [
        {
            "rule": "more_confirmers",
            "description": "Elegir el fuerte con más confirmadores T2 observados",
            "m3_matches_manual": bool(m3["m3_tiebreak"]["hypothesis_more_confirmers"]),
            "multi_days": len(tb_cases),
            "max_confirmers_exact_rate_pct": pct(
                sum(1 for t in tb_cases if t["max_confirmers_exact"]), len(tb_cases)
            ),
            "note": "Candidata de investigación; no incorporada al motor. Ver contraejemplos en multi_days.",
        },
        {
            "rule": "manual_M3_35_over_22",
            "description": "En 49+44+70 el socio eligió 35 (2 conf) sobre 22 (1 conf)",
            "matches": True,
            "counterexamples_needed": True,
        },
    ]
    write_csv(ART / "tie_break_candidates.csv", tie_break_candidates)
    (ART / "tie_break_eval.json").write_text(
        json.dumps({"multi_day_evals": tb_cases[:200], "summary": tie_break_candidates}, indent=2),
        encoding="utf-8",
    )

    # ---- Dynamics sequences ----
    seq_opp = Counter()
    seq_hit = Counter()
    seq_examples = defaultdict(list)
    minus1_producers = Counter()
    minus1_numbers = Counter()
    minus1_then_fuerte = 0
    minus1_then_m2 = 0
    minus1_was_confirmer = 0
    family_dyn_rows = []
    miss_rows = []
    edge_all = Counter()
    edge_d1 = Counter()
    edge_d2 = Counter()
    edge_d3 = Counter()
    edge_exact = Counter()
    edge_t1 = Counter()
    edge_t2 = Counter()
    edge_m1 = Counter()
    edge_p1 = Counter()
    cycles = Counter()
    cycle_examples = defaultdict(list)

    # family center stats: code -> member stats
    center = defaultdict(lambda: defaultdict(lambda: {"as_fuerte": 0, "as_posterior": 0, "as_origin": 0}))

    for r in acts_unique:
        f = int(r["fuerte"])
        apps = apps_by.get((r["case_date"], r["fuerte"]), [])
        first_day = {}
        for a in apps:
            n = int(a["result"])
            d = int(a["day_offset"])
            if n not in first_day or d < first_day[n]:
                first_day[n] = d
            edge_all[(f, n)] += 1
            if d == 1:
                edge_d1[(f, n)] += 1
            elif d == 2:
                edge_d2[(f, n)] += 1
            elif d == 3:
                edge_d3[(f, n)] += 1
            if n == f:
                edge_exact[(f, n)] += 1
            labs = a.get("labels") or ""
            if "MISMO_GRUPO_T1" in labs:
                edge_t1[(f, n)] += 1
            if "MISMO_GRUPO_T2" in labs:
                edge_t2[(f, n)] += 1

        n_m1 = relative_number(cat, f, -1)
        n_p1 = relative_number(cat, f, 1)
        n_m2 = relative_number(cat, f, -2)
        n_p2 = relative_number(cat, f, 2)
        for dist, num in ((-1, n_m1), (1, n_p1), (-2, n_m2), (2, n_p2)):
            if num is None:
                continue
            key = f"opp_{dist}"
            seq_opp[key] += 1
            if num in first_day:
                seq_hit[key] += 1
                if dist == -1:
                    edge_m1[(f, num)] += 1
                    minus1_producers[f] += 1
                    minus1_numbers[num] += 1
                    if int(r["confirmer"]) == num:
                        minus1_was_confirmer += 1
                if dist == 1:
                    edge_p1[(f, num)] += 1

        flags = detect_sequence_flags(
            first_day=first_day, fuerte=f, n_m1=n_m1, n_p1=n_p1, n_m2=n_m2, n_p2=n_p2
        )
        # F→-1→F if fuerte appears, then -1, then fuerte again later
        if n_m1 and f in first_day and n_m1 in first_day:
            f_days = sorted(int(a["day_offset"]) for a in apps if int(a["result"]) == f)
            if len(f_days) >= 2 and first_day[n_m1] > f_days[0] and any(fd > first_day[n_m1] for fd in f_days):
                flags.append("F→-1→F")
                cycles["F→-1→F"] += 1
        for fl in flags:
            seq_hit[fl] += 1
            if len(seq_examples[fl]) < 8:
                seq_examples[fl].append(
                    {
                        "case_date": r["case_date"],
                        "fuerte": f,
                        "n_m1": n_m1,
                        "n_p1": n_p1,
                        "n_m2": n_m2,
                        "first_day": {str(k): v for k, v in first_day.items() if k in {f, n_m1, n_p1, n_m2, n_p2}},
                    }
                )
        for dist, num in ((-1, n_m1), (1, n_p1), (-2, n_m2), (2, n_p2)):
            if num is not None:
                seq_opp[f"flag_base_{dist}"] += 1

        if n_m1 and n_m1 in first_day and f in first_day and first_day[n_m1] < first_day[f]:
            minus1_then_fuerte += 1
        if n_m1 and n_m2 and n_m1 in first_day and n_m2 in first_day and first_day[n_m1] < first_day[n_m2]:
            minus1_then_m2 += 1

        # family dynamics row
        code = cat.table1_number_to_code[f]
        group = t1_group_ordered(cat, f)
        center[code][f]["as_fuerte"] += 1
        for a in apps:
            n = int(a["result"])
            if n in group:
                center[code][n]["as_posterior"] += 1
        center[code][int(r["origin"])]["as_origin"] += 1

        family_dyn_rows.append(
            {
                "case_date": r["case_date"],
                "fuerte": f,
                "t1_code": code,
                "t1_group": "|".join(map(str, group)),
                "t1_pos": r["t1_pos_fuerte"],
                "num_-1": n_m1 or "",
                "num_+1": n_p1 or "",
                "num_-2": n_m2 or "",
                "num_+2": n_p2 or "",
                "day_-1": first_day.get(n_m1, "") if n_m1 else "",
                "day_+1": first_day.get(n_p1, "") if n_p1 else "",
                "day_fuerte": first_day.get(f, ""),
                "sequences": "|".join(flags),
                "fuerte_appeared": r["fuerte_appeared"],
            }
        )

        # misses detailed
        if str(r["fuerte_appeared"]).lower() != "true":
            first_t1 = None
            first_any = None
            for a in apps:
                labs = set((a.get("labels") or "").split("|"))
                if first_any is None and "SIN_RELACION_DIRECTA_IDENTIFICADA" not in labs:
                    first_any = a
                if first_t1 is None and "MISMO_GRUPO_T1" in labs and int(a["result"]) != f:
                    first_t1 = a
            miss_rows.append(
                {
                    "case_date": r["case_date"],
                    "fuerte": f,
                    "origin": r["origin"],
                    "confirmer": r["confirmer"],
                    "t1_group": "|".join(map(str, group)),
                    "t1_pos_fuerte": r["t1_pos_fuerte"],
                    "first_t1_companion": first_t1["result"] if first_t1 else "",
                    "first_t1_dist": first_t1.get("t1_dist", "") if first_t1 else "",
                    "first_t1_pos": first_t1.get("t1_pos_result", "") if first_t1 else "",
                    "first_t1_day": first_t1["day_offset"] if first_t1 else "",
                    "first_t1_lottery": first_t1["result_lottery"] if first_t1 else "",
                    "first_t1_draw_position": first_t1["result_draw_position"] if first_t1 else "",
                    "first_related": first_any["result"] if first_any else "",
                    "first_related_primary": first_any["primary_relation"] if first_any else "",
                    "first_related_day": first_any["day_offset"] if first_any else "",
                    "other_fuertes": r.get("other_fuertes", ""),
                }
            )

        # simple A→B→A cycle within window using first days of two numbers
        for a in apps:
            n = int(a["result"])
            if n == f:
                continue
            if n in first_day and f in first_day and first_day[f] < first_day[n]:
                # if f reappears after n
                f_days = [int(x["day_offset"]) for x in apps if int(x["result"]) == f]
                if any(fd > first_day[n] for fd in f_days):
                    cycles[f"A→B→A:{f}→{n}→{f}"] += 1
                    if len(cycle_examples[f"{f}-{n}"]) < 3:
                        cycle_examples[f"{f}-{n}"].append(r["case_date"])

    write_csv(ART / "family_dynamics.csv", family_dyn_rows)
    write_csv(ART / "misses_552_detailed.csv", miss_rows)
    write_csv(
        ART / "position_minus_one.csv",
        [
            {
                "fuerte": f,
                "times_produced_-1": c,
                "number_at_-1": relative_number(cat, f, -1) or "",
            }
            for f, c in minus1_producers.most_common()
        ],
    )

    # Family centers
    center_rows = []
    for code, members in sorted(center.items()):
        group = cat.table1_code_to_numbers.get(code, [])
        scored = []
        for n in group:
            st = members.get(n, {"as_fuerte": 0, "as_posterior": 0, "as_origin": 0})
            scored.append(
                {
                    "t1_code": code,
                    "number": n,
                    "t1_pos": position_in_group(group, n),
                    "as_fuerte": st["as_fuerte"],
                    "as_posterior": st["as_posterior"],
                    "as_origin": st["as_origin"],
                    "connections": st["as_fuerte"] + st["as_posterior"] + st["as_origin"],
                }
            )
        if not scored:
            continue
        geo_center = group[len(group) // 2] if group else None
        by_fuerte = max(scored, key=lambda x: x["as_fuerte"])
        by_post = max(scored, key=lambda x: x["as_posterior"])
        by_conn = max(scored, key=lambda x: x["connections"])
        for s in scored:
            s["geometric_center"] = geo_center
            s["center_by_fuerte_activations"] = by_fuerte["number"]
            s["center_by_posterior"] = by_post["number"]
            s["center_by_connections"] = by_conn["number"]
            center_rows.append(s)
    write_csv(ART / "family_centers.csv", center_rows)

    # Cycles export
    cycle_rows = [
        {"cycle": k, "count": v, "examples": "|".join(cycle_examples.get("-".join(k.split(":")[-1].split("→")[0:2]), [])[:5])}
        for k, v in cycles.most_common(200)
    ]
    # fix examples mapping simply
    cycle_rows = [{"cycle": k, "count": v} for k, v in cycles.most_common(200)]
    write_csv(ART / "cycles.csv", cycle_rows)

    # Paths / transitions top
    path_rows = [
        {"from": a, "to": b, "count": c, "type": "fuerte_to_result_all"}
        for (a, b), c in edge_all.most_common(300)
    ]
    write_csv(ART / "paths.csv", path_rows)

    # Number profiles 1-100
    # from deep number_profiles + enrich
    deep_prof = {int(r["number"]): r for r in csv.DictReader((DEEP / "number_profiles.csv").open())}
    profiles = []
    for n in range(1, 101):
        g = t1_group_ordered(cat, n)
        pf = position_in_group(g, n)
        dp = deep_prof.get(n, {})
        profiles.append(
            {
                "number": n,
                "t1_code": cat.table1_number_to_code[n],
                "t1_group": "|".join(map(str, g)),
                "t1_pos": pf,
                "num_-1": relative_number(cat, n, -1) or "",
                "num_+1": relative_number(cat, n, 1) or "",
                "num_-2": relative_number(cat, n, -2) or "",
                "num_+2": relative_number(cat, n, 2) or "",
                "t2_group": "|".join(map(str, t2_group_ordered(cat, n))),
                "times_fuerte": dp.get("times_fuerte", 0),
                "exact_any": dp.get("exact_any", 0),
                "times_origin": dp.get("times_origin", 0),
                "times_confirmer": dp.get("times_confirmer", 0),
                "produced_-1_count": minus1_producers.get(n, 0),
                "appeared_as_-1_count": minus1_numbers.get(n, 0),
            }
        )
    write_csv(ART / "number_profiles.csv", profiles)

    # Direct T2 signals export
    write_csv(
        ART / "direct_t2_signals.csv",
        [
            {
                "case_id": "M2",
                "observed_a": 41,
                "observed_b": 62,
                "manual_fuerte": 75,
                "t2_link_from": 62,
                "classification": "VECINO_T2_DIRECTO",
                "incorporated": False,
            }
        ],
    )

    # Graphs
    def edges_list(counter, n=80):
        return [(a, b, c) for (a, b), c in counter.most_common(n)]

    network_svg(edges_list(edge_all), "Red global fuerte→resultado (top)", ASSETS / "global_network.svg")
    network_svg(edges_list(edge_d1), "Red D+1", ASSETS / "D1_network.svg")
    network_svg(edges_list(edge_d2), "Red D+2", ASSETS / "D2_network.svg")
    network_svg(edges_list(edge_d3), "Red D+3", ASSETS / "D3_network.svg")
    network_svg(edges_list(edge_exact), "Red exactos", ASSETS / "exact_network.svg")
    network_svg(edges_list(edge_t1), "Red compañeros T1", ASSETS / "T1_family_network.svg")
    network_svg(edges_list(edge_t2), "Red vecinos T2", ASSETS / "T2_neighbor_network.svg")
    network_svg(edges_list(edge_m1), "Red posición −1", ASSETS / "minus_one_network.svg")
    network_svg(edges_list(edge_p1), "Red posición +1", ASSETS / "plus_one_network.svg")
    # cycles network: top A-B from A→B→A keys
    cyc_edges = []
    for k, v in cycles.most_common(60):
        if "A→B→A:" in k:
            body = k.split(":", 1)[1]
            parts = body.split("→")
            if len(parts) >= 2:
                cyc_edges.append((int(parts[0]), int(parts[1]), v))
    network_svg(cyc_edges, "Red ciclos A→B→A", ASSETS / "cycles_network.svg")

    bar_svg(
        {str(f): float(c) for f, c in minus1_producers.most_common(15)},
        "Fuertes que más producen aparición en −1",
        ASSETS / "minus1_producers.svg",
    )
    bar_svg(
        {k: float(seq_hit[k]) for k in ("F→-1", "F→+1", "F→-2", "F→+2", "F→-1→-2", "F→+1→+2", "F→-1→F") if k in seq_hit},
        "Secuencias dinámicas observadas (conteo)",
        ASSETS / "sequences.svg",
    )

    graph = {
        "edges": {
            "all": [{"from": a, "to": b, "count": c} for (a, b), c in edge_all.most_common(500)],
            "D1": [{"from": a, "to": b, "count": c} for (a, b), c in edge_d1.most_common(200)],
            "minus_one": [{"from": a, "to": b, "count": c} for (a, b), c in edge_m1.most_common(200)],
        }
    }
    (ART / "relationship_graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")

    findings = {
        "audit_id": audit_id,
        "branch": "feature/nr-dynamics-topology-manual-rules-audit",
        "base_commit": "ba15158",
        "methodology_version": METHODOLOGY_VERSION,
        "motor_modified": False,
        "tables_modified": False,
        "production_touched": False,
        "j11a_started": False,
        "random_baseline_used": False,
        "manual_cases": [
            {
                "case_id": m["case_id"],
                "classification": m["classification"],
                "certainty": m["certainty"],
                "official": m["official_fuertes"],
                "manual": m["manual_fuerte"],
                "evidence": m["evidence"],
            }
            for m in manual_repros
        ],
        "m5b_39_84": {
            "classification": m5_84["classification"],
            "official": m5_84["official_fuertes"],
            "both_confirm": manual_repros[4]["m5_alternate_84"]["both_confirm_94"],
        },
        "hist_35_54_14": {
            "activations": hist_35_54_14["activations"],
            "exact_rate_pct": hist_35_54_14["exact_rate_pct"],
            "years": hist_35_54_14["years"],
        },
        "hist_39_94_84": {
            "activations": hist_39_94_84["activations"],
            "exact_rate_pct": hist_39_94_84["exact_rate_pct"],
            "years": hist_39_94_84["years"],
        },
        "hist_39_94_58": {
            "activations": hist_39_94_58["activations"],
            "exact_rate_pct": hist_39_94_58["exact_rate_pct"],
            "years": hist_39_94_58["years"],
        },
        "sequences": {
            "opp_-1": seq_opp.get("opp_-1", 0),
            "hit_-1": seq_hit.get("opp_-1", 0),
            "rate_-1": pct(seq_hit.get("opp_-1", 0), seq_opp.get("opp_-1", 0)),
            "flags": {k: seq_hit[k] for k in seq_hit if k.startswith("F") or k.startswith("-") or k.startswith("+")},
            "examples": {k: seq_examples[k] for k in list(seq_examples)[:12]},
        },
        "minus_one_role": {
            "producers_top": minus1_producers.most_common(15),
            "numbers_top": minus1_numbers.most_common(15),
            "minus1_then_fuerte": minus1_then_fuerte,
            "minus1_then_minus2": minus1_then_m2,
            "minus1_was_confirmer_count": minus1_was_confirmer,
            "interpretation": (
                "−1 funciona principalmente como destino frecuente de la familia "
                f"(tasa {pct(seq_hit.get('opp_-1',0), seq_opp.get('opp_-1',0))}%). "
                f"En {minus1_then_fuerte} activaciones −1 apareció antes que el fuerte "
                f"(puente/precursor). En {minus1_then_m2} casos −1 precedió a −2. "
                f"Fue el confirmador original en {minus1_was_confirmer} activaciones."
            ),
        },
        "misses": {
            "count": len(miss_rows),
            "with_t1_companion": sum(1 for m in miss_rows if m["first_t1_companion"]),
            "top_substitutes": Counter(m["first_t1_companion"] for m in miss_rows if m["first_t1_companion"]).most_common(15),
            "top_t1_dist": Counter(m["first_t1_dist"] for m in miss_rows if m["first_t1_dist"]).most_common(),
        },
        "multi_strong_days": len(multi_days),
        "tie_break_candidates": tie_break_candidates,
        "cycles_top": cycles.most_common(20),
        "direct_t2": direct_t2_41_62,
    }
    (ART / "full_findings.json").write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
    (ART / "m4_dossier_35_54_14.json").write_text(
        json.dumps(hist_35_54_14, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Book + PDF
    from write_dynamics_topology_book import write_book

    write_book(findings, manual_repros, m5_84, profiles, hist_35_54_14, hist_39_94_58, hist_39_94_84)

    print(
        json.dumps(
            {
                "audit_id": audit_id,
                "manual": [(m["case_id"], m["classification"]) for m in manual_repros],
                "m4_activations": hist_35_54_14["activations"],
                "m5_58_act": hist_39_94_58["activations"],
                "m5_84_act": hist_39_94_84["activations"],
                "misses": len(miss_rows),
                "seq_F_m1": seq_hit.get("F→-1"),
                "cycles_top": cycles.most_common(5),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
