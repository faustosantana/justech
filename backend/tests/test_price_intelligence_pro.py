"""Tests — Price Intelligence Pro (listas indexadas)."""

from decimal import Decimal

from app.services.price_margin_engine import MarginConfig, PriceMarginEngine
from app.services.price_product_matcher import (
    extract_dgcp_line_items,
    filters_from_requirement,
    parse_requirement_line,
)
from app.services.price_supplier_scorer import score_supplier_offer


def test_parse_laptop_requirement():
    parsed = parse_requirement_line("25 laptops 16GB 512GB SSD 14 pulgadas Dell Latitude")
    assert parsed["quantity"] == 25
    assert parsed["ram_gb"] == 16
    assert parsed["storage_gb"] == 512
    assert parsed["product_type"] == "laptop"


def test_filters_from_requirement():
    f = filters_from_requirement("laptop Dell 16GB 512GB")
    assert f.ram_gb == 16
    assert f.storage_gb == 512
    assert f.product_type == "laptop"


def test_extract_dgcp_lines():
    text = "Adquisición de 25 laptops 16GB RAM 512GB SSD\nMonitores 24 pulgadas cantidad 10"
    lines = extract_dgcp_line_items(text)
    assert len(lines) >= 1
    assert lines[0]["quantity"] == 25


def test_margin_engine():
    m = PriceMarginEngine().calculate(
        Decimal("818"),
        currency="USD",
        quantity=25,
        config=MarginConfig(target_margin_pct=Decimal("20")),
    )
    assert m.total_cost > Decimal("818")
    assert m.sale_price_suggested > m.total_cost
    assert m.total_cost_all == m.total_cost * 25
    assert m.margin_pct_actual > 0


def test_supplier_scorer():
    from app.schemas.prices import PriceProductResponse
    from datetime import datetime, timezone
    from uuid import uuid4

    product = PriceProductResponse(
        id=uuid4(),
        supplier="Ingram",
        manufacturer=None,
        brand="Dell",
        sku="SKU1",
        mpn=None,
        model="Latitude 5450",
        description="Dell Pro 14 16GB 512GB",
        category="Notebooks",
        product_type="laptop",
        is_cotizable=True,
        processor=None,
        ram_gb=16,
        storage_gb=512,
        storage_type="SSD",
        display='14"',
        operating_system="W11P",
        price=Decimal("818"),
        preferred_price=Decimal("818"),
        currency="USD",
        stock=25,
        in_transit=None,
        warranty="1Y",
        source_filename="ingram.xlsx",
        source_sheet="Comercial",
        source_row=10,
        source_file_date=datetime.now(timezone.utc),
        file_id=uuid4(),
        indexed_at=datetime.now(timezone.utc),
    )
    score, risk, reasons = score_supplier_offer(product, price_rank=0, total_offers=4, quantity_needed=25)
    assert score >= 70
    assert risk == "bajo"
    assert reasons
