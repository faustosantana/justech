"""Odoo multi-company context and user mappings

Revision ID: 005
Revises: 004
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "user_company_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "jaios_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("odoo_company_id", sa.Integer(), nullable=False),
        sa.Column("odoo_company_name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "selected_at",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "jaios_user_id", name="uq_user_company_context"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_user_company_contexts_tenant_user",
        "user_company_contexts",
        ["tenant_id", "jaios_user_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "odoo_user_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "jaios_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("odoo_user_id", sa.Integer(), nullable=False),
        sa.Column("odoo_login", sa.String(255), nullable=False),
        sa.Column("odoo_partner_id", sa.Integer()),
        sa.Column(
            "allowed_company_ids",
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("default_company_id", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
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
        sa.UniqueConstraint("tenant_id", "jaios_user_id", name="uq_odoo_user_mapping"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_odoo_user_mappings_tenant",
        "odoo_user_mappings",
        ["tenant_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_odoo_user_mappings_tenant", table_name="odoo_user_mappings", schema=SCHEMA)
    op.drop_table("odoo_user_mappings", schema=SCHEMA)
    op.drop_index(
        "ix_user_company_contexts_tenant_user",
        table_name="user_company_contexts",
        schema=SCHEMA,
    )
    op.drop_table("user_company_contexts", schema=SCHEMA)
