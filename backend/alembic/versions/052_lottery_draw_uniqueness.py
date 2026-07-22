"""028 — Endurecer unicidad de sorteos/números (NULL-safe).

Revision ID: 052_lottery_draw_uniqueness
Revises: 051_lottery_module

PostgreSQL trata NULL como distinto en UNIQUE constraints, por lo que
uq_lottery_draws_natural_key no impedía duplicados cuando draw_time o
source_reference son NULL. La fuente SQLite tiene ~80 981 draw_time NULL
pero 0 source_reference NULL; aun así se endurece para ambos casos.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "052_lottery_draw_uniqueness"
down_revision: Union[str, None] = "051_lottery_module"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1) Quitar unique natural inseguro con NULLs
    uqs = {uq["name"] for uq in insp.get_unique_constraints("lottery_draws", schema=SCHEMA)}
    if "uq_lottery_draws_natural_key" in uqs:
        op.drop_constraint("uq_lottery_draws_natural_key", "lottery_draws", schema=SCHEMA, type_="unique")

    indexes = {ix["name"] for ix in insp.get_indexes("lottery_draws", schema=SCHEMA)}

    # 2) Dedup primaria: (lottery_id, source_reference) cuando reference existe
    if "uq_lottery_draws_lottery_source_ref" not in indexes:
        op.execute(
            sa.text(
                f"""
                CREATE UNIQUE INDEX uq_lottery_draws_lottery_source_ref
                ON {SCHEMA}.lottery_draws (lottery_id, source_reference)
                WHERE source_reference IS NOT NULL
                """
            )
        )

    # 3) Fallback NULL-safe cuando falta source_reference
    if "uq_lottery_draws_natural_coalesce" not in indexes:
        op.execute(
            sa.text(
                f"""
                CREATE UNIQUE INDEX uq_lottery_draws_natural_coalesce
                ON {SCHEMA}.lottery_draws (
                    lottery_id,
                    draw_date,
                    COALESCE(draw_time, TIME '00:00:00'),
                    game_name,
                    COALESCE(source_reference, '')
                )
                """
            )
        )

    # 4) Números idempotentes por posición + tipo
    num_indexes = {ix["name"] for ix in insp.get_indexes("lottery_draw_numbers", schema=SCHEMA)}
    if "uq_lottery_draw_numbers_draw_pos_type" not in num_indexes:
        op.execute(
            sa.text(
                f"""
                CREATE UNIQUE INDEX uq_lottery_draw_numbers_draw_pos_type
                ON {SCHEMA}.lottery_draw_numbers (draw_id, position, number_type)
                """
            )
        )

    # 5) Columnas operativas adicionales en import_runs (JSONB sigue siendo flexible)
    cols = {c["name"] for c in insp.get_columns("lottery_import_runs", schema=SCHEMA)}
    if "dry_run" not in cols:
        op.add_column(
            "lottery_import_runs",
            sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            schema=SCHEMA,
        )
    if "resume" not in cols:
        op.add_column(
            "lottery_import_runs",
            sa.Column("resume", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            schema=SCHEMA,
        )
    if "batch_size" not in cols:
        op.add_column(
            "lottery_import_runs",
            sa.Column("batch_size", sa.Integer(), nullable=False, server_default="1000"),
            schema=SCHEMA,
        )
    if "git_commit" not in cols:
        op.add_column(
            "lottery_import_runs",
            sa.Column("git_commit", sa.String(64), nullable=True),
            schema=SCHEMA,
        )
    if "app_version" not in cols:
        op.add_column(
            "lottery_import_runs",
            sa.Column("app_version", sa.String(64), nullable=True),
            schema=SCHEMA,
        )
    if "source_path" not in cols:
        op.add_column(
            "lottery_import_runs",
            sa.Column("source_path", sa.String(512), nullable=True),
            schema=SCHEMA,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("lottery_import_runs", schema=SCHEMA)}
    for col in ("source_path", "app_version", "git_commit", "batch_size", "resume", "dry_run"):
        if col in cols:
            op.drop_column("lottery_import_runs", col, schema=SCHEMA)

    indexes_num = {ix["name"] for ix in insp.get_indexes("lottery_draw_numbers", schema=SCHEMA)}
    if "uq_lottery_draw_numbers_draw_pos_type" in indexes_num:
        op.drop_index("uq_lottery_draw_numbers_draw_pos_type", table_name="lottery_draw_numbers", schema=SCHEMA)

    indexes = {ix["name"] for ix in insp.get_indexes("lottery_draws", schema=SCHEMA)}
    if "uq_lottery_draws_natural_coalesce" in indexes:
        op.drop_index("uq_lottery_draws_natural_coalesce", table_name="lottery_draws", schema=SCHEMA)
    if "uq_lottery_draws_lottery_source_ref" in indexes:
        op.drop_index("uq_lottery_draws_lottery_source_ref", table_name="lottery_draws", schema=SCHEMA)

    # Restaurar unique original (con la limitación conocida de NULLs)
    uqs = {uq["name"] for uq in insp.get_unique_constraints("lottery_draws", schema=SCHEMA)}
    if "uq_lottery_draws_natural_key" not in uqs:
        op.create_unique_constraint(
            "uq_lottery_draws_natural_key",
            "lottery_draws",
            ["lottery_id", "draw_date", "draw_time", "game_name", "source_reference"],
            schema=SCHEMA,
        )
