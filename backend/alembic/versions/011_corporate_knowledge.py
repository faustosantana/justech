"""Fase 7.2 — Corporate Knowledge Repository + Knowledge Graph

Revision ID: 011
Revises: 010
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "knowledge_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_provider", sa.String(32), nullable=False, server_default="filesystem"),
        sa.Column("source_root", sa.String(512), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("folder_category", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("format", sa.String(16), nullable=False, server_default="other"),
        sa.Column("document_type", sa.String(64), nullable=False, server_default="general"),
        sa.Column("company_key", sa.String(64), nullable=True),
        sa.Column("supplier_name", sa.String(255), nullable=True),
        sa.Column("manufacturer_name", sa.String(255), nullable=True),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("source_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("intelligence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("vigency_status", sa.String(32), nullable=False, server_default="sin_fecha"),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("keywords", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_knowledge_assets_tenant_path",
        "knowledge_assets",
        ["tenant_id", "source_provider", "relative_path"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_index("ix_knowledge_assets_document_type", "knowledge_assets", ["tenant_id", "document_type"], schema=SCHEMA)
    op.create_index("ix_knowledge_assets_company", "knowledge_assets", ["tenant_id", "company_key"], schema=SCHEMA)

    op.create_table(
        "knowledge_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("company_key", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_knowledge_entities_tenant_slug",
        "knowledge_entities",
        ["tenant_id", "entity_type", "slug"],
        unique=True,
        schema=SCHEMA,
    )

    op.create_table(
        "knowledge_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(64), nullable=False),
        sa.Column("knowledge_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.knowledge_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "knowledge_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("knowledge_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.knowledge_assets.id", ondelete="CASCADE"), nullable=True),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "knowledge_sync_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_provider", sa.String(32), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assets_synced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assets_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assets_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_knowledge_sync_state_tenant_provider",
        "knowledge_sync_state",
        ["tenant_id", "source_provider"],
        unique=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("uq_knowledge_sync_state_tenant_provider", table_name="knowledge_sync_state", schema=SCHEMA)
    op.drop_table("knowledge_sync_state", schema=SCHEMA)
    op.drop_table("knowledge_alerts", schema=SCHEMA)
    op.drop_table("knowledge_relationships", schema=SCHEMA)
    op.drop_index("uq_knowledge_entities_tenant_slug", table_name="knowledge_entities", schema=SCHEMA)
    op.drop_table("knowledge_entities", schema=SCHEMA)
    op.drop_index("ix_knowledge_assets_company", table_name="knowledge_assets", schema=SCHEMA)
    op.drop_index("ix_knowledge_assets_document_type", table_name="knowledge_assets", schema=SCHEMA)
    op.drop_index("uq_knowledge_assets_tenant_path", table_name="knowledge_assets", schema=SCHEMA)
    op.drop_table("knowledge_assets", schema=SCHEMA)
