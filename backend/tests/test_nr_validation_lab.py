"""Validation Lab — explain-only; must not alter motor tables."""

from __future__ import annotations

from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.validation_lab import run_validation_lab


def test_case4_35_14_produces_54_exact():
    out = run_validation_lab(
        observed=[{"number": 35, "lottery_name": "Nacional"}, {"number": 14, "lottery_name": "Loteka"}],
        manual_fuerte=54,
    )
    assert out["coincidence"] == "SI_FUERTE_OFICIAL"
    assert out["fuerte_oficial"]["result"] == 54
    assert out["manual_status"]["classification"] == "FUERTE_OFICIAL"


def test_case1_41_70_produces_29():
    out = run_validation_lab(
        observed=[{"number": 41}, {"number": 70}],
        manual_fuerte=29,
    )
    assert out["coincidence"] in ("SI_FUERTE_OFICIAL", "SI_FUERTE_OFICIAL_CON_OTROS")
    assert out["manual_status"]["is_official_fuerte"] is True


def test_case2_classified_as_direct_t2_not_official():
    out = run_validation_lab(
        observed=[{"number": 41}, {"number": 62}],
        manual_fuerte=75,
    )
    assert out["coincidence"] == "SENAL_T2_DIRECTA_NO_OFICIAL"
    assert out["manual_status"]["classification"] == "DIRECT_T2_NEIGHBOR_SIGNAL"
    assert out["manual_status"]["is_official_fuerte"] is False
    assert out["manual_status"]["is_direct_t2_neighbor_signal"] is True
    assert out["fuerte_oficial"]["candidates"] == []
    edges = out["manual_status"]["direct_t2_edges_for_manual"]
    assert any(e["observed"] == 62 and e["direct_t2_neighbor"] == 75 for e in edges)


def test_lab_does_not_change_catalog():
    cat = build_catalog()
    before = list(cat.get_table1_companions(35))
    run_validation_lab(observed=[{"number": 35}, {"number": 14}], manual_fuerte=54)
    after = list(build_catalog().get_table1_companions(35))
    assert before == after
