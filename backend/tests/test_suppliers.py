"""Tests — Directorio inteligente de proveedores."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.mark.asyncio
async def test_suppliers_require_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/suppliers")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_suppliers_crud_search_flow():
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

        categories = await client.get("/api/v1/suppliers/categories/list", headers=headers)
        assert categories.status_code == 200
        assert categories.json()["total"] >= 20

        create = await client.post(
            "/api/v1/suppliers",
            headers=headers,
            json={
                "name": "Distribuidor QA Toners",
                "company_type": "distribuidor",
                "tax_id": "999888777",
                "email": "toners@qa.test",
                "whatsapp": "8095551234",
                "brands": ["HP", "Canon"],
                "products_services": ["toners", "cartuchos", "consumibles"],
                "status": "activo",
            },
        )
        assert create.status_code == 201, create.text
        supplier_id = create.json()["id"]

        search = await client.post(
            "/api/v1/suppliers/search",
            headers=headers,
            json={"query": "Necesito comprar toners HP", "limit": 10},
        )
        assert search.status_code == 200
        assert search.json()["total"] >= 1

        quote = await client.post(
            f"/api/v1/suppliers/{supplier_id}/request-quote",
            headers=headers,
            json={"products": ["toners HP"], "channel": "both"},
        )
        assert quote.status_code == 200
        assert quote.json()["whatsapp_message"]

        tender = await client.post(
            "/api/v1/suppliers/tender-suggestions",
            headers=headers,
            json={"description": "Licitación requiere laptops e impresoras", "limit": 5},
        )
        assert tender.status_code == 200

        updated = await client.put(
            f"/api/v1/suppliers/{supplier_id}",
            headers=headers,
            json={"status": "preferido", "internal_rating": 4.5},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "preferido"

        deleted = await client.delete(f"/api/v1/suppliers/{supplier_id}", headers=headers)
        assert deleted.status_code == 204
