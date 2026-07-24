"""Fase B — análisis histórico, scoring, exclusiones, ranking, trazabilidad."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from app.lottery.numeric_relations.analysis import analyze_observed_number
from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.history import InMemoryDrawHistory
from app.lottery.numeric_relations.models import DrawNumberRef, HistoricalOccurrence, OccurrenceLimit


def _occ(
    *,
    lottery_id,
    lottery_name: str,
    draw_date: date,
    observed: int,
    others: list[tuple[int, int]],
    draw_id=None,
) -> HistoricalOccurrence:
    """others: list of (position, number). Always includes observed at position 1."""
    refs = [DrawNumberRef(position=1, drawn_number=observed, position_label="Primera")]
    for pos, num in others:
        refs.append(DrawNumberRef(position=pos, drawn_number=num, position_label=f"P{pos}"))
    return HistoricalOccurrence(
        lottery_id=lottery_id,
        lottery_name=lottery_name,
        draw_id=draw_id or uuid4(),
        draw_date=draw_date,
        observed_number=observed,
        draw_numbers=tuple(refs),
    )


@pytest.fixture
def catalog():
    return build_catalog(force_rebuild=True)


def test_history_searches_only_drawn_number_n_not_companions(catalog):
    lot = uuid4()
    companions = catalog.get_table1_companions(34)
    assert companions
    companion = companions[0]
    assert companion != 34

    # Draw where companion appears but NOT 34 — must NOT count as occurrence of 34
    only_companion = HistoricalOccurrence(
        lottery_id=lot,
        lottery_name="Test",
        draw_id=uuid4(),
        draw_date=date(2026, 1, 1),
        observed_number=34,  # metadata irrelevant; event is draw_numbers
        draw_numbers=(DrawNumberRef(position=1, drawn_number=companion),),
    )
    real_34 = _occ(
        lottery_id=lot,
        lottery_name="Test",
        draw_date=date(2026, 2, 1),
        observed=34,
        others=[(2, companion)],
    )
    hist = InMemoryDrawHistory([only_companion, real_34])
    found = hist.find_occurrences(34, [lot], OccurrenceLimit.all())
    assert len(found) == 1
    assert found[0].draw_date == date(2026, 2, 1)
    assert any(r.drawn_number == 34 for r in found[0].draw_numbers)


def test_n_excluded_as_confirmation(catalog):
    lot = uuid4()
    # Neighbors of some companion may theoretically include nothing about N exclusion:
    # Build draw with only N and numbers that are NOT neighbors — score should not
    # increase merely because N is present.
    companions = catalog.get_table1_companions(34)
    c = companions[0]
    neighbors = set(catalog.get_table2_neighbors(c, exclude_self=True))
    # Pick a filler number that is not a neighbor and not N
    filler = next(x for x in range(1, 101) if x not in neighbors and x != 34 and x != c)
    occ = _occ(
        lottery_id=lot,
        lottery_name="Test",
        draw_date=date(2026, 3, 1),
        observed=34,
        others=[(2, filler)],
    )
    hist = InMemoryDrawHistory([occ])
    result = analyze_observed_number(
        34, [lot], OccurrenceLimit.all(), history=hist, catalog=catalog
    )
    cand = next(x for x in result.candidates if x.number == c)
    assert cand.score == 0
    # N never appears as matched neighbor
    for cand in result.candidates:
        assert 34 not in cand.matched_neighbors


def test_exclude_self_and_strengthen_companion_not_neighbor(catalog):
    lot = uuid4()
    c = 1
    assert 1 in catalog.get_table1_companions(34)
    neighbors = catalog.get_table2_neighbors(c, exclude_self=True)
    assert c not in neighbors
    assert neighbors, "companion 1 should have neighbors in table 2"
    v = neighbors[0]
    occ = _occ(
        lottery_id=lot,
        lottery_name="Leidsa",
        draw_date=date(2026, 4, 1),
        observed=34,
        others=[(2, v)],
    )
    result = analyze_observed_number(
        34,
        [lot],
        OccurrenceLimit.all(),
        history=InMemoryDrawHistory([occ]),
        catalog=catalog,
    )
    by_num = {x.number: x for x in result.candidates}
    assert by_num[c].score >= 1
    assert v in by_num[c].matched_neighbors
    # Neighbor is not a strengthened candidate unless it is also a companion of 34
    if v not in catalog.get_table1_companions(34):
        assert v not in by_num or by_num[v].score == 0 or v not in by_num[v].matched_neighbors
    # Explicit: we never add score to the neighbor row for being the match target
    # Strength goes to companion c only for this match
    assert all(m.companion == c for m in by_num[c].matches if m.neighbor == v)


def test_multiple_neighbors_same_draw_sum_multiple_points(catalog):
    lot = uuid4()
    # Real catalog: companion of mother 26 with ≥3 neighbors (not equal to mother)
    mother = 26
    companion = 27
    assert companion in catalog.get_table1_companions(mother)
    neighbors = [x for x in catalog.get_table2_neighbors(companion, exclude_self=True) if x != mother]
    assert len(neighbors) >= 3
    trio = neighbors[:3]
    occ = _occ(
        lottery_id=lot,
        lottery_name="Leidsa",
        draw_date=date(2026, 5, 1),
        observed=mother,
        others=[(2, trio[0]), (3, trio[1]), (4, trio[2])],
    )
    result = analyze_observed_number(
        mother,
        [lot],
        OccurrenceLimit.all(),
        history=InMemoryDrawHistory([occ]),
        catalog=catalog,
    )
    cand = next(x for x in result.candidates if x.number == companion)
    assert cand.score == 3
    assert set(cand.matched_neighbors) == set(trio)
    # Neighbors themselves are not awarded those points as targets
    for v in trio:
        if v in catalog.get_table1_companions(mother):
            continue
        assert all(m.companion == companion for m in cand.matches if m.neighbor == v)


def test_scores_accumulate_across_draws_and_dedupe(catalog):
    lot = uuid4()
    c = 1
    v = catalog.get_table2_neighbors(c, exclude_self=True)[0]
    draw_id = uuid4()
    occ1 = _occ(
        lottery_id=lot,
        lottery_name="A",
        draw_date=date(2026, 6, 1),
        observed=34,
        others=[(2, v)],
        draw_id=draw_id,
    )
    # Exact same event duplicated in history feed
    occ1_dup = _occ(
        lottery_id=lot,
        lottery_name="A",
        draw_date=date(2026, 6, 1),
        observed=34,
        others=[(2, v)],
        draw_id=draw_id,
    )
    occ2 = _occ(
        lottery_id=lot,
        lottery_name="A",
        draw_date=date(2026, 6, 8),
        observed=34,
        others=[(2, v)],
    )
    result = analyze_observed_number(
        34,
        [lot],
        OccurrenceLimit.all(),
        history=InMemoryDrawHistory([occ1, occ1_dup, occ2]),
        catalog=catalog,
    )
    cand = next(x for x in result.candidates if x.number == c)
    # Two distinct draws → +2; duplicate event not double-counted
    assert cand.score == 2
    assert len(cand.matches) == 2


def test_all_companions_ranked_including_zero(catalog):
    lot = uuid4()
    companions = catalog.get_table1_companions(34)
    occ = _occ(
        lottery_id=lot,
        lottery_name="A",
        draw_date=date(2026, 7, 1),
        observed=34,
        others=[(2, 99)],  # unlikely neighbor noise; still full ranking
    )
    result = analyze_observed_number(
        34,
        [lot],
        OccurrenceLimit.all(),
        history=InMemoryDrawHistory([occ]),
        catalog=catalog,
    )
    assert len(result.candidates) == len(companions)
    assert result.direct_companions == companions
    scores = [c.score for c in result.candidates]
    assert scores == sorted(scores, reverse=True)
    # at least the zero-score companions present
    assert any(c.score == 0 for c in result.candidates)


def test_trace_contains_full_path(catalog):
    lot = uuid4()
    c = 1
    v = catalog.get_table2_neighbors(c, exclude_self=True)[0]
    occ = _occ(
        lottery_id=lot,
        lottery_name="Quiniela Leidsa",
        draw_date=date(2026, 7, 10),
        observed=34,
        others=[(2, v)],
    )
    result = analyze_observed_number(
        34,
        [lot],
        OccurrenceLimit.all(),
        history=InMemoryDrawHistory([occ]),
        catalog=catalog,
    )
    cand = next(x for x in result.candidates if x.number == c)
    assert cand.matches
    tr = cand.matches[0].trace
    for needle in (
        "salió 34",
        "ocurrencia histórica real",
        "código madre 34",
        f"compañero {c}",
        "código Tabla 2",
        "grupo Tabla 2",
        "vecinos",
        f"vecino encontrado {v}",
        "Quiniela Leidsa",
        "2026-07-10",
        f"compañero {c}",
    ):
        assert needle in tr, needle


def test_lottery_scope_not_mixed(catalog):
    lot_a, lot_b = uuid4(), uuid4()
    c = 1
    v = catalog.get_table2_neighbors(c, exclude_self=True)[0]
    occ_a = _occ(lottery_id=lot_a, lottery_name="A", draw_date=date(2026, 8, 1), observed=34, others=[(2, v)])
    occ_b = _occ(lottery_id=lot_b, lottery_name="B", draw_date=date(2026, 8, 2), observed=34, others=[(2, v)])
    result = analyze_observed_number(
        34,
        [lot_a],
        OccurrenceLimit.all(),
        history=InMemoryDrawHistory([occ_a, occ_b]),
        catalog=catalog,
    )
    cand = next(x for x in result.candidates if x.number == c)
    assert cand.score == 1
    assert all(str(m.lottery_id) == str(lot_a) for m in cand.matches)


def test_occurrence_limit_last_k(catalog):
    lot = uuid4()
    c = 1
    v = catalog.get_table2_neighbors(c, exclude_self=True)[0]
    occs = [
        _occ(lottery_id=lot, lottery_name="A", draw_date=date(2026, 1, d), observed=34, others=[(2, v)])
        for d in (1, 2, 3, 4, 5)
    ]
    result = analyze_observed_number(
        34,
        [lot],
        OccurrenceLimit.last_k(2),
        history=InMemoryDrawHistory(occs),
        catalog=catalog,
    )
    assert result.occurrences_found == 5
    assert result.occurrences_used == 2
    cand = next(x for x in result.candidates if x.number == c)
    assert cand.score == 2
