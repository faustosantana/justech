"""Tests — memoria conversacional del Assistant."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD
from app.services.assistant_conversation_context import ConversationContextStore, ConversationEntities
from app.services.conversation_follow_up_resolver import resolve_follow_up
from app.services.sales_question_service import SalesQuestionService, SalesIntent


def test_follow_up_buyers_expands_product():
    ctx = ConversationEntities(current_product="papel 365", current_product_terms=["papel 365", "365"])
    res = resolve_follow_up("¿A quiénes se lo hemos vendido?", ctx)
    assert res.was_follow_up is True
    assert "papel 365" in res.question.lower()
    assert "comprado" in res.question.lower() or "clientes" in res.question.lower()


def test_follow_up_price_expands_product():
    ctx = ConversationEntities(current_product="papel 365")
    res = resolve_follow_up("¿Y a qué precio?", ctx)
    assert res.was_follow_up is True
    assert "papel 365" in res.question.lower()


def test_follow_up_top_buyer():
    ctx = ConversationEntities(current_product="papel 365", last_intent="sales_quantity_query")
    res = resolve_follow_up("¿Quién compró más?", ctx)
    assert res.was_follow_up is True
    assert "más" in res.question.lower()
    assert "papel 365" in res.question.lower()


def test_follow_up_year_only():
    ctx = ConversationEntities(
        current_product="papel 365",
        last_intent="top_buyer_query",
    )
    res = resolve_follow_up("¿Y este año?", ctx)
    assert res.was_follow_up is True
    assert "papel 365" in res.question.lower()


def test_parse_with_context_buyers():
    ctx = ConversationEntities(current_product="papel 365", current_product_terms=["papel", "365"])
    parsed = SalesQuestionService.parse_with_context("¿A quiénes se lo hemos vendido?", ctx)
    assert parsed.intent == SalesIntent.BUYERS
    assert parsed.product_label is not None
    assert "365" in " ".join(parsed.search_terms)


def test_topic_reset_clears_context():
    ctx = ConversationEntities(current_product="papel 365")
    assert ConversationContextStore.should_reset("otra cosa, hablemos de laptops")
    ctx.reset()
    assert ctx.current_product is None


@pytest.mark.asyncio
async def test_assistant_conversation_chain_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "tenant_slug": "justech",
            },
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible")
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        conv_id = "qa-conv-papel-365"

        first = await client.post(
            "/api/v1/assistant/query",
            headers=headers,
            json={
                "question": "¿Cuántos rollos de papel 365 hemos vendido?",
                "conversation_id": conv_id,
                "debug_context": True,
            },
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body.get("conversation_context", {}).get("producto") or first_body.get("query_type")

        follow = await client.post(
            "/api/v1/assistant/query",
            headers=headers,
            json={
                "question": "¿A quiénes se lo hemos vendido?",
                "conversation_id": conv_id,
                "debug_context": True,
            },
        )
        assert follow.status_code == 200, follow.text
        follow_body = follow.json()
        assert follow_body.get("was_follow_up") is True
        assert follow_body.get("resolved_question")
        assert "365" in (follow_body.get("resolved_question") or "").lower() or "papel" in (
            follow_body.get("resolved_question") or ""
        ).lower()
