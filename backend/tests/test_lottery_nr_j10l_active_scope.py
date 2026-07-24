"""J-10L — Política de universo activo (featured) sin tocar DB DEV."""

from __future__ import annotations

from app.lottery.numeric_relations.active_scope_policy import (
    ACTIVE_ANALYSIS_USER_REPLY,
    EXPECTED_PRODUCT_SEVEN_NAMES,
    SEED_FEATURED_SEVEN_NAMES,
    ActiveLottery,
    AnalysisScope,
    analysis_scope_for_featured,
    build_analysis_scope_metadata,
    filter_to_active_ids,
    name_set_discrepancy,
    scope_set_hash,
)
from app.lottery.numeric_relations.catalog import build_catalog


def test_filter_rejects_non_active():
    active = {"a", "b", "c"}
    accepted, rejected = filter_to_active_ids(["a", "x", "b", "y", "a"], active)
    assert accepted == ["a", "b"]
    assert rejected == ["x", "y"]


def test_empty_request_means_intersection_empty_when_filtering():
    accepted, rejected = filter_to_active_ids([], {"a"})
    assert accepted == []
    assert rejected == []


def test_scope_hash_stable_order_independent():
    assert scope_set_hash(["b", "a"]) == scope_set_hash(["a", "b"])
    assert scope_set_hash(["a"]) != scope_set_hash(["a", "b"])


def test_analysis_scope_derived_from_featured():
    assert analysis_scope_for_featured(True) is AnalysisScope.ACTIVE
    assert analysis_scope_for_featured(False) is AnalysisScope.ARCHIVED


def test_metadata_includes_scope_hash_and_note():
    lots = [
        ActiveLottery(id="1", name="Quiniela Leidsa"),
        ActiveLottery(id="2", name="Quiniela Loteka"),
    ]
    meta = build_analysis_scope_metadata(lots, rejected_ids=["archived-id"])
    assert meta["analysis_scope"] == "FEATURED_SEVEN"
    assert meta["active_lottery_count"] == 2
    assert meta["ignored_non_active_count"] == 1
    assert "scope_set_hash" in meta
    assert "loterías activas" in meta["user_note"].lower() or "activas" in meta["user_note"].lower()


def test_name_discrepancy_documents_ny_vs_seed():
    # Simula el seed actual (Loto*) vs producto (NY*)
    disc = name_set_discrepancy(list(SEED_FEATURED_SEVEN_NAMES))
    assert disc["active_count"] == 7
    assert disc["matches_seed_featured_names"] is True
    assert disc["matches_expected_product_names"] is False
    assert any("new york" in x for x in disc["missing_vs_product"])


def test_expected_product_seven_count():
    assert len(EXPECTED_PRODUCT_SEVEN_NAMES) == 7
    assert len(SEED_FEATURED_SEVEN_NAMES) == 7


def test_table_formulas_intact_after_ui_cleanup():
    """Las fórmulas internas no se alteran (solo UI)."""
    cat = build_catalog()
    assert len(cat.table1_rows) == 100
    assert len(cat.table2_rows) == 100
    row1 = next(r for r in cat.table1_rows if r.number == 35)
    assert row1.formula
    assert row1.visible_value
    assert row1.digits_without_point
    assert row1.digit_count >= 1
    row2 = next(r for r in cat.table2_rows if r.number == 35)
    assert row2.formula


def test_ai_refusal_copy():
    assert "siete" in ACTIVE_ANALYSIS_USER_REPLY.lower() or "activas" in ACTIVE_ANALYSIS_USER_REPLY.lower()
    assert "archiv" in ACTIVE_ANALYSIS_USER_REPLY.lower() or "destacadas" in ACTIVE_ANALYSIS_USER_REPLY.lower()


def test_motor_table_product_columns_contract():
    """Contrato documental: la UI de producto no debe listar columnas técnicas."""
    forbidden = {"Fórmula", "Resultado", "Cadena dígitos", "Cant. dígitos", "Cadena de dígitos"}
    product = {"Número", "Código", "Compañeros", "Confirmadores relacionados", "Analizar"}
    assert not forbidden.intersection(product)
