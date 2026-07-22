"""Tests Microsoft 365 — OAuth, Graph, admin y webhooks."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from integrations.microsoft365.schemas import M365CalendarEvent, M365SharePointSite

ADMIN_EMAIL = "admin@justech.do"
ADMIN_PASSWORD = "JaiosAdmin2026!"
TENANT_SLUG = "justech"


async def _login(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "tenant_slug": TENANT_SLUG},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_graph_webhook_validation_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/m365/webhooks/graph?validationToken=test-token-123",
        )
    assert resp.status_code == 200
    assert resp.text == "test-token-123"


@pytest.mark.asyncio
async def test_oauth_authorize_url_requires_config():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client)
        resp = await client.get(
            "/api/v1/m365/oauth/authorize-url",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code in (200, 400)
    if resp.status_code == 200:
        assert "authorize_url" in resp.json()
        assert "login.microsoftonline.com" in resp.json()["authorize_url"]


@pytest.mark.asyncio
async def test_m365_admin_config_and_permissions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        cfg = await client.get("/api/v1/admin/m365/config", headers=headers)
        assert cfg.status_code == 200
        body = cfg.json()
        assert "client_id" in body
        assert "oauth_ready" in body

        perms = await client.get("/api/v1/admin/m365/graph-permissions", headers=headers)
        assert perms.status_code == 200
        assert len(perms.json()["delegated_scopes"]) >= 5

        test = await client.post("/api/v1/admin/m365/test-connection", headers=headers)
        assert test.status_code == 200
        assert "message" in test.json()


@pytest.mark.asyncio
async def test_graph_services_with_mock_token():
    from integrations.microsoft365.client import M365Client
    from integrations.microsoft365.config import M365Config
    from integrations.microsoft365.schemas import M365OAuthTokens

    cfg = M365Config(
        tenant_id="00000000-0000-0000-0000-000000000001",
        client_id="00000000-0000-0000-0000-000000000002",
        client_secret="secret",
        redirect_uri="http://localhost/callback",
    )
    client = M365Client(cfg, tokens=M365OAuthTokens(access_token="fake-token"))

    async def fake_request(method, path, **kwargs):
        if "messages" in path:
            return {"value": [{"id": "1", "subject": "Test", "from": {"emailAddress": {"address": "a@b.c"}}}]}
        if "events" in path:
            return {"value": [{"id": "e1", "subject": "Reunión", "start": {"dateTime": "2026-06-10T10:00:00"}}]}
        if "sites" in path:
            return {"value": [{"id": "s1", "displayName": "Intranet", "webUrl": "https://sp.example.com"}]}
        return {"value": []}

    with patch.object(client.graph(), "request", side_effect=fake_request):
        msgs = await client.outlook.list_messages(limit=5)
        events = await client.calendar.list_events(limit=5)
        sites = await client.sharepoint.list_sites(limit=5)

    assert msgs[0].subject == "Test"
    assert events[0].subject == "Reunión"
    assert sites[0].name == "Intranet"


@pytest.mark.asyncio
async def test_oauth_refresh_tokens_mock():
    from app.services.m365_oauth_service import M365OAuthService
    from integrations.microsoft365.schemas import M365OAuthTokens
    from datetime import UTC, datetime, timedelta

    tokens = M365OAuthTokens(
        access_token="new-access",
        refresh_token="new-refresh",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        scopes=["Mail.Read"],
    )
    with patch(
        "app.services.m365_oauth_service.refresh_tokens",
        new_callable=AsyncMock,
        return_value=tokens,
    ):
        # smoke: refresh_tokens import path exists
        assert tokens.access_token == "new-access"
