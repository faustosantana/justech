"""Ampliar size_bytes en m365_repository_files a BIGINT."""

from alembic import op
import sqlalchemy as sa

revision = "029_m365_repo_size_bigint"
down_revision = "028_m365_repository"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.alter_column(
        "m365_repository_files",
        "size_bytes",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.alter_column(
        "m365_repository_files",
        "size_bytes",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
        schema=SCHEMA,
    )
