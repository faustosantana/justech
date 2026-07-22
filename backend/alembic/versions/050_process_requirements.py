"""Fase 1 — process_requirements (fuente única de verdad para requisitos del proceso)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "050_process_requirements"
down_revision = "049_dgcp_funnel_needs_review"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "process_requirements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.dgcp_opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requirement_key", sa.String(128), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("mandatory", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("priority", sa.String(16), server_default="normal", nullable=False),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("source", sa.String(32), server_default="manual", nullable=False),
        sa.Column("source_evidence", JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "assignee_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("document_ref_type", sa.String(32), nullable=True),
        sa.Column("document_ref_id", UUID(as_uuid=True), nullable=True),
        sa.Column("template_ref", JSONB(), nullable=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("autofill_allowed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("autofill_last_result", JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("history", JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("legacy_checklist_item_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pr_tenant_opportunity",
        "process_requirements",
        ["tenant_id", "opportunity_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "uq_pr_tenant_opp_key",
        "process_requirements",
        ["tenant_id", "opportunity_id", "requirement_key"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pr_assignee_status",
        "process_requirements",
        ["assignee_user_id", "status"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pr_due_date",
        "process_requirements",
        ["due_date"],
        schema=SCHEMA,
        postgresql_where=sa.text("due_date IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_pr_due_date", table_name="process_requirements", schema=SCHEMA)
    op.drop_index("ix_pr_assignee_status", table_name="process_requirements", schema=SCHEMA)
    op.drop_index("uq_pr_tenant_opp_key", table_name="process_requirements", schema=SCHEMA)
    op.drop_index("ix_pr_tenant_opportunity", table_name="process_requirements", schema=SCHEMA)
    op.drop_table("process_requirements", schema=SCHEMA)
