"""Conectores dinámicos — APIs configurables desde UI."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "032_dynamic_connectors"
down_revision = "031_integration_settings"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "integration_providers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(96), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("connector_type", sa.String(32), nullable=False, server_default="rest_api"),
        sa.Column("auth_method", sa.String(32), nullable=False, server_default="api_key"),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("secrets_encrypted", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_link_mode", sa.String(16), nullable=False, server_default="none"),
        sa.Column("documentation", sa.Text(), nullable=True),
        sa.Column("read_only", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("environment", sa.String(16), nullable=False, server_default="development"),
        sa.Column("connected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_ok", sa.Boolean(), nullable=True),
        sa.Column("last_test_message", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_integration_provider_slug"),
        schema=SCHEMA,
    )
    op.create_index("ix_integration_providers_tenant", "integration_providers", ["tenant_id"], schema=SCHEMA)

    op.create_table(
        "integration_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.integration_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("credential_key", sa.String(64), nullable=False),
        sa.Column("value_encrypted", sa.Text(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_by", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("provider_id", "credential_key", name="uq_integration_credential_key"),
        schema=SCHEMA,
    )

    op.create_table(
        "integration_endpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.integration_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("http_method", sa.String(8), nullable=False, server_default="GET"),
        sa.Column("query_params", JSONB, nullable=False, server_default="{}"),
        sa.Column("body_template", sa.Text(), nullable=True),
        sa.Column("headers", JSONB, nullable=False, server_default="{}"),
        sa.Column("response_hint", JSONB, nullable=False, server_default="{}"),
        sa.Column("transform", JSONB, nullable=False, server_default="{}"),
        sa.Column("assistant_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "integration_user_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.integration_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_account_id", sa.String(255), nullable=True),
        sa.Column("external_account_label", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="linked"),
        sa.Column("permissions", JSONB, nullable=False, server_default="{}"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("provider_id", "user_id", name="uq_integration_user_link"),
        schema=SCHEMA,
    )

    op.create_table(
        "integration_test_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.integration_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.integration_endpoints.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("request_summary", sa.Text(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("tested_by", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "integration_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.integration_providers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("details", JSONB, nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )


def downgrade() -> None:
    for table in (
        "integration_audit_logs",
        "integration_test_logs",
        "integration_user_links",
        "integration_endpoints",
        "integration_credentials",
        "integration_providers",
    ):
        op.drop_table(table, schema=SCHEMA)
