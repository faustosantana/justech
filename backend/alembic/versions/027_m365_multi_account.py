"""M365 multi-cuenta y estado de token."""

from alembic import op
import sqlalchemy as sa

revision = "027_m365_multi_account"
down_revision = "026_m365_imap_accounts"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.add_column(
        "m365_user_accounts",
        sa.Column("last_graph_error", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "m365_user_accounts",
        sa.Column("token_status", sa.String(16), server_default="unknown", nullable=False),
        schema=SCHEMA,
    )
    op.drop_constraint("uq_m365_user_accounts_tenant_user", "m365_user_accounts", schema=SCHEMA, type_="unique")
    op.create_unique_constraint(
        "uq_m365_user_accounts_tenant_email",
        "m365_user_accounts",
        ["tenant_id", "email"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint("uq_m365_user_accounts_tenant_email", "m365_user_accounts", schema=SCHEMA, type_="unique")
    op.create_unique_constraint(
        "uq_m365_user_accounts_tenant_user",
        "m365_user_accounts",
        ["tenant_id", "jaios_user_id"],
        schema=SCHEMA,
    )
    op.drop_column("m365_user_accounts", "token_status", schema=SCHEMA)
    op.drop_column("m365_user_accounts", "last_graph_error", schema=SCHEMA)
