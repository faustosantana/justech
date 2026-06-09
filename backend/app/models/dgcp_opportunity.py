import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DGCPOpportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dgcp_opportunities"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_dgcp_opportunities_tenant_code"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    ocid: Mapped[str | None] = mapped_column(String(128))
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="DOP")
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="detected", index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", index=True)
    company: Mapped[str] = mapped_column(String(32), nullable=False, default="unclassified", index=True)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    classification_reason: Mapped[str | None] = mapped_column(Text)
    dgcp_status: Mapped[str | None] = mapped_column(String(64))
    modalidad: Mapped[str | None] = mapped_column(String(128))
    objeto_proceso: Mapped[str | None] = mapped_column(String(64))
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    full_info: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    similar_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    risks: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    ai_recommendations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    suggested_action: Mapped[str | None] = mapped_column(String(64))
    justech_potential_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=0
    )
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
