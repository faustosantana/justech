"""Memoria conversacional del Assistant — contexto de entidades por sesión."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

TOPIC_RESET_PHRASES = (
    "otra cosa",
    "nuevo tema",
    "cambiar de tema",
    "otro tema",
    "empecemos de nuevo",
    "olvidar contexto",
    "limpiar contexto",
)


@dataclass
class ConversationEntities:
    current_product: str | None = None
    current_product_terms: list[str] = field(default_factory=list)
    current_customer: str | None = None
    current_customer_terms: list[str] = field(default_factory=list)
    current_vendor: str | None = None
    current_document: str | None = None
    current_bid_id: str | None = None
    current_bid_label: str | None = None
    current_task_id: str | None = None
    current_quote_id: str | None = None
    current_company_scope: str | None = None
    year_filter: int | None = None
    last_intent: str | None = None
    last_query_type: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def reset(self) -> None:
        self.current_product = None
        self.current_product_terms = []
        self.current_customer = None
        self.current_customer_terms = []
        self.current_vendor = None
        self.current_document = None
        self.current_bid_id = None
        self.current_bid_label = None
        self.current_task_id = None
        self.current_quote_id = None
        self.year_filter = None
        self.last_intent = None
        self.last_query_type = None
        self.updated_at = datetime.now(timezone.utc)

    def to_debug_dict(self) -> dict[str, str | list[str] | int | None]:
        return {
            "producto": self.current_product,
            "cliente": self.current_customer,
            "proveedor": self.current_vendor,
            "documento": self.current_document,
            "licitacion": self.current_bid_label or self.current_bid_id,
            "tarea": self.current_task_id,
            "cotizacion": self.current_quote_id,
            "empresa": self.current_company_scope,
            "filtro_anio": self.year_filter,
            "ultima_intencion": self.last_intent,
        }


class ConversationContextStore:
    """Store en memoria con TTL — suficiente para sesiones activas del Assistant."""

    _sessions: dict[str, ConversationEntities] = {}
    _ttl = timedelta(hours=4)

    @classmethod
    def _key(cls, tenant_id: uuid.UUID, user_id: uuid.UUID, conversation_id: str) -> str:
        return f"{tenant_id}:{user_id}:{conversation_id}"

    @classmethod
    def get(
        cls,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_id: str | None,
    ) -> ConversationEntities:
        if not conversation_id:
            return ConversationEntities()
        key = cls._key(tenant_id, user_id, conversation_id)
        ctx = cls._sessions.get(key)
        if ctx is None:
            ctx = ConversationEntities()
            cls._sessions[key] = ctx
            return ctx
        if datetime.now(timezone.utc) - ctx.updated_at > cls._ttl:
            ctx.reset()
        return ctx

    @classmethod
    def save(
        cls,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_id: str | None,
        ctx: ConversationEntities,
    ) -> None:
        if not conversation_id:
            return
        ctx.updated_at = datetime.now(timezone.utc)
        cls._sessions[cls._key(tenant_id, user_id, conversation_id)] = ctx

    @staticmethod
    def should_reset(question: str) -> bool:
        lowered = question.lower().strip()
        return any(p in lowered for p in TOPIC_RESET_PHRASES)

    @staticmethod
    def detect_year_filter(question: str) -> int | None:
        lowered = question.lower()
        if re.search(r"\beste\s+a[nñ]o\b", lowered):
            return datetime.now(timezone.utc).year
        m = re.search(r"\ben\s+(20\d{2})\b", lowered)
        if m:
            return int(m.group(1))
        m = re.search(r"\b(20\d{2})\b", lowered)
        if m and len(lowered.split()) <= 4:
            return int(m.group(1))
        return None

    @classmethod
    def update_from_sales(
        cls,
        ctx: ConversationEntities,
        *,
        product_label: str | None,
        product_terms: list[str] | None,
        customer_label: str | None = None,
        customer_terms: list[str] | None = None,
        intent: str | None = None,
        year_filter: int | None = None,
    ) -> None:
        if product_label:
            ctx.current_product = product_label
        if product_terms:
            ctx.current_product_terms = list(product_terms)
        if customer_label:
            ctx.current_customer = customer_label
        if customer_terms:
            ctx.current_customer_terms = list(customer_terms)
        if intent:
            ctx.last_intent = intent
        ctx.last_query_type = "sales_query"
        if year_filter is not None:
            ctx.year_filter = year_filter
        ctx.updated_at = datetime.now(timezone.utc)

    @classmethod
    def update_from_response(
        cls,
        ctx: ConversationEntities,
        *,
        query_type: str,
        data: dict | None = None,
        record_type: str | None = None,
        record_id: str | None = None,
    ) -> None:
        data = data or {}
        ctx.last_query_type = query_type
        if data.get("product_label"):
            ctx.current_product = str(data["product_label"])
        if data.get("search_terms"):
            ctx.current_product_terms = list(data["search_terms"])
        if data.get("customer_label"):
            ctx.current_customer = str(data["customer_label"])
        if record_type in ("dgcp", "dgcp_opportunity") and record_id:
            ctx.current_bid_id = record_id
        ctx.updated_at = datetime.now(timezone.utc)
