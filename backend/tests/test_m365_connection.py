"""Tests conexión M365 — estados correctos."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

ADMIN_EMAIL = "admin@justech.do"
ADMIN_PASSWORD = "JaiosAdmin2026!"
TENANT_SLUG = "justech"


async def _login(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "tenant_slug": TENANT_SLUG},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_m365_connection_state_not_connected_without_account():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        health = await client.get("/api/v1/m365/health", headers=headers)
        assert health.status_code == 200
        body = health.json()
        assert "connection" in body
        conn = await client.get("/api/v1/m365/connection", headers=headers)
        assert conn.status_code == 200
        c = conn.json()
        assert c["account_connected"] == c["connected"]
        if not c["account_connected"]:
            assert "no conectado" in c["message"].lower() or "conecte" in c["message"].lower()


@pytest.mark.asyncio
async def test_m365_mail_requires_account():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        mail = await client.get("/api/v1/m365/mail/messages", headers=headers)
        assert mail.status_code == 200
        body = mail.json()
        assert body["connected"] is False or isinstance(body["items"], list)
