"""Tests — acciones del Assistant."""

from app.services.assistant_actions import build_entity_actions, table_row
from app.services.odoo_url_helper import build_odoo_url, build_jaios_path


def test_build_jaios_path_product():
    assert build_jaios_path("product", 42) == "/odoo/products/42"


def test_build_odoo_url_format(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "odoo_url", "https://justgroup.app")
    url = build_odoo_url("product.product", 99)
    assert url == "https://justgroup.app/web#id=99&model=product.product&view_type=form"


def test_table_row_with_actions(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "odoo_url", "https://justgroup.app")
    row = table_row(["Laptop"], entity_type="product", entity_id=10)
    assert row["cells"] == ["Laptop"]
    assert len(row["actions"]) == 3
    assert row["actions"][0]["type"] == "internal_link"
    assert row["actions"][1]["type"] == "external_link"
    assert row["actions"][2]["type"] == "quick_view"


def test_build_entity_actions_dgcp():
    actions = build_entity_actions("dgcp", "uuid-1")
    assert actions[0]["url"] == "/dgcp/uuid-1"
    assert actions[-1]["entity_type"] == "dgcp"
