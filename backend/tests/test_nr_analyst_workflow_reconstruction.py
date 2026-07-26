"""Tests for analyst workflow reconstruction."""

from __future__ import annotations

from datetime import date

from app.lottery.numeric_relations.analyst_workflow_reconstruction import (
    PendingCase,
    enumerate_combinations,
    observations_from_draws,
    simulate_day_flow,
)
from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.historical_manual_audit import ObservedNumber


def test_41_70_produces_29():
    cat = build_catalog()
    obs = [
        ObservedNumber("a", "Gana Mas", "1", date(2026, 6, 21), None, 1, "1", 41, None),
        ObservedNumber("b", "Leidsa", "2", date(2026, 6, 21), None, 1, "1", 70, None),
    ]
    combos = enumerate_combinations(obs, cat)
    assert any(c["fuerte"] == 29 and c["origin"] == 41 and 70 in c["confirmers"] for c in combos)


def test_35_14_produces_54():
    cat = build_catalog()
    obs = [
        ObservedNumber("a", "Nacional", "1", date(2026, 6, 23), None, 1, "1", 35, None),
        ObservedNumber("b", "Loteka", "2", date(2026, 6, 23), None, 1, "1", 14, None),
    ]
    combos = enumerate_combinations(obs, cat)
    assert any(c["fuerte"] == 54 and c["origin"] == 35 and 14 in c["confirmers"] for c in combos)


def test_first_pos_modality_picks_first_in_universe():
    draws = [
        {
            "lottery_id": "1",
            "lottery_name": "Nacional",
            "draw_id": "d1",
            "draw_time": "21:00:00",
            "numbers": [35, 0, 63],
            "positions": [1, 2, 3],
            "position_labels": ["1", "2", "3"],
            "source_reference": "x",
            "is_featured": True,
        }
    ]
    obs = observations_from_draws(draws, d=date(2026, 6, 23), mode="first_pos")
    assert len(obs) == 1
    assert obs[0].number == 35


def test_case_closure_on_fulfillment_day():
    draws23 = [
        {
            "lottery_id": "1",
            "lottery_name": "Quiniela Leidsa",
            "draw_id": "l",
            "draw_time": "21:00:00",
            "numbers": [29, 1, 26],
            "positions": [1, 2, 3],
            "position_labels": ["1", "2", "3"],
            "source_reference": "a",
            "is_featured": True,
        },
        {
            "lottery_id": "2",
            "lottery_name": "Loteria Nacional",
            "draw_id": "n",
            "draw_time": "21:01:00",
            "numbers": [35, 0, 63],
            "positions": [1, 2, 3],
            "position_labels": ["1", "2", "3"],
            "source_reference": "b",
            "is_featured": True,
        },
        {
            "lottery_id": "3",
            "lottery_name": "Quiniela Loteka",
            "draw_id": "k",
            "draw_time": "21:02:00",
            "numbers": [14, 42, 57],
            "positions": [1, 2, 3],
            "position_labels": ["1", "2", "3"],
            "source_reference": "c",
            "is_featured": True,
        },
    ]
    flow = simulate_day_flow(
        day=date(2026, 6, 23),
        draws=draws23,
        pending=PendingCase(29, date(2026, 6, 21), 41, [70]),
        mode="first_pos",
        featured_only=True,
    )
    assert flow["fulfilled"] is True
    assert flow["closed_case"]["fuerte"] == 29
    assert any(c["fuerte"] == 54 for c in flow["combinations"])
    assert "CASO_CERRADO" in flow["states"]
    assert "NUEVO_ANALISIS" in flow["states"]


def test_motor_catalog_unchanged_after_workflow():
    cat = build_catalog()
    before = cat.table1_number_to_code[54]
    simulate_day_flow(
        day=date(2026, 6, 23),
        draws=[],
        pending=None,
        mode="first_pos",
        featured_only=True,
    )
    assert build_catalog().table1_number_to_code[54] == before
