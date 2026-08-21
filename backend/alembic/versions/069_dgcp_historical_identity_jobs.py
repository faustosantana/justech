"""069 — identity merge audit + job completion markers (histórico 360°)."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

revision: str = "069_dgcp_hist_identity_jobs"
down_revision: Union[str, None] = "068_dgcp_hist_profile_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if insp.has_table("dgcp_historical_index_jobs", schema=SCHEMA):
        cols = {c["name"] for c in insp.get_columns("dgcp_historical_index_jobs", schema=SCHEMA)}
        alters = []
        if "rows_processed" not in cols:
            alters.append("ADD COLUMN rows_processed INTEGER")
        if "duration_ms" not in cols:
            alters.append("ADD COLUMN duration_ms INTEGER")
        if "result_hash" not in cols:
            alters.append("ADD COLUMN result_hash VARCHAR(64)")
        if "source_status" not in cols:
            alters.append("ADD COLUMN source_status VARCHAR(32)")
        if "result_meta" not in cols:
            alters.append("ADD COLUMN result_meta JSONB NOT NULL DEFAULT '{}'::jsonb")
        for fragment in alters:
            bind.execute(text(f"ALTER TABLE {SCHEMA}.dgcp_historical_index_jobs {fragment}"))

    if not insp.has_table("dgcp_historical_identity_actions", schema=SCHEMA):
        bind.execute(
            text(
                f"""
                CREATE TABLE {SCHEMA}.dgcp_historical_identity_actions (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL REFERENCES {SCHEMA}.tenants(id) ON DELETE CASCADE,
                    party_type VARCHAR(16) NOT NULL,
                    identity_a VARCHAR(256) NOT NULL,
                    identity_b VARCHAR(256) NOT NULL,
                    canonical_key VARCHAR(256),
                    action VARCHAR(32) NOT NULL,
                    criterion VARCHAR(64),
                    confidence VARCHAR(32),
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    actor_user_id UUID,
                    note TEXT,
                    meta JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        bind.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_dgcp_hist_identity_actions_tenant "
                f"ON {SCHEMA}.dgcp_historical_identity_actions (tenant_id)"
            )
        )
        bind.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_dgcp_hist_identity_actions_keys "
                f"ON {SCHEMA}.dgcp_historical_identity_actions (tenant_id, party_type, status)"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.dgcp_historical_identity_actions"))
