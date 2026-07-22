"""029 — Favoritos, preferencias, recientes y metadatos de exportación.

Revision ID: 053_lottery_productization
Revises: 052_lottery_draw_uniqueness
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "053_lottery_productization"
down_revision: Union[str, None] = "052_lottery_draw_uniqueness"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names(schema=SCHEMA))

    if "lottery_user_favorites" not in tables:
        op.create_table(
            "lottery_user_favorites",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("lottery_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.lottery_lotteries.id", ondelete="CASCADE"), nullable=False),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("tenant_id", "user_id", "lottery_id", name="uq_lottery_favorites_tenant_user_lottery"),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_favorites_tenant_user", "lottery_user_favorites", ["tenant_id", "user_id"], schema=SCHEMA)

    if "lottery_user_preferences" not in tables:
        op.create_table(
            "lottery_user_preferences",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("tenant_id", "user_id", name="uq_lottery_prefs_tenant_user"),
            schema=SCHEMA,
        )

    if "lottery_recent_queries" not in tables:
        op.create_table(
            "lottery_recent_queries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("query_type", sa.String(64), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("parameters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_recent_tenant_user_created", "lottery_recent_queries", ["tenant_id", "user_id", "created_at"], schema=SCHEMA)

    if "lottery_exports" not in tables:
        op.create_table(
            "lottery_exports",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("query_type", sa.String(64), nullable=False),
            sa.Column("format", sa.String(16), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="ready"),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("storage_name", sa.String(255), nullable=False),
            sa.Column("mime_type", sa.String(128), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("row_count", sa.Integer(), nullable=True),
            sa.Column("parameters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_exports_tenant_user", "lottery_exports", ["tenant_id", "user_id"], schema=SCHEMA)
        op.create_index("ix_lottery_exports_expires", "lottery_exports", ["expires_at"], schema=SCHEMA)

    # Enrich saved queries without breaking existing rows
    cols = {c["name"] for c in insp.get_columns("lottery_saved_queries", schema=SCHEMA)} if "lottery_saved_queries" in tables else set()
    if "lottery_saved_queries" in tables:
        if "description" not in cols:
            op.add_column("lottery_saved_queries", sa.Column("description", sa.String(512), nullable=True), schema=SCHEMA)
        if "query_type" not in cols:
            op.add_column("lottery_saved_queries", sa.Column("query_type", sa.String(64), nullable=True), schema=SCHEMA)
        if "is_favorite" not in cols:
            op.add_column("lottery_saved_queries", sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")), schema=SCHEMA)
        if "run_count" not in cols:
            op.add_column("lottery_saved_queries", sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"), schema=SCHEMA)
        if "last_run_at" not in cols:
            op.add_column("lottery_saved_queries", sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA)
        if "tags" not in cols:
            op.add_column("lottery_saved_queries", sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")), schema=SCHEMA)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names(schema=SCHEMA))

    if "lottery_saved_queries" in tables:
        cols = {c["name"] for c in insp.get_columns("lottery_saved_queries", schema=SCHEMA)}
        for col in ("tags", "last_run_at", "run_count", "is_favorite", "query_type", "description"):
            if col in cols:
                op.drop_column("lottery_saved_queries", col, schema=SCHEMA)

    for table in ("lottery_exports", "lottery_recent_queries", "lottery_user_preferences", "lottery_user_favorites"):
        if table in tables:
            op.drop_table(table, schema=SCHEMA)
