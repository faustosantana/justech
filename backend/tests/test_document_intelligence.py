"""Tests — Document Intelligence Platform (Fase 7)."""

import io

import pytest
from httpx import ASGITransport, AsyncClient

from app.assistant.router import AssistantRouter, AssistantSource
from app.main import app
from app.services.business_intent_router import BusinessIntent, BusinessIntentRouter
from app.services.document_intelligence_engine import DocumentIntelligenceEngine
from app.services.document_completion_service import DocumentCompletionService


def test_document_intent_router_classifies_rpe():
    parsed = BusinessIntentRouter.classify("¿Dónde está el RPE de Justech?")
    assert parsed.intent == BusinessIntent.DOCUMENT
    assert parsed.search_term is not None
    assert "rpe" in parsed.search_term.lower() or "justech" in parsed.search_term.lower()


def test_document_intent_router_sncc_completion():
    parsed = BusinessIntentRouter.classify("Busca el formulario SNCC F042")
    assert parsed.intent == BusinessIntent.DOCUMENT
    assert parsed.sub_intent == "completion_preview"


def test_document_intent_router_licitacion_expediente():
    parsed = BusinessIntentRouter.classify("¿Qué documentos faltan para esta licitación?")
    assert parsed.intent == BusinessIntent.DOCUMENT
    assert parsed.sub_intent == "expediente"


def test_assistant_router_detects_documents():
    sources = AssistantRouter.detect_sources("¿Qué documentos tenemos de Banco Ademi?", "/documents")
    assert AssistantSource.DOCUMENTS in sources


def test_intelligence_engine_extracts_entities():
    text = (
        "Certificación TSS vigente hasta 31/12/2026. "
        "Cliente: Banco Ademi. RNC 101234567. "
        "Contacto: info@justech.do Tel 809-555-1234"
    )
    result = DocumentIntelligenceEngine().analyze(
        text=text,
        title="Certificación TSS Justech",
        filename="tss.pdf",
        category="certificacion_tss",
    )
    assert result.document_type == "certificacion_tss"
    assert result.summary
    assert result.entities.get("emails")


def test_completion_preview_sncc_f042():
    preview = DocumentCompletionService().preview(form_type="SNCC.F042", company_key="justech")
    assert preview.form_type == "SNCC.F042"
    assert preview.fields.get("razon_social")
    assert "no se modifica" in preview.note.lower()


@pytest.mark.asyncio
async def test_documents_health_endpoint():
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
        response = await client.get("/api/v1/documents/health", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "documents_count" in body
    assert body["enabled"] is True


@pytest.mark.asyncio
async def test_register_and_search_document():
    transport = ASGITransport(app=app)
    content = (
        "Contrato de servicios con Banco Ademi. "
        "Proveedor Ingram Micro. Referencia DGCP-LPN-2024-001. "
        "Vigencia hasta 31/12/2027."
    ).encode("utf-8")

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
        upload = await client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": ("contrato_ademi.txt", io.BytesIO(content), "text/plain")},
            data={"title": "Contrato Banco Ademi", "client_name": "Banco Ademi"},
        )
        assert upload.status_code == 200, upload.text
        doc = upload.json()
        assert doc["title"] == "Contrato Banco Ademi"

        search = await client.get(
            "/api/v1/documents/search",
            headers=headers,
            params={"q": "Ingram"},
        )
        assert search.status_code == 200
        hits = search.json()["hits"]
        assert any("Ingram" in h["snippet"] or "Ingram" in h["title"] for h in hits)


@pytest.mark.asyncio
async def test_assistant_document_query():
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
        response = await client.post(
            "/api/v1/assistant/query",
            json={
                "question": "¿Qué certificaciones vencen este mes?",
                "current_module": "/documents",
            },
            headers=headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["query_type"] == "document_query"
    assert "documents" in body["sources"]
