"""062 — Lottery prospective pilot persistence (DEV/UAT only).

Revision ID: 062_lottery_prospective_pilot
Revises: 061_lottery_ia_control_center

Do NOT apply this migration against Production.
Gate: app_env in {development, uat, test} + lottery_prospective_persist_enabled.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "062_lottery_prospective_pilot"
down_revision: Union[str, None] = "061_lottery_ia_control_center"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "lottery_pilot_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pilot_name", sa.String(128), nullable=False),
        sa.Column("start_date", sa.String(32)),
        sa.Column("end_date", sa.String(32)),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("lotteries", postgresql.JSONB()),
        sa.Column("positions", postgresql.JSONB()),
        sa.Column("input_mode", sa.String(64), nullable=False, server_default="generator_first"),
        sa.Column("analysis_time", sa.String(32)),
        sa.Column("lock_deadline", sa.String(64)),
        sa.Column("evaluation_window", sa.String(32), nullable=False, server_default="D+1_D+7"),
        sa.Column("ranking_profile", sa.String(64), nullable=False, server_default="socio"),
        sa.Column(
            "tiebreak_profile",
            sa.String(64),
            nullable=False,
            server_default="TIEBREAK_PROFILE_SOCIO_V1",
        ),
        sa.Column("derivation_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auto_run", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("auto_lock", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("auto_evaluate", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("minimum_samples", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("responsible_user", sa.String(128)),
        sa.Column("environment", sa.String(32), nullable=False, server_default="DEV/UAT"),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_lottery_pilot_cfg_status",
        "lottery_pilot_configurations",
        ["status"],
        schema=SCHEMA,
    )

    op.create_table(
        "lottery_prospective_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("prediction_key", sa.String(64), nullable=False),
        sa.Column("pilot_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_by", sa.String(128)),
        sa.Column("analysis_date", sa.String(32)),
        sa.Column("target_date", sa.String(32)),
        sa.Column("lottery", sa.String(128)),
        sa.Column("position", sa.String(64)),
        sa.Column("input_numbers", postgresql.JSONB()),
        sa.Column("engine_version", sa.String(128), nullable=False),
        sa.Column("table1_version", sa.String(128), nullable=False),
        sa.Column("table2_version", sa.String(128), nullable=False),
        sa.Column("ranking_profile", sa.String(64), nullable=False, server_default="socio"),
        sa.Column(
            "tiebreak_profile",
            sa.String(64),
            nullable=False,
            server_default="TIEBREAK_PROFILE_SOCIO_V1",
        ),
        sa.Column("derivation_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidates", postgresql.JSONB()),
        sa.Column("ranking", postgresql.JSONB()),
        sa.Column("primary_signal", postgresql.JSONB()),
        sa.Column("secondary_signals", postgresql.JSONB()),
        sa.Column("multi_strong_candidates", postgresql.JSONB()),
        sa.Column("score_components", postgresql.JSONB()),
        sa.Column("confidence", sa.Float()),
        sa.Column("evidence", postgresql.JSONB()),
        sa.Column("tiebreak", postgresql.JSONB()),
        sa.Column("shadow_profiles", postgresql.JSONB()),
        sa.Column("lock_status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("locked_by", sa.String(128)),
        sa.Column("prediction_hash", sa.String(128)),
        sa.Column("canonical_payload", postgresql.JSONB()),
        sa.Column("engine_commit", sa.String(64)),
        sa.Column("result_received_at", sa.DateTime(timezone=True)),
        sa.Column("future_result", postgresql.JSONB()),
        sa.Column("evaluation_status", sa.String(64)),
        sa.Column("evaluation", postgresql.JSONB()),
        sa.Column("evaluated_at", sa.DateTime(timezone=True)),
        sa.Column("integrity_ok", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("input_complete", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("input_incomplete_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["pilot_id"],
            [f"{SCHEMA}.lottery_pilot_configurations.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("prediction_key", name="uq_lottery_prospective_prediction_key"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_lottery_prospective_runs_status",
        "lottery_prospective_runs",
        ["lock_status"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_lottery_prospective_runs_analysis_date",
        "lottery_prospective_runs",
        ["analysis_date"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_lottery_prospective_runs_target_date",
        "lottery_prospective_runs",
        ["target_date"],
        schema=SCHEMA,
    )

    op.create_table(
        "lottery_prospective_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("prediction_key", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("detail", postgresql.JSONB()),
        sa.Column("actor", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_lottery_prospective_audit_pred",
        "lottery_prospective_audit_logs",
        ["prediction_key", "created_at"],
        schema=SCHEMA,
    )

    op.create_table(
        "lottery_pilot_daily_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pilot_id", postgresql.UUID(as_uuid=True)),
        sa.Column("snapshot_date", sa.String(32), nullable=False),
        sa.Column("metrics", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_lottery_pilot_snapshot_date",
        "lottery_pilot_daily_snapshots",
        ["snapshot_date"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("lottery_pilot_daily_snapshots", schema=SCHEMA)
    op.drop_table("lottery_prospective_audit_logs", schema=SCHEMA)
    op.drop_table("lottery_prospective_runs", schema=SCHEMA)
    op.drop_table("lottery_pilot_configurations", schema=SCHEMA)
