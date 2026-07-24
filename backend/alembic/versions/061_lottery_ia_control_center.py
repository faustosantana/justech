"""061 — Lottery IA Control Center: prediction motors registry + prompt version metadata.

Revision ID: 061_lottery_ia_control_center
Revises: 060_lottery_ai_alerting_closeout
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "061_lottery_ia_control_center"
down_revision: Union[str, None] = "060_lottery_ai_alerting_closeout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "lottery_prediction_motors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="NO_IMPLEMENTADO"),
        sa.Column("implemented", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("implementation_ref", sa.String(255)),
        sa.Column("version", sa.String(64)),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("weight", sa.Numeric(8, 4)),
        sa.Column("docs", sa.Text()),
        sa.Column("health", sa.String(32)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_result", postgresql.JSONB()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_lottery_prediction_motors_status",
        "lottery_prediction_motors",
        ["status"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_lottery_prediction_motors_tenant_id",
        "lottery_prediction_motors",
        ["tenant_id"],
        schema=SCHEMA,
    )
    op.create_unique_constraint(
        "uq_lottery_prediction_motor_tenant_key",
        "lottery_prediction_motors",
        ["key", "tenant_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "lottery_prediction_motor_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("motor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("trigger", sa.String(32), nullable=False, server_default="admin"),
        sa.Column("input", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output", postgresql.JSONB()),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["motor_id"],
            [f"{SCHEMA}.lottery_prediction_motors.id"],
            ondelete="CASCADE",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_lottery_prediction_runs_motor",
        "lottery_prediction_motor_runs",
        ["motor_id", "started_at"],
        schema=SCHEMA,
    )

    # Prompt version human metadata (I-4/I-5) — additive, nullable
    bind = op.get_bind()
    cols = {
        c["name"]
        for c in sa.inspect(bind).get_columns("lottery_ai_prompt_versions", schema=SCHEMA)
    }
    add_cols = [
        ("display_name", sa.Column("display_name", sa.String(255))),
        ("change_reason", sa.Column("change_reason", sa.Text())),
        ("notes", sa.Column("notes", sa.Text())),
        ("analysis_steps", sa.Column("analysis_steps", postgresql.JSONB())),
        ("tool_bindings", sa.Column("tool_bindings", postgresql.JSONB())),
        ("motor_bindings", sa.Column("motor_bindings", postgresql.JSONB())),
        ("benchmark_summary", sa.Column("benchmark_summary", postgresql.JSONB())),
        ("gates_snapshot", sa.Column("gates_snapshot", postgresql.JSONB())),
        ("archived_at", sa.Column("archived_at", sa.DateTime(timezone=True))),
        ("parent_draft_of", sa.Column("parent_draft_of", postgresql.UUID(as_uuid=True))),
    ]
    for name, col in add_cols:
        if name not in cols:
            op.add_column("lottery_ai_prompt_versions", col, schema=SCHEMA)


def downgrade() -> None:
    bind = op.get_bind()
    cols = {
        c["name"]
        for c in sa.inspect(bind).get_columns("lottery_ai_prompt_versions", schema=SCHEMA)
    }
    for name in (
        "parent_draft_of",
        "archived_at",
        "gates_snapshot",
        "benchmark_summary",
        "motor_bindings",
        "tool_bindings",
        "analysis_steps",
        "notes",
        "change_reason",
        "display_name",
    ):
        if name in cols:
            op.drop_column("lottery_ai_prompt_versions", name, schema=SCHEMA)

    op.drop_table("lottery_prediction_motor_runs", schema=SCHEMA)
    op.drop_table("lottery_prediction_motors", schema=SCHEMA)
