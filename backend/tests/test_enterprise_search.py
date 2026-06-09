"""Tests — Búsqueda empresarial global."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.assistant.router import AssistantRouter, AssistantSource
from app.main import app
from app.services.assistant_service import AssistantService


@pytest.fixture
async def auth_headers():
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
        yield {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_assistant_router_detects_enterprise_search():
    sources = AssistantRouter.detect_sources("Busca todo sobre Banco Ademi", "/dashboard")
    assert AssistantSource.ENTERPRISE_SEARCH in sources


def test_extract_enterprise_search_query():
    assert AssistantService._extract_enterprise_search_query("Busca todo sobre Banco Ademi") == "Banco Ademi"
    assert AssistantService._extract_enterprise_search_query("Buscar Dell laptops") == "Dell laptops"


@pytest.mark.asyncio
async def test_search_endpoint_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/search?q=Banco")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_search_endpoint_structure(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for query in ("Banco", "Dell", "MIREX"):
            response = await client.get(
                f"/api/v1/search?q={query}",
                headers=auth_headers,
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["query"] == query
            assert "total" in body
            assert "groups" in body
            assert isinstance(body["groups"], list)
            for group in body["groups"]:
                assert "type" in group
                assert "label" in group
                assert "count" in group
                assert "items" in group
                for item in group["items"]:
                    assert "id" in item
                    assert "type" in item
                    assert "title" in item
                    assert "source" in item
                    assert "url" in item
                    assert "score" in item


@pytest.mark.asyncio
async def test_search_short_query_returns_empty(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/search?q=a", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_assistant_uses_enterprise_search(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={
                "question": "Busca todo sobre Banco Ademi",
                "current_module": "/dashboard",
            },
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["query_type"] in ("enterprise_search_query", "enterprise_search", "enterprise_search_empty")
    assert any(
        s in ("enterprise_search", "Búsqueda empresarial") for s in body.get("sources", [])
    )
