"""Fase 7.3 — DGCP Expediente Intelligence & Proposal Automation

Revision ID: 012
Revises: 011
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "dgcp_process_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.dgcp_opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("knowledge_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.knowledge_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="reference"),
        sa.Column("doc_role", sa.String(64), nullable=False, server_default="general"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="media"),
        sa.Column("format", sa.String(16), nullable=False, server_default="other"),
        sa.Column("ingestion_status", sa.String(32), nullable=False, server_default="registered"),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dgcp_process_documents_opportunity",
        "dgcp_process_documents",
        ["tenant_id", "opportunity_id"],
        schema=SCHEMA,
    )

    op.add_column("dgcp_bid_packages", sa.Column("expediente_status", sa.String(64), nullable=False, server_default="sin_preparar"), schema=SCHEMA)
    op.add_column("dgcp_bid_packages", sa.Column("expediente_path", sa.Text(), nullable=True), schema=SCHEMA)
    op.add_column("dgcp_bid_packages", sa.Column("user_input", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), schema=SCHEMA)
    op.add_column("dgcp_bid_packages", sa.Column("alerts", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")), schema=SCHEMA)
    op.add_column("dgcp_bid_packages", sa.Column("generated_forms", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")), schema=SCHEMA)
    op.add_column("dgcp_bid_packages", sa.Column("requirement_evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")), schema=SCHEMA)
    op.add_column("dgcp_bid_packages", sa.Column("process_documents_summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")), schema=SCHEMA)
    op.add_column("dgcp_bid_packages", sa.Column("manifest", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), schema=SCHEMA)


def downgrade() -> None:
    op.drop_column("dgcp_bid_packages", "manifest", schema=SCHEMA)
    op.drop_column("dgcp_bid_packages", "process_documents_summary", schema=SCHEMA)
    op.drop_column("dgcp_bid_packages", "requirement_evidence", schema=SCHEMA)
    op.drop_column("dgcp_bid_packages", "generated_forms", schema=SCHEMA)
    op.drop_column("dgcp_bid_packages", "alerts", schema=SCHEMA)
    op.drop_column("dgcp_bid_packages", "user_input", schema=SCHEMA)
    op.drop_column("dgcp_bid_packages", "expediente_path", schema=SCHEMA)
    op.drop_column("dgcp_bid_packages", "expediente_status", schema=SCHEMA)
    op.drop_index("ix_dgcp_process_documents_opportunity", table_name="dgcp_process_documents", schema=SCHEMA)
    op.drop_table("dgcp_process_documents", schema=SCHEMA)
