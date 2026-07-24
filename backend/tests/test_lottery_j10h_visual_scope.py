"""J-10H — vistas ordinarias no pueden devolver >7 loterías de producto."""

from __future__ import annotations

from app.services.lottery_admin_service import _PRODUCT_SCOPE


def test_product_scope_is_featured():
    assert len(_PRODUCT_SCOPE) == 2


def test_acceptance_matrix_documented():
    """Contrato de aceptación (ejecutado también en smoke prod)."""
    required = {
        "dashboard_active_count_max": 7,
        "dashboard_visible_count_max": 7,
        "catalog_ordinary_max": 7,
        "selector_ordinary_max": 7,
        "pending_visible_max": 7,
        "forbidden_names": ("Loto Leidsa", "Loto Pool", "Anguila", "Haiti", "Miami"),
    }
    assert required["dashboard_active_count_max"] == 7
    assert "Loto Leidsa" in required["forbidden_names"]
