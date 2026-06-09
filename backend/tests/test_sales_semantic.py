"""Tests — normalización semántica de ventas (papel, Farma Trix, variantes)."""

import pytest

from app.services.business_entity_normalizer import normalize_customer, normalize_product
from app.services.business_intent_router import BusinessIntent, BusinessIntentRouter
from app.services.sales_question_service import SalesIntent, SalesQuestionService


def test_normalize_product_papel_350_variants():
    norm = normalize_product("papel 350")
    assert norm is not None
    assert "papel" in norm.label.lower()
    assert any("350" in v for v in norm.variants_display)
    assert any("rollo" in v.lower() or "papel" in v.lower() for v in norm.variants_display)


def test_normalize_customer_farma_trix_aliases():
    norm = normalize_customer("Farma Trix")
    assert norm is not None
    assert "farma" in norm.label.lower()
    assert any("farmatrix" in v.lower() or "farma trix" in v.lower() for v in norm.search_terms)


def test_parse_faldos_papel_farma_trix():
    parsed = SalesQuestionService.parse(
        "cuantos faldos de papel le hemos vendido a Farma Trix"
    )
    assert parsed.intent == SalesIntent.SALES_TO_CUSTOMER
    assert parsed.customer_label is not None
    assert "farma" in parsed.customer_label.lower()
    assert parsed.product_label is not None
    assert parsed.product_variants


def test_parse_rollos_papel_350_quantity():
    parsed = SalesQuestionService.parse("¿Cuántos rollos de papel 350 hemos vendido?")
    assert parsed.intent == SalesIntent.SALES_QUANTITY
    assert parsed.product_label is not None
    assert parsed.search_terms


def test_business_intent_sales_papel_350():
    parsed = BusinessIntentRouter.classify("¿Cuántos rollos de papel 350 hemos vendido?")
    assert parsed.intent == BusinessIntent.SALES


@pytest.mark.parametrize(
    "question",
    [
        "¿Cuántos rollos de papel 350 hemos vendido?",
        "cuantos faldos de papel le hemos vendido a Farma Trix",
        "papel 350",
    ],
)
def test_sales_signal_or_price_not_generic_help_intent(question):
    parsed = BusinessIntentRouter.classify(question)
    if SalesQuestionService.has_sales_signal(question):
        assert parsed.intent == BusinessIntent.SALES
    else:
        assert parsed.intent in (BusinessIntent.PRICE, BusinessIntent.NONE, BusinessIntent.SALES)
