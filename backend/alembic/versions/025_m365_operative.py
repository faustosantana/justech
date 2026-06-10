"""025 — Microsoft 365 Operativo (email intelligence)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "025_m365_operative"
down_revision = "024_assistant_conversations"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names(schema=SCHEMA)

    if "m365_monitored_mailboxes" not in tables:
        op.create_table(
            "m365_monitored_mailboxes",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("address", sa.String(255), nullable=False),
            sa.Column("display_name", sa.String(255)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("auto_process", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_m365_monitored_mailboxes_tenant_id", "m365_monitored_mailboxes", ["tenant_id"], schema=SCHEMA)
        op.create_index("ix_m365_monitored_mailboxes_address", "m365_monitored_mailboxes", ["address"], schema=SCHEMA)

    if "m365_processed_emails" not in tables:
        op.create_table(
            "m365_processed_emails",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("mailbox", sa.String(255), nullable=False),
            sa.Column("external_message_id", sa.String(255), nullable=False),
            sa.Column("subject", sa.Text(), nullable=False),
            sa.Column("sender_email", sa.String(255), nullable=False),
            sa.Column("sender_name", sa.String(255)),
            sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("body_preview", sa.Text()),
            sa.Column("body_text", sa.Text()),
            sa.Column("classification", sa.String(64), nullable=False),
            sa.Column("classification_confidence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("extracted_data", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column("relations", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column("suggested_actions", postgresql.JSONB(), nullable=False, server_default="[]"),
            sa.Column("attachments", postgresql.JSONB(), nullable=False, server_default="[]"),
            sa.Column("sharepoint_path", sa.Text()),
            sa.Column("processing_status", sa.String(32), nullable=False, server_default="processed"),
            sa.Column("graph_connected", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("demo_source", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("hermes_indexed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL")),
            sa.Column("related_dgcp_process_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.dgcp_opportunities.id", ondelete="SET NULL")),
            sa.Column("related_task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tasks.id", ondelete="SET NULL")),
            sa.Column("amount", sa.Numeric(18, 2)),
            sa.Column("currency", sa.String(8)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_m365_processed_emails_tenant_id", "m365_processed_emails", ["tenant_id"], schema=SCHEMA)
        op.create_index("ix_m365_processed_emails_mailbox", "m365_processed_emails", ["mailbox"], schema=SCHEMA)
        op.create_index("ix_m365_processed_emails_classification", "m365_processed_emails", ["classification"], schema=SCHEMA)
        op.create_index("ix_m365_processed_emails_received_at", "m365_processed_emails", ["received_at"], schema=SCHEMA)
        op.create_index(
            "uq_m365_processed_emails_tenant_external",
            "m365_processed_emails",
            ["tenant_id", "external_message_id"],
            unique=True,
            schema=SCHEMA,
        )

    if "m365_email_action_logs" not in tables:
        op.create_table(
            "m365_email_action_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("email_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.m365_processed_emails.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL")),
            sa.Column("action_key", sa.String(64), nullable=False),
            sa.Column("action_label", sa.String(255), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
            sa.Column("result", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_m365_email_action_logs_email_id", "m365_email_action_logs", ["email_id"], schema=SCHEMA)

    if "m365_automation_events" not in tables:
        op.create_table(
            "m365_automation_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("source", sa.String(64), nullable=False),
            sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("n8n_workflow_id", sa.String(128)),
            sa.Column("n8n_triggered", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index("ix_m365_automation_events_tenant_id", "m365_automation_events", ["tenant_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("m365_automation_events", schema=SCHEMA)
    op.drop_table("m365_email_action_logs", schema=SCHEMA)
    op.drop_table("m365_processed_emails", schema=SCHEMA)
    op.drop_table("m365_monitored_mailboxes", schema=SCHEMA)
