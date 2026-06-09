"""Tests — BusinessIntentRouter y QA obligatorio del Assistant."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.business_intent_router import BusinessIntent, BusinessIntentRouter
from app.services.sales_question_service import SalesIntent, SalesQuestionService

QA_CASES = [
    ("hemos vendido teclados?", BusinessIntent.SALES, "teclado"),
    ("cuántas laptops hemos vendido?", BusinessIntent.SALES, "laptop"),
    ("cuánto hemos vendido en laptops?", BusinessIntent.SALES, "laptop"),
    ("qué clientes compraron laptops?", BusinessIntent.SALES, "laptop"),
    ("licencias microsoft le hemos vendido a Banco Ademi?", BusinessIntent.SALES, "microsoft"),
    ("qué le hemos vendido a Banco Ademi?", BusinessIntent.SALES, None),
    ("qué proveedor nos vendió laptops?", BusinessIntent.PURCHASE, "laptop"),
    ("a quién le compramos teclados?", BusinessIntent.PURCHASE, "teclado"),
    ("cuál fue el último costo de Dell?", BusinessIntent.PURCHASE, "dell"),
    ("dime qué licitaciones hay de licencias", BusinessIntent.DGCP, "licencia"),
    ("dime qué licitaciones hay de computadoras", BusinessIntent.DGCP, "computadora"),
    ("hay licitaciones de impresoras?", BusinessIntent.DGCP, "impresora"),
    ("qué tareas tiene Jennipher?", BusinessIntent.TASKS, None),
    ("qué tiene pendiente Diana?", BusinessIntent.TASKS, None),
    ("cuáles tareas están vencidas?", BusinessIntent.TASKS, None),
    ("busca correos de Banco Ademi", BusinessIntent.M365, None),
    ("busca todo sobre Banco Ademi", BusinessIntent.ENTERPRISE_SEARCH, None),
    ("busca Dell", BusinessIntent.ENTERPRISE_SEARCH, None),
]


@pytest.mark.parametrize("question,expected_intent,entity_fragment", QA_CASES)
def test_business_intent_router_classifies(question, expected_intent, entity_fragment):
    parsed = BusinessIntentRouter.classify(question)
    assert parsed.intent == expected_intent
    if entity_fragment and expected_intent == BusinessIntent.SALES:
        assert parsed.product_label is not None
        assert entity_fragment.lower() in parsed.product_label.lower()
    if entity_fragment and expected_intent == BusinessIntent.PURCHASE:
        assert parsed.product_label is not None
        assert entity_fragment.lower() in parsed.product_label.lower()
    if entity_fragment and expected_intent == BusinessIntent.DGCP:
        assert parsed.product_label is not None
        assert entity_fragment.lower() in parsed.product_label.lower()


def test_informal_sales_teclados_parser():
    parsed = SalesQuestionService.parse("hemos vendido teclados?")
    assert parsed.intent == SalesIntent.SALES_QUANTITY
    assert parsed.product_label is not None
    assert "teclado" in parsed.product_label.lower() or "teclados" in parsed.product_label.lower()
    assert len(parsed.search_terms) >= 1


def test_never_insufficient_for_clear_product():
    parsed = SalesQuestionService.parse("hemos vendido teclados?")
    assert parsed.intent != SalesIntent.INSUFFICIENT


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
@pytest.mark.parametrize("question,expected_intent,_", QA_CASES)
async def test_assistant_qa_no_generic_help(auth_headers, question, expected_intent, _):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={"question": question, "current_module": "/dashboard"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["query_type"] != "help"
    assert "Puedo ayudarte con ventas" not in body["answer"]
    assert "Puedo responder sobre:" not in body["answer"]
    assert "No tengo información suficiente" not in body["answer"]
    assert body["query_type"] in (
        "sales_query",
        "purchase_query",
        "dgcp_query",
        "tasks_query",
        "customer_finance_query",
        "supplier_query",
        "enterprise_search_query",
        "m365_query",
        "not_connected",
        "not_found",
    ) or body["query_type"] == expected_intent.value


@pytest.mark.asyncio
async def test_assistant_teclados_sales_query(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={"question": "hemos vendido teclados?", "current_module": "/odoo"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["query_type"] == "sales_query"
    assert "No tengo información suficiente" not in body["answer"]
    sd = body.get("structured_data")
    if sd and "No encontré" not in body["answer"]:
        assert sd["type"] == "business_answer"
        assert sd["intent"] == "sales_query"
