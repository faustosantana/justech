"""Directorio inteligente de proveedores — categorías, interacciones y extensiones."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "038_supplier_directory"
down_revision = "037_membership_allowed_modules"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    # --- Extender business_companies ---
    op.add_column("business_companies", sa.Column("legal_name", sa.String(255)), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("whatsapp", sa.String(64)), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("address", sa.Text()), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("city", sa.String(128)), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("province", sa.String(128)), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("country", sa.String(64), server_default="República Dominicana"), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("payment_terms", sa.String(255)), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("delivery_time", sa.String(128)), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("currency", sa.String(8), server_default="DOP"), schema=SCHEMA)
    op.add_column(
        "business_companies",
        sa.Column("products_services", ARRAY(sa.String(255)), server_default="{}", nullable=False),
        schema=SCHEMA,
    )
    op.add_column(
        "business_companies",
        sa.Column("subcategories", ARRAY(sa.String(128)), server_default="{}", nullable=False),
        schema=SCHEMA,
    )
    op.add_column(
        "business_companies",
        sa.Column("tags", ARRAY(sa.String(64)), server_default="{}", nullable=False),
        schema=SCHEMA,
    )
    op.add_column("business_companies", sa.Column("internal_rating", sa.Numeric(3, 1)), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("last_purchase_at", sa.DateTime(timezone=True)), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("last_quote_at", sa.DateTime(timezone=True)), schema=SCHEMA)
    op.add_column("business_companies", sa.Column("primary_category_id", UUID(as_uuid=True)), schema=SCHEMA)

    op.create_index(
        "ix_business_companies_tenant_status",
        "business_companies",
        ["tenant_id", "status"],
        schema=SCHEMA,
    )

    # --- Categorías de proveedores ---
    op.create_table(
        "supplier_categories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("synonyms", ARRAY(sa.String(128)), server_default="{}", nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.supplier_categories.id", ondelete="SET NULL")),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_supplier_categories_tenant_slug", "supplier_categories", ["tenant_id", "slug"], unique=True, schema=SCHEMA)

    op.create_foreign_key(
        "fk_business_companies_primary_category",
        "business_companies",
        "supplier_categories",
        ["primary_category_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )

    op.create_table(
        "supplier_category_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.business_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.supplier_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_supplier_category_links_supplier",
        "supplier_category_links",
        ["supplier_id", "category_id"],
        unique=True,
        schema=SCHEMA,
    )

    op.create_table(
        "supplier_contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.business_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(128)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(64)),
        sa.Column("whatsapp", sa.String(64)),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "supplier_interactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.business_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL")),
        sa.Column("interaction_type", sa.String(32), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(512)),
        sa.Column("body", sa.Text()),
        sa.Column("metadata_json", JSONB, server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_supplier_interactions_supplier", "supplier_interactions", ["supplier_id", "created_at"], schema=SCHEMA)

    op.create_table(
        "supplier_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.business_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(64)),
        sa.Column("file_path", sa.Text()),
        sa.Column("graph_file_id", sa.String(128)),
        sa.Column("metadata_json", JSONB, server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "supplier_ratings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.business_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL")),
        sa.Column("rating", sa.Numeric(3, 1), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "supplier_price_list_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.business_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_list_file_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.price_list_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("detected_brands", ARRAY(sa.String(128)), server_default="{}", nullable=False),
        sa.Column("detected_categories", ARRAY(sa.String(128)), server_default="{}", nullable=False),
        sa.Column("product_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_supplier_price_list_links_unique",
        "supplier_price_list_links",
        ["supplier_id", "price_list_file_id"],
        unique=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_supplier_price_list_links_unique", table_name="supplier_price_list_links", schema=SCHEMA)
    op.drop_table("supplier_price_list_links", schema=SCHEMA)
    op.drop_table("supplier_ratings", schema=SCHEMA)
    op.drop_table("supplier_documents", schema=SCHEMA)
    op.drop_index("ix_supplier_interactions_supplier", table_name="supplier_interactions", schema=SCHEMA)
    op.drop_table("supplier_interactions", schema=SCHEMA)
    op.drop_table("supplier_contacts", schema=SCHEMA)
    op.drop_index("ix_supplier_category_links_supplier", table_name="supplier_category_links", schema=SCHEMA)
    op.drop_table("supplier_category_links", schema=SCHEMA)
    op.drop_constraint("fk_business_companies_primary_category", "business_companies", schema=SCHEMA, type_="foreignkey")
    op.drop_index("ix_supplier_categories_tenant_slug", table_name="supplier_categories", schema=SCHEMA)
    op.drop_table("supplier_categories", schema=SCHEMA)
    op.drop_index("ix_business_companies_tenant_status", table_name="business_companies", schema=SCHEMA)
    for col in (
        "legal_name", "whatsapp", "address", "city", "province", "country",
        "payment_terms", "delivery_time", "currency", "products_services",
        "subcategories", "tags", "internal_rating", "last_purchase_at",
        "last_quote_at", "primary_category_id",
    ):
        op.drop_column("business_companies", col, schema=SCHEMA)
