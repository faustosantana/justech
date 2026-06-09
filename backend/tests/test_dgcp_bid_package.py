"""Tests — DGCP Requirements & Bid Package (Fase 7.1)."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.dgcp_requirements_extractor import DGCPRequirementsExtractor
from tests.dgcp_test_helpers import analyze_with_interest, ensure_operational_interest


def _sample_opportunity() -> DGCPOpportunity:
    from datetime import date
    from decimal import Decimal
    import uuid

    return DGCPOpportunity(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        code="LPN-2024-TEST",
        institution="Ministerio Test",
        title="Adquisición de equipos informáticos",
        amount=Decimal("500000"),
        deadline=date(2026, 12, 31),
        description=(
            "Se requiere RPE vigente, certificación TSS, certificación DGII, "
            "registro mercantil, SNCC F.042, oferta técnica y oferta económica. "
            "Garantía de seriedad de oferta. Presentar muestras físicas."
        ),
        full_info={},
        raw_payload={},
    )


def test_requirements_extractor_finds_documents():
    opp = _sample_opportunity()
    result = DGCPRequirementsExtractor().extract(opp)
    keys = {d.key for d in result.mandatory_documents}
    assert "rpe" in keys
    assert "certificacion_tss" in keys
    assert "sncc_f042" in keys
    assert result.guarantees
    assert result.samples


def test_requirements_extractor_sncc_forms():
    opp = _sample_opportunity()
    opp.description = "Formularios SNCC F.033 y SNCC F.047 requeridos"
    result = DGCPRequirementsExtractor().extract(opp)
    keys = {d.key for d in result.mandatory_documents}
    assert "sncc_f033" in keys
    assert "sncc_f047" in keys
    assert any("33" in f for f in result.sncc_forms)
    assert any("47" in f for f in result.sncc_forms)


@pytest.mark.asyncio
async def test_dgcp_bid_package_endpoints():
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
            pytest.skip("Login no disponible")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        list_res = await client.get("/api/v1/dgcp/opportunities?limit=1", headers=headers)
        if list_res.status_code != 200 or not list_res.json()["items"]:
            pytest.skip("Sin oportunidades DGCP")
        opp_id = list_res.json()["items"][0]["id"]

        analyze = await analyze_with_interest(client, opp_id, headers)
        assert analyze.status_code == 200, analyze.text
        body = analyze.json()
        assert "checklist" in body
        assert body["bid_package"]["preparation_pct"] >= 0

        checklist = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist",
            headers=headers,
        )
        assert checklist.status_code == 200
        assert checklist.json()["total"] >= 1

        preview = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/forms/preview",
            headers=headers,
            json={"form_type": "SNCC.F042", "company": "justech"},
        )
        assert preview.status_code == 200
        assert preview.json()["generate_enabled"] is False


@pytest.mark.asyncio
async def test_parallel_tab_load_without_auto_analyze_race():
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
            pytest.skip("Login no disponible")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        list_res = await client.get("/api/v1/dgcp/opportunities?limit=20", headers=headers)
        if list_res.status_code != 200 or not list_res.json()["items"]:
            pytest.skip("Sin oportunidades DGCP")

        opp_id = None
        for item in list_res.json()["items"]:
            checklist = await client.get(
                f"/api/v1/dgcp/opportunities/{item['id']}/checklist",
                headers=headers,
            )
            if checklist.status_code == 200 and checklist.json()["total"] == 0:
                opp_id = item["id"]
                break
        if not opp_id:
            pytest.skip("Sin oportunidad sin análisis previo")

        responses = await asyncio.gather(
            client.get(f"/api/v1/dgcp/opportunities/{opp_id}/requirements", headers=headers),
            client.get(f"/api/v1/dgcp/opportunities/{opp_id}/checklist", headers=headers),
            client.get(f"/api/v1/dgcp/opportunities/{opp_id}/bid-package", headers=headers),
            client.get(f"/api/v1/dgcp/opportunities/{opp_id}/document-matches", headers=headers),
        )
        assert all(r.status_code == 200 for r in responses), [r.text for r in responses]


@pytest.mark.asyncio
async def test_concurrent_analyze_is_idempotent():
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
            pytest.skip("Login no disponible")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        list_res = await client.get("/api/v1/dgcp/opportunities?limit=1", headers=headers)
        if list_res.status_code != 200 or not list_res.json()["items"]:
            pytest.skip("Sin oportunidades DGCP")
        opp_id = list_res.json()["items"][0]["id"]

        await ensure_operational_interest(client, opp_id, headers)
        responses = await asyncio.gather(
            client.post(
                f"/api/v1/dgcp/opportunities/{opp_id}/requirements/analyze",
                headers=headers,
            ),
            client.post(
                f"/api/v1/dgcp/opportunities/{opp_id}/requirements/analyze",
                headers=headers,
            ),
            client.post(
                f"/api/v1/dgcp/opportunities/{opp_id}/requirements/analyze",
                headers=headers,
            ),
        )
        assert all(r.status_code == 200 for r in responses), [r.text for r in responses]


@pytest.mark.asyncio
async def test_assistant_dgcp_requirements_context():
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
            pytest.skip("Login no disponible")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        list_res = await client.get("/api/v1/dgcp/opportunities?limit=1", headers=headers)
        if not list_res.json().get("items"):
            pytest.skip("Sin oportunidades")
        opp_id = list_res.json()["items"][0]["id"]

        await analyze_with_interest(client, opp_id, headers)

        response = await client.post(
            "/api/v1/assistant/query",
            json={
                "question": "¿Qué porcentaje del expediente está listo?",
                "current_module": "/dgcp",
                "record_type": "dgcp",
                "current_record_id": opp_id,
            },
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["query_type"] == "dgcp_requirements_query"
        assert "expediente" in body["answer"].lower() or "%" in body["answer"]
