"""Hub documental — pendientes y tokens de formulario de perfil."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "036_document_hub_pending"
down_revision = "035_repository_sync_engine"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "document_pending_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_key", sa.String(64), nullable=False),
        sa.Column(
            "company_profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.licitador_company_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("item_type", sa.String(32), nullable=False, server_default="document"),
        sa.Column("item_key", sa.String(128), nullable=False),
        sa.Column("item_label", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("severity", sa.String(32), nullable=False, server_default="missing"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_to_email", sa.String(255), nullable=True),
        sa.Column("requested_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("reminder_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("onedrive_path", sa.Text(), nullable=True),
        sa.Column("onedrive_url", sa.Text(), nullable=True),
        sa.Column("suggested_filename", sa.String(512), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="auto"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_document_pending_tenant_status", "document_pending_items", ["tenant_id", "status"], schema=SCHEMA)
    op.create_index("ix_document_pending_company", "document_pending_items", ["tenant_id", "company_key"], schema=SCHEMA)

    op.create_table(
        "company_profile_form_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "company_profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.licitador_company_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_profile_form_token", "company_profile_form_tokens", ["token"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("company_profile_form_tokens", schema=SCHEMA)
    op.drop_table("document_pending_items", schema=SCHEMA)
