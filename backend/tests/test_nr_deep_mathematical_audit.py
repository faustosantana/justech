"""Tests for deep mathematical relations audit (read-only geometry)."""

from __future__ import annotations

from datetime import date, timedelta

from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.deep_mathematical_audit import (
    PERIOD_FROM,
    PERIOD_TO,
    classify_appearance,
    collect_future,
    enumerate_official_chains,
    positional_distance,
    position_in_group,
    t1_candidates_from_observed,
    t1_group_ordered,
    t2_group_ordered,
)
from app.lottery.numeric_relations.historical_manual_audit import ObservedNumber


def _obs(n: int, lottery: str, pos: int = 1) -> ObservedNumber:
    return ObservedNumber(
        lottery_id=lottery,
        lottery_name=lottery,
        draw_id=f"{lottery}-{n}",
        draw_date=date(2020, 1, 5),
        draw_time=None,
        position=pos,
        position_label=str(pos),
        number=n,
        source_reference=f"src-{n}",
    )


def test_period_constants():
    assert PERIOD_FROM == date(2019, 7, 23)
    assert PERIOD_TO == date(2026, 7, 16)


def test_t1_candidates_use_observed_as_mother_code():
    cat = build_catalog()
    # Official geometry: 35 → candidates include 54
    cands = t1_candidates_from_observed(cat, 35)
    assert 54 in cands


def test_position_and_distance_canonical_order():
    cat = build_catalog()
    group = t1_group_ordered(cat, 54)
    assert group == sorted(group)
    p54 = position_in_group(group, 54)
    assert p54 is not None
    # distance to self is 0
    assert positional_distance(group, 54, 54) == 0
    others = [x for x in group if x != 54]
    if others:
        d = positional_distance(group, 54, others[0])
        assert d == position_in_group(group, others[0]) - p54


def test_official_chain_35_14_54_no_lookahead():
    cat = build_catalog()
    obs = [_obs(35, "Nacional"), _obs(14, "Loteka")]
    chains = enumerate_official_chains(date(2020, 1, 5), obs, catalog=cat)
    assert any(c.fuerte == 54 and c.origin == 35 and c.confirmer == 14 for c in chains)
    # confirmer is never the fuerte
    assert all(c.confirmer != c.fuerte for c in chains)


def test_collect_future_d1_to_d7_excludes_d0_and_d8():
    case = date(2020, 1, 5)
    by_date = {}
    for off in range(0, 9):
        d = case + timedelta(days=off)
        by_date[d] = [
            {
                "draw_id": f"d{off}",
                "lottery_id": "L",
                "lottery_name": "L",
                "draw_date": d,
                "draw_time": None,
                "source_reference": None,
                "numbers": [10 + off],
                "positions": [1],
                "position_labels": ["1"],
            }
        ]
    apps = collect_future(case, by_date)
    offsets = {a.day_offset for a in apps}
    assert offsets == {1, 2, 3, 4, 5, 6, 7}
    assert all(a.number != 10 for a in apps)  # D+0 excluded
    assert all(a.number != 18 for a in apps)  # D+8 excluded


def test_classify_fuerte_exact_and_companion_labels():
    cat = build_catalog()
    obs = [_obs(35, "Nacional"), _obs(14, "Loteka")]
    chains = enumerate_official_chains(date(2020, 1, 5), obs, catalog=cat)
    chain = next(c for c in chains if c.fuerte == 54)
    from app.lottery.numeric_relations.deep_mathematical_audit import FutureAppearance

    exact = FutureAppearance(
        number=54,
        day_offset=1,
        draw_date=date(2020, 1, 6),
        lottery_name="Leidsa",
        lottery_id="x",
        position=2,
        position_label="2",
        draw_time=None,
        source_reference="s",
        draw_id="1",
    )
    clf = classify_appearance(cat=cat, chain=chain, app=exact)
    assert "FUERTE_EXACTO" in clf["labels"]
    assert clf["t1_dist"] == 0

    companions = [n for n in chain.t1_group_of_fuerte if n != 54]
    if companions:
        comp = companions[0]
        app = FutureAppearance(
            number=comp,
            day_offset=2,
            draw_date=date(2020, 1, 7),
            lottery_name="Real",
            lottery_id="y",
            position=1,
            position_label="1",
            draw_time=None,
            source_reference="s2",
            draw_id="2",
        )
        clf2 = classify_appearance(cat=cat, chain=chain, app=app)
        assert "MISMO_GRUPO_T1" in clf2["labels"]
        assert clf2["t1_dist"] is not None


def test_t2_group_contains_confirmer_for_54():
    cat = build_catalog()
    t2 = t2_group_ordered(cat, 54)
    assert 14 in t2
