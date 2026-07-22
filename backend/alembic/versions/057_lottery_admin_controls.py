"""057 — Lottery 2.0 admin controls (visibility / search / AI / sync).

Revision ID: 057_lottery_admin_controls
Revises: 056_lottery_scheduler_operations
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "057_lottery_admin_controls"
down_revision: Union[str, None] = "056_lottery_scheduler_operations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    cols = [
        ("is_visible", sa.Boolean(), False, True),
        ("is_visible_dashboard", sa.Boolean(), False, True),
        ("is_visible_catalog", sa.Boolean(), False, True),
        ("is_searchable", sa.Boolean(), False, True),
        ("is_ai_enabled", sa.Boolean(), False, True),
        ("is_comparable", sa.Boolean(), False, True),
        ("is_sync_enabled", sa.Boolean(), False, False),
        ("is_auto_write_enabled", sa.Boolean(), False, False),
        ("is_featured", sa.Boolean(), False, False),
        ("display_order", sa.Integer(), False, 1000),
        ("commercial_name", sa.String(255), True, None),
        ("short_name", sa.String(128), True, None),
        ("logo_url", sa.Text(), True, None),
        ("icon_key", sa.String(64), True, None),
        ("currency", sa.String(16), True, None),
        ("data_source", sa.String(128), True, None),
        ("adapter_key", sa.String(128), True, None),
        ("external_id", sa.String(128), True, None),
        ("draw_schedule_cron", sa.String(128), True, None),
        ("draw_days", sa.String(64), True, None),
        ("draw_times", sa.String(255), True, None),
        ("sync_interval_minutes", sa.Integer(), True, None),
        ("sync_post_draw_delay_minutes", sa.Integer(), True, None),
        ("sync_max_retries", sa.Integer(), True, None),
        ("sync_active_hours", sa.String(64), True, None),
        ("last_sync_at", sa.DateTime(timezone=True), True, None),
        ("last_result_at", sa.DateTime(timezone=True), True, None),
        ("next_draw_estimated_at", sa.DateTime(timezone=True), True, None),
        ("health_status", sa.String(32), False, "unknown"),
        ("last_error", sa.Text(), True, None),
        ("numbers_count", sa.Integer(), False, 0),
        ("admin_notes", sa.Text(), True, None),
    ]

    for name, coltype, nullable, default in cols:
        kwargs: dict = {"nullable": nullable}
        if default is not None and not nullable:
            if isinstance(default, bool):
                kwargs["server_default"] = sa.text("true" if default else "false")
            elif isinstance(default, str):
                kwargs["server_default"] = sa.text(f"'{default}'")
            else:
                kwargs["server_default"] = sa.text(str(int(default)))
        op.add_column("lottery_lotteries", sa.Column(name, coltype, **kwargs), schema=SCHEMA)

    # Seed defaults: aggregates hidden; active lotteries visible/searchable/AI; sync off
    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.lottery_lotteries SET
              is_visible = CASE WHEN is_aggregate THEN false ELSE active END,
              is_visible_dashboard = CASE WHEN is_aggregate THEN false ELSE active END,
              is_visible_catalog = CASE WHEN is_aggregate THEN false ELSE active END,
              is_searchable = CASE WHEN is_aggregate THEN false ELSE active END,
              is_ai_enabled = CASE WHEN is_aggregate THEN false ELSE active END,
              is_comparable = CASE WHEN is_aggregate THEN false ELSE active END,
              is_sync_enabled = false,
              is_auto_write_enabled = false,
              is_featured = false,
              display_order = source_id,
              commercial_name = name,
              short_name = split_part(name, ' ', 1),
              data_source = 'elboletoganador',
              adapter_key = 'elboletoganador.historial.v1',
              external_id = source_id::text,
              health_status = CASE WHEN active AND NOT is_aggregate THEN 'healthy' ELSE 'disabled' END,
              numbers_count = 0
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.lottery_lotteries l SET numbers_count = COALESCE((
              SELECT COUNT(*) FROM {SCHEMA}.lottery_draw_numbers n
              JOIN {SCHEMA}.lottery_draws d ON d.id = n.draw_id
              WHERE d.lottery_id = l.id
            ), 0)
            """
        )
    )

    op.create_index("ix_lottery_lotteries_is_visible", "lottery_lotteries", ["is_visible"], schema=SCHEMA)
    op.create_index("ix_lottery_lotteries_is_searchable", "lottery_lotteries", ["is_searchable"], schema=SCHEMA)
    op.create_index("ix_lottery_lotteries_is_ai_enabled", "lottery_lotteries", ["is_ai_enabled"], schema=SCHEMA)
    op.create_index("ix_lottery_lotteries_is_sync_enabled", "lottery_lotteries", ["is_sync_enabled"], schema=SCHEMA)
    op.create_index("ix_lottery_lotteries_display_order", "lottery_lotteries", ["display_order"], schema=SCHEMA)

    # Drop server defaults that were only for backfill (keep NOT NULL without forced default for bools we manage in app)
    for name in (
        "is_visible",
        "is_visible_dashboard",
        "is_visible_catalog",
        "is_searchable",
        "is_ai_enabled",
        "is_comparable",
        "is_sync_enabled",
        "is_auto_write_enabled",
        "is_featured",
        "display_order",
        "health_status",
        "numbers_count",
    ):
        op.alter_column("lottery_lotteries", name, server_default=None, schema=SCHEMA)


def downgrade() -> None:
    for ix in (
        "ix_lottery_lotteries_display_order",
        "ix_lottery_lotteries_is_sync_enabled",
        "ix_lottery_lotteries_is_ai_enabled",
        "ix_lottery_lotteries_is_searchable",
        "ix_lottery_lotteries_is_visible",
    ):
        op.drop_index(ix, table_name="lottery_lotteries", schema=SCHEMA)
    for name in (
        "admin_notes",
        "numbers_count",
        "last_error",
        "health_status",
        "next_draw_estimated_at",
        "last_result_at",
        "last_sync_at",
        "sync_active_hours",
        "sync_max_retries",
        "sync_post_draw_delay_minutes",
        "sync_interval_minutes",
        "draw_times",
        "draw_days",
        "draw_schedule_cron",
        "external_id",
        "adapter_key",
        "data_source",
        "currency",
        "icon_key",
        "logo_url",
        "short_name",
        "commercial_name",
        "display_order",
        "is_featured",
        "is_auto_write_enabled",
        "is_sync_enabled",
        "is_comparable",
        "is_ai_enabled",
        "is_searchable",
        "is_visible_catalog",
        "is_visible_dashboard",
        "is_visible",
    ):
        op.drop_column("lottery_lotteries", name, schema=SCHEMA)
