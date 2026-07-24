"""Análisis histórico de relaciones: compañeros T1 × vecinos T2 × sorteos ancla."""

from __future__ import annotations

from uuid import UUID

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.constants import N_MAX, N_MIN
from app.lottery.numeric_relations.decimal_math import validate_n
from app.lottery.numeric_relations.history import DrawHistoryPort
from app.lottery.numeric_relations.models import (
    AnalysisResult,
    HistoricalOccurrence,
    Match,
    OccurrenceLimit,
    StrengthenedCandidate,
)
from app.lottery.numeric_relations.scoring import make_dedupe_key, score_candidate
from app.lottery.numeric_relations.trace import build_candidate_trace, build_match_trace


def match_neighbors_against_draw_numbers(
    neighbors: list[int],
    draw_numbers: list[int],
    *,
    exclude_numbers: set[int],
) -> list[int]:
    """Intersección vecinos ∩ números del sorteo, excluyendo anclas (p.ej. N)."""
    peer_set = {int(x) for x in draw_numbers if N_MIN <= int(x) <= N_MAX} - {
        int(x) for x in exclude_numbers
    }
    neighbor_set = {int(x) for x in neighbors}
    return sorted(neighbor_set & peer_set)


def analyze_observed_number(
    observed_number: int,
    lottery_ids: list[UUID | str],
    limit: OccurrenceLimit,
    *,
    history: DrawHistoryPort,
    catalog: TableCatalog | None = None,
    lottery_names: dict[str, str] | None = None,
) -> AnalysisResult:
    """
    Flujo confirmado:
    salió N → ocurrencias reales drawn_number=N → N como código madre T1 →
    todos los compañeros → vecinos T2 → cruce con demás números del sorteo →
    ranking completo por score.
    """
    n = validate_n(int(observed_number))
    if not lottery_ids:
        raise ValueError("lottery_ids must not be empty")

    cat = catalog or build_catalog()
    mother_code = n
    companions = cat.get_table1_companions(mother_code)

    occurrences = history.find_occurrences(n, list(lottery_ids), limit)
    # occurrences_found: same query without truncating when last_k — approximate via all then slice
    # For accurate found count when using last_k, ask history with all if port supports; else len(used)
    if limit.mode == "last_k":
        all_occ = history.find_occurrences(n, list(lottery_ids), OccurrenceLimit.all())
        occurrences_found = len(all_occ)
        occurrences_used_list = all_occ[: int(limit.k or 0)]
    else:
        occurrences_used_list = occurrences
        occurrences_found = len(occurrences)

    names_map = {str(k): v for k, v in (lottery_names or {}).items()}
    lottery_id_strs = [str(x) for x in lottery_ids]
    lottery_name_list = [names_map.get(lid, lid) for lid in lottery_id_strs]

    historical_payload = [
        {
            "lottery_id": str(o.lottery_id),
            "lottery_name": o.lottery_name,
            "draw_id": str(o.draw_id),
            "draw_date": o.draw_date.isoformat(),
            "draw_time": o.draw_time.isoformat() if o.draw_time else None,
            "observed_number": o.observed_number,
            "draw_numbers": [
                {
                    "position": ref.position,
                    "position_label": ref.position_label,
                    "drawn_number": ref.drawn_number,
                }
                for ref in o.draw_numbers
            ],
        }
        for o in occurrences_used_list
    ]

    candidates: list[StrengthenedCandidate] = []
    for companion in companions:
        t2_code = cat.get_table2_code_for_number(companion)
        table2_group = list(cat.table2_code_to_numbers.get(t2_code, []))
        neighbors = cat.get_table2_neighbors(companion, exclude_self=True)
        matches: list[Match] = []
        seen_keys: set[str] = set()

        for occ in occurrences_used_list:
            hits = match_neighbors_against_draw_numbers(
                neighbors,
                occ.numbers_1_to_100(),
                exclude_numbers={n},
            )
            # Map neighbor → position refs in this draw (may appear multiple positions)
            for neighbor in hits:
                for ref in occ.draw_numbers:
                    if int(ref.drawn_number) != int(neighbor):
                        continue
                    if not (N_MIN <= int(ref.drawn_number) <= N_MAX):
                        continue
                    key = make_dedupe_key(
                        lottery_id=occ.lottery_id,
                        draw_id=occ.draw_id,
                        position=ref.position,
                        neighbor=neighbor,
                        companion=companion,
                    )
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    m = Match(
                        companion=companion,
                        neighbor=neighbor,
                        lottery_id=occ.lottery_id,
                        lottery_name=occ.lottery_name,
                        draw_id=occ.draw_id,
                        draw_date=occ.draw_date,
                        position=ref.position,
                        position_label=ref.position_label,
                        observed_number=n,
                        mother_code=mother_code,
                        table2_code=t2_code,
                        table2_group=list(table2_group),
                        neighbors=list(neighbors),
                        points=1,
                        dedupe_key=key,
                    )
                    m.trace = build_match_trace(m)
                    matches.append(m)

        matched_neighbors = sorted({m.neighbor for m in matches})
        score = score_candidate(matches)
        cand = StrengthenedCandidate(
            number=companion,
            table1_code=mother_code,
            table2_code=t2_code,
            table2_group=list(table2_group),
            neighbors=list(neighbors),
            matched_neighbors=matched_neighbors,
            score=score,
            matches=matches,
        )
        cand.trace = build_candidate_trace(cand, observed_number=n)
        candidates.append(cand)

    candidates.sort(key=lambda c: (-c.score, c.number))

    return AnalysisResult(
        observed_number=n,
        mother_code=mother_code,
        primary_table="table_1",
        lottery_ids=lottery_id_strs,
        lottery_names=lottery_name_list,
        occurrence_limit=limit.to_dict(),
        occurrences_found=occurrences_found,
        occurrences_used=len(occurrences_used_list),
        historical_occurrences=historical_payload,
        direct_companions=list(companions),
        candidates=candidates,
    )


def analyze_mother_code(
    mother_code: int,
    lottery_ids: list[UUID | str],
    limit: OccurrenceLimit,
    *,
    history: DrawHistoryPort,
    catalog: TableCatalog | None = None,
) -> AnalysisResult:
    """Alias: el código madre analizado es el número observado N."""
    return analyze_observed_number(
        mother_code,
        lottery_ids,
        limit,
        history=history,
        catalog=catalog,
    )
