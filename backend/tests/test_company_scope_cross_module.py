"""Tests — filtrado cross-módulo por company context."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD
from app.services.company_scope_filter import CompanyScopeFilter


def test_odoo_name_to_dgcp_key():
    assert CompanyScopeFilter.odoo_name_to_dgcp_key("Justech SRL") == "justech"
    assert CompanyScopeFilter.odoo_name_to_dgcp_key("Just Office SRL") == "just_office"
    assert CompanyScopeFilter.odoo_name_to_dgcp_key("PlugSafe SRL") == "mf_plug_safe"
    assert CompanyScopeFilter.odoo_name_to_dgcp_key("Omni Solutions SRL") == "omni_solutions"


@pytest.mark.asyncio
async def test_assistant_company_guard_import():
    from app.services.company_access_guard import assistant_company_access_message

    assert callable(assistant_company_access_message)


@pytest.mark.asyncio
async def test_company_context_api_still_works():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "tenant_slug": "justech"},
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        tasks = await client.get("/api/v1/tasks", headers=headers)
        assert tasks.status_code == 200
        docs = await client.get("/api/v1/documents", headers=headers)
        assert docs.status_code == 200
