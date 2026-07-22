"""024 — Assistant 3.0 conversaciones persistentes."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "024_assistant_conversations"
down_revision = "023_knowledge_entities"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "assistant_conversations" not in insp.get_table_names(schema=SCHEMA):
        op.create_table(
            "assistant_conversations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
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
            sa.Column("title", sa.String(255)),
            sa.Column("module_context", sa.String(128)),
            sa.Column("company_context_id", sa.Integer()),
            sa.Column("entity_snapshot", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column("briefing_mode", sa.String(32), nullable=False, server_default="managerial"),
            sa.Column("last_message_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
    if "assistant_messages" not in insp.get_table_names(schema=SCHEMA):
        op.create_table(
            "assistant_messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "conversation_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.assistant_conversations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(16), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("query_type", sa.String(64)),
            sa.Column("sources", postgresql.JSONB(), nullable=False, server_default="[]"),
            sa.Column("structured_data", postgresql.JSONB()),
            sa.Column("resolved_question", sa.Text()),
            sa.Column("was_follow_up", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
    op.create_index(
        "ix_assistant_conversations_tenant_user",
        "assistant_conversations",
        ["tenant_id", "user_id"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_assistant_messages_conversation",
        "assistant_messages",
        ["conversation_id", "created_at"],
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_messages_conversation", table_name="assistant_messages", schema=SCHEMA)
    op.drop_index("ix_assistant_conversations_tenant_user", table_name="assistant_conversations", schema=SCHEMA)
    op.drop_table("assistant_messages", schema=SCHEMA)
    op.drop_table("assistant_conversations", schema=SCHEMA)
