"""DGCP production: company, priority, sync, history

Revision ID: 003
Revises: 002
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.add_column("dgcp_opportunities", sa.Column("ocid", sa.String(128)), schema=SCHEMA)
    op.add_column("dgcp_opportunities", sa.Column("source_url", sa.Text()), schema=SCHEMA)
    op.add_column("dgcp_opportunities", sa.Column("dgcp_status", sa.String(64)), schema=SCHEMA)
    op.add_column("dgcp_opportunities", sa.Column("modalidad", sa.String(128)), schema=SCHEMA)
    op.add_column("dgcp_opportunities", sa.Column("objeto_proceso", sa.String(64)), schema=SCHEMA)
    op.add_column(
        "dgcp_opportunities",
        sa.Column("company", sa.String(32), nullable=False, server_default="unclassified"),
        schema=SCHEMA,
    )
    op.add_column(
        "dgcp_opportunities",
        sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
        schema=SCHEMA,
    )
    op.add_column("dgcp_opportunities", sa.Column("synced_at", sa.DateTime(timezone=True)), schema=SCHEMA)
    op.add_column(
        "dgcp_opportunities",
        sa.Column("raw_payload", postgresql.JSONB, nullable=False, server_default="{}"),
        schema=SCHEMA,
    )
    op.create_index("ix_dgcp_opportunities_company", "dgcp_opportunities", ["company"], schema=SCHEMA)
    op.create_index("ix_dgcp_opportunities_priority", "dgcp_opportunities", ["priority"], schema=SCHEMA)
    op.create_unique_constraint(
        "uq_dgcp_opportunities_tenant_code", "dgcp_opportunities", ["tenant_id", "code"], schema=SCHEMA
    )

    op.create_table(
        "dgcp_sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trigger", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("pages_synced", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        schema=SCHEMA,
    )
    op.create_index("ix_dgcp_sync_jobs_tenant", "dgcp_sync_jobs", ["tenant_id"], schema=SCHEMA)

    op.create_table(
        "dgcp_opportunity_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.dgcp_opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32)),
        sa.Column("notes", sa.Text),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dgcp_history_opportunity", "dgcp_opportunity_history", ["opportunity_id"], schema=SCHEMA
    )

    op.create_table(
        "dgcp_sync_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("interval_hours", sa.Integer, nullable=False, server_default="6"),
        sa.Column("max_pages", sa.Integer, nullable=False, server_default="5"),
        sa.Column("page_size", sa.Integer, nullable=False, server_default="50"),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("dgcp_sync_schedules", schema=SCHEMA)
    op.drop_table("dgcp_opportunity_history", schema=SCHEMA)
    op.drop_table("dgcp_sync_jobs", schema=SCHEMA)
    op.drop_constraint("uq_dgcp_opportunities_tenant_code", "dgcp_opportunities", schema=SCHEMA)
    for col in [
        "raw_payload", "synced_at", "priority", "company", "objeto_proceso",
        "modalidad", "dgcp_status", "source_url", "ocid",
    ]:
        op.drop_column("dgcp_opportunities", col, schema=SCHEMA)
