"""Tests — Empresas y proveedores."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.mark.asyncio
async def test_companies_require_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/companies")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_companies_crud_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "tenant_slug": "justech",
            },
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible")
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post(
            "/api/v1/companies",
            headers=headers,
            json={
                "name": "Proveedor QA Test",
                "company_type": "proveedor",
                "tax_id": "123456789",
                "email": "qa@test.local",
                "status": "activo",
                "brands": ["HP", "Dell"],
            },
        )
        assert create.status_code == 201, create.text
        company_id = create.json()["id"]
        assert create.json()["name"] == "Proveedor QA Test"

        listing = await client.get(
            "/api/v1/companies?search=Proveedor+QA",
            headers=headers,
        )
        assert listing.status_code == 200
        assert listing.json()["total"] >= 1

        detail = await client.get(f"/api/v1/companies/{company_id}", headers=headers)
        assert detail.status_code == 200

        updated = await client.put(
            f"/api/v1/companies/{company_id}",
            headers=headers,
            json={"category": "Tecnología"},
        )
        assert updated.status_code == 200
        assert updated.json()["category"] == "Tecnología"

        deactivated = await client.post(
            f"/api/v1/companies/{company_id}/deactivate",
            headers=headers,
        )
        assert deactivated.status_code == 200
        assert deactivated.json()["status"] == "inactivo"
