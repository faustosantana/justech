"""Admin Center + M365 user accounts (preparación)

Revision ID: 007
Revises: 006
Create Date: 2026-06-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.add_column(
        "tenant_memberships",
        sa.Column("department", sa.String(64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tenant_memberships",
        sa.Column(
            "supervisor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "tenant_memberships",
        sa.Column(
            "visible_company_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "tenant_memberships",
        sa.Column("odoo_user_id", sa.Integer(), nullable=True),
        schema=SCHEMA,
    )

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "key", name="uq_departments_tenant_key"),
        schema=SCHEMA,
    )

    op.create_table(
        "tenant_modules",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("module_key", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_future", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )

    op.add_column(
        "routing_rules",
        sa.Column("default_supervisor_name", sa.String(128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "routing_rules",
        sa.Column(
            "default_supervisor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "m365_user_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "jaios_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("microsoft_user_id", sa.String(128), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("connection_status", sa.String(32), nullable=False, server_default="not_connected"),
        sa.Column("scopes_granted", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "jaios_user_id", name="uq_m365_user_accounts_tenant_user"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("m365_user_accounts", schema=SCHEMA)
    op.drop_column("routing_rules", "default_supervisor_id", schema=SCHEMA)
    op.drop_column("routing_rules", "default_supervisor_name", schema=SCHEMA)
    op.drop_table("tenant_modules", schema=SCHEMA)
    op.drop_table("departments", schema=SCHEMA)
    op.drop_column("tenant_memberships", "odoo_user_id", schema=SCHEMA)
    op.drop_column("tenant_memberships", "visible_company_ids", schema=SCHEMA)
    op.drop_column("tenant_memberships", "supervisor_id", schema=SCHEMA)
    op.drop_column("tenant_memberships", "department", schema=SCHEMA)
