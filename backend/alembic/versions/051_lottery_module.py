"""027 — Módulo Resultados de Loterías / Lotería IA (schema base).

Revision ID: 051_lottery_module
Revises: 026_m365_imap_accounts
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "051_lottery_module"
down_revision: Union[str, None] = "050_process_requirements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names(schema=SCHEMA))

    if "lottery_lotteries" not in tables:
        op.create_table(
            "lottery_lotteries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("source_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("normalized_name", sa.String(255), nullable=False),
            sa.Column("slug", sa.String(255), nullable=False),
            sa.Column("country", sa.String(64)),
            sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Santo_Domingo"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_loto", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_aggregate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("source_url", sa.Text()),
            sa.Column("first_draw_date", sa.Date()),
            sa.Column("last_draw_date", sa.Date()),
            sa.Column("draw_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("source_id", name="uq_lottery_lotteries_source_id"),
            sa.UniqueConstraint("slug", name="uq_lottery_lotteries_slug"),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_lotteries_normalized_name", "lottery_lotteries", ["normalized_name"], schema=SCHEMA)

    if "lottery_draws" not in tables:
        op.create_table(
            "lottery_draws",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "lottery_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.lottery_lotteries.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("draw_date", sa.Date(), nullable=False),
            sa.Column("draw_time", sa.Time()),
            sa.Column("game_name", sa.String(128), nullable=False, server_default="quiniela"),
            sa.Column("source_reference", sa.String(255)),
            sa.Column("source_url", sa.Text()),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("raw_payload", postgresql.JSONB()),
            sa.Column("scraped_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint(
                "lottery_id",
                "draw_date",
                "draw_time",
                "game_name",
                "source_reference",
                name="uq_lottery_draws_natural_key",
            ),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_draws_lottery_id", "lottery_draws", ["lottery_id"], schema=SCHEMA)
        op.create_index("ix_lottery_draws_lottery_date", "lottery_draws", ["lottery_id", "draw_date"], schema=SCHEMA)
        op.create_index(
            "ix_lottery_draws_lottery_date_time",
            "lottery_draws",
            ["lottery_id", "draw_date", "draw_time"],
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_draws_source_reference", "lottery_draws", ["source_reference"], schema=SCHEMA)

    if "lottery_draw_numbers" not in tables:
        op.create_table(
            "lottery_draw_numbers",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "draw_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.lottery_draws.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("position_label", sa.String(64), nullable=False),
            sa.Column("number_value", sa.String(32), nullable=False),
            sa.Column("number_raw", sa.String(32), nullable=False),
            sa.Column("number_type", sa.String(32), nullable=False, server_default="principal"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_draw_numbers_draw_id", "lottery_draw_numbers", ["draw_id"], schema=SCHEMA)
        op.create_index(
            "ix_lottery_draw_numbers_draw_position",
            "lottery_draw_numbers",
            ["draw_id", "position"],
            schema=SCHEMA,
        )
        op.create_index(
            "ix_lottery_draw_numbers_number_value",
            "lottery_draw_numbers",
            ["number_value"],
            schema=SCHEMA,
        )

    if "lottery_aliases" not in tables:
        op.create_table(
            "lottery_aliases",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "lottery_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.lottery_lotteries.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("alias", sa.String(255), nullable=False),
            sa.Column("normalized_alias", sa.String(255), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("normalized_alias", name="uq_lottery_aliases_normalized_alias"),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_aliases_lottery_id", "lottery_aliases", ["lottery_id"], schema=SCHEMA)
        op.create_index(
            "ix_lottery_aliases_normalized_alias",
            "lottery_aliases",
            ["normalized_alias"],
            schema=SCHEMA,
        )

    if "lottery_import_runs" not in tables:
        op.create_table(
            "lottery_import_runs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("mode", sa.String(32), nullable=False, server_default="sqlite_import"),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("source_path_hash", sa.String(64)),
            sa.Column("started_at", sa.DateTime(timezone=True)),
            sa.Column("finished_at", sa.DateTime(timezone=True)),
            sa.Column("lotteries_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("draws_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("numbers_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("errors_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("checkpoint", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column(
                "triggered_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )

    if "lottery_import_errors" not in tables:
        op.create_table(
            "lottery_import_errors",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "import_run_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.lottery_import_runs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("stage", sa.String(64), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("context", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_lottery_import_errors_import_run_id",
            "lottery_import_errors",
            ["import_run_id"],
            schema=SCHEMA,
        )

    if "lottery_saved_queries" not in tables:
        op.create_table(
            "lottery_saved_queries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_saved_queries_tenant_id", "lottery_saved_queries", ["tenant_id"], schema=SCHEMA)
        op.create_index("ix_lottery_saved_queries_user_id", "lottery_saved_queries", ["user_id"], schema=SCHEMA)
        op.create_index(
            "ix_lottery_saved_queries_tenant_user",
            "lottery_saved_queries",
            ["tenant_id", "user_id"],
            schema=SCHEMA,
        )

    if "lottery_chat_sessions" not in tables:
        op.create_table(
            "lottery_chat_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("title", sa.String(255)),
            sa.Column("context", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("last_message_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_chat_sessions_tenant_id", "lottery_chat_sessions", ["tenant_id"], schema=SCHEMA)
        op.create_index("ix_lottery_chat_sessions_user_id", "lottery_chat_sessions", ["user_id"], schema=SCHEMA)
        op.create_index(
            "ix_lottery_chat_sessions_tenant_user",
            "lottery_chat_sessions",
            ["tenant_id", "user_id"],
            schema=SCHEMA,
        )

    if "lottery_chat_messages" not in tables:
        op.create_table(
            "lottery_chat_messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "session_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.lottery_chat_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(16), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("tool_name", sa.String(128)),
            sa.Column("tool_payload", postgresql.JSONB()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_chat_messages_session_id", "lottery_chat_messages", ["session_id"], schema=SCHEMA)

    if "lottery_audit_log" not in tables:
        op.create_table(
            "lottery_audit_log",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="SET NULL"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
            ),
            sa.Column("action", sa.String(128), nullable=False),
            sa.Column("tool_name", sa.String(128)),
            sa.Column("parameters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("result_count", sa.Integer()),
            sa.Column("duration_ms", sa.Integer()),
            sa.Column("ip_address", sa.String(64)),
            sa.Column("error", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_lottery_audit_log_tenant_id", "lottery_audit_log", ["tenant_id"], schema=SCHEMA)
        op.create_index("ix_lottery_audit_log_user_id", "lottery_audit_log", ["user_id"], schema=SCHEMA)
        op.create_index(
            "ix_lottery_audit_log_tenant_created",
            "lottery_audit_log",
            ["tenant_id", "created_at"],
            schema=SCHEMA,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names(schema=SCHEMA))

    def drop_indexes(table: str, names: list[str]) -> None:
        if table not in tables:
            return
        existing = {ix["name"] for ix in insp.get_indexes(table, schema=SCHEMA)}
        for name in names:
            if name in existing:
                op.drop_index(name, table_name=table, schema=SCHEMA)

    drop_indexes(
        "lottery_audit_log",
        ["ix_lottery_audit_log_tenant_created", "ix_lottery_audit_log_user_id", "ix_lottery_audit_log_tenant_id"],
    )
    if "lottery_audit_log" in tables:
        op.drop_table("lottery_audit_log", schema=SCHEMA)

    drop_indexes("lottery_chat_messages", ["ix_lottery_chat_messages_session_id"])
    if "lottery_chat_messages" in tables:
        op.drop_table("lottery_chat_messages", schema=SCHEMA)

    drop_indexes(
        "lottery_chat_sessions",
        [
            "ix_lottery_chat_sessions_tenant_user",
            "ix_lottery_chat_sessions_user_id",
            "ix_lottery_chat_sessions_tenant_id",
        ],
    )
    if "lottery_chat_sessions" in tables:
        op.drop_table("lottery_chat_sessions", schema=SCHEMA)

    drop_indexes(
        "lottery_saved_queries",
        [
            "ix_lottery_saved_queries_tenant_user",
            "ix_lottery_saved_queries_user_id",
            "ix_lottery_saved_queries_tenant_id",
        ],
    )
    if "lottery_saved_queries" in tables:
        op.drop_table("lottery_saved_queries", schema=SCHEMA)

    drop_indexes("lottery_import_errors", ["ix_lottery_import_errors_import_run_id"])
    if "lottery_import_errors" in tables:
        op.drop_table("lottery_import_errors", schema=SCHEMA)

    if "lottery_import_runs" in tables:
        op.drop_table("lottery_import_runs", schema=SCHEMA)

    drop_indexes(
        "lottery_aliases",
        ["ix_lottery_aliases_normalized_alias", "ix_lottery_aliases_lottery_id"],
    )
    if "lottery_aliases" in tables:
        op.drop_table("lottery_aliases", schema=SCHEMA)

    drop_indexes(
        "lottery_draw_numbers",
        [
            "ix_lottery_draw_numbers_number_value",
            "ix_lottery_draw_numbers_draw_position",
            "ix_lottery_draw_numbers_draw_id",
        ],
    )
    if "lottery_draw_numbers" in tables:
        op.drop_table("lottery_draw_numbers", schema=SCHEMA)

    drop_indexes(
        "lottery_draws",
        [
            "ix_lottery_draws_source_reference",
            "ix_lottery_draws_lottery_date_time",
            "ix_lottery_draws_lottery_date",
            "ix_lottery_draws_lottery_id",
        ],
    )
    if "lottery_draws" in tables:
        op.drop_table("lottery_draws", schema=SCHEMA)

    drop_indexes("lottery_lotteries", ["ix_lottery_lotteries_normalized_name"])
    if "lottery_lotteries" in tables:
        op.drop_table("lottery_lotteries", schema=SCHEMA)
