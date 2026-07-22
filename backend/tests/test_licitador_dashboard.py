"""Tests — dashboards Licitador."""

from app.services.licitador_dashboard_service import (
    COMPANY_KEYS,
    EXPECTED_LEGAL,
    LicitadorDashboardService,
    TEMPLATE_TYPE_HINTS,
)


def test_company_keys_cover_justech_group():
    keys = {k for k, _ in COMPANY_KEYS}
    assert "justech" in keys
    assert "omni_solutions" in keys
    assert "mf_plug_safe" in keys


def test_expected_legal_types():
    assert "dgii" in EXPECTED_LEGAL
    assert "proveedor_estado" in EXPECTED_LEGAL


def test_detect_template_type_sncc():
    t = LicitadorDashboardService._detect_template_type("SNCC F042 Oferente.docx")
    assert t == "sncc"


def test_detect_template_type_oferta():
    t = LicitadorDashboardService._detect_template_type("Formato Oferta Economica.xlsx")
    assert t == "oferta_economica"


def test_company_from_path():
    assert LicitadorDashboardService._company_from_path("JUSTECH/RNC") == "justech"
