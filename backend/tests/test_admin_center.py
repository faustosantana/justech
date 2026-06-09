"""Tests Fase 5.2 — Admin Center + M365 accounts."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.mark.asyncio
async def test_admin_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/admin/access")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_center_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "tenant_slug": "justech"},
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        access = await client.get("/api/v1/admin/access", headers=headers)
        assert access.status_code == 200
        body = access.json()
        assert body["can_view"] is True
        assert body["can_mutate"] is True

        modules = await client.get("/api/v1/admin/modules", headers=headers)
        assert modules.status_code == 200
        assert len(modules.json()["items"]) >= 7

        rules = await client.get("/api/v1/admin/routing-rules", headers=headers)
        assert rules.status_code == 200
        assert len(rules.json()["items"]) >= 1

        m365 = await client.post(
            "/api/v1/m365/accounts/prepare",
            headers=headers,
            json={"email": "usuario@m365.preparado"},
        )
        assert m365.status_code == 201
        assert m365.json()["connection_status"] == "prepared"


@pytest.mark.asyncio
async def test_member_cannot_access_admin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "marieli@justech.do",
                "password": "JaiosTeam2026!",
                "tenant_slug": "justech",
            },
        )
        if login.status_code != 200:
            pytest.skip("Usuario equipo no disponible — ejecutar seed")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        access = await client.get("/api/v1/admin/access", headers=headers)
        assert access.status_code == 200
        assert access.json()["can_view"] is False

        users = await client.get("/api/v1/admin/users", headers=headers)
        assert users.status_code == 403
