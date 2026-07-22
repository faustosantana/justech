"""Jobs de sincronización de repositorios OneDrive/SharePoint."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class RepositorySyncJob(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "repository_sync_jobs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    binding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_repository_bindings.id", ondelete="SET NULL"), nullable=True
    )
    trigger: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    files_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_new: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_deleted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_indexed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
