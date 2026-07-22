"""Repositorios empresariales M365 — indexación y clasificación."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "028_m365_repository"
down_revision = "027_m365_multi_account"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "m365_repository_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id"), nullable=False),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.m365_user_accounts.id"), nullable=True),
        sa.Column("source", sa.String(32), server_default="onedrive", nullable=False),
        sa.Column("graph_item_id", sa.String(256), nullable=False),
        sa.Column("drive_id", sa.String(256), nullable=True),
        sa.Column("parent_path", sa.Text(), server_default="", nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("web_url", sa.Text(), nullable=True),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("is_folder", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("document_category", sa.String(64), server_default="general", nullable=False),
        sa.Column("document_type", sa.String(64), server_default="general", nullable=False),
        sa.Column("folder_category", sa.String(64), server_default="general", nullable=False),
        sa.Column("classification_confidence", sa.Integer(), server_default="50", nullable=False),
        sa.Column("tags", JSONB(), server_default="[]", nullable=False),
        sa.Column("company_key", sa.String(64), nullable=True),
        sa.Column("modified_at_graph", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_m365_repo_tenant_category", "m365_repository_files", ["tenant_id", "document_category"], schema=SCHEMA)
    op.create_index("ix_m365_repo_graph_item", "m365_repository_files", ["tenant_id", "graph_item_id"], unique=True, schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_m365_repo_graph_item", table_name="m365_repository_files", schema=SCHEMA)
    op.drop_index("ix_m365_repo_tenant_category", table_name="m365_repository_files", schema=SCHEMA)
    op.drop_table("m365_repository_files", schema=SCHEMA)
