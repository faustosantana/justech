"""Configuración de integraciones por tenant (UI, sin .env)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "031_integration_settings"
down_revision = "030_odoo_permission_cache"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "tenant_integration_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("secrets_encrypted", JSONB, nullable=False, server_default="{}"),
        sa.Column("connected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_ok", sa.Boolean(), nullable=True),
        sa.Column("last_test_message", sa.Text(), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "provider", name="uq_tenant_integration_provider"),
        schema=SCHEMA,
    )
    op.create_index("ix_tenant_integration_tenant", "tenant_integration_settings", ["tenant_id"], schema=SCHEMA)

    op.create_table(
        "integration_repository_bindings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("folder_key", sa.String(64), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="onedrive"),
        sa.Column("graph_item_id", sa.String(256), nullable=True),
        sa.Column("drive_id", sa.String(256), nullable=True),
        sa.Column("folder_path", sa.Text(), nullable=True),
        sa.Column("web_url", sa.Text(), nullable=True),
        sa.Column("auto_sync", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("indexed_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "folder_key", name="uq_integration_repo_folder"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("integration_repository_bindings", schema=SCHEMA)
    op.drop_table("tenant_integration_settings", schema=SCHEMA)
