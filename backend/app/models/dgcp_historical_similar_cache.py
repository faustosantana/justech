"""Cache de resultados de búsqueda histórica similar por proceso DGCP."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DGCPProcessHistoricalSimilarResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dgcp_process_historical_similar_results"
    __table_args__ = (UniqueConstraint("tenant_id", "opportunity_id", name="uq_dgcp_hist_similar_cache_opp"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dgcp_opportunities.id", ondelete="CASCADE"), nullable=False
    )
    process_code: Mapped[str] = mapped_column(String(128), nullable=False)
    buyer_institution: Mapped[str] = mapped_column(String(512), nullable=False)
    keywords_used: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    searched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    results: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="dgcp_api_on_demand", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="searched", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    pages_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidates_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    refresh_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
