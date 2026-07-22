"""Repositorios empresariales indexados desde Microsoft 365."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class M365RepositoryFile(Base):
    __tablename__ = "m365_repository_files"
    __table_args__ = {"schema": "jaios"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jaios.tenants.id"), index=True)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jaios.m365_user_accounts.id"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(32), default="onedrive")
    graph_item_id: Mapped[str] = mapped_column(String(256), index=True)
    drive_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    parent_path: Mapped[str] = mapped_column(Text, default="")
    name: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    web_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_folder: Mapped[bool] = mapped_column(Boolean, default=False)
    document_category: Mapped[str] = mapped_column(String(64), default="general", index=True)
    document_type: Mapped[str] = mapped_column(String(64), default="general")
    folder_category: Mapped[str] = mapped_column(String(64), default="general")
    classification_confidence: Mapped[int] = mapped_column(Integer, default=50)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    company_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    modified_at_graph: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    binding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_repository_bindings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
