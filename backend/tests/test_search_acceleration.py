"""Tests Fase 6.5 — Search Acceleration Engine."""

import time
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.search_cache_service import SearchCacheService


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
        token = login.json()["access_token"]
        tenant_id = login.json().get("tenant_id")
        headers = {"Authorization": f"Bearer {token}"}
        if tenant_id:
            headers["X-Tenant-ID"] = str(tenant_id)
        yield headers


@pytest.mark.asyncio
async def test_search_analytics_endpoint(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/v1/search?q=Banco", headers=auth_headers)
        response = await client.get("/api/v1/search/analytics?days=7", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert "top_queries" in body
    assert body["summary"]["total_queries"] >= 1
    assert "avg_latency_ms" in body["summary"]
    assert "cache_hit_ratio" in body["summary"]


@pytest.mark.asyncio
async def test_search_cache_hit_second_request(auth_headers):
    tenant_id = auth_headers.get("X-Tenant-ID")
    if tenant_id:
        await SearchCacheService().invalidate_tenant(uuid.UUID(tenant_id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/api/v1/search?q=Dell", headers=auth_headers)
        assert first.status_code == 200
        assert first.json().get("cache_hit") is False
        assert first.json().get("latency_ms") is not None

        second = await client.get("/api/v1/search?q=Dell", headers=auth_headers)
        assert second.status_code == 200
        body = second.json()
        assert body.get("cache_hit") is True
        assert body["total"] == first.json()["total"]
        assert body.get("latency_ms", 9999) <= first.json().get("latency_ms", 0) + 50


@pytest.mark.asyncio
async def test_search_response_includes_acceleration_meta(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/search?q=MIREX", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "cache_hit" in body
    assert "index_hit" in body
    assert "latency_ms" in body


@pytest.mark.asyncio
async def test_search_benchmark_cache_improvement(auth_headers):
    """Compara latencia fría vs cache (segunda petición)."""
    tenant_id = auth_headers.get("X-Tenant-ID")
    if tenant_id:
        await SearchCacheService().invalidate_tenant(uuid.UUID(tenant_id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        q = "Banco%20Ademi"
        t0 = time.perf_counter()
        cold = await client.get(f"/api/v1/search?q={q}", headers=auth_headers)
        cold_ms = int((time.perf_counter() - t0) * 1000)

        t1 = time.perf_counter()
        warm = await client.get(f"/api/v1/search?q={q}", headers=auth_headers)
        warm_ms = int((time.perf_counter() - t1) * 1000)

    assert cold.status_code == 200
    assert warm.status_code == 200
    assert warm.json()["cache_hit"] is True
    api_cold = cold.json().get("latency_ms") or cold_ms
    api_warm = warm.json().get("latency_ms") or warm_ms
    print(f"\n[benchmark Banco Ademi] cold={api_cold}ms warm={api_warm}ms http_cold={cold_ms}ms http_warm={warm_ms}ms")
    assert warm.json()["cache_hit"] is True
    if api_cold > 0:
        assert api_warm <= api_cold


@pytest.mark.asyncio
async def test_banco_ademi_and_assistant(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        search = await client.get(
            "/api/v1/search?q=Banco%20Ademi", headers=auth_headers
        )
        assert search.status_code == 200
        assert search.json()["query"] == "Banco Ademi"

        assistant = await client.post(
            "/api/v1/assistant/query",
            json={
                "question": "Busca todo sobre Banco Ademi",
                "current_module": "/search",
            },
            headers=auth_headers,
        )
        assert assistant.status_code == 200
        assert assistant.json()["query_type"] in (
            "enterprise_search_query", "enterprise_search", "enterprise_search_empty"
        )
