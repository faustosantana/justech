"""Tests — DGCP Expediente Intelligence (Fase 7.3)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from tests.dgcp_test_helpers import analyze_with_interest

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.dgcp_requirements_extractor import DGCPRequirementsExtractor


class _FakeProcessDoc:
    def __init__(self, title: str, doc_role: str = "pliego") -> None:
        self.id = uuid.uuid4()
        self.title = title
        self.doc_role = doc_role


def _sample_opportunity() -> DGCPOpportunity:
    return DGCPOpportunity(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        code="LPN-2024-EXP",
        institution="Ministerio Test",
        title="Adquisición equipos",
        amount=Decimal("250000"),
        deadline=date(2026, 12, 31),
        description="Proceso de prueba con requisitos legales.",
        full_info={},
        raw_payload={},
    )


def test_extractor_evidence_from_process_corpus():
    opp = _sample_opportunity()
    corpus = (
        "Pliego de Condiciones — Documentación Legal. "
        "El oferente deberá presentar certificación vigente de la TSS. "
        "Se requiere visita técnica obligatoria. "
        "Criterios de evaluación: 70% técnico, 30% económico."
    )
    docs = [_FakeProcessDoc("Pliego de Condiciones.pdf", "pliego")]
    result = DGCPRequirementsExtractor().extract(
        opp,
        process_corpus=corpus,
        process_documents=docs,
    )
    tss = next((d for d in result.mandatory_documents if d.key == "certificacion_tss"), None)
    assert tss is not None
    assert tss.evidence
    assert "Pliego" in tss.evidence[0].documento_origen
    assert tss.evidence[0].confianza == "alta"

    visita = next((r for r in result.technical if r.key == "visita_tecnica"), None)
    assert visita is not None


async def _auth_headers() -> dict[str, str] | None:
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
            return None
        return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_dgcp_expediente_api_flow():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        list_res = await client.get("/api/v1/dgcp/opportunities?limit=1", headers=headers)
        if list_res.status_code != 200 or not list_res.json()["items"]:
            pytest.skip("Sin oportunidades DGCP")
        opp_id = list_res.json()["items"][0]["id"]

        analyze = await analyze_with_interest(client, opp_id, headers)
        assert analyze.status_code == 200, analyze.text
        body = analyze.json()
        assert "process_documents" in body
        assert "alerts" in body

        proc_docs = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/process-documents",
            headers=headers,
        )
        assert proc_docs.status_code == 200

        alerts = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/alerts",
            headers=headers,
        )
        assert alerts.status_code == 200
        assert alerts.json()["total"] >= 0

        autofill = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/forms/autofill-preview",
            headers=headers,
            json={"form_type": "SNCC.F042", "company": "justech"},
        )
        assert autofill.status_code == 200
        assert autofill.json()["generate_enabled"] is True
        assert any(f.get("source") for f in autofill.json()["fields"])

        licitar = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/actions",
            headers=headers,
            json={"action": "licitar", "notes": "Interés QA — habilitar expediente"},
        )
        assert licitar.status_code == 200, licitar.text

        prepare = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/prepare",
            headers=headers,
        )
        assert prepare.status_code == 200, prepare.text
        manifest = prepare.json()["manifest"]
        assert manifest.get("opportunity_code")
        assert manifest.get("preparation_pct") is not None

        status = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/status",
            headers=headers,
        )
        assert status.status_code == 200
        assert status.json()["can_download"] is True

        download = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/download",
            headers=headers,
        )
        assert download.status_code == 200
        assert download.headers.get("content-type", "").startswith("application/zip")

        user_input = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/user-input",
            headers=headers,
            json={"fabricante": "Dell", "monto": "RD$250,000"},
        )
        assert user_input.status_code == 200


@pytest.mark.asyncio
async def test_assistant_live_input_updates_expediente():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        list_res = await client.get("/api/v1/dgcp/opportunities?limit=1", headers=headers)
        if not list_res.json().get("items"):
            pytest.skip("Sin oportunidades")
        opp_id = list_res.json()["items"][0]["id"]

        await analyze_with_interest(client, opp_id, headers)

        response = await client.post(
            "/api/v1/assistant/query",
            json={
                "question": "El fabricante es Dell y el monto será RD$250,000",
                "current_module": "/dgcp",
                "record_type": "dgcp",
                "current_record_id": opp_id,
            },
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["query_type"] == "dgcp_requirements_query"
        assert "dell" in body["answer"].lower() or "actualicé" in body["answer"].lower()
