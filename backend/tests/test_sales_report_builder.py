"""Tests — reporte estructurado de ventas."""

from decimal import Decimal

from app.schemas.odoo import OdooSaleHistoryItem
from app.services.sales_report_builder import build_sales_report, empty_report_message


def _line(**kwargs) -> OdooSaleHistoryItem:
    defaults = {
        "id": 1,
        "order_name": "SO001",
        "order_date": "2026-03-06",
        "partner_name": "Cliente A",
        "product_name": "Laptop Dell",
        "quantity": 2.0,
        "unit_price": Decimal("1000"),
        "subtotal": Decimal("2000"),
    }
    defaults.update(kwargs)
    return OdooSaleHistoryItem(**defaults)


def test_build_sales_report_structure():
    lines = [
        _line(id=1, order_date="2026-03-06", quantity=3, product_id=101),
        _line(
            id=2,
            order_date="2026-06-03",
            order_name="SO002",
            partner_name="Cliente B",
            partner_id=202,
            product_id=101,
            quantity=5,
        ),
    ]
    report = build_sales_report(
        lines=lines,
        product_label="laptops",
        company_name="Justech",
        intent="sales_quantity_query",
    )
    assert report["type"] == "sales_report"
    assert "laptops" in report["summary"].lower() or "Vendimos" in report["summary"]
    assert len(report["metrics"]) >= 8
    assert len(report["tables"]) == 3
    assert report["tables"][0]["title"] == "Productos vendidos"
    assert len(report["warnings"]) == 1
    first_row = report["tables"][0]["rows"][0]
    assert "cells" in first_row
    assert len(first_row["cells"]) == 5


def test_empty_report_message_customer_product():
    msg = empty_report_message(product_label="licencias Microsoft", customer_label="Banco Ademi")
    assert "licencias Microsoft" in msg
    assert "Banco Ademi" in msg
    assert "No encontré" in msg
