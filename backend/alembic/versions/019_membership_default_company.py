"""membership default_company_id for admin empresas."""

from alembic import op
import sqlalchemy as sa

revision = "019_membership_default_company"
down_revision = "018"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.add_column(
        "tenant_memberships",
        sa.Column("default_company_id", sa.Integer(), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("tenant_memberships", "default_company_id", schema=SCHEMA)
