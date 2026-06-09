"""Widen content_hash for parser version suffix."""

from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.alter_column(
        "price_list_files",
        "content_hash",
        type_=sa.String(80),
        existing_type=sa.String(64),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.alter_column(
        "price_list_files",
        "content_hash",
        type_=sa.String(64),
        existing_type=sa.String(80),
        schema=SCHEMA,
    )
