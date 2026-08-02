"""063 — Lottery IA conversational provider settings (UI / DB driven).

Revision ID: 063_lottery_ai_settings
Revises: 062_lottery_prospective_pilot
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "063_lottery_ai_settings"
down_revision: Union[str, None] = "062_lottery_prospective_pilot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "lottery_ai_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("conversation_provider", sa.String(32), nullable=False, server_default="huawei"),
        sa.Column(
            "conversation_model", sa.String(128), nullable=False, server_default="deepseek-v4-flash"
        ),
        sa.Column("temperature", sa.Numeric(4, 2), nullable=False, server_default="0"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="700"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_test_at", sa.DateTime(timezone=True)),
        sa.Column("last_test_ok", sa.Boolean()),
        sa.Column("last_test_latency_ms", sa.Numeric(12, 2)),
        sa.Column("last_test_model", sa.String(128)),
        sa.Column("last_test_error", sa.Text()),
        sa.Column("last_test_message", sa.Text()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_lottery_ai_settings_active",
        "lottery_ai_settings",
        ["is_active"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_lottery_ai_settings_active", table_name="lottery_ai_settings", schema=SCHEMA)
    op.drop_table("lottery_ai_settings", schema=SCHEMA)
