"""Lottery prospective pilot models (DEV/UAT). Production writes are forbidden by app gate."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LotteryPilotConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_pilot_configurations"
    __table_args__ = (Index("ix_lottery_pilot_cfg_status", "status"),)

    pilot_name: Mapped[str] = mapped_column(String(128), nullable=False)
    start_date: Mapped[str | None] = mapped_column(String(32))
    end_date: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    lotteries: Mapped[list | None] = mapped_column(JSONB, default=list)
    positions: Mapped[list | None] = mapped_column(JSONB, default=list)
    input_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="generator_first")
    analysis_time: Mapped[str | None] = mapped_column(String(32))
    lock_deadline: Mapped[str | None] = mapped_column(String(64))
    evaluation_window: Mapped[str] = mapped_column(String(32), nullable=False, default="D+1_D+7")
    ranking_profile: Mapped[str] = mapped_column(String(64), nullable=False, default="socio")
    tiebreak_profile: Mapped[str] = mapped_column(
        String(64), nullable=False, default="TIEBREAK_PROFILE_SOCIO_V1"
    )
    derivation_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    auto_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_lock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_evaluate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    minimum_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    responsible_user: Mapped[str | None] = mapped_column(String(128))
    environment: Mapped[str] = mapped_column(String(32), nullable=False, default="DEV/UAT")
    payload: Mapped[dict | None] = mapped_column(JSONB, default=dict)


class LotteryProspectiveRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lottery_prospective_runs"
    __table_args__ = (
        Index("ix_lottery_prospective_runs_status", "lock_status"),
        Index("ix_lottery_prospective_runs_analysis_date", "analysis_date"),
        Index("ix_lottery_prospective_runs_target_date", "target_date"),
    )

    prediction_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    pilot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lottery_pilot_configurations.id", ondelete="SET NULL")
    )
    created_by: Mapped[str | None] = mapped_column(String(128))
    analysis_date: Mapped[str | None] = mapped_column(String(32))
    target_date: Mapped[str | None] = mapped_column(String(32))
    lottery: Mapped[str | None] = mapped_column(String(128))
    position: Mapped[str | None] = mapped_column(String(64))
    input_numbers: Mapped[list | None] = mapped_column(JSONB, default=list)
    engine_version: Mapped[str] = mapped_column(String(128), nullable=False)
    table1_version: Mapped[str] = mapped_column(String(128), nullable=False)
    table2_version: Mapped[str] = mapped_column(String(128), nullable=False)
    ranking_profile: Mapped[str] = mapped_column(String(64), nullable=False, default="socio")
    tiebreak_profile: Mapped[str] = mapped_column(
        String(64), nullable=False, default="TIEBREAK_PROFILE_SOCIO_V1"
    )
    derivation_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidates: Mapped[list | None] = mapped_column(JSONB, default=list)
    ranking: Mapped[list | None] = mapped_column(JSONB, default=list)
    primary_signal: Mapped[dict | None] = mapped_column(JSONB)
    secondary_signals: Mapped[list | None] = mapped_column(JSONB, default=list)
    multi_strong_candidates: Mapped[list | None] = mapped_column(JSONB, default=list)
    score_components: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Float)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    tiebreak: Mapped[dict | None] = mapped_column(JSONB)
    shadow_profiles: Mapped[dict | None] = mapped_column(JSONB)
    lock_status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(128))
    prediction_hash: Mapped[str | None] = mapped_column(String(128))
    canonical_payload: Mapped[dict | None] = mapped_column(JSONB)
    engine_commit: Mapped[str | None] = mapped_column(String(64))
    result_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    future_result: Mapped[dict | None] = mapped_column(JSONB)
    evaluation_status: Mapped[str | None] = mapped_column(String(64))
    evaluation: Mapped[dict | None] = mapped_column(JSONB)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    integrity_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    input_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    input_incomplete_reason: Mapped[str | None] = mapped_column(Text)


class LotteryProspectiveAuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_prospective_audit_logs"
    __table_args__ = (Index("ix_lottery_prospective_audit_pred", "prediction_key", "created_at"),)

    prediction_key: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    actor: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LotteryPilotDailySnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lottery_pilot_daily_snapshots"
    __table_args__ = (Index("ix_lottery_pilot_snapshot_date", "snapshot_date"),)

    pilot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    snapshot_date: Mapped[str] = mapped_column(String(32), nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
