"""Tests conector Ingram — demo + API mock."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from integrations.suppliers.config import IngramConnectorConfig
from integrations.suppliers.ingram_connector import IngramConnector


@pytest.mark.asyncio
async def test_ingram_demo_search():
    cfg = IngramConnectorConfig(enabled=True, demo_mode=True)
    conn = IngramConnector(cfg)
    rows = await conn.search_products("dell laptop 16GB", limit=5)
    assert len(rows) >= 1
    assert rows[0].source == "ingram_demo"
    assert rows[0].price == Decimal("818.51")


@pytest.mark.asyncio
async def test_ingram_api_search_mock():
    cfg = IngramConnectorConfig(
        enabled=True,
        demo_mode=False,
        client_id="cid",
        client_secret="secret",
        customer_number="12345",
        use_sandbox=True,
    )
    conn = IngramConnector(cfg)

    fake_catalog = {
        "catalog": [
            {
                "ingramPartNumber": "ABC123",
                "description": "Dell Pro 14 Test",
                "vendorName": "Dell",
                "pricing": {"customerPrice": 799.99, "currencyCode": "USD"},
                "availability": {"totalAvailability": 10},
            }
        ]
    }

    with patch.object(conn, "_oauth_token", AsyncMock(return_value="token")):
        with patch("httpx.AsyncClient") as client_cls:
            mock_client = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json.return_value = fake_catalog
            mock_resp.raise_for_status = lambda: None
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            client_cls.return_value = mock_client

            rows = await conn._search_api("dell", limit=5)

    assert len(rows) == 1
    assert rows[0].sku == "ABC123"
    assert rows[0].price == Decimal("799.99")
    assert rows[0].stock == 10


@pytest.mark.asyncio
async def test_ingram_disabled_returns_empty():
    cfg = IngramConnectorConfig(enabled=False)
    conn = IngramConnector(cfg)
    assert await conn.search_products("dell") == []
