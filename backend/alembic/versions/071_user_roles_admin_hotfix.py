"""071 — multirol en memberships + credentials_version para invalidar JWT."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

revision: str = "071_user_roles_admin_hotfix"
down_revision: Union[str, None] = "070_dgcp_preparation_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    cols = {c["name"] for c in insp.get_columns("tenant_memberships", schema=SCHEMA)}
    if "roles" not in cols:
        bind.execute(
            text(
                f"ALTER TABLE {SCHEMA}.tenant_memberships "
                f"ADD COLUMN roles JSONB NOT NULL DEFAULT '[]'::jsonb"
            )
        )

    # Backfill: roles = [role] when empty
    bind.execute(
        text(
            f"""
            UPDATE {SCHEMA}.tenant_memberships
            SET roles = jsonb_build_array(COALESCE(NULLIF(role, ''), 'usuario'))
            WHERE roles IS NULL
               OR roles = '[]'::jsonb
               OR jsonb_typeof(roles) <> 'array'
            """
        )
    )

    user_cols = {c["name"] for c in insp.get_columns("users", schema=SCHEMA)}
    if "credentials_version" not in user_cols:
        bind.execute(
            text(
                f"ALTER TABLE {SCHEMA}.users "
                f"ADD COLUMN credentials_version INTEGER NOT NULL DEFAULT 0"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("tenant_memberships", schema=SCHEMA)}
    if "roles" in cols:
        bind.execute(text(f"ALTER TABLE {SCHEMA}.tenant_memberships DROP COLUMN roles"))
    user_cols = {c["name"] for c in insp.get_columns("users", schema=SCHEMA)}
    if "credentials_version" in user_cols:
        bind.execute(text(f"ALTER TABLE {SCHEMA}.users DROP COLUMN credentials_version"))
