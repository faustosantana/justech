"""Work Operations Center — tasks, notifications, routing

Revision ID: 006
Revises: 005
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="pendiente"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="media"),
        sa.Column("category", sa.String(64), nullable=False, server_default="otro"),
        sa.Column("department", sa.String(64), nullable=False, server_default="operaciones"),
        sa.Column("source", sa.String(64), nullable=False, server_default="manual"),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "assigned_to_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "supervisor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        ),
        sa.Column("suggested_assignee_name", sa.String(128)),
        sa.Column("due_date", sa.Date()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("company_id", sa.Integer()),
        sa.Column("customer_name", sa.String(255)),
        sa.Column("customer_id", sa.String(64)),
        sa.Column("odoo_customer_id", sa.Integer()),
        sa.Column("odoo_invoice_id", sa.Integer()),
        sa.Column("odoo_quotation_id", sa.Integer()),
        sa.Column("odoo_opportunity_id", sa.Integer()),
        sa.Column("odoo_project_id", sa.Integer()),
        sa.Column("dgcp_process_id", postgresql.UUID(as_uuid=True)),
        sa.Column("support_ticket_id", sa.String(64)),
        sa.Column("related_email_id", sa.String(128)),
        sa.Column("related_document_id", sa.String(128)),
        sa.Column("amount", sa.Numeric(18, 2)),
        sa.Column("currency", sa.String(8), server_default="DOP"),
        sa.Column("tags", postgresql.ARRAY(sa.String(64)), server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_tasks_status", "tasks", ["status"], schema=SCHEMA)
    op.create_index("ix_tasks_priority", "tasks", ["priority"], schema=SCHEMA)
    op.create_index("ix_tasks_category", "tasks", ["category"], schema=SCHEMA)
    op.create_index("ix_tasks_assigned_to_id", "tasks", ["assigned_to_id"], schema=SCHEMA)
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"], schema=SCHEMA)

    op.create_table(
        "task_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        ),
        sa.Column("user_name", sa.String(255)),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"], schema=SCHEMA)

    op.create_table(
        "task_checklists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.String(500), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default="false"),
        sa.Column(
            "completed_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        ),
        sa.Column("completed_by_name", sa.String(255)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index("ix_task_checklists_task_id", "task_checklists", ["task_id"], schema=SCHEMA)

    op.create_table(
        "task_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(64)),
        sa.Column("storage_path", sa.String(512)),
        sa.Column("related_document_id", sa.String(128)),
        sa.Column(
            "uploaded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index("ix_task_attachments_task_id", "task_attachments", ["task_id"], schema=SCHEMA)

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), server_default="info"),
        sa.Column("is_read", sa.Boolean(), server_default="false"),
        sa.Column(
            "related_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tasks.id", ondelete="SET NULL"),
        ),
        sa.Column("related_entity_type", sa.String(64)),
        sa.Column("related_entity_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        schema=SCHEMA,
    )
    op.create_index("ix_notifications_tenant_id", "notifications", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], schema=SCHEMA)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], schema=SCHEMA)

    op.create_table(
        "routing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("department", sa.String(64), nullable=False),
        sa.Column("default_priority", sa.String(16), server_default="media"),
        sa.Column("default_assignee_name", sa.String(128)),
        sa.Column(
            "default_assignee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        ),
        sa.Column("due_hours", sa.Integer()),
        sa.Column("notification_message", sa.Text()),
        sa.Column("checklist_template", postgresql.JSONB(), server_default="[]"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index("ix_routing_rules_tenant_id", "routing_rules", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_routing_rules_event_type", "routing_rules", ["event_type"], schema=SCHEMA)

    op.create_table(
        "task_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index("ix_task_audit_logs_tenant_id", "task_audit_logs", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_task_audit_logs_task_id", "task_audit_logs", ["task_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("task_audit_logs", schema=SCHEMA)
    op.drop_table("routing_rules", schema=SCHEMA)
    op.drop_table("notifications", schema=SCHEMA)
    op.drop_table("task_attachments", schema=SCHEMA)
    op.drop_table("task_checklists", schema=SCHEMA)
    op.drop_table("task_comments", schema=SCHEMA)
    op.drop_table("tasks", schema=SCHEMA)
