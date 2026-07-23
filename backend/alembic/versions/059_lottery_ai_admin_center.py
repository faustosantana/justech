"""059 — Lottery AI Admin Center (prompts, config versions, tools, packs, audit).

Revision ID: 059_lottery_ai_admin_center
Revises: 058_lottery_3_0_platform
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "059_lottery_ai_admin_center"
down_revision: Union[str, None] = "058_lottery_3_0_platform"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "lottery_ai_prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("description", sa.Text()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("blocks", postgresql.JSONB()),
        sa.Column("changelog", sa.Text()),
        sa.Column("recommended_model", sa.String(128)),
        sa.Column("temperature", sa.Numeric(4, 2)),
        sa.Column("max_tokens", sa.Integer()),
        sa.Column("timeout_seconds", sa.Integer()),
        sa.Column("variables", postgresql.JSONB()),
        sa.Column("tags", postgresql.JSONB()),
        sa.Column("checksum", sa.String(64)),
        sa.Column("benchmark_id", postgresql.UUID(as_uuid=True)),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("previous_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", "version", name="uq_lottery_ai_prompt_name_version"),
        schema=SCHEMA,
    )
    op.create_index("ix_lottery_ai_prompt_status", "lottery_ai_prompt_versions", ["status"], schema=SCHEMA)
    op.create_index("ix_lottery_ai_prompt_versions_tenant_id", "lottery_ai_prompt_versions", ["tenant_id"], schema=SCHEMA)

    op.create_table(
        "lottery_ai_config_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("version_label", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("description", sa.Text()),
        sa.Column("changelog", sa.Text()),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("previous_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_lottery_ai_config_status", "lottery_ai_config_versions", ["status"], schema=SCHEMA)
    op.create_index("ix_lottery_ai_config_versions_tenant_id", "lottery_ai_config_versions", ["tenant_id"], schema=SCHEMA)

    op.create_table(
        "lottery_ai_tool_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(64)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("timeout_seconds", sa.Integer()),
        sa.Column("rate_limit_per_min", sa.Integer()),
        sa.Column("allowed_roles", postgresql.JSONB()),
        sa.Column("blocked_lottery_ids", postgresql.JSONB()),
        sa.Column("config", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tool_name", "tenant_id", name="uq_lottery_ai_tool_tenant"),
        schema=SCHEMA,
    )
    op.create_index("ix_lottery_ai_tool_settings_tenant_id", "lottery_ai_tool_settings", ["tenant_id"], schema=SCHEMA)

    op.create_table(
        "lottery_ai_analysis_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("pack_key", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("pack_key", "tenant_id", name="uq_lottery_ai_pack_tenant"),
        schema=SCHEMA,
    )
    op.create_index("ix_lottery_ai_analysis_packs_tenant_id", "lottery_ai_analysis_packs", ["tenant_id"], schema=SCHEMA)

    op.create_table(
        "lottery_ai_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64)),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("before", postgresql.JSONB()),
        sa.Column("after", postgresql.JSONB()),
        sa.Column("reason", sa.Text()),
        sa.Column("version_label", sa.String(64)),
        sa.Column("result", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_lottery_ai_audit_created", "lottery_ai_audit_events", ["created_at"], schema=SCHEMA)
    op.create_index("ix_lottery_ai_audit_events_tenant_id", "lottery_ai_audit_events", ["tenant_id"], schema=SCHEMA)

    op.create_table(
        "lottery_ai_benchmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("cases", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_result", postgresql.JSONB()),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_lottery_ai_benchmarks_tenant_id", "lottery_ai_benchmarks", ["tenant_id"], schema=SCHEMA)

    op.create_table(
        "lottery_ai_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB()),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_lottery_ai_alerts_created", "lottery_ai_alerts", ["created_at"], schema=SCHEMA)
    op.create_index("ix_lottery_ai_alerts_tenant_id", "lottery_ai_alerts", ["tenant_id"], schema=SCHEMA)


def downgrade() -> None:
    for table in (
        "lottery_ai_alerts",
        "lottery_ai_benchmarks",
        "lottery_ai_audit_events",
        "lottery_ai_analysis_packs",
        "lottery_ai_tool_settings",
        "lottery_ai_config_versions",
        "lottery_ai_prompt_versions",
    ):
        op.drop_table(table, schema=SCHEMA)
