"""DGCP classification confidence fields

Revision ID: 004
Revises: 003
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.add_column(
        "dgcp_opportunities",
        sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="0"),
        schema=SCHEMA,
    )
    op.add_column(
        "dgcp_opportunities",
        sa.Column("classification_reason", sa.Text()),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("dgcp_opportunities", "classification_reason", schema=SCHEMA)
    op.drop_column("dgcp_opportunities", "confidence_score", schema=SCHEMA)
