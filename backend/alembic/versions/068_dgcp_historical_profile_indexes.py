"""068 — índices perfil histórico 360° (award_date, rpe, institution_code)."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

revision: str = "068_dgcp_hist_profile_idx"
down_revision: Union[str, None] = "067_reconcile_dgcp_bid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def _index_exists(table: str, index_name: str) -> bool:
    insp = inspect(op.get_bind())
    return any(i["name"] == index_name for i in insp.get_indexes(table, schema=SCHEMA))


def upgrade() -> None:
    if not inspect(op.get_bind()).has_table("dgcp_historical_awards", schema=SCHEMA):
        return
    stmts = [
        (
            "ix_dgcp_hist_awards_award_date",
            f"CREATE INDEX IF NOT EXISTS ix_dgcp_hist_awards_award_date "
            f"ON {SCHEMA}.dgcp_historical_awards (award_date DESC NULLS LAST)",
        ),
        (
            "ix_dgcp_hist_awards_supplier_rpe",
            f"CREATE INDEX IF NOT EXISTS ix_dgcp_hist_awards_supplier_rpe "
            f"ON {SCHEMA}.dgcp_historical_awards (tenant_id, supplier_rpe)",
        ),
        (
            "ix_dgcp_hist_awards_inst_code",
            f"CREATE INDEX IF NOT EXISTS ix_dgcp_hist_awards_inst_code "
            f"ON {SCHEMA}.dgcp_historical_awards (tenant_id, buyer_institution_code)",
        ),
        (
            "ix_dgcp_hist_awards_tenant_date",
            f"CREATE INDEX IF NOT EXISTS ix_dgcp_hist_awards_tenant_date "
            f"ON {SCHEMA}.dgcp_historical_awards (tenant_id, award_date DESC NULLS LAST)",
        ),
    ]
    bind = op.get_bind()
    for name, sql in stmts:
        if not _index_exists("dgcp_historical_awards", name):
            bind.execute(text(sql))


def downgrade() -> None:
    bind = op.get_bind()
    for name in (
        "ix_dgcp_hist_awards_tenant_date",
        "ix_dgcp_hist_awards_inst_code",
        "ix_dgcp_hist_awards_supplier_rpe",
        "ix_dgcp_hist_awards_award_date",
    ):
        bind.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.{name}"))
