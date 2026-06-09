"""Price Intelligence v2.2 — clasificación estricta y borradores operativos."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.add_column(
        "price_list_products",
        sa.Column("excluded_from_laptop", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        schema=SCHEMA,
    )
    op.add_column(
        "price_list_products",
        sa.Column("is_cotizable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema=SCHEMA,
    )
    op.add_column(
        "price_list_products",
        sa.Column("price_review_status", sa.String(32), server_default="ok", nullable=False),
        schema=SCHEMA,
    )
    op.add_column(
        "price_list_products",
        sa.Column("classification_label", sa.String(64), server_default="producto general", nullable=False),
        schema=SCHEMA,
    )
    op.add_column(
        "price_list_products",
        sa.Column("stock_source_column", sa.String(64), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_price_products_laptop_search",
        "price_list_products",
        ["tenant_id", "product_type", "excluded_from_laptop"],
        schema=SCHEMA,
    )

    op.add_column(
        "price_quote_drafts",
        sa.Column("task_id", UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_price_quote_drafts_task_id",
        "price_quote_drafts",
        "tasks",
        ["task_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_price_quote_drafts_task_id", "price_quote_drafts", schema=SCHEMA, type_="foreignkey")
    op.drop_column("price_quote_drafts", "task_id", schema=SCHEMA)
    op.drop_index("ix_price_products_laptop_search", table_name="price_list_products", schema=SCHEMA)
    for col in (
        "stock_source_column",
        "classification_label",
        "price_review_status",
        "is_cotizable",
        "excluded_from_laptop",
    ):
        op.drop_column("price_list_products", col, schema=SCHEMA)
