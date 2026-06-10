"""corporate identity assets + document finalization records."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "021_corp_identity_pdf"
down_revision = "020_economic_offer_drafts"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "corporate_identity_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset_type", sa.String(16), nullable=False),
        sa.Column("company_key", sa.String(64), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_relative_path", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="disponible"),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "asset_type",
            "company_key",
            "filename",
            name="uq_corporate_identity_asset",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_corporate_identity_assets_tenant_id",
        "corporate_identity_assets",
        ["tenant_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "document_finalization_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.dgcp_opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requirement_key", sa.String(64), nullable=False),
        sa.Column("checklist_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("company_key", sa.String(64), nullable=False),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.dgcp_process_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_filename", sa.String(512), nullable=True),
        sa.Column("signature_filename", sa.String(255), nullable=True),
        sa.Column("stamp_filename", sa.String(255), nullable=True),
        sa.Column("output_filename", sa.String(512), nullable=False),
        sa.Column("output_storage_uri", sa.String(1024), nullable=False),
        sa.Column("previous_status", sa.String(64), nullable=True),
        sa.Column("new_status", sa.String(64), nullable=False, server_default="pdf_final_generado"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_document_finalization_records_opportunity_id",
        "document_finalization_records",
        ["opportunity_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("document_finalization_records", schema=SCHEMA)
    op.drop_table("corporate_identity_assets", schema=SCHEMA)
