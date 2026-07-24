"""Fase B — exclusiones y validaciones de entrada."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from app.lottery.numeric_relations.analysis import analyze_observed_number
from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.decimal_math import validate_n
from app.lottery.numeric_relations.history import InMemoryDrawHistory
from app.lottery.numeric_relations.models import DrawNumberRef, HistoricalOccurrence, OccurrenceLimit


def test_validate_n_range():
    assert validate_n(1) == 1
    assert validate_n(100) == 100
    with pytest.raises(ValueError):
        validate_n(0)
    with pytest.raises(ValueError):
        validate_n(101)


def test_numbers_outside_1_100_ignored_in_peers():
    cat = build_catalog()
    lot = uuid4()
    c = 1
    v = cat.get_table2_neighbors(c, exclude_self=True)[0]
    occ = HistoricalOccurrence(
        lottery_id=lot,
        lottery_name="A",
        draw_id=uuid4(),
        draw_date=date(2026, 9, 1),
        observed_number=34,
        draw_numbers=(
            DrawNumberRef(position=1, drawn_number=34),
            DrawNumberRef(position=2, drawn_number=v),
            DrawNumberRef(position=3, drawn_number=999),  # ignored
        ),
    )
    result = analyze_observed_number(
        34,
        [lot],
        OccurrenceLimit.all(),
        history=InMemoryDrawHistory([occ]),
        catalog=cat,
    )
    cand = next(x for x in result.candidates if x.number == c)
    assert cand.score == 1
    assert 999 not in cand.matched_neighbors
