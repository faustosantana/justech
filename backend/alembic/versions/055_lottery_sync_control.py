"""031 — Sync control: runs enriquecidos, revisiones, checkpoints.

Revision ID: 055_lottery_sync_control
Revises: 054_lottery_secure_shares
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "055_lottery_sync_control"
down_revision: Union[str, None] = "054_lottery_secure_shares"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names(schema=SCHEMA))

    if "lottery_sync_runs" in tables:
        cols = {c["name"] for c in insp.get_columns("lottery_sync_runs", schema=SCHEMA)}
        adds = [
            ("environment", sa.String(64)),
            ("mode", sa.String(32)),
            ("write_enabled", sa.Boolean(), sa.text("false")),
            ("from_date", sa.Date()),
            ("to_date", sa.Date()),
            ("lottery_ids", postgresql.JSONB(), sa.text("'[]'::jsonb")),
            ("heartbeat_at", sa.DateTime(timezone=True)),
            ("lock_key", sa.String(255)),
            ("checkpoint", postgresql.JSONB(), sa.text("'{}'::jsonb")),
            ("records_inserted", sa.Integer(), "0"),
            ("records_unchanged", sa.Integer(), "0"),
            ("records_changed", sa.Integer(), "0"),
            ("records_conflicted", sa.Integer(), "0"),
            ("records_invalid", sa.Integer(), "0"),
            ("draws_before", sa.Integer()),
            ("draws_after", sa.Integer()),
            ("numbers_before", sa.Integer()),
            ("numbers_after", sa.Integer()),
            ("warning_count", sa.Integer(), "0"),
            ("initiated_by", sa.String(255)),
            ("rollback_status", sa.String(32)),
            ("change_policy", sa.String(32), sa.text("'reject'")),
            ("inserted_draw_ids", postgresql.JSONB(), sa.text("'[]'::jsonb")),
            ("updated_draw_ids", postgresql.JSONB(), sa.text("'[]'::jsonb")),
            ("backup_path", sa.String(512)),
        ]
        for name, coltype, *rest in adds:
            if name in cols:
                continue
            kwargs = {}
            server_default = rest[0] if rest else None
            if server_default is not None:
                if isinstance(server_default, str) and server_default.isdigit():
                    op.add_column(
                        "lottery_sync_runs",
                        sa.Column(name, coltype, nullable=False, server_default=server_default),
                        schema=SCHEMA,
                    )
                else:
                    op.add_column(
                        "lottery_sync_runs",
                        sa.Column(name, coltype, server_default=server_default),
                        schema=SCHEMA,
                    )
            else:
                op.add_column("lottery_sync_runs", sa.Column(name, coltype), schema=SCHEMA)

    if "lottery_draw_revisions" not in tables:
        op.create_table(
            "lottery_draw_revisions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("draw_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.lottery_draws.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sync_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.lottery_sync_runs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("previous_content_hash", sa.String(64), nullable=True),
            sa.Column("new_content_hash", sa.String(64), nullable=False),
            sa.Column("previous_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("new_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("change_reason", sa.String(255), nullable=True),
            sa.Column("source", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", sa.String(255), nullable=True),
            sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reverted_by", sa.String(255), nullable=True),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_draw_revisions_draw", "lottery_draw_revisions", ["draw_id"], schema=SCHEMA)
        op.create_index("ix_lottery_draw_revisions_run", "lottery_draw_revisions", ["sync_run_id"], schema=SCHEMA)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names(schema=SCHEMA))
    if "lottery_draw_revisions" in tables:
        op.drop_table("lottery_draw_revisions", schema=SCHEMA)
    if "lottery_sync_runs" in tables:
        cols = {c["name"] for c in insp.get_columns("lottery_sync_runs", schema=SCHEMA)}
        for name in (
            "environment", "mode", "write_enabled", "from_date", "to_date", "lottery_ids",
            "heartbeat_at", "lock_key", "checkpoint", "records_inserted", "records_unchanged",
            "records_changed", "records_conflicted", "records_invalid", "draws_before",
            "draws_after", "numbers_before", "numbers_after", "warning_count", "initiated_by",
            "rollback_status", "change_policy", "inserted_draw_ids", "updated_draw_ids", "backup_path",
        ):
            if name in cols:
                op.drop_column("lottery_sync_runs", name, schema=SCHEMA)
