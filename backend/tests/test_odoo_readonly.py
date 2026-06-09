import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from integrations.odoo.client import OdooClient
from integrations.odoo.exceptions import OdooReadOnlyError
from integrations.odoo.safe_client import SafeOdooClient


@pytest.mark.asyncio
async def test_odoo_health_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/odoo/health")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_odoo_invoices_open_not_parsed_as_id():
    """Rutas fijas /invoices/open y /overdue deben ir antes de /invoices/{id}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        open_res = await client.get("/api/v1/odoo/invoices/open")
        overdue_res = await client.get("/api/v1/odoo/invoices/overdue")
    assert open_res.status_code == 401
    assert overdue_res.status_code == 401
    assert "int_parsing" not in open_res.text
    assert "int_parsing" not in overdue_res.text


@pytest.mark.asyncio
async def test_odoo_customers_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/odoo/customers")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_safe_client_blocks_write():
    raw = MagicMock(spec=OdooClient)
    raw.is_configured = True
    audit = AsyncMock()
    safe = SafeOdooClient(raw, read_only=True, audit_callback=audit)

    with pytest.raises(OdooReadOnlyError) as exc:
        await safe.execute_kw("res.partner", "write", [[1], {"name": "test"}])

    assert "Odoo está en modo solo lectura" in str(exc.value)
    audit.assert_awaited_once()
    call_args = audit.call_args[0]
    assert call_args[0] == "odoo.write_blocked"
    assert call_args[1] == "res.partner"


@pytest.mark.asyncio
async def test_safe_client_blocks_create():
    raw = MagicMock(spec=OdooClient)
    raw.is_configured = True
    safe = SafeOdooClient(raw, read_only=True)

    with pytest.raises(OdooReadOnlyError):
        await safe.execute_kw("sale.order", "create", [{"partner_id": 1}])


@pytest.mark.asyncio
async def test_safe_client_blocks_action_confirm():
    raw = MagicMock(spec=OdooClient)
    raw.is_configured = True
    safe = SafeOdooClient(raw, read_only=True)

    with pytest.raises(OdooReadOnlyError):
        await safe.execute_kw("sale.order", "action_confirm", [[1]])


@pytest.mark.asyncio
async def test_safe_client_allows_search_read():
    raw = MagicMock(spec=OdooClient)
    raw.is_configured = True
    raw.search_read = AsyncMock(return_value=[{"id": 1, "name": "Test"}])
    safe = SafeOdooClient(raw, read_only=True)

    result = await safe.search_read("res.partner", [], ["name"], limit=1)
    assert result == [{"id": 1, "name": "Test"}]
    raw.search_read.assert_awaited_once()


@pytest.mark.asyncio
async def test_safe_client_write_allowed_when_not_read_only():
    raw = MagicMock(spec=OdooClient)
    raw.is_configured = True
    raw.execute_kw = AsyncMock(return_value=True)
    safe = SafeOdooClient(raw, read_only=False)

    result = await safe.execute_kw("res.partner", "write", [[1], {"name": "ok"}])
    assert result is True
    raw.execute_kw.assert_awaited_once()
