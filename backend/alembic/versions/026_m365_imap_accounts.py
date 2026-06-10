"""026 — M365 cuentas IMAP (cliente correo por usuario)."""

from alembic import op
import sqlalchemy as sa

revision = "026_m365_imap_accounts"
down_revision = "025_m365_operative"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("m365_user_accounts", schema=SCHEMA)}
    if "connection_mode" not in cols:
        op.add_column(
            "m365_user_accounts",
            sa.Column("connection_mode", sa.String(16), nullable=False, server_default="none"),
            schema=SCHEMA,
        )
    if "imap_host" not in cols:
        op.add_column(
            "m365_user_accounts",
            sa.Column("imap_host", sa.String(255), nullable=True),
            schema=SCHEMA,
        )
    if "imap_port" not in cols:
        op.add_column(
            "m365_user_accounts",
            sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
            schema=SCHEMA,
        )
    if "imap_password_encrypted" not in cols:
        op.add_column(
            "m365_user_accounts",
            sa.Column("imap_password_encrypted", sa.Text(), nullable=True),
            schema=SCHEMA,
        )


def downgrade() -> None:
    op.drop_column("m365_user_accounts", "imap_password_encrypted", schema=SCHEMA)
    op.drop_column("m365_user_accounts", "imap_port", schema=SCHEMA)
    op.drop_column("m365_user_accounts", "imap_host", schema=SCHEMA)
    op.drop_column("m365_user_accounts", "connection_mode", schema=SCHEMA)
