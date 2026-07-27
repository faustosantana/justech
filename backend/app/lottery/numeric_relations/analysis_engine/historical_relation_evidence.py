"""Historical relation evidence for Complete Analysis (explanatory layer only).

Does NOT change Tabla 1 / Tabla 2 formulas or ranking weights.
Tabla 1 remains the primary candidate source; history describes past behaviour.

Windows: same_day_after, next_draw, D+1, D+2, D+3, D+7
(calendar days AND posterior draw counts are both recorded).

Similarity levels:
  1 exact pair X+Y → C
  2 same X, any Y confirming C via T2
  3 structural group (any T1 origin in mother group of X, any T2 confirmer of C)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from statistics import mean, median
from typing import Any, Iterable, Sequence

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog

POS_KEYS = ("primera", "segunda", "tercera")
POS_LABEL = {"primera": "primera", "segunda": "segunda", "tercera": "tercera", 1: "primera", 2: "segunda", 3: "tercera"}

RESULT_EXACT = "ACIERTO_CANDIDATO_EXACTO"
RESULT_T1 = "ACIERTO_FAMILIA_T1"
RESULT_T2 = "ACIERTO_VECINO_T2"
RESULT_ALT = "ACIERTO_ALTERNATIVA"
RESULT_NONE = "SIN_COINCIDENCIA"
RESULT_PENDING = "PENDIENTE"

RESULT_LABELS = {
    RESULT_EXACT: "Candidato exacto",
    RESULT_T1: "Compañero de Tabla 1",
    RESULT_T2: "Vecino de Tabla 2",
    RESULT_ALT: "Alternativa",
    RESULT_NONE: "Sin coincidencia",
    RESULT_PENDING: "Pendiente",
}

EVIDENCE_QUANTITY = (
    (0, 4, "insuficiente", "Existe poca evidencia histórica para esta combinación."),
    (5, 14, "limitada", "La evidencia histórica es limitada."),
    (15, 29, "moderada", "La evidencia histórica es moderada."),
    (30, 10_000_000, "amplia", "La evidencia histórica es amplia."),
)

WINDOWS = ("same_day_after", "next_draw", "d1", "d2", "d3", "d7")
WINDOW_DAYS = {"d1": 1, "d2": 2, "d3": 3, "d7": 7}


def _parse_num(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        n = int(str(raw).lstrip("0") or "0")
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 100 else None


def evidence_quantity_label(n_cases: int) -> tuple[str, str]:
    for lo, hi, key, msg in EVIDENCE_QUANTITY:
        if lo <= n_cases <= hi:
            return key, msg
    return "insuficiente", EVIDENCE_QUANTITY[0][3]


def result_label(code: str) -> str:
    return RESULT_LABELS.get(code, code)


@dataclass
class DayNumberHit:
    number: int
    lottery: str
    lottery_id: str | None
    position: str
    draw_id: str | None
    date: str


@dataclass
class DaySnapshot:
    date: str
    hits: list[DayNumberHit] = field(default_factory=list)
    by_number: dict[int, list[DayNumberHit]] = field(default_factory=dict)

    def numbers(self, *, positions: Sequence[str] | None = None) -> set[int]:
        if not positions:
            return set(self.by_number)
        wanted = {POS_LABEL.get(p, str(p)) for p in positions}
        out: set[int] = set()
        for n, rows in self.by_number.items():
            if any(h.position in wanted for h in rows):
                out.add(n)
        return out


@dataclass
class HistoricalRelationCase:
    date: str
    origin_x: int
    confirmer_y: int
    candidate_c: int
    lottery_x: str | None
    position_x: str | None
    lottery_y: str | None
    position_y: str | None
    table1_route: str
    table2_route: str
    similarity_level: int
    lotteries_reviewed: list[str] = field(default_factory=list)
    same_day_numbers: list[int] = field(default_factory=list)
    posterior_draws_evaluated: int = 0
    result_type: str = RESULT_PENDING
    result_label: str = RESULT_LABELS[RESULT_PENDING]
    result_number: int | None = None
    result_lottery: str | None = None
    result_position: str | None = None
    result_date: str | None = None
    days_elapsed: int | None = None
    draws_elapsed: int | None = None
    window_hit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateHistoricalMetrics:
    candidate_number: int
    exact_cases: int = 0
    evaluable_cases: int = 0
    exact_hits: int = 0
    t1_family_hits: int = 0
    t2_neighbor_hits: int = 0
    alternative_hits: int = 0
    no_match: int = 0
    pending: int = 0
    exact_hit_rate: float | None = None
    expanded_support_rate: float | None = None
    d1_hits: int = 0
    d3_hits: int = 0
    d7_hits: int = 0
    median_draws_to_hit: float | None = None
    mean_days_to_hit: float | None = None
    top_lotteries: list[dict[str, Any]] = field(default_factory=list)
    top_positions: list[dict[str, Any]] = field(default_factory=list)
    recent_cases: list[dict[str, Any]] = field(default_factory=list)
    evidence_quantity: str = "insuficiente"
    evidence_quantity_message: str = EVIDENCE_QUANTITY[0][3]
    structural_cases: int = 0
    level2_cases: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateEvidenceCard:
    candidate_number: int
    table1_support: bool
    table2_support: bool
    same_day_cross_support: bool
    independent_lotteries: int
    independent_positions: int
    independent_routes: int
    exact_historical_cases: int
    structural_historical_cases: int
    exact_hits: int
    t1_family_hits: int
    t2_neighbor_hits: int
    d1_hits: int
    d3_hits: int
    d7_hits: int
    recent_cases: list[dict[str, Any]]
    evidence_quantity: str
    evidence_quality: str
    final_explanation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_day_index(
    rows: Iterable[dict[str, Any]],
    *,
    positions: Sequence[str] | None = None,
) -> dict[str, DaySnapshot]:
    """Index flat result rows (primera/segunda/tercera) by calendar date."""
    allow = None
    if positions:
        allow = {POS_LABEL.get(p, str(p)) for p in positions}
        # accept first/second/third aliases
        alias = {"first": "primera", "second": "segunda", "third": "tercera"}
        allow |= {alias.get(p, p) for p in positions if isinstance(p, str)}

    by_date: dict[str, DaySnapshot] = {}
    for row in rows:
        d = str(row.get("date") or row.get("draw_date") or "")[:10]
        if not d:
            continue
        lot = str(row.get("lottery") or row.get("lottery_name") or "—")
        lot_id = row.get("lottery_id")
        draw_id = row.get("draw_id") or row.get("id")
        snap = by_date.get(d)
        if snap is None:
            snap = DaySnapshot(date=d)
            by_date[d] = snap
        for key in POS_KEYS:
            if allow is not None and key not in allow:
                continue
            n = _parse_num(row.get(key))
            if n is None:
                continue
            hit = DayNumberHit(
                number=n,
                lottery=lot,
                lottery_id=str(lot_id) if lot_id else None,
                position=key,
                draw_id=str(draw_id) if draw_id else None,
                date=d,
            )
            snap.hits.append(hit)
            snap.by_number.setdefault(n, []).append(hit)
    return dict(sorted(by_date.items(), key=lambda kv: kv[0]))


def _sorted_dates(day_index: dict[str, DaySnapshot]) -> list[str]:
    return sorted(day_index.keys())


def _dates_after(all_dates: Sequence[str], anchor: str) -> list[str]:
    return [d for d in all_dates if d > anchor]


def _find_hit_appearance(
    day_index: dict[str, DaySnapshot],
    dates: Sequence[str],
    targets: set[int],
    *,
    max_calendar_days: int | None,
    anchor: str,
) -> tuple[DayNumberHit | None, int, int]:
    """Return (hit, days_elapsed, draws_elapsed) for first matching target."""
    draws = 0
    anchor_d = date.fromisoformat(anchor)
    for d in dates:
        draws += 1
        days = (date.fromisoformat(d) - anchor_d).days
        if max_calendar_days is not None and days > max_calendar_days:
            break
        snap = day_index.get(d)
        if not snap:
            continue
        for n in targets:
            if n in snap.by_number:
                return snap.by_number[n][0], days, draws
    return None, 0, draws


def _window_name(days: int | None, draws: int | None, *, same_day: bool) -> str:
    if same_day:
        return "same_day_after"
    if draws == 1:
        return "next_draw"
    if days is None:
        return "next_draw"
    if days <= 1:
        return "d1"
    if days <= 2:
        return "d2"
    if days <= 3:
        return "d3"
    if days <= 7:
        return "d7"
    return f"d{days}"


def _classify_posterior(
    *,
    candidate_c: int,
    origin_x: int,
    catalog: TableCatalog,
    alternatives: Sequence[int],
    day_index: dict[str, DaySnapshot],
    all_dates: Sequence[str],
    anchor: str,
    max_days: int = 7,
) -> dict[str, Any]:
    after = _dates_after(all_dates, anchor)
    if not after:
        return {
            "result_type": RESULT_PENDING,
            "result_label": result_label(RESULT_PENDING),
            "posterior_draws_evaluated": 0,
        }

    t1_family = set(catalog.get_table1_companions(origin_x)) - {candidate_c, origin_x}
    t2_neighbors = set(catalog.get_table2_neighbors(candidate_c, exclude_self=True))
    alt_set = set(int(a) for a in alternatives) - {candidate_c}

    # Priority: exact C, then T1 family, then T2 neighbor, then alternative
    for targets, rtype in (
        ({candidate_c}, RESULT_EXACT),
        (t1_family, RESULT_T1),
        (t2_neighbors, RESULT_T2),
        (alt_set, RESULT_ALT),
    ):
        if not targets:
            continue
        hit, days, draws = _find_hit_appearance(
            day_index, after, targets, max_calendar_days=max_days, anchor=anchor
        )
        if hit is None:
            continue
        return {
            "result_type": rtype,
            "result_label": result_label(rtype),
            "result_number": hit.number,
            "result_lottery": hit.lottery,
            "result_position": hit.position,
            "result_date": hit.date,
            "days_elapsed": days,
            "draws_elapsed": draws,
            "window_hit": _window_name(days, draws, same_day=False),
            "posterior_draws_evaluated": draws,
        }

    # No hit within window — count how many posterior dates were scanned
    scanned = 0
    anchor_d = date.fromisoformat(anchor)
    for d in after:
        days = (date.fromisoformat(d) - anchor_d).days
        if days > max_days:
            break
        scanned += 1
    return {
        "result_type": RESULT_NONE,
        "result_label": result_label(RESULT_NONE),
        "posterior_draws_evaluated": scanned,
        "days_elapsed": None,
        "draws_elapsed": None,
    }


def _pick_appearance(hits: list[DayNumberHit]) -> DayNumberHit:
    # Prefer primera when multiple positions same day
    for pref in POS_KEYS:
        for h in hits:
            if h.position == pref:
                return h
    return hits[0]


def find_relation_cases(
    day_index: dict[str, DaySnapshot],
    *,
    origin_x: int,
    confirmer_y: int | None,
    candidate_c: int,
    catalog: TableCatalog | None = None,
    alternatives: Sequence[int] | None = None,
    similarity_level: int = 1,
    max_days: int = 7,
) -> list[HistoricalRelationCase]:
    cat = catalog or build_catalog()
    alts = list(alternatives or [])
    dates = _sorted_dates(day_index)
    t2_of_c = set(cat.get_table2_neighbors(candidate_c, exclude_self=True))
    # Mother-group peers of X (numbers that share X as mother code companions)
    mother_peers = set(cat.get_table1_companions(origin_x)) | {origin_x}
    # Also include other mothers that list C as companion — structural L3
    structural_origins = {origin_x}
    for code, members in cat.table1_code_to_numbers.items():
        if candidate_c in members:
            structural_origins.add(int(code))
            structural_origins.update(int(m) for m in members)

    out: list[HistoricalRelationCase] = []
    for d in dates:
        snap = day_index[d]
        nums = set(snap.by_number)

        if similarity_level == 1:
            if confirmer_y is None:
                continue
            if origin_x not in nums or confirmer_y not in nums:
                continue
            if confirmer_y not in t2_of_c:
                # Exact pair must still form the T1×T2 route to C
                continue
            if candidate_c not in cat.get_table1_companions(origin_x):
                continue
            origins = [origin_x]
            confirmers = [confirmer_y]
            level = 1
        elif similarity_level == 2:
            if origin_x not in nums:
                continue
            if candidate_c not in cat.get_table1_companions(origin_x):
                continue
            confirmers = sorted(n for n in nums if n in t2_of_c and n != origin_x)
            if confirmer_y is not None:
                # Prefer listing exact confirmer first but allow others
                confirmers = sorted(confirmers, key=lambda n: (0 if n == confirmer_y else 1, n))
            if not confirmers:
                continue
            origins = [origin_x]
            level = 2
        else:
            origins = sorted(n for n in nums if n in structural_origins)
            confirmers = sorted(n for n in nums if n in t2_of_c)
            if not origins or not confirmers:
                continue
            level = 3

        for x in origins:
            companions = set(cat.get_table1_companions(x))
            if candidate_c not in companions:
                continue
            for y in confirmers:
                if y == x:
                    continue
                if y not in t2_of_c:
                    continue
                ax = _pick_appearance(snap.by_number[x])
                ay = _pick_appearance(snap.by_number[y])
                post = _classify_posterior(
                    candidate_c=candidate_c,
                    origin_x=x,
                    catalog=cat,
                    alternatives=alts,
                    day_index=day_index,
                    all_dates=dates,
                    anchor=d,
                    max_days=max_days,
                )
                case = HistoricalRelationCase(
                    date=d,
                    origin_x=x,
                    confirmer_y=y,
                    candidate_c=candidate_c,
                    lottery_x=ax.lottery,
                    position_x=ax.position,
                    lottery_y=ay.lottery,
                    position_y=ay.position,
                    table1_route=f"{x} → Tabla 1 → {candidate_c}",
                    table2_route=f"{y} → Tabla 2 → {candidate_c}",
                    similarity_level=level,
                    lotteries_reviewed=sorted({h.lottery for h in snap.hits}),
                    same_day_numbers=sorted(nums),
                    posterior_draws_evaluated=int(post.get("posterior_draws_evaluated") or 0),
                    result_type=str(post.get("result_type") or RESULT_PENDING),
                    result_label=str(post.get("result_label") or result_label(RESULT_PENDING)),
                    result_number=post.get("result_number"),
                    result_lottery=post.get("result_lottery"),
                    result_position=post.get("result_position"),
                    result_date=post.get("result_date"),
                    days_elapsed=post.get("days_elapsed"),
                    draws_elapsed=post.get("draws_elapsed"),
                    window_hit=post.get("window_hit"),
                )
                out.append(case)
    # Deduplicate same date+x+y+c+level (one case per relation/day)
    seen: set[tuple] = set()
    unique: list[HistoricalRelationCase] = []
    for c in out:
        key = (c.date, c.origin_x, c.confirmer_y, c.candidate_c, c.similarity_level)
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    unique.sort(key=lambda c: c.date, reverse=True)
    return unique


def aggregate_metrics(
    cases: Sequence[HistoricalRelationCase],
    *,
    candidate_c: int,
    structural_cases: int = 0,
    level2_cases: int = 0,
) -> CandidateHistoricalMetrics:
    exact = [c for c in cases if c.similarity_level == 1]
    pool = exact if exact else list(cases)
    evaluable = [c for c in pool if c.result_type != RESULT_PENDING]
    exact_hits = [c for c in evaluable if c.result_type == RESULT_EXACT]
    t1_hits = [c for c in evaluable if c.result_type == RESULT_T1]
    t2_hits = [c for c in evaluable if c.result_type == RESULT_T2]
    alt_hits = [c for c in evaluable if c.result_type == RESULT_ALT]
    none_hits = [c for c in evaluable if c.result_type == RESULT_NONE]
    pending = [c for c in pool if c.result_type == RESULT_PENDING]

    def _rate(num: int, den: int) -> float | None:
        if den <= 0:
            return None
        return round(100.0 * num / den, 1)

    expanded = len(exact_hits) + len(t1_hits) + len(t2_hits)
    draws_list = [c.draws_elapsed for c in exact_hits + t1_hits + t2_hits if c.draws_elapsed]
    days_list = [c.days_elapsed for c in exact_hits + t1_hits + t2_hits if c.days_elapsed is not None]

    lot_counter: Counter[str] = Counter()
    pos_counter: Counter[str] = Counter()
    for c in exact_hits + t1_hits + t2_hits:
        if c.result_lottery:
            lot_counter[c.result_lottery] += 1
        if c.result_position:
            pos_counter[c.result_position] += 1

    def _in_window(c: HistoricalRelationCase, max_d: int) -> bool:
        return c.days_elapsed is not None and c.days_elapsed <= max_d and c.result_type == RESULT_EXACT

    qty, qty_msg = evidence_quantity_label(len(pool))
    recent = []
    for c in pool[:12]:
        recent.append(
            {
                "date": c.date,
                "observed": [c.origin_x, c.confirmer_y],
                "candidate": c.candidate_c,
                "result": c.result_label,
                "result_number": c.result_number,
                "window": c.window_hit,
                "lottery_result": c.result_lottery,
                "similarity_level": c.similarity_level,
            }
        )

    return CandidateHistoricalMetrics(
        candidate_number=candidate_c,
        exact_cases=len(exact) if exact else len([c for c in cases if c.similarity_level == 1]),
        evaluable_cases=len(evaluable),
        exact_hits=len(exact_hits),
        t1_family_hits=len(t1_hits),
        t2_neighbor_hits=len(t2_hits),
        alternative_hits=len(alt_hits),
        no_match=len(none_hits),
        pending=len(pending),
        exact_hit_rate=_rate(len(exact_hits), len(evaluable)),
        expanded_support_rate=_rate(expanded, len(evaluable)),
        d1_hits=sum(1 for c in evaluable if _in_window(c, 1)),
        d3_hits=sum(1 for c in evaluable if _in_window(c, 3)),
        d7_hits=sum(1 for c in evaluable if _in_window(c, 7)),
        median_draws_to_hit=float(median(draws_list)) if draws_list else None,
        mean_days_to_hit=round(float(mean(days_list)), 2) if days_list else None,
        top_lotteries=[{"lottery": k, "count": v} for k, v in lot_counter.most_common(5)],
        top_positions=[{"position": k, "count": v} for k, v in pos_counter.most_common(5)],
        recent_cases=recent,
        evidence_quantity=qty,
        evidence_quantity_message=qty_msg,
        structural_cases=structural_cases,
        level2_cases=level2_cases,
    )


def build_evidence_card(
    *,
    candidate_number: int,
    table1_sources: Sequence[int],
    table2_confirmers: Sequence[int],
    same_day_cross_support: bool,
    lotteries: Sequence[str],
    positions: Sequence[str],
    metrics: CandidateHistoricalMetrics,
    independent_routes: int,
) -> CandidateEvidenceCard:
    qty = metrics.evidence_quantity
    quality = "alta" if metrics.exact_hits >= 5 and qty in {"moderada", "amplia"} else (
        "media" if metrics.exact_hits >= 1 or qty in {"limitada", "moderada"} else "baja"
    )
    parts = []
    if table1_sources:
        parts.append(f"Tabla 1 desde {', '.join(str(x) for x in table1_sources)}")
    if table2_confirmers:
        parts.append(f"Tabla 2 vía {', '.join(str(x) for x in table2_confirmers)}")
    if same_day_cross_support:
        parts.append("cruce del mismo día")
    if metrics.exact_cases:
        parts.append(f"{metrics.exact_cases} casos históricos equivalentes")
    explanation = (
        f"El {candidate_number} acumula evidencia de {', '.join(parts)}."
        if parts
        else f"El {candidate_number} no acumula evidencia estructural suficiente."
    )
    return CandidateEvidenceCard(
        candidate_number=candidate_number,
        table1_support=bool(table1_sources),
        table2_support=bool(table2_confirmers),
        same_day_cross_support=bool(same_day_cross_support),
        independent_lotteries=len({x for x in lotteries if x}),
        independent_positions=len({x for x in positions if x}),
        independent_routes=int(independent_routes),
        exact_historical_cases=metrics.exact_cases,
        structural_historical_cases=metrics.structural_cases,
        exact_hits=metrics.exact_hits,
        t1_family_hits=metrics.t1_family_hits,
        t2_neighbor_hits=metrics.t2_neighbor_hits,
        d1_hits=metrics.d1_hits,
        d3_hits=metrics.d3_hits,
        d7_hits=metrics.d7_hits,
        recent_cases=list(metrics.recent_cases),
        evidence_quantity=qty,
        evidence_quality=quality,
        final_explanation=explanation,
    )


def compare_candidates_text(primary: CandidateEvidenceCard, rival: CandidateEvidenceCard) -> str:
    if primary.table1_support and not rival.table1_support:
        return (
            f"{primary.candidate_number} supera a {rival.candidate_number} porque posee respaldo "
            f"de Tabla 1, confirmación de Tabla 2"
            f"{' y evidencia histórica equivalente' if primary.exact_historical_cases else ''} "
            f", mientras que {rival.candidate_number} solo tiene una relación directa de Tabla 2."
            if rival.table2_support
            else (
                f"{primary.candidate_number} supera a {rival.candidate_number} por respaldo de Tabla 1 "
                f"y confirmación de Tabla 2; {rival.candidate_number} carece de esa estructura."
            )
        )
    return (
        f"{primary.candidate_number} concentra más evidencia estructural e histórica "
        f"({primary.exact_historical_cases} casos, {primary.exact_hits} aciertos exactos) "
        f"frente a {rival.candidate_number} ({rival.exact_historical_cases} casos, "
        f"{rival.exact_hits} aciertos exactos)."
    )


def build_historical_narrative(
    *,
    origin_x: int,
    confirmer_y: int | None,
    candidate_c: int,
    metrics: CandidateHistoricalMetrics,
    period_label: str,
    primary_card: CandidateEvidenceCard | None = None,
    rival_card: CandidateEvidenceCard | None = None,
    same_day_lotteries: Sequence[str] | None = None,
) -> dict[str, str]:
    conf = confirmer_y
    conclusion = (
        f"{candidate_c} es el número fortalecido porque el {origin_x} lo relaciona mediante Tabla 1"
        + (
            f" y el {conf}, salido en otra lotería el mismo día, lo confirma mediante Tabla 2."
            if conf is not None
            else "."
        )
    )
    ind = primary_card.independent_routes if primary_card else 0
    lots = primary_card.independent_lotteries if primary_card else len(same_day_lotteries or [])
    evidence_now = (
        f"Acumuló {max(ind, 1)} evidencias independientes provenientes de Tabla 1, Tabla 2"
        f"{f' y {lots} loterías diferentes' if lots else ''}."
        if primary_card and (primary_card.table1_support or primary_card.table2_support)
        else "La evidencia actual proviene del análisis estructural del motor."
    )

    if metrics.exact_cases < 5 and metrics.level2_cases == 0:
        historical = metrics.evidence_quantity_message + f" Período: {period_label}."
    else:
        n = metrics.exact_cases or metrics.evaluable_cases
        historical = (
            f"En {n} casos históricos equivalentes (período: {period_label}), "
            f"el {candidate_c} apareció {metrics.exact_hits} veces dentro de los siguientes 7 días"
        )
        if metrics.t1_family_hits:
            historical += (
                f". En otros {metrics.t1_family_hits} casos apareció un compañero de su misma "
                f"familia de Tabla 1"
            )
        if metrics.t2_neighbor_hits:
            historical += (
                f". En {metrics.t2_neighbor_hits} casos apareció un vecino de Tabla 2"
            )
        historical += "."

    comparison = ""
    if primary_card and rival_card:
        comparison = compare_candidates_text(primary_card, rival_card)

    warning = (
        "El histórico describe comportamientos anteriores y no garantiza que el resultado "
        "vuelva a repetirse."
    )
    return {
        "conclusion": conclusion,
        "evidence_current": evidence_now,
        "historical_behavior": historical,
        "comparison": comparison,
        "warning": warning,
    }


def flat_rows_from_draw_refs(draws: Sequence[Any]) -> list[dict[str, Any]]:
    """Convert DrawRef-like objects into flatten_draw-compatible rows."""
    rows: list[dict[str, Any]] = []
    for d in draws:
        date_s = d.draw_date.isoformat() if hasattr(d.draw_date, "isoformat") else str(d.draw_date)[:10]
        row: dict[str, Any] = {
            "date": date_s,
            "lottery": getattr(d, "lottery_name", None) or str(getattr(d, "lottery_id", "")),
            "lottery_id": str(getattr(d, "lottery_id", "") or ""),
            "draw_id": str(getattr(d, "draw_id", "") or ""),
            "primera": None,
            "segunda": None,
            "tercera": None,
        }
        for pos, val in getattr(d, "numbers", ()) or ():
            try:
                p = int(pos)
                n = int(val)
            except (TypeError, ValueError):
                continue
            key = {1: "primera", 2: "segunda", 3: "tercera"}.get(p)
            if key:
                row[key] = f"{n:02d}" if n <= 99 else str(n)
        rows.append(row)
    return rows


def resolve_period_bounds(
    period: str | None,
    *,
    today: date | None = None,
) -> tuple[date | None, date, str]:
    """Return (from_date|None, to_date, label). None from_date = full history."""
    to_d = today or date.today()
    p = (period or "all").strip().lower()
    if p in {"all", "todo", "full", "todo_el_historico", "todo_el_histórico"}:
        return None, to_d, "Todo el histórico"
    years = {"5y": 5, "5": 5, "ultimos_5": 5, "3y": 3, "3": 3, "ultimos_3": 3, "1y": 1, "1": 1, "ultimo_ano": 1}
    y = years.get(p)
    if y:
        return to_d - timedelta(days=365 * y + y // 4), to_d, f"Últimos {y} años"
    return None, to_d, "Todo el histórico"


def analyze_historical_relations(
    rows: Sequence[dict[str, Any]],
    *,
    origin_x: int,
    confirmer_y: int | None,
    candidate_c: int,
    alternatives: Sequence[int] | None = None,
    catalog: TableCatalog | None = None,
    period: str | None = "all",
    positions: Sequence[str] | None = None,
    primary_meta: dict[str, Any] | None = None,
    rival_meta: dict[str, Any] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Main entry — deterministic historical evidence package for one candidate."""
    cat = catalog or build_catalog()
    from_d, to_d, period_label = resolve_period_bounds(period, today=today)
    filtered = []
    min_date = None
    max_date = None
    for row in rows:
        d = str(row.get("date") or "")[:10]
        if not d:
            continue
        try:
            dd = date.fromisoformat(d)
        except ValueError:
            continue
        if from_d and dd < from_d:
            continue
        if dd > to_d:
            continue
        filtered.append(row)
        min_date = dd if min_date is None or dd < min_date else min_date
        max_date = dd if max_date is None or dd > max_date else max_date

    # Default: all three positions for co-occurrence and hits
    day_index = build_day_index(filtered, positions=positions)

    level1 = find_relation_cases(
        day_index,
        origin_x=origin_x,
        confirmer_y=confirmer_y,
        candidate_c=candidate_c,
        catalog=cat,
        alternatives=alternatives,
        similarity_level=1,
    )
    level2 = find_relation_cases(
        day_index,
        origin_x=origin_x,
        confirmer_y=confirmer_y,
        candidate_c=candidate_c,
        catalog=cat,
        alternatives=alternatives,
        similarity_level=2,
    )
    level3 = find_relation_cases(
        day_index,
        origin_x=origin_x,
        confirmer_y=confirmer_y,
        candidate_c=candidate_c,
        catalog=cat,
        alternatives=alternatives,
        similarity_level=3,
    )

    # Prefer exact; if insufficient, surface level2 in metrics but keep L3 separate
    primary_cases = level1 if len(level1) >= 5 or not level2 else level1
    if len(level1) < 5 and level2:
        # Use level2 only for expanded view; exact metrics stay on level1
        pass

    metrics = aggregate_metrics(
        level1,
        candidate_c=candidate_c,
        structural_cases=len(level3),
        level2_cases=len(level2),
    )
    # If exact empty, report level2 counts in evaluable narrative fields carefully
    if not level1 and level2:
        metrics_l2 = aggregate_metrics(
            level2,
            candidate_c=candidate_c,
            structural_cases=len(level3),
            level2_cases=len(level2),
        )
        metrics.level2_cases = len(level2)
        metrics.structural_cases = len(level3)
        metrics.evidence_quantity = metrics_l2.evidence_quantity
        metrics.evidence_quantity_message = (
            "No hay coincidencias exactas suficientes; se muestra la ruta ampliada (mismo origen, "
            "otros confirmadores de Tabla 2). " + metrics_l2.evidence_quantity_message
        )
        metrics.recent_cases = metrics_l2.recent_cases
        # Keep exact_* at 0; attach expanded hit counts under family/t2 via level2 aggregate
        metrics.evaluable_cases = metrics_l2.evaluable_cases
        metrics.exact_hits = metrics_l2.exact_hits
        metrics.t1_family_hits = metrics_l2.t1_family_hits
        metrics.t2_neighbor_hits = metrics_l2.t2_neighbor_hits
        metrics.d1_hits = metrics_l2.d1_hits
        metrics.d3_hits = metrics_l2.d3_hits
        metrics.d7_hits = metrics_l2.d7_hits
        metrics.exact_hit_rate = metrics_l2.exact_hit_rate
        metrics.expanded_support_rate = metrics_l2.expanded_support_rate
        metrics.top_lotteries = metrics_l2.top_lotteries
        metrics.top_positions = metrics_l2.top_positions
        metrics.median_draws_to_hit = metrics_l2.median_draws_to_hit
        metrics.mean_days_to_hit = metrics_l2.mean_days_to_hit

    pm = primary_meta or {}
    primary_card = build_evidence_card(
        candidate_number=candidate_c,
        table1_sources=pm.get("table1_sources") or [origin_x],
        table2_confirmers=pm.get("table2_confirmers")
        or ([confirmer_y] if confirmer_y is not None else []),
        same_day_cross_support=bool(pm.get("same_day_cross_support", confirmer_y is not None)),
        lotteries=pm.get("lotteries") or [],
        positions=pm.get("positions") or [],
        metrics=metrics,
        independent_routes=int(pm.get("independent_routes") or 0)
        or (
            (1 if pm.get("table1_sources") or origin_x else 0)
            + (1 if pm.get("table2_confirmers") or confirmer_y else 0)
            + (1 if pm.get("same_day_cross_support") else 0)
        ),
    )

    rival_card = None
    if rival_meta and rival_meta.get("number") is not None:
        rival_n = int(rival_meta["number"])
        rival_cases = find_relation_cases(
            day_index,
            origin_x=origin_x,
            confirmer_y=confirmer_y,
            candidate_c=rival_n,
            catalog=cat,
            alternatives=alternatives,
            similarity_level=1,
        )
        # Rival without T1 route to itself from X typically yields 0 exact cases
        rival_metrics = aggregate_metrics(rival_cases, candidate_c=rival_n)
        rival_card = build_evidence_card(
            candidate_number=rival_n,
            table1_sources=rival_meta.get("table1_sources") or [],
            table2_confirmers=rival_meta.get("table2_confirmers") or [],
            same_day_cross_support=bool(rival_meta.get("same_day_cross_support")),
            lotteries=rival_meta.get("lotteries") or [],
            positions=rival_meta.get("positions") or [],
            metrics=rival_metrics,
            independent_routes=int(rival_meta.get("independent_routes") or 0)
            or (1 if rival_meta.get("table2_confirmers") else 0),
        )

    narrative = build_historical_narrative(
        origin_x=origin_x,
        confirmer_y=confirmer_y,
        candidate_c=candidate_c,
        metrics=metrics,
        period_label=period_label,
        primary_card=primary_card,
        rival_card=rival_card,
        same_day_lotteries=pm.get("lotteries") or [],
    )

    return {
        "period": period or "all",
        "period_label": period_label,
        "date_from": min_date.isoformat() if min_date else None,
        "date_to": max_date.isoformat() if max_date else (to_d.isoformat() if to_d else None),
        "origin_x": origin_x,
        "confirmer_y": confirmer_y,
        "candidate_c": candidate_c,
        "positions_policy": list(positions) if positions else list(POS_KEYS),
        "level1_cases": [c.to_dict() for c in level1[:200]],
        "level2_cases": [c.to_dict() for c in level2[:200]],
        "level3_cases": [c.to_dict() for c in level3[:100]],
        "level1_count": len(level1),
        "level2_count": len(level2),
        "level3_count": len(level3),
        "metrics": metrics.to_dict(),
        "evidence_card": primary_card.to_dict(),
        "rival_card": rival_card.to_dict() if rival_card else None,
        "comparison": narrative.get("comparison"),
        "narrative": narrative,
        "draws_indexed": sum(len(s.hits) for s in day_index.values()),
        "days_indexed": len(day_index),
        "table1_priority": True,
        "ranking_unchanged": True,
    }
