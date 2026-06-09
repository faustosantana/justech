"""Tests — contexto global multiempresa."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD
from app.services.customer_entity_resolver import CustomerEntityResolver


@pytest.mark.asyncio
async def test_company_context_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/company-context")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_company_context_get_and_allowed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "tenant_slug": "justech"},
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        ctx = await client.get("/api/v1/company-context", headers=headers)
        assert ctx.status_code == 200
        body = ctx.json()
        assert "scope_label" in body
        assert "allowed_companies" in body

        allowed = await client.get("/api/v1/company-context/allowed", headers=headers)
        assert allowed.status_code == 200


def test_customer_entity_resolver_aliases():
    terms = CustomerEntityResolver.expand_query("farma trix")
    assert any("farmatrix" in t or "farma trix" in t for t in terms)

    terms2 = CustomerEntityResolver.expand_query("ademi")
    assert any("ademi" in t for t in terms2)
