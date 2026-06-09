"""Tests vinculación cuenta Odoo por usuario (Fase 3.4)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_odoo_link_user_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        post = await client.post("/api/v1/odoo/link-user", json={"odoo_login": "a@b.com"})
        delete = await client.delete("/api/v1/odoo/link-user")
    assert post.status_code == 401
    assert delete.status_code == 401


@pytest.mark.asyncio
async def test_odoo_unlink_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/v1/odoo/link-user")
    assert response.status_code == 401


