"""Price Intelligence Engine — listas de precios estructuradas

Revision ID: 013
Revises: 012
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "price_list_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier", sa.String(255)),
        sa.Column("manufacturer", sa.String(128)),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("file_modified_at", sa.DateTime(timezone=True)),
        sa.Column("indexed_at", sa.DateTime(timezone=True)),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="indexed"),
        sa.Column("errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_price_list_files_tenant_path",
        "price_list_files",
        ["tenant_id", "relative_path"],
        schema=SCHEMA,
    )

    op.create_table(
        "price_list_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.price_list_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("supplier", sa.String(255)),
        sa.Column("manufacturer", sa.String(128)),
        sa.Column("sku", sa.String(128)),
        sa.Column("mpn", sa.String(128)),
        sa.Column("model", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(128)),
        sa.Column("brand", sa.String(128)),
        sa.Column("processor", sa.String(128)),
        sa.Column("ram_gb", sa.Integer()),
        sa.Column("storage_gb", sa.Integer()),
        sa.Column("storage_type", sa.String(32)),
        sa.Column("display", sa.String(64)),
        sa.Column("operating_system", sa.String(128)),
        sa.Column("price", sa.Numeric(14, 2)),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("stock", sa.Integer()),
        sa.Column("in_transit", sa.Integer()),
        sa.Column("warranty", sa.String(128)),
        sa.Column("source_filename", sa.String(512), nullable=False),
        sa.Column("source_sheet", sa.String(128)),
        sa.Column("source_row", sa.Integer()),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_price_products_tenant_current", "price_list_products", ["tenant_id", "is_current"], schema=SCHEMA)
    op.create_index("ix_price_products_ram_storage", "price_list_products", ["tenant_id", "ram_gb", "storage_gb"], schema=SCHEMA)
    op.create_index("ix_price_products_brand_price", "price_list_products", ["tenant_id", "brand", "price"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_price_products_brand_price", table_name="price_list_products", schema=SCHEMA)
    op.drop_index("ix_price_products_ram_storage", table_name="price_list_products", schema=SCHEMA)
    op.drop_index("ix_price_products_tenant_current", table_name="price_list_products", schema=SCHEMA)
    op.drop_table("price_list_products", schema=SCHEMA)
    op.drop_index("ix_price_list_files_tenant_path", table_name="price_list_files", schema=SCHEMA)
    op.drop_table("price_list_files", schema=SCHEMA)
