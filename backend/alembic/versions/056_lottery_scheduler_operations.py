"""032 — Scheduler operations: state + alerts.

Revision ID: 056_lottery_scheduler_operations
Revises: 055_lottery_sync_control
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "056_lottery_scheduler_operations"
down_revision: Union[str, None] = "055_lottery_sync_control"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names(schema=SCHEMA))

    if "lottery_scheduler_state" not in tables:
        op.create_table(
            "lottery_scheduler_state",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("environment", sa.String(64), nullable=False, server_default="staging"),
            sa.Column("mode", sa.String(32), nullable=False, server_default="disabled"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("last_tick_at", sa.DateTime(timezone=True)),
            sa.Column("next_run_at", sa.DateTime(timezone=True)),
            sa.Column("last_run_id", postgresql.UUID(as_uuid=True)),
            sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("circuit_state", sa.String(32), nullable=False, server_default="closed"),
            sa.Column("circuit_opened_at", sa.DateTime(timezone=True)),
            sa.Column("circuit_reason", sa.String(512)),
            sa.Column("write_enabled_since", sa.DateTime(timezone=True)),
            sa.Column("source_contract_version", sa.String(64)),
            sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_lottery_scheduler_state_env",
            "lottery_scheduler_state",
            ["environment"],
            unique=True,
            schema=SCHEMA,
        )

    if "lottery_sync_alerts" not in tables:
        op.create_table(
            "lottery_sync_alerts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("environment", sa.String(64), nullable=False, server_default="staging"),
            sa.Column("severity", sa.String(16), nullable=False),
            sa.Column("code", sa.String(64), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("sync_run_id", postgresql.UUID(as_uuid=True)),
            sa.Column("status", sa.String(32), nullable=False, server_default="open"),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
            sa.Column("acknowledged_by", sa.String(255)),
            sa.Column("resolved_at", sa.DateTime(timezone=True)),
            sa.Column("resolved_by", sa.String(255)),
            sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_lottery_sync_alerts_status",
            "lottery_sync_alerts",
            ["environment", "status", "created_at"],
            schema=SCHEMA,
        )
        op.create_index(
            "ix_lottery_sync_alerts_code",
            "lottery_sync_alerts",
            ["code"],
            schema=SCHEMA,
        )


def downgrade() -> None:
    op.drop_index("ix_lottery_sync_alerts_code", table_name="lottery_sync_alerts", schema=SCHEMA)
    op.drop_index("ix_lottery_sync_alerts_status", table_name="lottery_sync_alerts", schema=SCHEMA)
    op.drop_table("lottery_sync_alerts", schema=SCHEMA)
    op.drop_index("ix_lottery_scheduler_state_env", table_name="lottery_scheduler_state", schema=SCHEMA)
    op.drop_table("lottery_scheduler_state", schema=SCHEMA)
