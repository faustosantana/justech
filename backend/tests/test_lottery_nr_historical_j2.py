"""J-2 tests — agregados atómicos, combinaciones, matriz, subconjuntos."""

from __future__ import annotations

from datetime import date, time

import pytest

from app.lottery.numeric_relations.catalog import TableCatalog
from app.lottery.numeric_relations.historical.aggregates import HistoricalAggregatesService
from app.lottery.numeric_relations.historical.enums import ConfirmationWindowMode
from app.lottery.numeric_relations.historical.models import (
    ConfirmationWindowConfig,
    DrawRef,
    LotteryScope,
)
from app.lottery.numeric_relations.historical.universe import InMemoryDrawUniverse
from app.lottery.numeric_relations.models import FormattedComputation, TableKind


def _row(n: int, code: int, table: TableKind) -> FormattedComputation:
    return FormattedComputation(
        number=n,
        table=table,
        formula=f"t-{n}",
        visible_value=str(n),
        digits_without_point=str(n),
        digit_count=1,
        digit_list=(n % 10,),
        code=code,
    )


@pytest.fixture
def catalog() -> TableCatalog:
    t1 = {1: 34, 2: 34, 3: 34, 4: 34, 5: 34}
    t2 = {4: 99, 6: 99, 7: 99, 8: 99, 9: 99, 10: 99, 11: 99, 1: 1, 2: 2, 3: 3, 5: 5}
    t1g: dict[int, list[int]] = {}
    for n, c in t1.items():
        t1g.setdefault(c, []).append(n)
    t2g: dict[int, list[int]] = {}
    for n, c in t2.items():
        t2g.setdefault(c, []).append(n)
    for g in (*t1g.values(), *t2g.values()):
        g.sort()
    return TableCatalog(
        table1_rows=[_row(n, c, TableKind.TABLE_1) for n, c in t1.items()],
        table2_rows=[_row(n, c, TableKind.TABLE_2) for n, c in t2.items()],
        table1_number_to_code=t1,
        table1_code_to_numbers=t1g,
        table2_number_to_code=t2,
        table2_code_to_numbers=t2g,
    )


def _d(i: str, lid: str, day: date, nums: list[int], t: time | None = None) -> DrawRef:
    return DrawRef(
        draw_id=i,
        lottery_id=lid,
        lottery_name=lid,
        draw_date=day,
        draw_time=t or time(20, 0),
        numbers=tuple((k + 1, n) for k, n in enumerate(nums)),
    )


@pytest.fixture
def universe() -> InMemoryDrawUniverse:
    u = InMemoryDrawUniverse()
    # Two anchors with combo {6,9,11} and one with {6,9}
    u.add(_d("A1", "leidsa", date(2015, 3, 1), [34, 6, 9, 11]))
    u.add(_d("A2", "leidsa", date(2016, 4, 1), [34, 6, 9, 11]))
    u.add(_d("A3", "leidsa", date(2017, 5, 1), [34, 6, 9]))
    for a, base in [("A1", date(2015, 3, 1)), ("A2", date(2016, 4, 1)), ("A3", date(2017, 5, 1))]:
        for i in range(1, 12):
            nums = [4] if i == 1 else [80]
            u.add(_d(f"{a}F{i}", "leidsa", date(base.year, base.month, min(28, base.day + i)), nums))
    return u


def test_atomic_count_confirmer_6(catalog, universe):
    svc = HistoricalAggregatesService(universe=universe, catalog=catalog)
    scope = LotteryScope.default_follow_primary(["leidsa"])
    window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)
    out = svc.compute(observed_number=34, scope=scope, window=window, candidate=4)
    atomic = {p["pattern_key"]: p for p in out["atomic_patterns"]}
    assert atomic["34->4->6"]["event_count"] == 3
    assert atomic["34->4->9"]["event_count"] == 3
    assert atomic["34->4->11"]["event_count"] == 2


def test_combination_exact_and_pair_subset(catalog, universe):
    svc = HistoricalAggregatesService(universe=universe, catalog=catalog)
    scope = LotteryScope.default_follow_primary(["leidsa"])
    window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)
    out = svc.compute(observed_number=34, scope=scope, window=window, candidate=4)
    combos = {p["confirmers_key"]: p for p in out["combination_patterns"] if p["match_type"] == "exact"}
    assert combos["6,9,11"]["event_count"] == 2
    assert combos["6,9"]["event_count"] == 1
    # subset pair 6,9 should count all 3 events that contain {6,9}
    subsets = [
        p
        for p in out["combination_patterns"]
        if p["match_type"] == "subset" and p["confirmers_key"] == "6,9"
    ]
    assert subsets
    assert subsets[0]["event_count"] == 3


def test_matrix_cells(catalog, universe):
    svc = HistoricalAggregatesService(universe=universe, catalog=catalog)
    scope = LotteryScope.default_follow_primary(["leidsa"])
    window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)
    out = svc.compute(observed_number=34, scope=scope, window=window, candidate=4)
    cell = next(c for c in out["matrix"]["cells"] if c["candidate"] == 4 and c["confirmer"] == 6)
    assert cell["event_count"] == 3
    assert cell["response_rate_next_draw"]["numerator"] == 3
    assert cell["response_rate_next_draw"]["denominator"] == 3
    assert "not_probability_of_winning" in cell["response_rate_next_draw"]


def test_by_year_breakdown(catalog, universe):
    svc = HistoricalAggregatesService(universe=universe, catalog=catalog)
    scope = LotteryScope.default_follow_primary(["leidsa"])
    window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)
    out = svc.compute(
        observed_number=34,
        scope=scope,
        window=window,
        candidate=4,
        date_from=date(2015, 1, 1),
    )
    p = next(x for x in out["atomic_patterns"] if x["pattern_key"] == "34->4->6")
    assert p["by_year"]["2015"] == 1
    assert p["by_year"]["2016"] == 1
    assert p["by_year"]["2017"] == 1
