"""065 — Lottery AI usage: lottery_key for consumption dashboard filters.

Revision ID: 065_lottery_ai_usage_lottery_key
Revises: 064_lottery_ai_openai_credentials
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "065_lottery_ai_usage_lottery_key"
down_revision: Union[str, None] = "064_lottery_ai_openai_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("lottery_ai_usage", schema=SCHEMA):
        return
    cols = {c["name"] for c in insp.get_columns("lottery_ai_usage", schema=SCHEMA)}
    if "lottery_key" not in cols:
        op.add_column(
            "lottery_ai_usage",
            sa.Column("lottery_key", sa.String(64), nullable=True),
            schema=SCHEMA,
        )
    indexes = {ix["name"] for ix in insp.get_indexes("lottery_ai_usage", schema=SCHEMA)}
    if "ix_lottery_ai_usage_lottery_key" not in indexes:
        op.create_index(
            "ix_lottery_ai_usage_lottery_key",
            "lottery_ai_usage",
            ["lottery_key"],
            schema=SCHEMA,
        )
    if "ix_lottery_ai_usage_created_at" not in indexes:
        op.create_index(
            "ix_lottery_ai_usage_created_at",
            "lottery_ai_usage",
            ["created_at"],
            schema=SCHEMA,
        )
    if "ix_lottery_ai_usage_tenant_created" not in indexes:
        op.create_index(
            "ix_lottery_ai_usage_tenant_created",
            "lottery_ai_usage",
            ["tenant_id", "created_at"],
            schema=SCHEMA,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("lottery_ai_usage", schema=SCHEMA):
        return
    indexes = {ix["name"] for ix in insp.get_indexes("lottery_ai_usage", schema=SCHEMA)}
    for name in (
        "ix_lottery_ai_usage_tenant_created",
        "ix_lottery_ai_usage_created_at",
        "ix_lottery_ai_usage_lottery_key",
    ):
        if name in indexes:
            op.drop_index(name, table_name="lottery_ai_usage", schema=SCHEMA)
    cols = {c["name"] for c in insp.get_columns("lottery_ai_usage", schema=SCHEMA)}
    if "lottery_key" in cols:
        op.drop_column("lottery_ai_usage", "lottery_key", schema=SCHEMA)
