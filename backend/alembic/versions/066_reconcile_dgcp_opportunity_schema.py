"""Reconcile missing DGCP opportunity columns (041/049) — idempotent DEV hotfix.

Cause: the local alembic chain replaced real 039–048 (incl. 041 jaios_intelligence)
and turned 049 into a no-op stub while alembic_version advanced past them. The running
API ORM expects needs_review + jaios_intelligence → sync/list 500 without these columns.

Creates only missing columns. Never drops data. Safe to re-run.

Note on revision lineage:
- DEV runtime previously stamped this as child of 063_reconcile_m365_cols (container-only
  reconcile branch). This repo's linear lottery head is 065_lottery_ai_usage_lottery_key;
  down_revision follows the repo chain. Columns are IF NOT EXISTS — already applied in DEV.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import JSONB

# Keep ≤32 chars: jaios.alembic_version.version_num is VARCHAR(32).
revision: str = "066_reconcile_dgcp_opp"
down_revision: Union[str, None] = "065_lottery_ai_usage_lottery_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def _column_exists(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table, schema=SCHEMA)}
    return column in cols


def upgrade() -> None:
    if not _column_exists("dgcp_opportunities", "needs_review"):
        op.add_column(
            "dgcp_opportunities",
            sa.Column(
                "needs_review",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            schema=SCHEMA,
        )
        # Legacy funnel remaps from original 049 (no-op when table empty / already migrated).
        op.execute(
            text(
                f"""
                UPDATE {SCHEMA}.dgcp_opportunities
                SET status = 'detected', needs_review = true
                WHERE status = 'to_review'
                """
            )
        )
        op.execute(
            text(
                f"""
                UPDATE {SCHEMA}.dgcp_opportunities
                SET status = 'preparing'
                WHERE status = 'to_bid'
                """
            )
        )
        op.execute(
            text(
                f"""
                UPDATE {SCHEMA}.dgcp_opportunities
                SET status = 'awarded'
                WHERE status = 'won'
                """
            )
        )

    if not _column_exists("dgcp_opportunities", "jaios_intelligence"):
        op.add_column(
            "dgcp_opportunities",
            sa.Column(
                "jaios_intelligence",
                JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            schema=SCHEMA,
        )

    # Post-condition validation (fail migration if still missing).
    bind = op.get_bind()
    for col in ("needs_review", "jaios_intelligence"):
        exists = bind.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = 'dgcp_opportunities'
                  AND column_name = :col
                """
            ),
            {"schema": SCHEMA, "col": col},
        ).scalar()
        if not exists:
            raise RuntimeError(
                f"066_reconcile_dgcp_opportunity_schema: column {col} still missing after upgrade"
            )


def downgrade() -> None:
    """No-op: columns may exist from real 041/049 path. Restore DEV dump to roll back."""
    op.execute(text("SELECT 1 -- 066_reconcile_dgcp_opportunity_schema: intentional no-op downgrade"))
