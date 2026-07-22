"""030 — Shares seguros y sync runs (dry-run).

Revision ID: 054_lottery_secure_shares
Revises: 053_lottery_productization
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "054_lottery_secure_shares"
down_revision: Union[str, None] = "053_lottery_productization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names(schema=SCHEMA))

    if "lottery_shared_queries" not in tables:
        op.create_table(
            "lottery_shared_queries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(128), nullable=False),
            sa.Column("query_type", sa.String(64), nullable=False),
            sa.Column("query_parameters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("max_views", sa.Integer(), nullable=True),
            sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("allow_export", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_shares_tenant_user", "lottery_shared_queries", ["tenant_id", "created_by_user_id"], schema=SCHEMA)
        op.create_index("ix_lottery_shares_token_hash", "lottery_shared_queries", ["token_hash"], unique=True, schema=SCHEMA)
        op.create_index("ix_lottery_shares_expires", "lottery_shared_queries", ["expires_at"], schema=SCHEMA)

    if "lottery_sync_runs" not in tables:
        op.create_table(
            "lottery_sync_runs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("source", sa.String(64), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="running"),
            sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("records_fetched", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_new", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_skipped", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("conflicts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_cursor", sa.String(255), nullable=True),
            sa.Column("last_successful_draw_date", sa.Date(), nullable=True),
            sa.Column("source_response_hash", sa.String(128), nullable=True),
            sa.Column("app_version", sa.String(64), nullable=True),
            sa.Column("git_commit", sa.String(64), nullable=True),
            sa.Column("report", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("error_message", sa.Text(), nullable=True),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_sync_runs_started", "lottery_sync_runs", ["started_at"], schema=SCHEMA)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names(schema=SCHEMA))
    if "lottery_sync_runs" in tables:
        op.drop_table("lottery_sync_runs", schema=SCHEMA)
    if "lottery_shared_queries" in tables:
        op.drop_table("lottery_shared_queries", schema=SCHEMA)
