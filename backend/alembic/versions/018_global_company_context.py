"""Migración — contexto global multiempresa."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_company_contexts",
        sa.Column("selection_mode", sa.String(16), nullable=False, server_default="single"),
        schema="jaios",
    )
    op.add_column(
        "user_company_contexts",
        sa.Column(
            "selected_company_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        schema="jaios",
    )


def downgrade() -> None:
    op.drop_column("user_company_contexts", "selected_company_ids", schema="jaios")
    op.drop_column("user_company_contexts", "selection_mode", schema="jaios")
