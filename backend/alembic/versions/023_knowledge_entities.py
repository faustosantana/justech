"""Fase 4 — knowledge entities for entity resolution."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "023_knowledge_entities"
down_revision = "022_real_expediente"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "knowledge_entities" not in insp.get_table_names(schema=SCHEMA):
        op.create_table(
            "knowledge_entities",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("entity_type", sa.String(32), nullable=False),
            sa.Column("canonical_name", sa.String(255), nullable=False),
            sa.Column("aliases", postgresql.ARRAY(sa.String(255)), nullable=False, server_default="{}"),
            sa.Column("source", sa.String(32), nullable=False, server_default="seed"),
            sa.Column("external_id", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
    op.create_index(
        "ix_knowledge_entities_tenant_type",
        "knowledge_entities",
        ["tenant_id", "entity_type"],
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_entities_tenant_type", table_name="knowledge_entities", schema=SCHEMA)
    op.drop_table("knowledge_entities", schema=SCHEMA)
