"""Fase 3 — real expediente DGCP fields on bid packages."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "022_real_expediente"
down_revision = "021_corp_identity_pdf"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.add_column(
        "dgcp_bid_packages",
        sa.Column("real_expediente_status", sa.String(64), nullable=False, server_default="sin_generar"),
        schema=SCHEMA,
    )
    op.add_column(
        "dgcp_bid_packages",
        sa.Column("real_expediente_path", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "dgcp_bid_packages",
        sa.Column("real_expediente_generated_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "dgcp_bid_packages",
        sa.Column(
            "real_expediente_manifest",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("dgcp_bid_packages", "real_expediente_manifest", schema=SCHEMA)
    op.drop_column("dgcp_bid_packages", "real_expediente_generated_at", schema=SCHEMA)
    op.drop_column("dgcp_bid_packages", "real_expediente_path", schema=SCHEMA)
    op.drop_column("dgcp_bid_packages", "real_expediente_status", schema=SCHEMA)
