"""Tests obligatorios del JAIOS Assistant — routing por intención y contexto."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.assistant.router import AssistantRouter, AssistantSource
from app.main import app
from app.services.assistant_context_policy import is_dgcp_record_question
from app.services.assistant_service import READ_ONLY_NOTICE, WRITE_PATTERNS
from app.services.business_intent_router import BusinessIntent, BusinessIntentRouter
from app.services.sales_question_service import SalesQuestionService

MANDATORY_ASSISTANT_CASES = [
    (
        "¿Quién me sale mejor laptop 16GB 512GB?",
        {"current_module": "/prices"},
        ("price_query", "price_compare"),
        ("price_intelligence",),
    ),
    (
        "¿Cuántas laptops hemos vendido?",
        {"current_module": "/odoo"},
        "sales_query",
        ("sales", "odoo"),
    ),
    (
        "¿Qué documentos están vencidos?",
        {"current_module": "/documents"},
        "document_query",
        ("documents",),
    ),
    (
        "¿Qué tareas tiene Jennipher?",
        {"current_module": "/tasks"},
        "tasks_query",
        ("tasks",),
    ),
    (
        "Busca todo sobre Banco Ademi",
        {"current_module": "/search"},
        "enterprise_search_query",
        ("enterprise_search",),
    ),
    (
        "¿Tenemos DGII vigente?",
        {"current_module": "/documents"},
        "document_query",
        ("documents",),
    ),
    (
        "Dime licitaciones de computadoras",
        {"current_module": "/dgcp"},
        "dgcp_query",
        ("dgcp",),
    ),
    (
        "¿Cuántos rollos de papel 350 hemos vendido?",
        {"current_module": "/odoo"},
        "sales_query",
        ("odoo",),
    ),
    (
        "cuantos faldos de papel le hemos vendido a Farma Trix",
        {"current_module": "/work"},
        "sales_query",
        ("odoo",),
    ),
]


def test_assistant_router_ambiguous_defaults_to_search_not_dgcp():
    sources = AssistantRouter.detect_sources("resumen del día", "/dashboard")
    assert AssistantSource.DGCP not in sources
    assert AssistantSource.ENTERPRISE_SEARCH in sources


def test_product_synonyms_papel_termico():
    from app.services.business_terms import detect_product_in_text, expand_product_terms, matches_product_name

    label, terms = detect_product_in_text("cuantos rollos de papel térmico 350 vendimos")
    assert label is not None
    expanded = expand_product_terms("rollo térmico")
    assert any("papel" in t or "350" in t or "termico" in t or "térmico" in t for t in expanded)
    assert matches_product_name("PAPEL TERMICO 350 FT", terms, filter_terms=["papel", "350"])


def test_product_lookup_intent():
    classified = BusinessIntentRouter.classify("papel 350")
    assert classified.intent == BusinessIntent.PRICE
    assert classified.product_label is not None
    parsed = SalesQuestionService.parse_product_lookup("papel 350")
    assert parsed is not None
    assert parsed.product_label is not None


def test_assistant_router_detects_odoo():
    sources = AssistantRouter.detect_sources("¿Cuánto nos debe Banco Ademi?", "/dashboard")
    assert AssistantSource.ODOO in sources


def test_assistant_router_detects_dgcp():
    sources = AssistantRouter.detect_sources("¿Qué procesos DGCP están para licitar?", "/dgcp")
    assert AssistantSource.DGCP in sources


def test_assistant_router_detects_enterprise_search():
    sources = AssistantRouter.detect_sources("Busca todo sobre Dell", "/search")
    assert AssistantSource.ENTERPRISE_SEARCH in sources


def test_assistant_router_detects_m365_stub():
    sources = AssistantRouter.detect_sources("Buscar archivos en SharePoint", "/m365")
    assert AssistantSource.M365_STUB in sources


@pytest.mark.asyncio
async def test_assistant_m365_not_connected():
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
                "question": "¿Tengo correos en Outlook?",
                "current_module": "/m365",
            },
            headers=headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert "no está conectado" in body["answer"].lower()
    assert body["query_type"] == "m365_query"
    assert "m365" in body["sources"]


@pytest.mark.asyncio
async def test_assistant_query_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={"question": "¿Cuánto nos debe el cliente?"},
        )
    assert response.status_code == 401


def test_write_intent_patterns():
    assert "modificar" in WRITE_PATTERNS
    assert READ_ONLY_NOTICE.startswith("No puedo modificar Odoo")


def test_price_question_not_dgcp_record():
    classified = BusinessIntentRouter.classify("¿Quién me sale mejor laptop 16GB 512GB?")
    assert classified.intent == BusinessIntent.PRICE
    assert not is_dgcp_record_question("¿Quién me sale mejor laptop 16GB 512GB?", classified)


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
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        if login.json().get("tenant_id"):
            headers["X-Tenant-ID"] = str(login.json()["tenant_id"])
        yield headers


@pytest.mark.asyncio
@pytest.mark.parametrize("question,payload,expected_query_types,expected_source_fragments", MANDATORY_ASSISTANT_CASES)
async def test_assistant_mandatory_routing(
    auth_headers, question, payload, expected_query_types, expected_source_fragments
):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={"question": question, **payload},
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    allowed = expected_query_types if isinstance(expected_query_types, tuple) else (expected_query_types,)
    assert body["query_type"] in allowed
    sources_joined = " ".join(body.get("sources", [])).lower()
    assert any(fragment in sources_joined or fragment in body["query_type"] for fragment in expected_source_fragments)
    assert "documento(s) obligatorio(s)" not in body["answer"].lower()
    assert body["query_type"] != "dgcp_requirements_query"


@pytest.mark.asyncio
async def test_assistant_dgcp_record_question_with_context(auth_headers):
    opp_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={
                "question": "¿Qué pide esta licitación?",
                "current_module": f"/dgcp/{opp_id}",
                "record_type": "dgcp",
                "current_record_id": opp_id,
            },
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["query_type"] in ("dgcp_requirements_query", "not_found")
    if body["query_type"] == "dgcp_requirements_query":
        assert "dgcp" in body["sources"]


@pytest.mark.asyncio
async def test_assistant_price_question_not_hijacked_by_dgcp_record(auth_headers):
    opp_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={
                "question": "¿Quién me sale mejor laptop 16GB 512GB?",
                "current_module": f"/dgcp/{opp_id}",
                "record_type": "dgcp",
                "current_record_id": opp_id,
            },
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["query_type"] != "dgcp_requirements_query"
    assert "documento(s) obligatorio(s)" not in body["answer"].lower()
    assert body["query_type"] in ("price_query", "not_found", "help") or "price" in body["query_type"]
