"""Store persistente de conversaciones — Assistant 3.0."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assistant_conversation import AssistantConversation, AssistantMessage
from app.schemas.assistant import AssistantQueryResponse
from app.services.assistant_conversation_context import ConversationEntities


def normalize_conversation_uuid(
    conversation_id: str | None,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> uuid.UUID | None:
    """UUID explícito o determinístico para IDs de sesión del frontend (p. ej. localStorage)."""
    if not conversation_id:
        return None
    try:
        return uuid.UUID(conversation_id)
    except ValueError:
        return uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"jaios-assistant/{tenant_id}/{user_id}/{conversation_id}",
        )


def entities_from_snapshot(data: dict | None) -> ConversationEntities:
    data = data or {}
    ctx = ConversationEntities()
    ctx.current_product = data.get("current_product")
    ctx.current_product_terms = list(data.get("current_product_terms") or [])
    ctx.current_customer = data.get("current_customer")
    ctx.current_customer_terms = list(data.get("current_customer_terms") or [])
    ctx.current_vendor = data.get("current_vendor")
    ctx.current_document = data.get("current_document")
    ctx.current_bid_id = data.get("current_bid_id")
    ctx.current_bid_label = data.get("current_bid_label")
    ctx.current_task_id = data.get("current_task_id")
    ctx.current_quote_id = data.get("current_quote_id")
    ctx.current_company_scope = data.get("current_company_scope")
    ctx.year_filter = data.get("year_filter")
    ctx.last_intent = data.get("last_intent")
    ctx.last_query_type = data.get("last_query_type")
    return ctx


def entities_to_snapshot(ctx: ConversationEntities) -> dict:
    return {
        "current_product": ctx.current_product,
        "current_product_terms": ctx.current_product_terms,
        "current_customer": ctx.current_customer,
        "current_customer_terms": ctx.current_customer_terms,
        "current_vendor": ctx.current_vendor,
        "current_document": ctx.current_document,
        "current_bid_id": ctx.current_bid_id,
        "current_bid_label": ctx.current_bid_label,
        "current_task_id": ctx.current_task_id,
        "current_quote_id": ctx.current_quote_id,
        "current_company_scope": ctx.current_company_scope,
        "year_filter": ctx.year_filter,
        "last_intent": ctx.last_intent,
        "last_query_type": ctx.last_query_type,
    }


class PersistentConversationStore:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def load_context(self, conversation_id: str | None) -> ConversationEntities:
        conv_uuid = normalize_conversation_uuid(conversation_id, self.tenant_id, self.user_id)
        if not conv_uuid:
            return ConversationEntities()
        row = await self.db.get(AssistantConversation, conv_uuid)
        if not row or row.tenant_id != self.tenant_id or row.user_id != self.user_id:
            return ConversationEntities()
        return entities_from_snapshot(row.entity_snapshot)

    async def ensure_conversation(
        self,
        conversation_id: str | None,
        *,
        module_context: str | None = None,
        company_context_id: int | None = None,
    ) -> uuid.UUID | None:
        conv_uuid = normalize_conversation_uuid(conversation_id, self.tenant_id, self.user_id)
        if not conv_uuid:
            return None
        row = await self.db.get(AssistantConversation, conv_uuid)
        if row is None:
            row = AssistantConversation(
                id=conv_uuid,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                module_context=module_context,
                company_context_id=company_context_id,
                entity_snapshot={},
            )
            self.db.add(row)
            await self.db.flush()
        return conv_uuid

    async def save_context(
        self,
        conversation_id: str | None,
        ctx: ConversationEntities,
        *,
        module_context: str | None = None,
        company_context_id: int | None = None,
    ) -> None:
        conv_uuid = await self.ensure_conversation(
            conversation_id,
            module_context=module_context,
            company_context_id=company_context_id,
        )
        if not conv_uuid:
            return
        row = await self.db.get(AssistantConversation, conv_uuid)
        if not row:
            return
        row.entity_snapshot = entities_to_snapshot(ctx)
        row.updated_at = datetime.now(timezone.utc)
        if module_context:
            row.module_context = module_context
        if company_context_id is not None:
            row.company_context_id = company_context_id
        await self.db.flush()

    async def append_exchange(
        self,
        conversation_id: str | None,
        *,
        user_question: str,
        assistant_response: AssistantQueryResponse,
    ) -> None:
        conv_uuid = await self.ensure_conversation(conversation_id)
        if not conv_uuid:
            return
        now = datetime.now(timezone.utc)
        self.db.add(AssistantMessage(conversation_id=conv_uuid, role="user", content=user_question))
        self.db.add(
            AssistantMessage(
                conversation_id=conv_uuid,
                role="assistant",
                content=assistant_response.answer,
                query_type=assistant_response.query_type,
                sources=assistant_response.sources,
                structured_data=assistant_response.structured_data,
                resolved_question=assistant_response.resolved_question,
                was_follow_up=assistant_response.was_follow_up,
            )
        )
        row = await self.db.get(AssistantConversation, conv_uuid)
        if row:
            row.last_message_at = now
            if not row.title and len(user_question) <= 120:
                row.title = user_question[:120]
        await self.db.flush()

    async def reset_conversation(self, conversation_id: str) -> None:
        from sqlalchemy import delete

        conv_uuid = normalize_conversation_uuid(conversation_id, self.tenant_id, self.user_id)
        if not conv_uuid:
            return
        row = await self.db.get(AssistantConversation, conv_uuid)
        if not row or row.tenant_id != self.tenant_id or row.user_id != self.user_id:
            return
        row.entity_snapshot = {}
        await self.db.execute(
            delete(AssistantMessage).where(AssistantMessage.conversation_id == conv_uuid)
        )
        await self.db.flush()

    async def get_briefing_mode(self, conversation_id: str | None) -> str:
        conv_uuid = normalize_conversation_uuid(conversation_id, self.tenant_id, self.user_id)
        if not conv_uuid:
            return "managerial"
        row = await self.db.get(AssistantConversation, conv_uuid)
        if row and row.tenant_id == self.tenant_id and row.user_id == self.user_id:
            return row.briefing_mode or "managerial"
        return "managerial"

    async def set_briefing_mode(self, conversation_id: str | None, mode: str) -> None:
        conv_uuid = await self.ensure_conversation(conversation_id)
        if not conv_uuid:
            return
        row = await self.db.get(AssistantConversation, conv_uuid)
        if row:
            row.briefing_mode = mode
            await self.db.flush()
