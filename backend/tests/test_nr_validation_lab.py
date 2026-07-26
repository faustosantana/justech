"""Validation Lab — explain-only; must not alter motor tables."""

from __future__ import annotations

from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.validation_lab import run_validation_lab


def test_case4_35_14_produces_54_exact():
    out = run_validation_lab(
        observed=[{"number": 35, "lottery_name": "Nacional"}, {"number": 14, "lottery_name": "Loteka"}],
        manual_fuerte=54,
    )
    assert out["coincidence"] == "SI"
    assert out["motor_shaped_result"] == 54
    f = next(h for h in out["crosses_and_intersections"] if h["id"] == "F")
    assert f["produced"] == [54]


def test_case1_41_70_produces_29():
    out = run_validation_lab(
        observed=[{"number": 41}, {"number": 70}],
        manual_fuerte=29,
    )
    assert out["coincidence"] in ("SI", "SI_CON_OTROS_CANDIDATOS")
    assert 29 in (out["motor_shaped_result"] if isinstance(out["motor_shaped_result"], list) else [out["motor_shaped_result"]])


def test_case2_41_62_does_not_motor_shape_75():
    """Documented divergence: 75 is T2 neighbor of 62, not F-shaped confirmation of 41."""
    out = run_validation_lab(
        observed=[{"number": 41}, {"number": 62}],
        manual_fuerte=75,
    )
    f = next(h for h in out["crosses_and_intersections"] if h["id"] == "F")
    e = next(h for h in out["crosses_and_intersections"] if h["id"] == "E")
    assert f["hit_manual"] is False
    assert e["hit_manual"] is True
    assert out["coincidence"] == "PARCIAL_RELACION_ALTERNATIVA"


def test_lab_does_not_change_catalog():
    cat = build_catalog()
    before = list(cat.get_table1_companions(35))
    run_validation_lab(observed=[{"number": 35}, {"number": 14}], manual_fuerte=54)
    after = list(build_catalog().get_table1_companions(35))
    assert before == after
