"""Caché de permisos Odoo por usuario JAIOS."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "030_odoo_permission_cache"
down_revision = "029_m365_repo_size_bigint"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "odoo_user_permission_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("jaios_user_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("odoo_user_id", sa.Integer(), nullable=False),
        sa.Column("groups", JSONB, nullable=False, server_default="[]"),
        sa.Column("model_access", JSONB, nullable=False, server_default="{}"),
        sa.Column("module_access", JSONB, nullable=False, server_default="{}"),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "jaios_user_id", name="uq_odoo_permission_cache_user"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_odoo_permission_cache_tenant",
        "odoo_user_permission_cache",
        ["tenant_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("odoo_user_permission_cache", schema=SCHEMA)
