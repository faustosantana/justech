"""037 stub — membership allowed modules (missing file on prod/platform; DB already past this)."""

from alembic import op
import sqlalchemy as sa

revision = "037_membership_allowed_modules"
down_revision = "036_document_hub_pending"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op stub to repair alembic graph; production already at 050+.
    pass


def downgrade() -> None:
    pass
