"""economic_offer_drafts table for DGCP Odoo quotation integration."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "020_economic_offer_drafts"
down_revision = "019_membership_default_company"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "economic_offer_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.dgcp_opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("odoo_partner_match_id", sa.Integer(), nullable=True),
        sa.Column("suggested_products", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("estimated_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="DOP"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("odoo_quotation_id", sa.Integer(), nullable=True),
        sa.Column("odoo_quotation_name", sa.String(64), nullable=True),
        sa.Column("process_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.dgcp_process_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "opportunity_id", "requirement_id", name="uq_economic_offer_draft_opportunity_requirement"),
        schema=SCHEMA,
    )
    op.create_index("ix_economic_offer_drafts_tenant_id", "economic_offer_drafts", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_economic_offer_drafts_opportunity_id", "economic_offer_drafts", ["opportunity_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("economic_offer_drafts", schema=SCHEMA)
