"""Tests — Assistant 3.0 (Semantic Resolver + Copilot)."""

from __future__ import annotations

import pytest

from app.services.conversation_follow_up_resolver import resolve_follow_up
from app.services.assistant_conversation_context import ConversationEntities
from app.services.semantic_resolver_engine import SemanticResolverEngine


@pytest.mark.asyncio
async def test_semantic_rewrite_ventas_de_ademi():
    engine = SemanticResolverEngine()
    result = await engine.resolve("ventas de Ademi")
    assert "vendid" in result.rewritten.lower()
    assert result.customer_label or any("ademi" in t for t in result.customer_terms)


@pytest.mark.asyncio
async def test_semantic_abbreviation_cxc():
    engine = SemanticResolverEngine()
    result = await engine.resolve("qué cxc vencen hoy")
    assert "cuentas por cobrar" in result.rewritten.lower() or "cxc" in result.normalized.lower()


@pytest.mark.asyncio
async def test_semantic_rewrite_historial_capital():
    engine = SemanticResolverEngine()
    result = await engine.resolve("historial Capital DBG")
    assert "vendid" in result.rewritten.lower() or result.customer_label


def test_follow_up_finance_debt_with_customer_context():
    ctx = ConversationEntities(current_customer="Banco Ademi")
    resolution = resolve_follow_up("¿Y cuánto nos deben?", ctx)
    assert resolution.was_follow_up
    assert "ademi" in resolution.question.lower()


def test_follow_up_finance_invoices_with_customer_context():
    ctx = ConversationEntities(current_customer="Banco Ademi")
    resolution = resolve_follow_up("¿Y las facturas vencidas?", ctx)
    assert resolution.was_follow_up
    assert "facturas" in resolution.question.lower()


@pytest.mark.asyncio
async def test_papel_350_detects_product():
    engine = SemanticResolverEngine()
    result = await engine.resolve("papel 350")
    assert result.product_label
    assert any("350" in t or "papel" in t for t in result.product_terms)
