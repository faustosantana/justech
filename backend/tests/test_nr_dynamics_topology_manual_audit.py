"""Tests for dynamics / topology / manual-rules audit."""

from __future__ import annotations

from app.lottery.numeric_relations.dynamics_topology_manual_audit import (
    MANUAL_CASES,
    reproduce_manual_case,
)
from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.historical_manual_audit import strengthen_official
from app.lottery.numeric_relations.dynamics_topology_manual_audit import obs_list


def test_manual_cases_specs_present():
    ids = {c.case_id for c in MANUAL_CASES}
    assert ids == {"M1", "M2", "M3", "M4", "M5"}


def test_m1_official_unique_29():
    r = reproduce_manual_case(next(c for c in MANUAL_CASES if c.case_id == "M1"))
    assert r["manual_fuerte"] == 29
    assert r["official_fuertes"] == [29]
    assert r["classification"] == "FUERTE_OFICIAL_UNICO"


def test_m2_direct_t2_75():
    r = reproduce_manual_case(next(c for c in MANUAL_CASES if c.case_id == "M2"))
    assert r["manual_fuerte"] == 75
    assert r["official_fuertes"] == []
    assert r["classification"] == "VECINO_T2_DIRECTO"
    assert any(x["observed"] == 62 for x in r["direct_t2_links"])


def test_m3_multiple_includes_35_and_22():
    r = reproduce_manual_case(next(c for c in MANUAL_CASES if c.case_id == "M3"))
    assert set(r["official_fuertes"]) == {22, 35}
    assert r["classification"] == "FUERTE_OFICIAL_ENTRE_VARIOS"
    assert r["m3_tiebreak"]["hypothesis_more_confirmers"] is True


def test_m4_official_54():
    r = reproduce_manual_case(next(c for c in MANUAL_CASES if c.case_id == "M4"))
    assert r["official_fuertes"] == [54]
    assert r["classification"] == "FUERTE_OFICIAL_UNICO"


def test_m5_both_58_and_84_confirm_94():
    cat = build_catalog()
    r58 = strengthen_official(obs_list([39, 58]), catalog=cat)
    r84 = strengthen_official(obs_list([39, 84]), catalog=cat)
    assert 94 in {h.candidate for h in r58}
    assert 94 in {h.candidate for h in r84}
    r = reproduce_manual_case(next(c for c in MANUAL_CASES if c.case_id == "M5"))
    assert r["classification"] == "FUERTE_OFICIAL_UNICO"
    assert r["m5_alternate_84"]["both_confirm_94"] is True


def test_motor_tables_not_imported_for_mutation():
    # Sanity: reproduce does not write catalog globals oddly
    cat1 = build_catalog()
    reproduce_manual_case(MANUAL_CASES[0], catalog=cat1)
    cat2 = build_catalog()
    assert cat1.table1_number_to_code[54] == cat2.table1_number_to_code[54]
