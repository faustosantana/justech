"""Tests — Corporate Knowledge Repository (Fase 7.2)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.knowledge_classifier import KnowledgeClassifier
from app.services.vigency_engine import VigencyEngine


def test_classifier_detects_rpe_from_filename():
    result = KnowledgeClassifier().classify(
        relative_path="01_DOCUMENTOS_LEGALES/JUSTECH/RPE Justech.pdf",
        filename="RPE Justech.pdf",
        text="Registro de Proveedores del Estado",
    )
    assert result.document_type == "rpe"
    assert result.company_key == "justech"


def test_classifier_detects_dgii_and_tss():
    clf = KnowledgeClassifier()
    dgii = clf.classify(
        relative_path="01_DOCUMENTOS_LEGALES/JUSTECH/DGII Certificacion.pdf",
        filename="DGII Certificacion.pdf",
        text="certificación dgii obligaciones",
    )
    tss = clf.classify(
        relative_path="01_DOCUMENTOS_LEGALES/JUSTECH/Certificacion TSS.pdf",
        filename="Certificacion TSS.pdf",
        text="certificación tss seguro social",
    )
    assert dgii.document_type == "dgii"
    assert tss.document_type == "tss"


def test_vigency_engine_classifies():
    from datetime import date, timedelta

    engine = VigencyEngine()
    assert engine.classify(date.today() + timedelta(days=60)) == "vigente"
    assert engine.classify(date.today() + timedelta(days=5)) == "proximo_a_vencer"
    assert engine.classify(date.today() - timedelta(days=1)) == "vencido"
    assert engine.classify(None) == "sin_fecha"


@pytest.mark.asyncio
async def test_knowledge_sync_and_search():
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

        health = await client.get("/api/v1/knowledge/health", headers=headers)
        assert health.status_code == 200
        if not health.json().get("source_available"):
            pytest.skip("JustechAI source not mounted")

        sync = await client.post("/api/v1/knowledge/sync", headers=headers)
        assert sync.status_code == 200, sync.text
        body = sync.json()
        assert body["assets_synced"] >= 1

        for doc_type in ("rpe", "dgii", "tss"):
            assets = await client.get(
                f"/api/v1/knowledge/assets?document_type={doc_type}&company_key=justech",
                headers=headers,
            )
            assert assets.status_code == 200
            assert assets.json()["total"] >= 1, f"Missing {doc_type} in knowledge repo"

        search = await client.get("/api/v1/knowledge/search?q=RPE", headers=headers)
        assert search.status_code == 200
        assert search.json()["total"] >= 1


@pytest.mark.asyncio
async def test_dgcp_smart_matching_uses_knowledge():
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

        health = await client.get("/api/v1/knowledge/health", headers=headers)
        if not health.json().get("source_available"):
            pytest.skip("JustechAI source not mounted")

        await client.post("/api/v1/knowledge/sync", headers=headers)

        list_res = await client.get("/api/v1/dgcp/opportunities?limit=1", headers=headers)
        if list_res.status_code != 200 or not list_res.json()["items"]:
            pytest.skip("Sin oportunidades DGCP")
        opp_id = list_res.json()["items"][0]["id"]

        from tests.dgcp_test_helpers import analyze_with_interest

        analyze = await analyze_with_interest(client, opp_id, headers)
        assert analyze.status_code == 200, analyze.text
        matches = analyze.json()["document_matches"]["matches"]
        knowledge_hits = [m for m in matches if m.get("match_source") == "knowledge_repository"]
        assert len(knowledge_hits) >= 3, "Expected RPE/DGII/TSS from corporate repository"


@pytest.mark.asyncio
async def test_assistant_corporate_knowledge_query():
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

        health = await client.get("/api/v1/knowledge/health", headers=headers)
        if not health.json().get("source_available"):
            pytest.skip("JustechAI source not mounted")
        await client.post("/api/v1/knowledge/sync", headers=headers)

        response = await client.post(
            "/api/v1/assistant/query",
            json={"question": "¿Dónde está el RPE de Justech?"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["query_type"] == "document_query"
        assert "rpe" in body["answer"].lower() or "repositorio" in body["answer"].lower() or "documento" in body["answer"].lower()
