"""Tests — persistencia y snapshot Assistant 3.0."""

from __future__ import annotations

from app.services.assistant_conversation_context import ConversationEntities
import uuid

from app.services.persistent_conversation_store import (
    entities_from_snapshot,
    entities_to_snapshot,
    normalize_conversation_uuid,
)


def test_entities_snapshot_roundtrip():
    ctx = ConversationEntities(
        current_product="papel 350",
        current_product_terms=["papel", "350"],
        current_customer="Banco Ademi",
        current_customer_terms=["ademi", "banco ademi"],
        last_intent="customer_sales_list_query",
        year_filter=2026,
    )
    restored = entities_from_snapshot(entities_to_snapshot(ctx))
    assert restored.current_product == ctx.current_product
    assert restored.current_customer == ctx.current_customer
    assert restored.year_filter == ctx.year_filter


def test_entities_snapshot_empty():
    ctx = entities_from_snapshot({})
    assert ctx.current_product is None
    assert ctx.current_customer is None


def test_normalize_conversation_uuid_deterministic():
    tenant = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user = uuid.UUID("00000000-0000-0000-0000-000000000002")
    explicit = uuid.UUID("11111111-1111-1111-1111-111111111111")
    assert normalize_conversation_uuid(str(explicit), tenant, user) == explicit
    a = normalize_conversation_uuid("qa-conv-papel-365", tenant, user)
    b = normalize_conversation_uuid("qa-conv-papel-365", tenant, user)
    assert a == b
    assert a != normalize_conversation_uuid("other-conv", tenant, user)
