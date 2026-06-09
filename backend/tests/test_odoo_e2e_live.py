"""Validación E2E live Odoo — requiere Odoo configurado y datos reales."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD
from app.config import settings

ODOO_PATHS = [
    "health",
    "summary",
    "customers",
    "products",
    "vendors",
    "invoices/open",
    "invoices/overdue",
    "quotations",
    "opportunities",
    "projects",
]


def _odoo_configured() -> bool:
    return bool(
        settings.odoo_url
        and settings.odoo_db
        and settings.odoo_username
        and settings.odoo_api_key
    )


@pytest.mark.asyncio
async def test_odoo_endpoints_require_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ODOO_PATHS:
            response = await client.get(f"/api/v1/odoo/{path}")
            assert response.status_code == 401, path


@pytest.mark.asyncio
@pytest.mark.skipif(not _odoo_configured(), reason="Odoo no configurado")
async def test_odoo_live_endpoints_return_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=120) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "tenant_slug": "justech",
            },
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        health = await client.get("/api/v1/odoo/health", headers=headers)
        assert health.status_code == 200
        assert health.json()["connected"] is True

        list_paths = [
            "customers",
            "products",
            "vendors",
            "invoices/open",
            "invoices/overdue",
            "quotations",
            "opportunities",
            "projects",
        ]
        for path in list_paths:
            response = await client.get(f"/api/v1/odoo/{path}", headers=headers)
            assert response.status_code == 200, f"{path}: {response.text[:500]}"
            body = response.json()
            assert body.get("connected") is True, path
            assert isinstance(body.get("items"), list), path
            assert body.get("total", 0) > 0, f"{path} sin datos"
            assert len(body["items"]) > 0, f"{path} items vacío"

        not_found = await client.post(
            "/api/v1/odoo/link-user",
            json={"odoo_login": "noexiste-jaios-qa@justech.do"},
            headers=headers,
        )
        assert not_found.status_code == 400
        assert not_found.json()["error"] == "ODOO_USER_NOT_FOUND"

        link = await client.post(
            "/api/v1/odoo/link-user",
            json={"odoo_login": "fausto@justech.do"},
            headers=headers,
        )
        assert link.status_code == 200, link.text
        mapping = link.json()
        assert mapping["odoo_user_id"] > 0
        assert mapping["odoo_login"] == "fausto@justech.do"
        assert mapping["is_active"] is True
        assert len(mapping["allowed_company_ids"]) > 0

        me = await client.get("/api/v1/odoo/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["user_mapping"]["odoo_user_id"] == mapping["odoo_user_id"]

        companies = await client.get("/api/v1/odoo/companies", headers=headers)
        assert companies.status_code == 200
        company_ids = {c["id"] for c in companies.json()["items"]}
        assert company_ids.issubset(set(mapping["allowed_company_ids"]))
        assert len(company_ids) > 0

        # Fase 3.5 — Sales Intelligence (detalle con datos reales)
        customers = await client.get("/api/v1/odoo/customers?limit=1", headers=headers)
        assert customers.status_code == 200
        customer_id = customers.json()["items"][0]["id"]
        customer_detail = await client.get(
            f"/api/v1/odoo/customers/{customer_id}", headers=headers
        )
        assert customer_detail.status_code == 200, customer_detail.text[:500]
        cd = customer_detail.json()
        assert cd["connected"] is True
        assert "total_sales_historical" in cd
        assert isinstance(cd["open_invoices"], list)
        assert isinstance(cd["products_purchased"], list)

        products = await client.get("/api/v1/odoo/products?limit=1", headers=headers)
        assert products.status_code == 200
        product_id = products.json()["items"][0]["id"]
        product_detail = await client.get(
            f"/api/v1/odoo/products/{product_id}", headers=headers
        )
        assert product_detail.status_code == 200, product_detail.text[:500]
        pd = product_detail.json()
        assert pd["connected"] is True
        assert "min_price" in pd and "max_price" in pd
        assert "estimated_margin_pct" in pd
        assert isinstance(pd["sales_history"], list)
        assert isinstance(pd["purchase_history"], list)
        assert isinstance(pd["buyers"], list)

        open_inv = await client.get("/api/v1/odoo/invoices/open?limit=1", headers=headers)
        if open_inv.json().get("total", 0) > 0:
            invoice_id = open_inv.json()["items"][0]["id"]
            invoice_detail = await client.get(
                f"/api/v1/odoo/invoices/{invoice_id}", headers=headers
            )
            assert invoice_detail.status_code == 200, invoice_detail.text[:500]
            inv = invoice_detail.json()
            assert inv["connected"] is True
            assert isinstance(inv["lines"], list)
            assert "amount_residual" in inv
            if inv["lines"]:
                assert "product_id" in inv["lines"][0]
                assert "discount" in inv["lines"][0]
                assert "subtotal" in inv["lines"][0]

        vendors = await client.get("/api/v1/odoo/vendors?limit=1", headers=headers)
        assert vendors.status_code == 200
        assert vendors.json().get("total", 0) > 0
        vendor_id = vendors.json()["items"][0]["id"]
        vendor_detail = await client.get(
            f"/api/v1/odoo/vendors/{vendor_id}", headers=headers
        )
        assert vendor_detail.status_code == 200, vendor_detail.text[:500]
        vd = vendor_detail.json()
        assert vd["connected"] is True
        assert isinstance(vd["purchase_history"], list)
        assert isinstance(vd["products_supplied"], list)
        assert "total_purchase_value" in vd
