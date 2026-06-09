"""Tests — intención de ventas en JAIOS Assistant."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.sales_question_service import SalesIntent, SalesQuestionService

SALES_QUESTIONS = [
    ("¿Cuántas laptops hemos vendido?", SalesIntent.SALES_QUANTITY, "laptops"),
    ("¿Cuántos monitores hemos vendido?", SalesIntent.SALES_QUANTITY, "monitores"),
    ("¿Qué clientes compraron laptops?", SalesIntent.BUYERS, "laptops"),
    ("¿Cuánto hemos vendido en laptops?", SalesIntent.SALES_AMOUNT, "laptops"),
    ("¿En cuánto vendimos la última laptop Dell?", SalesIntent.LAST_PRICE, "laptop"),
    ("¿Cuántas licencias Microsoft hemos vendido?", SalesIntent.SALES_QUANTITY, "licencias Microsoft"),
]

CUSTOMER_QUESTIONS = [
    (
        "¿Licencias Microsoft le hemos vendido a Banco Ademi?",
        SalesIntent.SALES_TO_CUSTOMER,
        "licencias Microsoft",
        "Banco Ademi",
    ),
    (
        "licencia de microsoft le hemos vendido a Banco ademi?",
        SalesIntent.SALES_TO_CUSTOMER,
        "licencia de microsoft",
        "Banco ademi",
    ),
    ("¿Qué le hemos vendido a Banco Ademi?", SalesIntent.CUSTOMER_SALES_LIST, None, "Banco Ademi"),
    ("¿Cuánto le hemos vendido a Banco Ademi?", SalesIntent.CUSTOMER_SALES_AMOUNT, None, "Banco Ademi"),
]

QA_ASSISTANT_QUESTIONS = [
    "¿Cuántas laptops hemos vendido?",
    "¿Cuánto hemos vendido en laptops?",
    "¿Qué clientes compraron laptops?",
    "¿Cuántas licencias Microsoft hemos vendido?",
    "¿Licencias Microsoft le hemos vendido a Banco Ademi?",
    "¿Qué le hemos vendido a Banco Ademi?",
    "¿Cuánto le hemos vendido a Banco Ademi?",
]


@pytest.mark.parametrize("question,expected_intent,product_fragment", SALES_QUESTIONS)
def test_sales_intent_parser(question, expected_intent, product_fragment):
    parsed = SalesQuestionService.parse(question)
    assert parsed.intent == expected_intent
    assert parsed.product_label is not None
    assert product_fragment.lower() in parsed.product_label.lower()
    assert len(parsed.search_terms) >= 1


@pytest.mark.parametrize("question,expected_intent,product_fragment,customer_fragment", CUSTOMER_QUESTIONS)
def test_customer_sales_intent_parser(question, expected_intent, product_fragment, customer_fragment):
    parsed = SalesQuestionService.parse(question)
    assert parsed.intent == expected_intent
    if product_fragment:
        assert parsed.product_label is not None
        assert product_fragment.lower() in parsed.product_label.lower()
        assert len(parsed.search_terms) >= 1
    if customer_fragment:
        assert parsed.customer_label is not None
        assert customer_fragment.lower() in parsed.customer_label.lower()


def test_sales_expand_laptop_synonyms():
    from app.services.business_terms import expand_product_terms

    terms = expand_product_terms("laptops")
    assert "laptop" in terms
    assert any(t in terms for t in ("notebook", "portátil", "portatil"))


def test_sales_signal_detected():
    assert SalesQuestionService.has_sales_signal("¿Cuántas laptops hemos vendido?")


def test_non_sales_returns_none_intent():
    parsed = SalesQuestionService.parse("¿Qué procesos DGCP vencen esta semana?")
    assert parsed.intent == SalesIntent.NONE


def test_no_product_list_in_parser_insufficient():
    parsed = SalesQuestionService.parse("¿Cuántas cosas raras hemos vendido?")
    assert parsed.intent != SalesIntent.NONE


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
@pytest.mark.parametrize("question,_,__", SALES_QUESTIONS)
async def test_assistant_no_generic_help_for_sales(auth_headers, question, _, __):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={"question": question, "current_module": "/odoo"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["query_type"] != "help"
    assert "Puedo responder sobre:" not in body["answer"]
    assert body["query_type"] in (
        "sales_query",
        "not_connected",
    )


@pytest.mark.asyncio
async def test_assistant_laptops_quantity_intent(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={"question": "¿Cuántas laptops hemos vendido?", "current_module": "/dashboard"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["query_type"] in ("sales_query", "not_connected")
    if body["query_type"] == "sales_query":
        assert "Productos considerados" not in body["answer"]
        assert "No tengo información suficiente" not in body["answer"]
        sd = body.get("structured_data")
        if sd and "No encontré" not in body["answer"]:
            assert sd["type"] == "business_answer"
            assert sd.get("summary")
            assert len(sd.get("metrics", [])) >= 8
            assert len(sd.get("tables", [])) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("question", QA_ASSISTANT_QUESTIONS)
async def test_qa_sales_structured_responses(auth_headers, question):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={"question": question, "current_module": "/odoo"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["query_type"] != "help"
    assert "Puedo responder sobre:" not in body["answer"]
    assert "Productos considerados" not in body["answer"]

    if body["query_type"] == "not_connected":
        return

    if body["query_type"] == "sales_query":
        sd = body.get("structured_data")
        if sd and body["answer"] and "No encontré" not in body["answer"]:
            assert sd["type"] == "business_answer"
            assert sd.get("summary")
            assert isinstance(sd.get("metrics"), list)
            assert isinstance(sd.get("tables"), list)
            assert len(body["answer"]) < 400

    if "Banco Ademi" in question and "licencias" in question.lower():
        if "No encontré" in body["answer"]:
            assert "Banco Ademi" in body["answer"]
        elif body["answer"]:
            assert body["answer"].startswith("Sí.") or "Vendimos" in body["answer"]
