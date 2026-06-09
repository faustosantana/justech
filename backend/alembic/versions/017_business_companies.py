"""Empresas y proveedores — directorio comercial."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "business_companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("company_type", sa.String(32), nullable=False),
        sa.Column("tax_id", sa.String(32), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("primary_contact", sa.String(255), nullable=True),
        sa.Column("website", sa.String(512), nullable=True),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("brands", ARRAY(sa.String(128)), nullable=False, server_default="{}"),
        sa.Column("commercial_terms", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="activo"),
        sa.Column("odoo_partner_id", sa.Integer(), nullable=True),
        sa.Column("price_supplier_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_business_companies_tenant_name", "business_companies", ["tenant_id", "name"], schema=SCHEMA)
    op.create_index("ix_business_companies_tenant_type", "business_companies", ["tenant_id", "company_type"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_business_companies_tenant_type", table_name="business_companies", schema=SCHEMA)
    op.drop_index("ix_business_companies_tenant_name", table_name="business_companies", schema=SCHEMA)
    op.drop_table("business_companies", schema=SCHEMA)
