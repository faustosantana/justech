"""Histórico de adjudicaciones DGCP — indexación y búsqueda inteligente."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "033_dgcp_historical_awards"
down_revision = "032_dynamic_connectors"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "dgcp_historical_awards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("process_code", sa.String(128), nullable=False),
        sa.Column("contract_code", sa.String(128), nullable=True),
        sa.Column("buyer_institution", sa.String(512), nullable=False),
        sa.Column("buyer_institution_code", sa.String(64), nullable=True),
        sa.Column("award_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contract_object", sa.Text(), nullable=True),
        sa.Column("item_description", sa.Text(), nullable=True),
        sa.Column("item_description_user", sa.Text(), nullable=True),
        sa.Column("supplier_name", sa.String(512), nullable=True),
        sa.Column("supplier_rpe", sa.String(64), nullable=True),
        sa.Column("awarded_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="DOP"),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("total_line_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("unit_measure", sa.String(64), nullable=True),
        sa.Column("modality", sa.String(128), nullable=True),
        sa.Column("objeto_proceso", sa.String(128), nullable=True),
        sa.Column("award_status", sa.String(128), nullable=True),
        sa.Column("process_url", sa.Text(), nullable=True),
        sa.Column("contract_url", sa.Text(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="dgcp_contratos"),
        sa.Column("unspsc_family", sa.String(32), nullable=True),
        sa.Column("unspsc_class", sa.String(32), nullable=True),
        sa.Column("unspsc_subclass", sa.String(32), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("raw_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "process_code",
            "contract_code",
            "item_description_user",
            name="uq_dgcp_hist_award_line",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_dgcp_hist_awards_tenant", "dgcp_historical_awards", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_dgcp_hist_awards_institution", "dgcp_historical_awards", ["buyer_institution"], schema=SCHEMA)
    op.create_index("ix_dgcp_hist_awards_process", "dgcp_historical_awards", ["process_code"], schema=SCHEMA)
    op.create_index("ix_dgcp_hist_awards_supplier", "dgcp_historical_awards", ["supplier_name"], schema=SCHEMA)
    op.execute(
        f"CREATE INDEX ix_dgcp_hist_awards_search_gin ON {SCHEMA}.dgcp_historical_awards "
        f"USING gin (to_tsvector('spanish', search_text))"
    )

    op.create_table(
        "dgcp_historical_index_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("pages_indexed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contracts_indexed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_indexed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.ix_dgcp_hist_awards_search_gin")
    op.drop_table("dgcp_historical_index_jobs", schema=SCHEMA)
    op.drop_table("dgcp_historical_awards", schema=SCHEMA)
