"""Price Intelligence v2 — raw row, multi-price, quote drafts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.add_column("price_list_files", sa.Column("audit_json", postgresql.JSONB(), nullable=False, server_default="[]"), schema=SCHEMA)
    op.add_column("price_list_files", sa.Column("file_date_estimated", sa.Boolean(), nullable=False, server_default=sa.text("true")), schema=SCHEMA)

    op.add_column("price_list_products", sa.Column("raw_row_json", postgresql.JSONB(), nullable=False, server_default="{}"), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("raw_columns_json", postgresql.JSONB(), nullable=False, server_default="[]"), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("prices_original", postgresql.JSONB(), nullable=False, server_default="{}"), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("preferred_price", sa.Numeric(14, 2)), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("preferred_price_field", sa.String(64)), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("price_regular", sa.Numeric(14, 2)), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("price_rebate", sa.Numeric(14, 2)), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("price_discount", sa.Numeric(14, 2)), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("stock_text_original", sa.Text()), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("product_type", sa.String(32), server_default="general"), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("is_commercial", sa.Boolean(), nullable=False, server_default=sa.text("true")), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("search_blob", sa.Text()), schema=SCHEMA)
    op.add_column("price_list_products", sa.Column("source_file_date", sa.DateTime(timezone=True)), schema=SCHEMA)

    op.create_index("ix_price_products_product_type", "price_list_products", ["tenant_id", "product_type"], schema=SCHEMA)
    op.create_index("ix_price_products_commercial", "price_list_products", ["tenant_id", "is_commercial"], schema=SCHEMA)
    op.create_index("ix_price_products_preferred_price", "price_list_products", ["tenant_id", "preferred_price"], schema=SCHEMA)

    op.create_table(
        "price_quote_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL")),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.price_list_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_name", sa.String(255)),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("description", sa.Text()),
        sa.Column("cost_price", sa.Numeric(14, 2)),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("supplier", sa.String(255)),
        sa.Column("margin_percent", sa.Numeric(6, 2)),
        sa.Column("sale_price_suggested", sa.Numeric(14, 2)),
        sa.Column("source_filename", sa.String(512)),
        sa.Column("source_sheet", sa.String(128)),
        sa.Column("source_row", sa.Integer()),
        sa.Column("source_file_date", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("odoo_product_id", sa.Integer()),
        sa.Column("odoo_match_status", sa.String(32)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_price_quote_drafts_tenant", "price_quote_drafts", ["tenant_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_price_quote_drafts_tenant", table_name="price_quote_drafts", schema=SCHEMA)
    op.drop_table("price_quote_drafts", schema=SCHEMA)
    op.drop_index("ix_price_products_preferred_price", table_name="price_list_products", schema=SCHEMA)
    op.drop_index("ix_price_products_commercial", table_name="price_list_products", schema=SCHEMA)
    op.drop_index("ix_price_products_product_type", table_name="price_list_products", schema=SCHEMA)
    for col in (
        "source_file_date", "search_blob", "is_commercial", "product_type",
        "stock_text_original", "price_discount", "price_rebate", "price_regular",
        "preferred_price_field", "preferred_price", "prices_original",
        "raw_columns_json", "raw_row_json",
    ):
        op.drop_column("price_list_products", col, schema=SCHEMA)
    op.drop_column("price_list_files", "file_date_estimated", schema=SCHEMA)
    op.drop_column("price_list_files", "audit_json", schema=SCHEMA)
