"""Modelos del módulo Resultados de Loterías / Lotería IA.

Histórico global (público): lotteries, draws, draw_numbers, aliases, import_*.
Por tenant/usuario: saved_queries, chat_*, audit_log.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LotteryLottery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_lotteries"
    __table_args__ = (
        UniqueConstraint("source_id", name="uq_lottery_lotteries_source_id"),
        UniqueConstraint("slug", name="uq_lottery_lotteries_slug"),
        Index("ix_lottery_lotteries_normalized_name", "normalized_name"),
    )

    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str | None] = mapped_column(String(64))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Santo_Domingo")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_loto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_aggregate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    first_draw_date: Mapped[date | None] = mapped_column(Date)
    last_draw_date: Mapped[date | None] = mapped_column(Date)
    draw_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Lottery 2.0 — independent admin controls (not a single flag)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_visible_dashboard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_visible_catalog: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_searchable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_comparable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_auto_write_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    commercial_name: Mapped[str | None] = mapped_column(String(255))
    short_name: Mapped[str | None] = mapped_column(String(128))
    logo_url: Mapped[str | None] = mapped_column(Text)
    icon_key: Mapped[str | None] = mapped_column(String(64))
    currency: Mapped[str | None] = mapped_column(String(16))
    data_source: Mapped[str | None] = mapped_column(String(128))
    adapter_key: Mapped[str | None] = mapped_column(String(128))
    external_id: Mapped[str | None] = mapped_column(String(128))
    draw_schedule_cron: Mapped[str | None] = mapped_column(String(128))
    draw_days: Mapped[str | None] = mapped_column(String(64))
    draw_times: Mapped[str | None] = mapped_column(String(255))
    sync_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    sync_post_draw_delay_minutes: Mapped[int | None] = mapped_column(Integer)
    sync_max_retries: Mapped[int | None] = mapped_column(Integer)
    sync_active_hours: Mapped[str | None] = mapped_column(String(64))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_result_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_draw_estimated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    last_error: Mapped[str | None] = mapped_column(Text)
    numbers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    admin_notes: Mapped[str | None] = mapped_column(Text)

    # Lottery 3.0 — multi-country + smart sync windows
    country_code: Mapped[str | None] = mapped_column(String(8), default="DO")
    operator_key: Mapped[str | None] = mapped_column(String(64))
    flag_emoji: Mapped[str | None] = mapped_column(String(16))
    sync_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    sync_timeout_seconds: Mapped[int | None] = mapped_column(Integer)
    sync_pre_window_minutes: Mapped[int | None] = mapped_column(Integer)
    sync_live_window_minutes: Mapped[int | None] = mapped_column(Integer)
    sync_post_window_minutes: Mapped[int | None] = mapped_column(Integer)
    sync_pre_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    sync_live_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    sync_post_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    sync_backoff_seconds: Mapped[int | None] = mapped_column(Integer)

    draws: Mapped[list["LotteryDraw"]] = relationship(back_populates="lottery")
    aliases: Mapped[list["LotteryAlias"]] = relationship(back_populates="lottery")


class LotteryDraw(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_draws"
    __table_args__ = (
        # Unicidad NULL-safe vía índices en migración 028:
        # - uq_lottery_draws_lottery_source_ref (parcial)
        # - uq_lottery_draws_natural_coalesce (expresión)
        Index("ix_lottery_draws_lottery_date", "lottery_id", "draw_date"),
        Index("ix_lottery_draws_lottery_date_time", "lottery_id", "draw_date", "draw_time"),
        Index("ix_lottery_draws_source_reference", "source_reference"),
    )

    lottery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lottery_lotteries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draw_date: Mapped[date] = mapped_column(Date, nullable=False)
    draw_time: Mapped[time | None] = mapped_column(Time)
    game_name: Mapped[str] = mapped_column(String(128), nullable=False, default="quiniela")
    source_reference: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lottery: Mapped[LotteryLottery] = relationship(back_populates="draws")
    numbers: Mapped[list["LotteryDrawNumber"]] = relationship(
        back_populates="draw", cascade="all, delete-orphan"
    )


class LotteryDrawNumber(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_draw_numbers"
    __table_args__ = (
        Index("ix_lottery_draw_numbers_draw_position", "draw_id", "position"),
        Index("ix_lottery_draw_numbers_number_value", "number_value"),
        # uq_lottery_draw_numbers_draw_pos_type creado en 028
    )

    draw_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lottery_draws.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    position_label: Mapped[str] = mapped_column(String(64), nullable=False)
    # TEXT: preservar 00, 01, 05, 08, 09 — nunca depender solo de integer.
    number_value: Mapped[str] = mapped_column(String(32), nullable=False)
    number_raw: Mapped[str] = mapped_column(String(32), nullable=False)
    number_type: Mapped[str] = mapped_column(String(32), nullable=False, default="principal")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    draw: Mapped[LotteryDraw] = relationship(back_populates="numbers")


class LotteryAlias(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_aliases"
    __table_args__ = (
        UniqueConstraint("normalized_alias", name="uq_lottery_aliases_normalized_alias"),
        Index("ix_lottery_aliases_normalized_alias", "normalized_alias"),
    )

    lottery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lottery_lotteries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lottery: Mapped[LotteryLottery] = relationship(back_populates="aliases")


class LotteryImportRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_import_runs"

    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="sqlite_import")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    source_path: Mapped[str | None] = mapped_column(String(512))
    source_path_hash: Mapped[str | None] = mapped_column(String(64))
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resume: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    git_commit: Mapped[str | None] = mapped_column(String(64))
    app_version: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lotteries_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    draws_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    numbers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checkpoint: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class LotteryImportError(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_import_errors"

    import_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lottery_import_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LotterySavedQuery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_saved_queries"
    __table_args__ = (Index("ix_lottery_saved_queries_tenant_user", "tenant_id", "user_id"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    query_type: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class LotteryChatSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_chat_sessions"
    __table_args__ = (Index("ix_lottery_chat_sessions_tenant_user", "tenant_id", "user_id"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255))
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list["LotteryChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class LotteryChatMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lottery_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(128))
    tool_payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[LotteryChatSession] = relationship(back_populates="messages")


class LotteryAuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_audit_log"
    __table_args__ = (Index("ix_lottery_audit_log_tenant_created", "tenant_id", "created_at"),)

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(128))
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result_count: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LotteryUserFavorite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_user_favorites"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "lottery_id", name="uq_lottery_favorites_tenant_user_lottery"),
        Index("ix_lottery_favorites_tenant_user", "tenant_id", "user_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lottery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lottery_lotteries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LotteryUserPreferences(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_user_preferences"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_lottery_prefs_tenant_user"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class LotteryRecentQuery(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_recent_queries"
    __table_args__ = (
        Index("ix_lottery_recent_tenant_user_created", "tenant_id", "user_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LotteryExport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_exports"
    __table_args__ = (
        Index("ix_lottery_exports_tenant_user", "tenant_id", "user_id"),
        Index("ix_lottery_exports_expires", "expires_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_type: Mapped[str] = mapped_column(String(64), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    row_count: Mapped[int | None] = mapped_column(Integer)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LotterySharedQuery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Enlace compartible temporal — token solo como hash."""

    __tablename__ = "lottery_shared_queries"
    __table_args__ = (
        Index("ix_lottery_shares_tenant_user", "tenant_id", "created_by_user_id"),
        Index("ix_lottery_shares_token_hash", "token_hash", unique=True),
        Index("ix_lottery_shares_expires", "expires_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    query_type: Mapped[str] = mapped_column(String(64), nullable=False)
    query_parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_views: Mapped[int | None] = mapped_column(Integer)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    allow_export: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LotterySyncRun(UUIDPrimaryKeyMixin, Base):
    """Ejecuciones de sincronización (dry-run o write controlado en staging)."""

    __tablename__ = "lottery_sync_runs"
    __table_args__ = (Index("ix_lottery_sync_runs_started", "started_at"),)

    source: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    records_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conflicts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_cursor: Mapped[str | None] = mapped_column(String(255))
    last_successful_draw_date: Mapped[date | None] = mapped_column(Date)
    source_response_hash: Mapped[str | None] = mapped_column(String(128))
    app_version: Mapped[str | None] = mapped_column(String(64))
    git_commit: Mapped[str | None] = mapped_column(String(64))
    report: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    environment: Mapped[str | None] = mapped_column(String(64))
    mode: Mapped[str | None] = mapped_column(String(32))
    write_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    from_date: Mapped[date | None] = mapped_column(Date)
    to_date: Mapped[date | None] = mapped_column(Date)
    lottery_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lock_key: Mapped[str | None] = mapped_column(String(255))
    checkpoint: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_changed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_conflicted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_invalid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    draws_before: Mapped[int | None] = mapped_column(Integer)
    draws_after: Mapped[int | None] = mapped_column(Integer)
    numbers_before: Mapped[int | None] = mapped_column(Integer)
    numbers_after: Mapped[int | None] = mapped_column(Integer)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    initiated_by: Mapped[str | None] = mapped_column(String(255))
    rollback_status: Mapped[str | None] = mapped_column(String(32))
    change_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="reject")
    inserted_draw_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    updated_draw_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    backup_path: Mapped[str | None] = mapped_column(String(512))


class LotterySchedulerState(UUIDPrimaryKeyMixin, Base):
    """Estado operacional del scheduler staging (un registro por environment)."""

    __tablename__ = "lottery_scheduler_state"
    __table_args__ = (Index("ix_lottery_scheduler_state_env", "environment", unique=True),)

    environment: Mapped[str] = mapped_column(String(64), nullable=False, default="staging")
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="disabled")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_tick_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    circuit_state: Mapped[str] = mapped_column(String(32), nullable=False, default="closed")
    circuit_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    circuit_reason: Mapped[str | None] = mapped_column(String(512))
    write_enabled_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_contract_version: Mapped[str | None] = mapped_column(String(64))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LotterySyncAlert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_sync_alerts"
    __table_args__ = (
        Index("ix_lottery_sync_alerts_status", "environment", "status", "created_at"),
        Index("ix_lottery_sync_alerts_code", "code"),
    )

    environment: Mapped[str] = mapped_column(String(64), nullable=False, default="staging")
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sync_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str | None] = mapped_column(String(255))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(255))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LotteryDrawRevision(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_draw_revisions"
    __table_args__ = (
        Index("ix_lottery_draw_revisions_draw", "draw_id"),
        Index("ix_lottery_draw_revisions_run", "sync_run_id"),
    )

    draw_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lottery_draws.id", ondelete="CASCADE"), nullable=False
    )
    sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lottery_sync_runs.id", ondelete="SET NULL")
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_content_hash: Mapped[str | None] = mapped_column(String(64))
    new_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    new_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    change_reason: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(String(255))
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reverted_by: Mapped[str | None] = mapped_column(String(255))


class LotterySource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_sources"
    __table_args__ = (
        UniqueConstraint("lottery_id", "source_key", name="uq_lottery_sources_lottery_key"),
        Index("ix_lottery_sources_lottery_role", "lottery_id", "role"),
    )

    lottery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lottery_lotteries.id", ondelete="CASCADE"), nullable=False
    )
    source_key: Mapped[str] = mapped_column(String(128), nullable=False)
    adapter_key: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="primary")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    health_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    latency_ema_ms: Mapped[int | None] = mapped_column(Integer)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    circuit_state: Mapped[str] = mapped_column(String(32), nullable=False, default="closed")


class LotterySourceAttempt(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_source_attempts"

    sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lottery_sync_runs.id", ondelete="CASCADE")
    )
    lottery_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lottery_sources.id", ondelete="SET NULL")
    )
    source_key: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    candidates: Mapped[int | None] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LotterySourceConflict(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_source_conflicts"

    lottery_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lottery_lotteries.id", ondelete="CASCADE")
    )
    draw_date: Mapped[date] = mapped_column(Date, nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_value: Mapped[str | None] = mapped_column(Text)
    other_value: Mapped[str | None] = mapped_column(Text)
    other_source: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LotteryAiUsage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_ai_usage"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(128))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 6))
    tool_names: Mapped[dict | list | None] = mapped_column(JSONB)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LotteryAiPromptVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_ai_prompt_versions"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_lottery_ai_prompt_name_version"),
        Index("ix_lottery_ai_prompt_status", "status"),
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    description: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    blocks: Mapped[dict | None] = mapped_column(JSONB)
    changelog: Mapped[str | None] = mapped_column(Text)
    recommended_model: Mapped[str | None] = mapped_column(String(128))
    temperature: Mapped[float | None] = mapped_column(Numeric(4, 2))
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer)
    variables: Mapped[list | dict | None] = mapped_column(JSONB)
    tags: Mapped[list | dict | None] = mapped_column(JSONB)
    checksum: Mapped[str | None] = mapped_column(String(64))
    benchmark_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class LotteryAiConfigVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_ai_config_versions"
    __table_args__ = (Index("ix_lottery_ai_config_status", "status"),)

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    description: Mapped[str | None] = mapped_column(Text)
    changelog: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class LotteryAiToolSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_ai_tool_settings"
    __table_args__ = (UniqueConstraint("tool_name", "tenant_id", name="uq_lottery_ai_tool_tenant"),)

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer)
    rate_limit_per_min: Mapped[int | None] = mapped_column(Integer)
    allowed_roles: Mapped[list | dict | None] = mapped_column(JSONB)
    blocked_lottery_ids: Mapped[list | dict | None] = mapped_column(JSONB)
    config: Mapped[dict | None] = mapped_column(JSONB)


class LotteryAiAnalysisPack(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_ai_analysis_packs"
    __table_args__ = (UniqueConstraint("pack_key", "tenant_id", name="uq_lottery_ai_pack_tenant"),)

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    pack_key: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class LotteryAiAuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_ai_audit_events"
    __table_args__ = (Index("ix_lottery_ai_audit_created", "created_at"),)

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    version_label: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LotteryAiBenchmark(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_ai_benchmarks"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    cases: Mapped[list | dict] = mapped_column(JSONB, nullable=False, default=list)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_result: Mapped[dict | None] = mapped_column(JSONB)
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class LotteryAiAlert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_ai_alerts"
    __table_args__ = (Index("ix_lottery_ai_alerts_created", "created_at"),)

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
