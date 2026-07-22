"""Cache de búsqueda histórica similar DGCP por proceso (on-demand)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "034_dgcp_hist_similar_cache"
down_revision = "033_dgcp_historical_awards"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "dgcp_process_historical_similar_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "opportunity_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.dgcp_opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("process_code", sa.String(128), nullable=False),
        sa.Column("buyer_institution", sa.String(512), nullable=False),
        sa.Column("keywords_used", JSONB, nullable=False, server_default="[]"),
        sa.Column("searched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("results", JSONB, nullable=False, server_default="{}"),
        sa.Column("source", sa.String(64), nullable=False, server_default="dgcp_api_on_demand"),
        sa.Column("status", sa.String(32), nullable=False, server_default="searched"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("pages_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidates_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("refresh_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "opportunity_id", name="uq_dgcp_hist_similar_cache_opp"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dgcp_hist_similar_cache_tenant",
        "dgcp_process_historical_similar_results",
        ["tenant_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dgcp_hist_similar_cache_expires",
        "dgcp_process_historical_similar_results",
        ["expires_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("dgcp_process_historical_similar_results", schema=SCHEMA)
