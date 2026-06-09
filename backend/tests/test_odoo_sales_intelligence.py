"""Tests Fase 3.5 — Odoo Sales Intelligence."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_odoo_vendors_list_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/odoo/vendors")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_odoo_vendors_route_not_parsed_as_id():
    """GET /vendors debe ir antes de /vendors/{id}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/odoo/vendors")
    assert response.status_code == 401
    assert "int_parsing" not in response.text
