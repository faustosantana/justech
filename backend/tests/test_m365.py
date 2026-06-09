"""Tests Fase 4 — Microsoft 365 Intelligence Center (estructura base)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.assistant.router import AssistantRouter, AssistantSource
from app.main import app
from app.schemas.m365 import NOT_CONNECTED_MESSAGE

M365_ENDPOINTS = [
    "/api/v1/m365/health",
    "/api/v1/m365/status",
    "/api/v1/m365/outlook/messages",
    "/api/v1/m365/sharepoint/sites",
    "/api/v1/m365/onedrive/files",
    "/api/v1/m365/calendar/events",
    "/api/v1/m365/teams",
    "/api/v1/m365/documents",
    "/api/v1/m365/search?q=test",
]


@pytest.mark.parametrize("path", M365_ENDPOINTS)
@pytest.mark.asyncio
async def test_m365_endpoints_require_auth(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)
    assert response.status_code == 401


def test_assistant_router_detects_m365():
    sources = AssistantRouter.detect_sources("¿Tengo correos nuevos en Outlook?", "/m365")
    assert AssistantSource.M365_STUB in sources


def test_assistant_router_detects_m365_from_module():
    sources = AssistantRouter.detect_sources("resumen del día", "/m365")
    assert AssistantSource.M365_STUB in sources


@pytest.mark.asyncio
async def test_m365_health_disconnected_with_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@justech.do",
                "password": "JaiosAdmin2026!",
                "tenant_slug": "justech",
            },
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible en entorno de test")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = await client.get("/api/v1/m365/health", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False
    assert body["read_only"] is True
    assert body["message"] == NOT_CONNECTED_MESSAGE
    assert "required_config" in body
    assert body["required_config"]["read_only"] is True


@pytest.mark.asyncio
async def test_m365_list_endpoints_return_disconnected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@justech.do",
                "password": "JaiosAdmin2026!",
                "tenant_slug": "justech",
            },
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible en entorno de test")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        for path in (
            "/api/v1/m365/outlook/messages",
            "/api/v1/m365/sharepoint/sites",
            "/api/v1/m365/search?q=contrato",
        ):
            response = await client.get(path, headers=headers)
            assert response.status_code == 200, path
            body = response.json()
            assert body["connected"] is False
            assert body["message"] == NOT_CONNECTED_MESSAGE
            assert body["read_only"] is True
            assert "required_config" in body
