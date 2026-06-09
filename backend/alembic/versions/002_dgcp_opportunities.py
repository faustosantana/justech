"""Add dgcp_opportunities table

Revision ID: 002
Revises: 001
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "dgcp_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("institution", sa.String(255), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="DOP"),
        sa.Column("probability", sa.Integer, nullable=False, server_default="0"),
        sa.Column("score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="detected"),
        sa.Column("deadline", sa.Date, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("full_info", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("similar_history", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("risks", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("ai_recommendations", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("suggested_action", sa.String(64)),
        sa.Column("justech_potential_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index("ix_dgcp_opportunities_tenant_id", "dgcp_opportunities", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_dgcp_opportunities_code", "dgcp_opportunities", ["code"], schema=SCHEMA)
    op.create_index("ix_dgcp_opportunities_status", "dgcp_opportunities", ["status"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("dgcp_opportunities", schema=SCHEMA)
