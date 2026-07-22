"""Persistencia de conversaciones del Assistant 3.0."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class AssistantConversation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assistant_conversations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255))
    module_context: Mapped[str | None] = mapped_column(String(128))
    company_context_id: Mapped[int | None] = mapped_column()
    entity_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    briefing_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="managerial")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["AssistantMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="AssistantMessage.created_at"
    )


class AssistantMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assistant_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[str | None] = mapped_column(String(64))
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    structured_data: Mapped[dict | None] = mapped_column(JSONB)
    resolved_question: Mapped[str | None] = mapped_column(Text)
    was_follow_up: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[AssistantConversation] = relationship(back_populates="messages")
