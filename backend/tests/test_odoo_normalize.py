"""Tests para normalización de valores Odoo JSON-RPC."""

from decimal import Decimal

from integrations.odoo.normalize import (
    odoo_bool,
    odoo_date,
    odoo_dec,
    odoo_float,
    odoo_m2m_ids,
    odoo_m2o_id,
    odoo_m2o_name,
    odoo_m2o_name_opt,
    odoo_str,
    odoo_str_opt,
)


def test_odoo_str_false_and_none():
    assert odoo_str(False) == ""
    assert odoo_str(None) == ""
    assert odoo_str("hello") == "hello"
    assert odoo_str(42) == "42"


def test_odoo_str_opt():
    assert odoo_str_opt(False) is None
    assert odoo_str_opt(None) is None
    assert odoo_str_opt("") is None
    assert odoo_str_opt("  ") is None
    assert odoo_str_opt("a@b.com") == "a@b.com"


def test_odoo_m2o():
    assert odoo_m2o_id(False) is None
    assert odoo_m2o_id([7, "Acme"]) == 7
    assert odoo_m2o_name(False) == ""
    assert odoo_m2o_name([7, "Acme"]) == "Acme"
    assert odoo_m2o_name_opt(False) is None
    assert odoo_m2o_name_opt([7, "Acme"]) == "Acme"


def test_odoo_m2m():
    assert odoo_m2m_ids(False) == []
    assert odoo_m2m_ids(None) == []
    assert odoo_m2m_ids([1, 2, 3]) == [1, 2, 3]


def test_odoo_date_and_float():
    assert odoo_date(False) is None
    assert odoo_date("2024-05-01 00:00:00") == "2024-05-01"
    assert odoo_float(False) == 0.0
    assert odoo_float(3.5) == 3.5
    assert odoo_dec(False) == Decimal("0")


def test_odoo_bool():
    assert odoo_bool(False) is False
    assert odoo_bool(True) is True
    assert odoo_bool(None, default=True) is True


def test_customer_response_accepts_false_fields():
    from app.schemas.odoo import OdooCustomerResponse

    row = {
        "id": 1,
        "name": "Test",
        "email": False,
        "phone": False,
        "vat": False,
        "city": False,
        "is_company": False,
    }
    item = OdooCustomerResponse(
        id=row["id"],
        name=odoo_str(row.get("name")),
        email=odoo_str_opt(row.get("email")),
        phone=odoo_str_opt(row.get("phone")),
        vat=odoo_str_opt(row.get("vat")),
        city=odoo_str_opt(row.get("city")),
        is_company=odoo_bool(row.get("is_company")),
    )
    assert item.email is None
    assert item.phone is None


def test_product_response_accepts_false_default_code():
    from app.schemas.odoo import OdooProductResponse

    item = OdooProductResponse(
        id=1,
        name="Widget",
        default_code=odoo_str_opt(False),
        list_price=odoo_dec(False),
        standard_price=odoo_dec(10),
        qty_available=odoo_float(False),
        uom=odoo_m2o_name_opt(False),
    )
    assert item.default_code is None
    assert item.uom is None
