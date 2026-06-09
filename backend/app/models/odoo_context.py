import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class UserCompanyContext(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Empresa Odoo activa seleccionada por usuario JAIOS."""

    __tablename__ = "user_company_contexts"
    __table_args__ = (UniqueConstraint("tenant_id", "jaios_user_id", name="uq_user_company_context"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    jaios_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    odoo_company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    odoo_company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    selection_mode: Mapped[str] = mapped_column(String(16), default="single", nullable=False)
    selected_company_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)


class OdooUserMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Mapeo usuario JAIOS ↔ usuario Odoo (preparado para credenciales por usuario)."""

    __tablename__ = "odoo_user_mappings"
    __table_args__ = (UniqueConstraint("tenant_id", "jaios_user_id", name="uq_odoo_user_mapping"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    jaios_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    odoo_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    odoo_login: Mapped[str] = mapped_column(String(255), nullable=False)
    odoo_partner_id: Mapped[int | None] = mapped_column(Integer)
    allowed_company_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list, nullable=False)
    default_company_id: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
