"""J-1 tests — eventos, ventanas, posterior, censura, tasas (catálogo controlado)."""

from __future__ import annotations

from datetime import date, time

import pytest

from app.lottery.numeric_relations.catalog import TableCatalog
from app.lottery.numeric_relations.historical.conditions import (
    build_events_for_anchor,
    build_historical_events,
)
from app.lottery.numeric_relations.historical.enums import ConfirmationWindowMode, SampleTier
from app.lottery.numeric_relations.historical.models import (
    ConfirmationWindowConfig,
    DrawRef,
    LotteryScope,
)
from app.lottery.numeric_relations.historical.rates import rates_payload
from app.lottery.numeric_relations.historical.sample import classify_sample, sample_warning
from app.lottery.numeric_relations.historical.service import HistoricalRelationsService
from app.lottery.numeric_relations.historical.universe import InMemoryDrawUniverse
from app.lottery.numeric_relations.models import FormattedComputation, TableKind


def _row(n: int, code: int, table: TableKind) -> FormattedComputation:
    return FormattedComputation(
        number=n,
        table=table,
        formula=f"test-{n}",
        visible_value=str(n),
        digits_without_point=str(n),
        digit_count=len(str(n)),
        digit_list=tuple(int(c) for c in str(n)),
        code=code,
    )


@pytest.fixture
def controlled_catalog() -> TableCatalog:
    """
    Observado 34 → mother_code 34 → candidatos 1,2,3,4,5 (ejemplo aprobado).
    Candidato 4 → Tabla 2 code 99 → grupo {4,6,7,8,9,10,11} → vecinos sin self.
    """
    t1_nums = {1: 34, 2: 34, 3: 34, 4: 34, 5: 34}
    t2_code = {4: 99, 6: 99, 7: 99, 8: 99, 9: 99, 10: 99, 11: 99, 1: 1, 2: 2, 3: 3, 5: 5}
    t1_rows = [_row(n, c, TableKind.TABLE_1) for n, c in t1_nums.items()]
    t2_rows = [_row(n, c, TableKind.TABLE_2) for n, c in t2_code.items()]
    t1_groups: dict[int, list[int]] = {}
    for n, c in t1_nums.items():
        t1_groups.setdefault(c, []).append(n)
    t2_groups: dict[int, list[int]] = {}
    for n, c in t2_code.items():
        t2_groups.setdefault(c, []).append(n)
    for g in t1_groups.values():
        g.sort()
    for g in t2_groups.values():
        g.sort()
    return TableCatalog(
        table1_rows=t1_rows,
        table2_rows=t2_rows,
        table1_number_to_code=t1_nums,
        table1_code_to_numbers=t1_groups,
        table2_number_to_code=t2_code,
        table2_code_to_numbers=t2_groups,
    )


def _draw(
    draw_id: str,
    lottery_id: str,
    d: date,
    numbers: list[int],
    *,
    t: time | None = None,
    name: str | None = None,
) -> DrawRef:
    return DrawRef(
        draw_id=draw_id,
        lottery_id=lottery_id,
        lottery_name=name or lottery_id,
        draw_date=d,
        draw_time=t or time(20, 0),
        numbers=tuple((i + 1, n) for i, n in enumerate(numbers)),
    )


@pytest.fixture
def universe_basic() -> InMemoryDrawUniverse:
    """
    Leidsa (primary):
      A1: 34,6,9,11  → confirma 4 con {6,9,11}
      A2: 34,6       → confirma 4 con {6}
      F1..F12: follow-ups after A1/A2
    Loteka (confirming for SAME_DATE):
      L1 same date as A1 with 7
    """
    u = InMemoryDrawUniverse()
    # Anchor A1
    u.add(_draw("A1", "leidsa", date(2024, 1, 1), [34, 6, 9, 11], name="Quiniela Leidsa"))
    # Follow-ups after A1 for leidsa (candidate 4 appears on 3rd)
    for i in range(1, 13):
        nums = [90 + (i % 5)]
        if i == 3:
            nums = [4, 55]
        u.add(
            _draw(
                f"A1F{i}",
                "leidsa",
                date(2024, 1, 1 + i),
                nums,
                name="Quiniela Leidsa",
            )
        )
    # Anchor A2 later
    u.add(_draw("A2", "leidsa", date(2024, 2, 1), [34, 6], name="Quiniela Leidsa"))
    # Only 2 follow-ups after A2 → censored for horizon 10
    u.add(_draw("A2F1", "leidsa", date(2024, 2, 2), [88], name="Quiniela Leidsa"))
    u.add(_draw("A2F2", "leidsa", date(2024, 2, 3), [4], name="Quiniela Leidsa"))
    # Loteka same date as A1
    u.add(_draw("L1", "loteka", date(2024, 1, 1), [7, 20], t=time(21, 0), name="Quiniela Loteka"))
    return u


def test_mother_code_and_candidates(controlled_catalog):
    assert controlled_catalog.get_table1_companions(34) == [1, 2, 3, 4, 5]


def test_strengthen_candidate_not_confirmer(controlled_catalog, universe_basic):
    scope = LotteryScope.default_follow_primary(["leidsa"], ["leidsa"], names={"leidsa": "Quiniela Leidsa"})
    window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)
    anchor = universe_basic.get_draw("A1")
    assert anchor is not None
    atomics, combos = build_events_for_anchor(
        observed_number=34,
        anchor=anchor,
        scope=scope,
        window=window,
        universe=universe_basic,
        catalog=controlled_catalog,
        candidate_filter=4,
    )
    assert combos
    combo = combos[0]
    assert combo.candidate == 4
    assert combo.confirmers == [6, 9, 11]
    assert combo.score_raw == 3
    for h in combo.hits:
        assert h.candidate_strengthened == 4
        assert h.score_delta == 1
        assert h.confirmer_number in (6, 9, 11)
    # No atomic event strengthening confirmer as candidate for this relation
    assert all(a.candidate == 4 for a in atomics)
    assert {a.confirmer for a in atomics} == {6, 9, 11}


def test_atomic_and_combination_levels(controlled_catalog, universe_basic):
    scope = LotteryScope.default_follow_primary(["leidsa"])
    window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)
    raw = build_historical_events(
        observed_number=34,
        scope=scope,
        window=window,
        universe=universe_basic,
        catalog=controlled_catalog,
        candidate_filter=4,
        date_from=date(2024, 1, 1),
        date_to=date(2024, 2, 28),
    )
    assert len(raw["atomic_events"]) >= 4  # 3 from A1 + 1 from A2
    assert len(raw["combination_events"]) == 2
    keys = {c.confirmers_key for c in raw["combination_events"]}
    assert "6,9,11" in keys
    assert "6" in keys


def test_posterior_and_censorship(controlled_catalog, universe_basic):
    svc = HistoricalRelationsService(universe=universe_basic, catalog=controlled_catalog)
    scope = LotteryScope.default_follow_primary(["leidsa"])
    window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)
    result = svc.search_conditions(
        observed_number=34,
        scope=scope,
        window=window,
        candidate=4,
        date_from=date(2024, 1, 1),
        date_to=date(2024, 2, 28),
    )
    combos = result["combination_events"]
    assert len(combos) == 2
    by_anchor = {c["anchor"]["draw_id"]: c for c in combos}
    p1 = by_anchor["A1"]["posterior"]
    assert p1["draws_until_response"] == 3
    assert p1["responded_next_draw"] is False
    assert p1["responded_within_3"] is True
    assert p1["censored"] is False

    p2 = by_anchor["A2"]["posterior"]
    assert p2["draws_until_response"] == 2
    assert p2["censored"] is True  # only 2 follow-ups < 10
    assert "within_10" in p2["censored_horizons"] or p2["responded_within_10"] is None


def test_rates_exclude_censored_denominator(controlled_catalog, universe_basic):
    svc = HistoricalRelationsService(universe=universe_basic, catalog=controlled_catalog)
    scope = LotteryScope.default_follow_primary(["leidsa"])
    window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)
    result = svc.search_conditions(
        observed_number=34,
        scope=scope,
        window=window,
        candidate=4,
    )
    rates = result["statistics"]["aliases"]
    # within_10: A2 censored → denom should be 1 (only A1 evaluable)
    r10 = rates["response_rate_within_10"]
    assert r10["denominator"] == 1
    assert r10["censored_count"] == 1
    assert r10["numerator"] == 1
    assert r10["not_probability_of_winning"] is True
    assert "numerador" not in r10  # Spanish labels in warning/docs; API uses numerator
    assert r10["numerator"] == 1


def test_same_date_cross_lottery(controlled_catalog, universe_basic):
    scope = LotteryScope(
        primary_lottery_ids=("leidsa",),
        confirming_lottery_ids=("leidsa", "loteka"),
        follow_up_lottery_ids=("leidsa",),
        lottery_names={"leidsa": "Quiniela Leidsa", "loteka": "Quiniela Loteka"},
    )
    window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DATE)
    anchor = universe_basic.get_draw("A1")
    assert anchor is not None
    atomics, combos = build_events_for_anchor(
        observed_number=34,
        anchor=anchor,
        scope=scope,
        window=window,
        universe=universe_basic,
        catalog=controlled_catalog,
        candidate_filter=4,
    )
    confirmers = set(combos[0].confirmers)
    assert 6 in confirmers and 9 in confirmers and 11 in confirmers
    assert 7 in confirmers  # from Loteka L1
    # Evidence keeps distinct draw_ids
    draw_ids = {h.confirmer_draw_id for h in combos[0].hits}
    assert "A1" in draw_ids and "L1" in draw_ids


def test_sample_tiers():
    assert classify_sample(1) == SampleTier.VERY_LOW
    assert classify_sample(5) == SampleTier.LOW
    assert classify_sample(10) == SampleTier.MODERATE
    assert classify_sample(30) == SampleTier.SOLID
    assert sample_warning(3) is not None
    assert sample_warning(10) is None


def test_no_date_merge_two_draws_same_date(controlled_catalog):
    u = InMemoryDrawUniverse()
    u.add(_draw("D1", "leidsa", date(2024, 5, 1), [34, 6]))
    u.add(_draw("D2", "leidsa", date(2024, 5, 1), [34, 9], t=time(21, 0)))
    for i in range(1, 12):
        u.add(_draw(f"F{i}", "leidsa", date(2024, 5, 1 + i), [4] if i == 1 else [80]))
    scope = LotteryScope.default_follow_primary(["leidsa"])
    window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)
    raw = build_historical_events(
        observed_number=34,
        scope=scope,
        window=window,
        universe=u,
        catalog=controlled_catalog,
        candidate_filter=4,
    )
    assert raw["anchors_examined"] == 2
    anchors = {c.anchor.draw_id for c in raw["combination_events"]}
    assert anchors == {"D1", "D2"}
