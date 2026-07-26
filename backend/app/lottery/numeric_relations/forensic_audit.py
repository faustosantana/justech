"""Forensic historical investigation — impartial, read-only.

For each analysis day: official T1×T2 fuertes, then inspect ONLY the next
7 calendar days (never same-day validation). When the fuerte misses, classify
what did appear by mathematical distance to the fuerte.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION
from app.lottery.numeric_relations.historical_manual_audit import (
    ObservedNumber,
    StrengthenedHit,
    _in_universe,
    strengthen_official,
)

DISTANCE_LABELS = {
    0: "FUERTE_EXACTO",
    1: "COMPANERO_TABLA1",
    2: "MISMO_CODIGO_T1",  # reserved; usually collapsed into 1
    3: "VECINO_TABLA2",
    4: "RELACION_INDIRECTA",
    5: "SIN_RELACION",
}


def new_audit_id() -> str:
    return str(uuid4())


def t1_group(cat: TableCatalog, n: int) -> set[int]:
    code = cat.table1_number_to_code.get(int(n))
    if code is None:
        return set()
    return {int(x) for x in cat.table1_code_to_numbers.get(code, []) if _in_universe(x)}


def t1_companions(cat: TableCatalog, n: int) -> set[int]:
    return t1_group(cat, n) - {int(n)}


def t2_code(cat: TableCatalog, n: int) -> int | None:
    try:
        return int(cat.get_table2_code_for_number(int(n)))
    except KeyError:
        return None


def t2_neighbors(cat: TableCatalog, n: int) -> set[int]:
    try:
        return set(int(x) for x in cat.get_table2_neighbors(int(n), exclude_self=True))
    except KeyError:
        return set()


def t2_group(cat: TableCatalog, n: int) -> set[int]:
    code = t2_code(cat, n)
    if code is None:
        return set()
    return {int(x) for x in cat.table2_code_to_numbers.get(code, []) if _in_universe(x)}


def distance_to_fuerte(cat: TableCatalog, fuerte: int, appeared: int) -> int:
    """0 exact … 5 unrelated. Deterministic."""
    f, a = int(fuerte), int(appeared)
    if not _in_universe(a):
        return 5
    if a == f:
        return 0
    if a in t1_companions(cat, f):
        return 1
    # same T1 code but not in companions list (shouldn't happen) 
    if t1_group(cat, f) and a in t1_group(cat, f):
        return 2
    if a in t2_neighbors(cat, f):
        return 3
    # indirect: one hop via T1 companion or T2 neighbor
    for c in t1_companions(cat, f):
        if a in t1_companions(cat, c) or a in t2_neighbors(cat, c):
            return 4
    for v in t2_neighbors(cat, f):
        if a in t1_companions(cat, v) or a in t2_neighbors(cat, v):
            return 4
    return 5


def classify_flags(cat: TableCatalog, fuerte: int, appeared: int) -> dict[str, bool]:
    f, a = int(fuerte), int(appeared)
    d = distance_to_fuerte(cat, f, a)
    return {
        "es_fuerte": a == f,
        "pertenece_grupo_t1": a in t1_group(cat, f),
        "pertenece_grupo_t2": a in t2_group(cat, f),
        "comparte_codigo_t1": cat.table1_number_to_code.get(a)
        == cat.table1_number_to_code.get(f)
        and a != f,
        "comparte_codigo_t2": t2_code(cat, a) is not None
        and t2_code(cat, a) == t2_code(cat, f)
        and a != f,
        "es_companero": a in t1_companions(cat, f),
        "es_vecino": a in t2_neighbors(cat, f),
        "relacion_indirecta": d == 4,
        "distancia": d,
        "distancia_label": DISTANCE_LABELS[d],
    }


@dataclass
class Appearance:
    number: int
    draw_date: date
    day_offset: int  # 1..7
    lottery_name: str
    lottery_id: str
    position: int
    position_label: str
    draw_time: str | None
    source_reference: str | None
    draw_id: str


def collect_window_appearances(
    *,
    case_date: date,
    by_date: dict[date, list[dict[str, Any]]],
) -> list[Appearance]:
    out: list[Appearance] = []
    for offset in range(1, 8):
        d = case_date + timedelta(days=offset)
        for dr in by_date.get(d, []):
            for n, pos, lab in zip(dr["numbers"], dr["positions"], dr["position_labels"]):
                if not _in_universe(int(n)):
                    continue
                out.append(
                    Appearance(
                        number=int(n),
                        draw_date=d,
                        day_offset=offset,
                        lottery_name=dr["lottery_name"],
                        lottery_id=dr["lottery_id"],
                        position=int(pos),
                        position_label=str(lab),
                        draw_time=dr.get("draw_time"),
                        source_reference=dr.get("source_reference"),
                        draw_id=dr["draw_id"],
                    )
                )
    return out


@dataclass
class FuerteOutcome:
    case_date: date
    year: int
    fuerte: int
    generator: int
    generator_lottery: str
    confirmers: list[int]
    confirmer_lotteries: list[str]
    n_confirmers: int
    fuerte_hit: bool
    fuerte_count: int
    first_fuerte: Appearance | None
    first_day_offset: int | None
    closest_distance: int
    closest_number: int | None
    closest_label: str
    outcome_bucket: str
    tree: dict[str, Any]
    miss_flags: dict[str, Any] | None


def build_tree(cat: TableCatalog, fuerte: int, apps: list[Appearance]) -> dict[str, Any]:
    t1 = sorted(t1_companions(cat, fuerte))
    t2 = sorted(t2_neighbors(cat, fuerte))
    by_dist: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen = set()
    for a in apps:
        key = (a.number, a.draw_date.isoformat(), a.lottery_name, a.position)
        if key in seen:
            continue
        seen.add(key)
        d = distance_to_fuerte(cat, fuerte, a.number)
        by_dist[DISTANCE_LABELS[d]].append(
            {
                "number": a.number,
                "date": a.draw_date.isoformat(),
                "day_offset": a.day_offset,
                "lottery": a.lottery_name,
                "position": a.position,
                "source_reference": a.source_reference,
            }
        )
    return {
        "fuerte": fuerte,
        "table1_companions": t1,
        "table1_code": cat.table1_number_to_code.get(fuerte),
        "table2_neighbors": t2,
        "table2_code": t2_code(cat, fuerte),
        "results_by_distance": {k: v[:40] for k, v in by_dist.items()},
        "result_counts_by_distance": {k: len(v) for k, v in by_dist.items()},
    }


def analyze_fuerte(
    *,
    case_date: date,
    hit: StrengthenedHit,
    apps: list[Appearance],
    catalog: TableCatalog,
) -> FuerteOutcome:
    f = hit.candidate
    fuerte_apps = [a for a in apps if a.number == f]
    fuerte_hit = bool(fuerte_apps)
    first = min(fuerte_apps, key=lambda a: (a.day_offset, a.draw_time or "")) if fuerte_apps else None

    # Closest mathematical relation among all appeared numbers
    closest_d = 5
    closest_n: int | None = None
    if apps:
        for a in apps:
            d = distance_to_fuerte(catalog, f, a.number)
            if d < closest_d:
                closest_d = d
                closest_n = a.number
                if d == 0:
                    break

    if fuerte_hit:
        bucket = "FUERTE_EXACTO"
    elif closest_d == 1:
        bucket = "COMPANERO_TABLA1"
    elif closest_d == 2:
        bucket = "MISMO_CODIGO_T1"
    elif closest_d == 3:
        bucket = "VECINO_TABLA2"
    elif closest_d == 4:
        bucket = "RELACION_INDIRECTA"
    else:
        bucket = "SIN_RELACION"

    miss_flags = None
    if not fuerte_hit and closest_n is not None:
        miss_flags = {
            "appeared_example": closest_n,
            **classify_flags(catalog, f, closest_n),
        }
    elif not fuerte_hit:
        miss_flags = {
            "appeared_example": None,
            "es_fuerte": False,
            "pertenece_grupo_t1": False,
            "pertenece_grupo_t2": False,
            "comparte_codigo_t1": False,
            "comparte_codigo_t2": False,
            "es_companero": False,
            "es_vecino": False,
            "relacion_indirecta": False,
            "distancia": 5,
            "distancia_label": "SIN_RELACION",
            "note": "No featured numbers in next-7-day window",
        }

    return FuerteOutcome(
        case_date=case_date,
        year=case_date.year,
        fuerte=f,
        generator=hit.generator_observed,
        generator_lottery=hit.generator_lottery,
        confirmers=list(hit.confirmers),
        confirmer_lotteries=list(hit.confirmer_lotteries),
        n_confirmers=len(hit.confirmers),
        fuerte_hit=fuerte_hit,
        fuerte_count=len(fuerte_apps),
        first_fuerte=first,
        first_day_offset=first.day_offset if first else None,
        closest_distance=closest_d,
        closest_number=closest_n,
        closest_label=DISTANCE_LABELS[closest_d],
        outcome_bucket=bucket,
        tree=build_tree(catalog, f, apps),
        miss_flags=miss_flags,
    )


def aggregate_forensic(outcomes: list[FuerteOutcome]) -> dict[str, Any]:
    n = len(outcomes)
    bucket_c = Counter(o.outcome_bucket for o in outcomes)
    dist_c = Counter(o.closest_distance for o in outcomes)
    hit_n = sum(1 for o in outcomes if o.fuerte_hit)
    miss_n = n - hit_n

    # When miss: distribution of closest relation
    miss = [o for o in outcomes if not o.fuerte_hit]
    miss_bucket = Counter(o.outcome_bucket for o in miss)

    def pct(part: int, whole: int) -> float:
        return round(100.0 * part / whole, 2) if whole else 0.0

    ranking_when_miss = [
        {
            "bucket": k,
            "count": miss_bucket[k],
            "pct_of_misses": pct(miss_bucket[k], miss_n),
        }
        for k in (
            "COMPANERO_TABLA1",
            "VECINO_TABLA2",
            "MISMO_CODIGO_T1",
            "RELACION_INDIRECTA",
            "SIN_RELACION",
        )
    ]

    # Day-offset when fuerte hits
    day_offset_hits = Counter(o.first_day_offset for o in outcomes if o.fuerte_hit and o.first_day_offset)

    # By year
    yearly: dict[str, Any] = {}
    for y in sorted({o.year for o in outcomes}):
        yo = [o for o in outcomes if o.year == y]
        yh = sum(1 for o in yo if o.fuerte_hit)
        yearly[str(y)] = {
            "activations": len(yo),
            "fuerte_exact_hits": yh,
            "fuerte_exact_rate_pct": pct(yh, len(yo)),
            "misses": len(yo) - yh,
            "miss_buckets": dict(Counter(o.outcome_bucket for o in yo if not o.fuerte_hit)),
        }

    # By number 1..100
    by_number = []
    for num in range(1, 101):
        oo = [o for o in outcomes if o.fuerte == num]
        if not oo:
            continue
        h = sum(1 for o in oo if o.fuerte_hit)
        m = len(oo) - h
        mb = Counter(o.outcome_bucket for o in oo if not o.fuerte_hit)
        by_number.append(
            {
                "number": num,
                "times_fuerte": len(oo),
                "exact_hits": h,
                "exact_rate_pct": pct(h, len(oo)),
                "misses": m,
                "miss_companion": mb.get("COMPANERO_TABLA1", 0),
                "miss_neighbor": mb.get("VECINO_TABLA2", 0),
                "miss_indirect": mb.get("RELACION_INDIRECTA", 0),
                "miss_none": mb.get("SIN_RELACION", 0),
            }
        )
    by_number.sort(key=lambda r: -r["times_fuerte"])

    # Lottery: confirmer lotteries vs hit rate
    lot_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"activations": 0, "hits": 0})
    for o in outcomes:
        for cl in o.confirmer_lotteries or ["(none)"]:
            lot_stats[cl]["activations"] += 1
            if o.fuerte_hit:
                lot_stats[cl]["hits"] += 1
    lottery_rows = []
    for name, st in lot_stats.items():
        lottery_rows.append(
            {
                "lottery": name,
                "activations": st["activations"],
                "exact_hits": st["hits"],
                "exact_rate_pct": pct(st["hits"], st["activations"]),
            }
        )
    lottery_rows.sort(key=lambda r: (-r["activations"], -r["exact_rate_pct"]))

    # Confirmation levels
    conf_stats = {}
    for o in outcomes:
        k = str(o.n_confirmers) if o.n_confirmers < 4 else "4+"
        conf_stats.setdefault(k, {"activations": 0, "hits": 0, "companion_on_miss": 0})
        conf_stats[k]["activations"] += 1
        if o.fuerte_hit:
            conf_stats[k]["hits"] += 1
        elif o.outcome_bucket == "COMPANERO_TABLA1":
            conf_stats[k]["companion_on_miss"] += 1
    for k, st in conf_stats.items():
        st["exact_rate_pct"] = pct(st["hits"], st["activations"])
        st["companion_on_miss_pct"] = pct(st["companion_on_miss"], st["activations"] - st["hits"] or 1)

    # Relatedness: any distance <= 3 in window (exact/companion/same/neighbor)
    related_hit = sum(1 for o in outcomes if o.closest_distance <= 3)
    family_hit = sum(1 for o in outcomes if o.closest_distance <= 1)  # exact or companion

    return {
        "methodology_version": METHODOLOGY_VERSION,
        "total_fuerte_activations": n,
        "fuerte_exact_hits": hit_n,
        "fuerte_exact_rate_pct": pct(hit_n, n),
        "misses": miss_n,
        "miss_rate_pct": pct(miss_n, n),
        "any_related_distance_le_3_pct": pct(related_hit, n),
        "family_exact_or_companion_pct": pct(family_hit, n),
        "outcome_buckets_all": dict(bucket_c),
        "distance_distribution_closest": {
            DISTANCE_LABELS[k]: v for k, v in sorted(dist_c.items())
        },
        "ranking_when_fuerte_misses": ranking_when_miss,
        "day_offset_when_fuerte_hits": {str(k): v for k, v in sorted(day_offset_hits.items())},
        "yearly": yearly,
        "by_number_top": by_number[:40],
        "by_number_all": by_number,
        "lottery_confirmer_stats": lottery_rows,
        "confirmation_level_stats": conf_stats,
        "answers_preview": {
            "fuerte_sale_exacto_pct": pct(hit_n, n),
            "cuando_no_sale_companero_pct_of_misses": pct(
                miss_bucket.get("COMPANERO_TABLA1", 0), miss_n
            ),
            "cuando_no_sale_vecino_pct_of_misses": pct(
                miss_bucket.get("VECINO_TABLA2", 0), miss_n
            ),
            "cuando_no_sale_sin_relacion_pct_of_misses": pct(
                miss_bucket.get("SIN_RELACION", 0), miss_n
            ),
            "aparece_familia_exacto_o_companero_pct": pct(family_hit, n),
        },
    }


def pick_case_studies(outcomes: list[FuerteOutcome], *, limit: int = 12) -> list[dict[str, Any]]:
    """Educational mix: hits, companion-miss, neighbor-miss, none, multi-conf."""
    selected: list[FuerteOutcome] = []

    def take(pred, n: int) -> None:
        for o in outcomes:
            if len(selected) >= limit:
                return
            if n <= 0:
                return
            if o in selected:
                continue
            if pred(o):
                selected.append(o)
                n -= 1

    take(lambda o: o.fuerte_hit and o.first_day_offset == 1, 2)
    take(lambda o: o.fuerte_hit and (o.first_day_offset or 0) >= 4, 1)
    take(lambda o: (not o.fuerte_hit) and o.outcome_bucket == "COMPANERO_TABLA1", 3)
    take(lambda o: (not o.fuerte_hit) and o.outcome_bucket == "VECINO_TABLA2", 2)
    take(lambda o: (not o.fuerte_hit) and o.outcome_bucket == "SIN_RELACION", 2)
    take(lambda o: o.n_confirmers >= 2, 2)

    cards = []
    for i, o in enumerate(selected, start=1):
        cards.append(
            {
                "id": f"FX-{i:03d}",
                "date": o.case_date.isoformat(),
                "year": o.year,
                "fuerte": o.fuerte,
                "generator": o.generator,
                "generator_lottery": o.generator_lottery,
                "confirmers": o.confirmers,
                "confirmer_lotteries": o.confirmer_lotteries,
                "fuerte_hit": o.fuerte_hit,
                "first_day_offset": o.first_day_offset,
                "first_appearance": None
                if not o.first_fuerte
                else {
                    "date": o.first_fuerte.draw_date.isoformat(),
                    "lottery": o.first_fuerte.lottery_name,
                    "position": o.first_fuerte.position,
                    "source_reference": o.first_fuerte.source_reference,
                },
                "outcome_bucket": o.outcome_bucket,
                "closest_distance": o.closest_distance,
                "closest_number": o.closest_number,
                "miss_flags": o.miss_flags,
                "tree_summary": {
                    "table1_companions": o.tree.get("table1_companions"),
                    "table2_neighbors": o.tree.get("table2_neighbors"),
                    "result_counts_by_distance": o.tree.get("result_counts_by_distance"),
                },
            }
        )
    return cards
