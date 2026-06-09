import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from integrations.odoo.company_context import OdooCompanyContext, apply_company_domain
from integrations.odoo.exceptions import OdooReadOnlyError
from integrations.odoo.safe_client import SafeOdooClient


def test_apply_company_domain_filters_invoices():
    domain = [("move_type", "=", "out_invoice")]
    result = apply_company_domain(domain, "account.move", 3)
    assert ("company_id", "=", 3) in result


def test_apply_company_domain_shared_products():
    domain = [("sale_ok", "=", True)]
    result = apply_company_domain(domain, "product.product", 2, include_shared=True)
    assert "|" in result
    assert ("company_id", "=", False) in result
    assert ("company_id", "=", 2) in result


def test_apply_company_domain_skips_unknown_model():
    domain = [("customer_rank", ">", 0)]
    result = apply_company_domain(domain, "res.partner", 1)
    assert result == domain


def test_odoo_company_context_to_odoo_context():
    ctx = OdooCompanyContext.from_company_id(5)
    assert ctx.to_odoo_context() == {"allowed_company_ids": [5], "company_id": 5}


@pytest.mark.asyncio
async def test_odoo_companies_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/odoo/companies")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_odoo_company_context_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        get_res = await client.get("/api/v1/odoo/company-context")
        put_res = await client.put(
            "/api/v1/odoo/company-context",
            json={"odoo_company_id": 1},
        )
    assert get_res.status_code == 401
    assert put_res.status_code == 401


@pytest.mark.asyncio
async def test_odoo_me_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/odoo/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_safe_client_passes_company_context():
    raw = MagicMock()
    raw.is_configured = True
    raw.search_read = AsyncMock(return_value=[])
    ctx = OdooCompanyContext.from_company_id(7)
    safe = SafeOdooClient(
        raw,
        read_only=True,
        company_context=ctx,
        jaios_user_id=uuid.uuid4(),
    )
    await safe.search_read("account.move", [], ["name"], limit=5)
    raw.search_read.assert_awaited_once()
    call_kwargs = raw.search_read.call_args.kwargs
    assert call_kwargs["context"] == {"allowed_company_ids": [7], "company_id": 7}


@pytest.mark.asyncio
async def test_safe_client_write_blocked_with_user_context():
    raw = MagicMock()
    raw.is_configured = True
    audit = AsyncMock()
    uid = uuid.uuid4()
    safe = SafeOdooClient(
        raw,
        read_only=True,
        audit_callback=audit,
        company_context=OdooCompanyContext.from_company_id(1),
        jaios_user_id=uid,
    )
    with pytest.raises(OdooReadOnlyError):
        await safe.execute_kw("res.partner", "write", [[1], {"name": "x"}])
    audit.assert_awaited_once()
    details = audit.call_args[0][2]
    assert details["jaios_user_id"] == str(uid)
    assert details["company_id"] == 1
