"""Deep mathematical relations audit — deterministic, positional, temporal.

Read-only. Does not modify motor, Tabla 1/2, draws, or Production.
Does not use random baselines as the analytical axis.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Iterable
from uuid import uuid4

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION
from app.lottery.numeric_relations.historical_manual_audit import (
    ObservedNumber,
    StrengthenedHit,
    _in_universe,
    strengthen_official,
)

PERIOD_FROM = date(2019, 7, 23)
PERIOD_TO = date(2026, 7, 16)  # analysis end (window needs +7 beyond)


def new_audit_id() -> str:
    return str(uuid4())


# ---------------------------------------------------------------------------
# Canonical ordered groups (sorted ascending = official group order)
# ---------------------------------------------------------------------------


def t1_code_of(cat: TableCatalog, n: int) -> int | None:
    return cat.table1_number_to_code.get(int(n))


def t2_code_of(cat: TableCatalog, n: int) -> int | None:
    try:
        return int(cat.get_table2_code_for_number(int(n)))
    except KeyError:
        return None


def t1_group_ordered(cat: TableCatalog, n: int) -> list[int]:
    """Canonical T1 group of number n: all numbers sharing n's T1 digit-sum code."""
    code = t1_code_of(cat, n)
    if code is None:
        return []
    return list(cat.table1_code_to_numbers.get(code, []))


def t1_candidates_from_observed(cat: TableCatalog, observed: int) -> list[int]:
    """Official motor step: observed number used as mother code → candidates."""
    return list(cat.get_table1_companions(int(observed)))


def t2_group_ordered(cat: TableCatalog, n: int) -> list[int]:
    code = t2_code_of(cat, n)
    if code is None:
        return []
    return list(cat.table2_code_to_numbers.get(code, []))


def position_in_group(group: list[int], n: int) -> int | None:
    """1-based position in canonical ordered group, or None."""
    try:
        return group.index(int(n)) + 1
    except ValueError:
        return None


def positional_distance(group: list[int], fuerte: int, appeared: int) -> int | None:
    pf = position_in_group(group, fuerte)
    pa = position_in_group(group, appeared)
    if pf is None or pa is None:
        return None
    return pa - pf


# ---------------------------------------------------------------------------
# Official chains O → F ← C (without mutating strengthen_official)
# ---------------------------------------------------------------------------


@dataclass
class OfficialChain:
    case_date: date
    origin: int
    origin_lottery: str
    origin_position: int
    origin_position_label: str
    origin_draw_id: str
    origin_source: str | None
    fuerte: int
    confirmer: int
    confirmer_lottery: str
    confirmer_position: int
    confirmer_position_label: str
    confirmer_draw_id: str
    confirmer_source: str | None
    t1_candidates: list[int]
    t2_group_of_fuerte: list[int]
    t1_group_of_fuerte: list[int]
    t1_pos_fuerte: int | None
    t2_pos_fuerte: int | None
    t2_pos_confirmer: int | None
    n_confirmers_for_fuerte: int
    n_fuertes_same_day: int
    other_fuertes_same_day: list[int]
    other_candidates_same_day: list[int]


def _first_obs(by_num: dict[int, list[ObservedNumber]], n: int) -> ObservedNumber:
    return sorted(by_num[n], key=lambda o: (o.lottery_name, o.position, o.draw_id))[0]


def enumerate_official_chains(
    case_date: date,
    observations: list[ObservedNumber],
    *,
    catalog: TableCatalog,
) -> list[OfficialChain]:
    """Every official O→F←C triple for the day (deterministic)."""
    cat = catalog
    by_num: dict[int, list[ObservedNumber]] = {}
    for o in observations:
        if _in_universe(o.number):
            by_num.setdefault(int(o.number), []).append(o)
    uniq = sorted(by_num.keys())
    hits = strengthen_official(observations, catalog=cat)
    fuertes = {h.candidate: h for h in hits}
    all_fuertes = sorted(fuertes.keys())
    all_cands: set[int] = set()
    for gen in uniq:
        all_cands.update(t1_candidates_from_observed(cat, gen))

    chains: list[OfficialChain] = []
    for gen_n in uniq:
        others = set(uniq) - {gen_n}
        cands = t1_candidates_from_observed(cat, gen_n)
        for cand in cands:
            confs = sorted(set(t2_group_ordered(cat, cand)) & others - {cand})
            # Official: confirmer must be T2 neighbor of candidate (exclude self)
            confs = [
                c
                for c in confs
                if c in set(cat.get_table2_neighbors(cand, exclude_self=True))
            ]
            if not confs:
                continue
            if cand not in fuertes:
                # Should not happen if strengthen_official matches; skip if mismatch
                continue
            go = _first_obs(by_num, gen_n)
            t1g = t1_group_ordered(cat, cand)
            t2g = t2_group_ordered(cat, cand)
            for conf in confs:
                co = _first_obs(by_num, conf)
                chains.append(
                    OfficialChain(
                        case_date=case_date,
                        origin=gen_n,
                        origin_lottery=go.lottery_name,
                        origin_position=go.position,
                        origin_position_label=go.position_label,
                        origin_draw_id=go.draw_id,
                        origin_source=go.source_reference,
                        fuerte=cand,
                        confirmer=conf,
                        confirmer_lottery=co.lottery_name,
                        confirmer_position=co.position,
                        confirmer_position_label=co.position_label,
                        confirmer_draw_id=co.draw_id,
                        confirmer_source=co.source_reference,
                        t1_candidates=list(cands),
                        t2_group_of_fuerte=t2g,
                        t1_group_of_fuerte=t1g,
                        t1_pos_fuerte=position_in_group(t1g, cand),
                        t2_pos_fuerte=position_in_group(t2g, cand),
                        t2_pos_confirmer=position_in_group(t2g, conf),
                        n_confirmers_for_fuerte=len(fuertes[cand].confirmers),
                        n_fuertes_same_day=len(all_fuertes),
                        other_fuertes_same_day=[x for x in all_fuertes if x != cand],
                        other_candidates_same_day=sorted(all_cands - {cand}),
                    )
                )
    chains.sort(key=lambda c: (c.fuerte, c.origin, c.confirmer))
    return chains


# ---------------------------------------------------------------------------
# Future appearances
# ---------------------------------------------------------------------------


@dataclass
class FutureAppearance:
    number: int
    day_offset: int
    draw_date: date
    lottery_name: str
    lottery_id: str
    position: int
    position_label: str
    draw_time: str | None
    source_reference: str | None
    draw_id: str


def collect_future(
    case_date: date,
    by_date: dict[date, list[dict[str, Any]]],
) -> list[FutureAppearance]:
    out: list[FutureAppearance] = []
    for offset in range(1, 8):
        d = case_date + timedelta(days=offset)
        for dr in by_date.get(d, []):
            for n, pos, lab in zip(dr["numbers"], dr["positions"], dr["position_labels"]):
                if not _in_universe(int(n)):
                    continue
                out.append(
                    FutureAppearance(
                        number=int(n),
                        day_offset=offset,
                        draw_date=d,
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


# ---------------------------------------------------------------------------
# Multi-label classification
# ---------------------------------------------------------------------------

LABELS = (
    "FUERTE_EXACTO",
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
    "SIN_RELACION_DIRECTA_IDENTIFICADA",
)


def chain_hop_closures(cat: TableCatalog, chain: OfficialChain) -> tuple[set[int], set[int]]:
    """Precompute 2nd/3rd level closures once per chain."""
    f = chain.fuerte
    mids = (set(chain.t1_group_of_fuerte) | set(chain.t2_group_of_fuerte)) - {f}
    hop1: set[int] = set()
    for mid in mids:
        hop1.update(t1_group_ordered(cat, mid))
        hop1.update(cat.get_table2_neighbors(mid, exclude_self=True))
    hop2: set[int] = set()
    for mid2 in hop1 - {f}:
        hop2.update(t1_group_ordered(cat, mid2))
        hop2.update(cat.get_table2_neighbors(mid2, exclude_self=True))
    return hop1, hop2


def classify_appearance(
    *,
    cat: TableCatalog,
    chain: OfficialChain,
    app: FutureAppearance,
    hop1: set[int] | None = None,
    hop2: set[int] | None = None,
    conf_t1: list[int] | None = None,
    conf_t2: set[int] | None = None,
) -> dict[str, Any]:
    f = chain.fuerte
    a = app.number
    t1g = chain.t1_group_of_fuerte
    t2g = chain.t2_group_of_fuerte
    t1_dist = positional_distance(t1g, f, a)
    t2_dist = positional_distance(t2g, f, a)
    t1_pos_a = position_in_group(t1g, a)
    t2_pos_a = position_in_group(t2g, a)

    labels: list[str] = []
    if a == f:
        labels.append("FUERTE_EXACTO")

    same_t1 = a in t1g
    if same_t1:
        labels.append("MISMO_GRUPO_T1")
        if t1_code_of(cat, a) == t1_code_of(cat, f):
            labels.append("MISMO_CODIGO_T1")
        if t1_dist is not None and a != f:
            ad = abs(t1_dist)
            if ad == 1:
                labels.append("POSICION_T1_ADYACENTE")
            elif 2 <= ad <= 3:
                labels.append("POSICION_T1_CERCANA")
            elif ad > 3:
                labels.append("POSICION_T1_LEJANA")

    same_t2 = a in t2g
    if same_t2:
        labels.append("MISMO_GRUPO_T2")
        if t2_code_of(cat, a) == t2_code_of(cat, f):
            labels.append("MISMO_CODIGO_T2")
        if t2_dist is not None and abs(t2_dist) == 1 and a != f:
            labels.append("POSICION_T2_ADYACENTE")

    if a == chain.confirmer:
        labels.append("CONFIRMADOR_ORIGINAL")

    if conf_t1 is None:
        conf_t1 = t1_group_ordered(cat, chain.confirmer)
    if conf_t2 is None:
        conf_t2 = set(cat.get_table2_neighbors(chain.confirmer, exclude_self=True))
    if a != chain.confirmer and a in conf_t1:
        labels.append("COMPANERO_DEL_CONFIRMADOR")
    if a in conf_t2:
        labels.append("VECINO_DEL_CONFIRMADOR")

    if a in chain.other_candidates_same_day and a != f:
        labels.append("CANDIDATO_ORIGINAL_ALTERNATIVO")
    if a in chain.other_fuertes_same_day:
        labels.append("FUERTE_ALTERNATIVO")

    # Second / third level (only if not already tightly related)
    tight = {
        "FUERTE_EXACTO",
        "MISMO_GRUPO_T1",
        "MISMO_GRUPO_T2",
        "CONFIRMADOR_ORIGINAL",
        "COMPANERO_DEL_CONFIRMADOR",
        "VECINO_DEL_CONFIRMADOR",
        "FUERTE_ALTERNATIVO",
        "CANDIDATO_ORIGINAL_ALTERNATIVO",
    }
    if not (set(labels) & tight):
        if hop1 is None or hop2 is None:
            hop1, hop2 = chain_hop_closures(cat, chain)
        if a in hop1:
            labels.append("RELACION_DE_SEGUNDO_NIVEL")
        elif a in hop2:
            labels.append("RELACION_DE_TERCER_NIVEL")
        else:
            labels.append("SIN_RELACION_DIRECTA_IDENTIFICADA")

    direction = None
    if t1_dist is not None:
        if t1_dist > 0:
            direction = "despues"
        elif t1_dist < 0:
            direction = "antes"
        else:
            direction = "misma"

    return {
        "labels": labels,
        "t1_code": t1_code_of(cat, a),
        "t2_code": t2_code_of(cat, a),
        "t1_pos": t1_pos_a,
        "t2_pos": t2_pos_a,
        "t1_dist": t1_dist,
        "t2_dist": t2_dist,
        "t1_direction": direction,
        "t1_group_size": len(t1g),
        "t2_group_size": len(t2g),
        "primary_relation": labels[0] if labels else "SIN_RELACION_DIRECTA_IDENTIFICADA",
    }


def consistency_level(n: int) -> str:
    if n < 5:
        return "NIVEL_1_CASO_AISLADO"
    if n < 10:
        return "NIVEL_2_REPETICION_BAJA"
    if n < 25:
        return "NIVEL_3_REPETICION_MODERADA"
    if n < 50:
        return "NIVEL_4_REPETICION_ALTA"
    return "NIVEL_5_REPETICION_MUY_ALTA"


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 2) if whole else 0.0


def matrix_with_margins(counter: dict[tuple[Any, Any], int]) -> dict[str, Any]:
    rows = sorted({k[0] for k in counter})
    cols = sorted({k[1] for k in counter})
    grid = {r: {c: counter.get((r, c), 0) for c in cols} for r in rows}
    row_tot = {r: sum(grid[r].values()) for r in rows}
    col_tot = {c: sum(grid[r][c] for r in rows) for c in cols}
    total = sum(row_tot.values())
    row_pct = {
        r: {c: pct(grid[r][c], row_tot[r]) for c in cols} for r in rows
    }
    col_pct = {
        r: {c: pct(grid[r][c], col_tot[c]) for c in cols} for r in rows
    }
    return {
        "rows": rows,
        "cols": cols,
        "counts": grid,
        "row_totals": row_tot,
        "col_totals": col_tot,
        "total": total,
        "row_pct": row_pct,
        "col_pct": col_pct,
    }


def accumulate_first_hit_days(first_offsets: list[int | None]) -> dict[str, Any]:
    """first appearance day stats + cumulative."""
    hits = [d for d in first_offsets if d is not None]
    by_d = Counter(hits)
    n = len(first_offsets)
    n_hit = len(hits)
    out = {
        "activations": n,
        "with_exact": n_hit,
        "without_exact": n - n_hit,
        "by_day": {f"D+{d}": by_d.get(d, 0) for d in range(1, 8)},
        "by_day_pct_of_hits": {f"D+{d}": pct(by_d.get(d, 0), n_hit) for d in range(1, 8)},
        "by_day_pct_of_activations": {
            f"D+{d}": pct(by_d.get(d, 0), n) for d in range(1, 8)
        },
        "cumulative": {},
    }
    cum = 0
    for d in range(1, 8):
        cum += by_d.get(d, 0)
        out["cumulative"][f"D+1–D+{d}" if d > 1 else "D+1"] = {
            "count": cum,
            "pct_of_activations": pct(cum, n),
            "pct_of_hits": pct(cum, n_hit),
        }
    return out


__all__ = [
    "PERIOD_FROM",
    "PERIOD_TO",
    "METHODOLOGY_VERSION",
    "LABELS",
    "OfficialChain",
    "FutureAppearance",
    "new_audit_id",
    "t1_code_of",
    "t2_code_of",
    "t1_group_ordered",
    "t1_candidates_from_observed",
    "t2_group_ordered",
    "position_in_group",
    "positional_distance",
    "enumerate_official_chains",
    "collect_future",
    "chain_hop_closures",
    "classify_appearance",
    "consistency_level",
    "pct",
    "matrix_with_margins",
    "accumulate_first_hit_days",
    "strengthen_official",
    "ObservedNumber",
]
