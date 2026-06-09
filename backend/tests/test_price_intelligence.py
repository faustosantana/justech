"""Tests — Price Intelligence Engine."""

import pytest

from decimal import Decimal

from app.services.price_classification import classify_product, infer_product_type, is_laptop_product
from app.services.price_list_parser import PriceListParser
from app.services.price_normalizer import parse_price, parse_ram_gb, parse_storage
from app.services.price_question_service import PriceQuestionService


def test_keep_your_hd_not_laptop():
    cls = classify_product(
        description="1Y Keep Your HD",
        category="Line of Business",
        sheet_name="Warranties",
        preferred_price=Decimal("8.93"),
        preferred_price_field="price_final",
    )
    assert cls.product_type == "warranty"
    assert cls.excluded_from_laptop is True
    assert cls.is_cotizable is False
    assert not is_laptop_product(
        "1Y Keep Your HD",
        "Line of Business",
        cls.product_type,
        source_sheet="Warranties",
        excluded_from_laptop=True,
    )


def test_comercial_laptop_valid():
    cls = classify_product(
        description="Dell Pro 14 PC14250 14 ENG U5 225U 16GB 512GB W11P 1Y",
        category="Notebooks",
        sheet_name="Comercial",
        preferred_price=Decimal("818.51"),
        preferred_price_field="price_final",
    )
    assert cls.product_type == "laptop"
    assert cls.excluded_from_laptop is False
    assert cls.is_cotizable is True


def test_warranty_sheet_forces_warranty_type():
    ptype = infer_product_type("ThinkPad 3Y Warranty Extension", "Notebooks", sheet_name="Warranties")
    assert ptype == "warranty"


def test_parse_ram_variants():
    assert parse_ram_gb("16GB") == 16
    assert parse_ram_gb("16 GB") == 16
    assert parse_ram_gb("16384MB") == 16


def test_parse_storage_variants():
    assert parse_storage("512GB") == (512, None)
    assert parse_storage("512 SSD") == (512, "SSD")
    assert parse_storage("512GB SSD") == (512, "SSD")
    assert parse_storage("1TB") == (1024, None)


def test_parse_price_variants():
    price, currency = parse_price("US$ 902.50")
    assert price == pytest.approx(902.50)
    assert currency == "USD"
    price2, currency2 = parse_price("RD$ 45,000")
    assert currency2 == "DOP"


def test_price_question_detection():
    assert PriceQuestionService.is_price_question("¿Quién me sale mejor para laptop 16GB 512GB?")
    assert PriceQuestionService.is_price_question("Busca laptop Dell 16GB RAM 512 SSD")
    assert not PriceQuestionService.is_price_question("¿Cuánto nos debe Banco Ademi?")


def test_price_question_parse_filters():
    svc = PriceQuestionService(db=None, tenant_id=None)  # type: ignore[arg-type]
    filters = svc._parse_question("Busca laptop Dell 16GB RAM 512 SSD disponible")
    assert filters.brand == "Dell"
    assert filters.product_type == "laptop"
    assert filters.ram_gb == 16
    assert filters.storage_gb == 512
    assert filters.stock_disponible is True


@pytest.mark.asyncio
async def test_prices_search_endpoint():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@justech.do",
                "password": "JaiosAdmin2026!",
                "tenant_slug": "justech",
            },
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible en entorno de test")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = await client.get(
            "/api/v1/prices/search",
            params={"categoria": "laptop", "ram_gb": 16, "almacenamiento_gb": 512, "limit": 5},
            headers=headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body


def test_parser_csv_minimal(tmp_path):
    csv_file = tmp_path / "test_prices.csv"
    csv_file.write_text(
        "SKU,Descripcion,Stock,P. Unitario US$\n"
        "ABC123,Laptop Dell 16GB 512GB SSD,5,899.99\n",
        encoding="utf-8",
    )
    result = PriceListParser().parse_file(csv_file, relative_path="03_PROVEEDORES/ENTRADAS/test_prices.csv")
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.sku == "ABC123"
    assert row.ram_gb == 16
    assert row.storage_gb == 512
    assert float(row.price) == pytest.approx(899.99)
