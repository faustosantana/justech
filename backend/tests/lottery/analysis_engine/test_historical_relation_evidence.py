"""Historical relation evidence — explanatory layer (no ranking changes)."""

from __future__ import annotations

from datetime import date, timedelta

from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.historical_relation_evidence import (
    analyze_historical_relations,
    build_day_index,
    find_relation_cases,
    result_label,
)
from app.lottery.numeric_relations.catalog import build_catalog


def _row(d: str, lottery: str, primera: str, segunda: str = "00", tercera: str = "00", draw_id: str = "x"):
    return {
        "date": d,
        "lottery": lottery,
        "primera": primera,
        "segunda": segunda,
        "tercera": tercera,
        "draw_id": f"{lottery}-{d}-{draw_id}",
        "lottery_id": lottery,
    }


def _build_history_with_hits():
    """Synthetic history: several 35+14 days, some followed by 54 within D+7."""
    rows = []
    # Case A: 35+14 then 54 next day
    rows.append(_row("2024-01-10", "Nacional", "35"))
    rows.append(_row("2024-01-10", "Loteka", "14"))
    rows.append(_row("2024-01-11", "Leidsa", "54"))
    # Case B: 35+14 then T1 family companion (11 is companion of mother 35?)
    cat = build_catalog()
    companions = [c for c in cat.get_table1_companions(35) if c != 54]
    family = companions[0] if companions else 11
    rows.append(_row("2024-02-10", "Nacional", "35"))
    rows.append(_row("2024-02-10", "Loteka", "14"))
    rows.append(_row("2024-02-12", "Real", f"{family:02d}"))
    # Case C: 35+14 then exact 54 in D+3
    rows.append(_row("2024-03-01", "Nacional", "35"))
    rows.append(_row("2024-03-01", "Loteka", "14"))
    rows.append(_row("2024-03-04", "GanaMas", "54"))
    # Case D: 35+14 no hit
    rows.append(_row("2024-04-01", "Nacional", "35"))
    rows.append(_row("2024-04-01", "Loteka", "14"))
    rows.append(_row("2024-04-20", "Leidsa", "99"))
    # Filler days so D+7 windows have content
    for i in range(5, 20):
        rows.append(_row(f"2024-01-{i:02d}", "NY", "01", draw_id=str(i)))
    return rows, family


def test_exact_level1_finds_35_14_54_cases():
    rows, _ = _build_history_with_hits()
    idx = build_day_index(rows)
    cases = find_relation_cases(
        idx, origin_x=35, confirmer_y=14, candidate_c=54, similarity_level=1
    )
    assert len(cases) >= 3
    assert all(c.origin_x == 35 and c.confirmer_y == 14 and c.candidate_c == 54 for c in cases)


def test_metrics_and_windows():
    rows, family = _build_history_with_hits()
    out = analyze_historical_relations(
        rows,
        origin_x=35,
        confirmer_y=14,
        candidate_c=54,
        period="all",
        primary_meta={
            "table1_sources": [35],
            "table2_confirmers": [14],
            "same_day_cross_support": True,
            "lotteries": ["Nacional", "Loteka"],
            "independent_routes": 3,
        },
        rival_meta={
            "number": 7,
            "table1_sources": [],
            "table2_confirmers": [35],
            "same_day_cross_support": False,
            "independent_routes": 1,
        },
        today=date(2026, 6, 23),
    )
    m = out["metrics"]
    assert m["exact_cases"] >= 3
    assert m["exact_hits"] >= 2
    assert m["d7_hits"] >= 2
    assert out["evidence_card"]["table1_support"] is True
    assert out["rival_card"]["table1_support"] is False
    assert "54" in out["narrative"]["conclusion"]
    assert "07" in out["narrative"]["comparison"] or "7" in out["narrative"]["comparison"]
    assert out["table1_priority"] is True
    assert out["ranking_unchanged"] is True
    assert out["date_to"] is not None
    # labels are human
    assert result_label("ACIERTO_CANDIDATO_EXACTO") == "Candidato exacto"


def test_insufficient_evidence_message():
    rows = [
        _row("2025-01-01", "Nacional", "35"),
        _row("2025-01-01", "Loteka", "14"),
        _row("2025-01-02", "Leidsa", "54"),
    ]
    out = analyze_historical_relations(
        rows, origin_x=35, confirmer_y=14, candidate_c=54, period="all"
    )
    assert out["metrics"]["exact_cases"] < 5
    assert "poca evidencia" in out["metrics"]["evidence_quantity_message"].lower() or out[
        "metrics"
    ]["evidence_quantity"] == "insuficiente"


def test_structural_analysis_unchanged_without_history():
    r = run_complete_analysis(
        {"numbers": [35, 14], "mode": "manual_reconstruido", "create_signals": False},
        persist=False,
    )
    assert r.primary_signal["number"] == 54
    r2 = run_complete_analysis(
        {"numbers": [39, 58], "mode": "manual_reconstruido", "create_signals": False},
        persist=False,
    )
    assert r2.primary_signal["number"] == 94


def test_history_does_not_override_primary_without_t1():
    """Inject history favoring 07 — primary for 35+14 must remain 54."""
    rows, _ = _build_history_with_hits()
    # Extra fake "hits" for 07 after random days — still must not beat T1×T2 ranking
    for i in range(1, 40):
        d0 = date(2023, 1, 1) + timedelta(days=i * 3)
        rows.append(_row(d0.isoformat(), "X", "07"))
        rows.append(_row((d0 + timedelta(days=1)).isoformat(), "Y", "07"))
    r = run_complete_analysis(
        {
            "numbers": [35],
            "same_day_confirmers": [14],
            "mode": "socio",
            "derivation_depth": 0,
            "create_signals": False,
            "historical_draws": rows,
            "historical_period": "all",
        },
        persist=False,
    )
    assert r.primary_signal["number"] == 54
    assert r.historical_evidence is not None
    assert r.historical_evidence.get("ranking_unchanged") is True


def test_legacy_cases_still_pass():
    cases = [
        ([35, 14], 54),
        ([39, 58], 94),
        ([41, 41, 70], 29),
        ([49, 44, 70], 35),
    ]
    for nums, expect in cases:
        r = run_complete_analysis(
            {"numbers": nums, "mode": "manual_reconstruido", "create_signals": False},
            persist=False,
        )
        assert r.primary_signal["number"] == expect, nums
    r = run_complete_analysis(
        {"numbers": [41, 62], "mode": "manual_reconstruido", "create_signals": False},
        persist=False,
    )
    assert r.primary_signal["number"] == 75
