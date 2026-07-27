"""Same-day cross-lottery confirmation (socio methodology).

Default confirmer positions = primeras only: including 2ª/3ª of 2026-06-23
would incorrectly strengthen 11 via 57/69 and bury the official 35→54←14 path.
UI still displays all three positions for context.
"""

from __future__ import annotations

from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.same_day_context import (
    build_same_day_context,
    find_same_day_cross_confirmations,
)

# Faithful fixture of featured primeras on 2026-06-23 (prod snapshot).
FIXTURE_2026_06_23 = [
    {
        "lottery": "Gana Más",
        "primera": "07",
        "segunda": "23",
        "tercera": "59",
        "draw_id": "gm",
        "date": "2026-06-23",
    },
    {
        "lottery": "Lotería Nacional",
        "primera": "35",
        "segunda": "00",
        "tercera": "63",
        "draw_id": "ln",
        "date": "2026-06-23",
    },
    {
        "lottery": "New York 10:30",
        "primera": "15",
        "segunda": "56",
        "tercera": "65",
        "draw_id": "ny1",
        "date": "2026-06-23",
    },
    {
        "lottery": "New York 2:30",
        "primera": "84",
        "segunda": "70",
        "tercera": "31",
        "draw_id": "ny2",
        "date": "2026-06-23",
    },
    {
        "lottery": "Quiniela Leidsa",
        "primera": "29",
        "segunda": "01",
        "tercera": "26",
        "draw_id": "leidsa",
        "date": "2026-06-23",
    },
    {
        "lottery": "Quiniela Loteka",
        "primera": "14",
        "segunda": "42",
        "tercera": "57",
        "draw_id": "loteka",
        "date": "2026-06-23",
    },
    {
        "lottery": "Quiniela Real",
        "primera": "67",
        "segunda": "69",
        "tercera": "16",
        "draw_id": "real",
        "date": "2026-06-23",
    },
]


def test_find_same_day_cross_35_14_54():
    ctx = build_same_day_context(
        FIXTURE_2026_06_23,
        draw_date="2026-06-23",
        positions=["first"],
        exclude_numbers=[35],
    )
    assert 14 in ctx.confirmer_numbers
    assert 57 not in ctx.confirmer_numbers  # tercera/segunda excluded by policy
    cross = find_same_day_cross_confirmations(
        [35], ctx.confirmer_numbers, day_context=ctx, date_s="2026-06-23"
    )
    assert any(c.companion_c == 54 and c.confirmer_y == 14 for c in cross)
    hit = next(c for c in cross if c.companion_c == 54)
    assert hit.lottery_x == "Lotería Nacional"
    assert hit.lottery_y == "Quiniela Loteka"
    assert hit.distinct_lotteries is True


def test_auto_day_context_ranks_54_over_07():
    ctx = build_same_day_context(
        FIXTURE_2026_06_23,
        draw_date="2026-06-23",
        positions=["first"],
        exclude_numbers=[35],
    )
    r = run_complete_analysis(
        {
            "numbers": [35],
            "date": "2026-06-23",
            "mode": "socio",
            "derivation_depth": 0,
            "same_day_confirmers": ctx.confirmer_numbers,
            "same_day_context": ctx.to_dict(),
        },
        persist=False,
    )
    assert r.primary_signal is not None
    assert r.primary_signal["number"] == 54
    assert r.primary_signal["table1_sources"] == [35]
    assert 14 in r.primary_signal["table2_confirmers"]
    assert r.primary_signal["same_day_cross_support"] is True
    assert any(c["companion_c"] == 54 and c["confirmer_y"] == 14 for c in r.same_day_cross)
    scores = {c["number"]: c["total_score"] for c in r.ranked_candidates}
    assert scores.get(54, 0) > scores.get(7, 0)
    summary = (r.explanation or {}).get("summary") or ""
    assert "35" in summary and "54" in summary and "14" in summary
    assert "Tabla 1" in summary and "Tabla 2" in summary


def test_manual_35_with_14_confirmer_field():
    r = run_complete_analysis(
        {
            "numbers": [35],
            "same_day_confirmers": [14],
            "mode": "socio",
            "derivation_depth": 0,
        },
        persist=False,
    )
    assert r.primary_signal["number"] == 54


def test_legacy_pairs_still_pass():
    cases = [
        ([35, 14], 54),
        ([39, 58], 94),
        ([41, 41, 70], 29),
        ([49, 44, 70], 35),
    ]
    for nums, expect in cases:
        r = run_complete_analysis(
            {"numbers": nums, "mode": "manual_reconstruido"}, persist=False
        )
        assert r.primary_signal["number"] == expect, (nums, r.primary_signal)


def test_structural_single_number_without_day_does_not_invent_54():
    r = run_complete_analysis(
        {"numbers": [35], "mode": "socio", "derivation_depth": 0}, persist=False
    )
    assert r.primary_signal is not None
    assert r.same_day_cross == []
    assert r.primary_signal["number"] != 54
