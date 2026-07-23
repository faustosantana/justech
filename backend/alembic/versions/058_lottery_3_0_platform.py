"""058 — Lottery 3.0 sync windows, multi-source, country/operator, AI usage.

Revision ID: 058_lottery_3_0_platform
Revises: 057_lottery_admin_controls
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "058_lottery_3_0_platform"
down_revision: Union[str, None] = "057_lottery_admin_controls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c["name"] for c in insp.get_columns("lottery_lotteries", schema=SCHEMA)}
    add_map = [
        ("country_code", sa.Column("country_code", sa.String(8), server_default="DO")),
        ("operator_key", sa.Column("operator_key", sa.String(64))),
        ("flag_emoji", sa.Column("flag_emoji", sa.String(16))),
        ("sync_priority", sa.Column("sync_priority", sa.Integer(), server_default="100", nullable=False)),
        ("sync_timeout_seconds", sa.Column("sync_timeout_seconds", sa.Integer())),
        ("sync_pre_window_minutes", sa.Column("sync_pre_window_minutes", sa.Integer())),
        ("sync_live_window_minutes", sa.Column("sync_live_window_minutes", sa.Integer())),
        ("sync_post_window_minutes", sa.Column("sync_post_window_minutes", sa.Integer())),
        ("sync_pre_interval_minutes", sa.Column("sync_pre_interval_minutes", sa.Integer())),
        ("sync_live_interval_minutes", sa.Column("sync_live_interval_minutes", sa.Integer())),
        ("sync_post_interval_minutes", sa.Column("sync_post_interval_minutes", sa.Integer())),
        ("sync_backoff_seconds", sa.Column("sync_backoff_seconds", sa.Integer())),
    ]
    for name, col in add_map:
        if name not in existing:
            op.add_column("lottery_lotteries", col, schema=SCHEMA)

    # Seed schedules for Stage B trio (Leidsa 5, Loteka 6, Nacional 4) — evenings DO
    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.lottery_lotteries
            SET draw_days = COALESCE(draw_days, 'daily'),
                draw_times = COALESCE(draw_times, '20:55'),
                sync_interval_minutes = COALESCE(sync_interval_minutes, 60),
                sync_pre_window_minutes = COALESCE(sync_pre_window_minutes, 15),
                sync_live_window_minutes = COALESCE(sync_live_window_minutes, 10),
                sync_post_window_minutes = COALESCE(COALESCE(sync_post_draw_delay_minutes, sync_post_window_minutes), 45),
                sync_pre_interval_minutes = COALESCE(sync_pre_interval_minutes, 5),
                sync_live_interval_minutes = COALESCE(sync_live_interval_minutes, 1),
                sync_post_interval_minutes = COALESCE(sync_post_interval_minutes, 1),
                sync_priority = CASE source_id WHEN 5 THEN 10 WHEN 6 THEN 20 WHEN 4 THEN 30 ELSE sync_priority END,
                country_code = COALESCE(country_code, 'DO'),
                flag_emoji = COALESCE(flag_emoji, '🇩🇴'),
                timezone = COALESCE(NULLIF(timezone, ''), 'America/Santo_Domingo')
            WHERE source_id IN (4, 5, 6);
            """
        )
    )

    # Recompute denormalized metadata from draws (fixes Quiniela Real 2099)
    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.lottery_lotteries l
            SET
              draw_count = s.cnt,
              first_draw_date = s.min_d,
              last_draw_date = s.max_d,
              updated_at = now()
            FROM (
              SELECT lottery_id, COUNT(*)::int AS cnt, MIN(draw_date) AS min_d, MAX(draw_date) AS max_d
              FROM {SCHEMA}.lottery_draws
              GROUP BY lottery_id
            ) s
            WHERE l.id = s.lottery_id
              AND (
                l.draw_count IS DISTINCT FROM s.cnt
                OR l.first_draw_date IS DISTINCT FROM s.min_d
                OR l.last_draw_date IS DISTINCT FROM s.max_d
              );
            """
        )
    )

    op.create_table(
        "lottery_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lottery_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.lottery_lotteries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_key", sa.String(128), nullable=False),
        sa.Column("adapter_key", sa.String(128), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="primary"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("health_status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("latency_ema_ms", sa.Integer()),
        sa.Column("last_error", sa.Text()),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column("circuit_state", sa.String(32), nullable=False, server_default="closed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("lottery_id", "source_key", name="uq_lottery_sources_lottery_key"),
        schema=SCHEMA,
    )
    op.create_index("ix_lottery_sources_lottery_role", "lottery_sources", ["lottery_id", "role"], schema=SCHEMA)

    op.create_table(
        "lottery_source_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sync_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.lottery_sync_runs.id", ondelete="CASCADE")),
        sa.Column("lottery_source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.lottery_sources.id", ondelete="SET NULL")),
        sa.Column("source_key", sa.String(128), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("error", sa.Text()),
        sa.Column("candidates", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "lottery_source_conflicts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lottery_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.lottery_lotteries.id", ondelete="CASCADE")),
        sa.Column("draw_date", sa.Date(), nullable=False),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("primary_value", sa.Text()),
        sa.Column("other_value", sa.Text()),
        sa.Column("other_source", sa.String(128)),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("evidence", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        schema=SCHEMA,
    )

    op.create_table(
        "lottery_ai_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("session_id", postgresql.UUID(as_uuid=True)),
        sa.Column("provider", sa.String(64)),
        sa.Column("model", sa.String(128)),
        sa.Column("prompt_tokens", sa.Integer()),
        sa.Column("completion_tokens", sa.Integer()),
        sa.Column("total_tokens", sa.Integer()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6)),
        sa.Column("tool_names", postgresql.JSONB()),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    # Seed primary sources for sync-enabled lotteries from adapter_key
    op.execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.lottery_sources (id, lottery_id, source_key, adapter_key, role, priority, enabled, health_status)
            SELECT gen_random_uuid(), id,
                   COALESCE(adapter_key, 'elboletoganador.historial.v1'),
                   COALESCE(adapter_key, 'elboletoganador.historial.v1'),
                   'primary', 10, true, 'unknown'
            FROM {SCHEMA}.lottery_lotteries
            WHERE is_sync_enabled = true
              AND NOT EXISTS (
                SELECT 1 FROM {SCHEMA}.lottery_sources s WHERE s.lottery_id = lottery_lotteries.id AND s.role = 'primary'
              );
            """
        )
    )
    # Secondary sqlite snapshot source for Stage B trio (failover contract)
    op.execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.lottery_sources (id, lottery_id, source_key, adapter_key, role, priority, enabled, health_status)
            SELECT gen_random_uuid(), id, 'sqlite.snapshot', 'sqlite.snapshot', 'secondary', 50, true, 'unknown'
            FROM {SCHEMA}.lottery_lotteries
            WHERE source_id IN (4, 5, 6)
              AND NOT EXISTS (
                SELECT 1 FROM {SCHEMA}.lottery_sources s WHERE s.lottery_id = lottery_lotteries.id AND s.role = 'secondary'
              );
            """
        )
    )


def downgrade() -> None:
    op.drop_table("lottery_ai_usage", schema=SCHEMA)
    op.drop_table("lottery_source_conflicts", schema=SCHEMA)
    op.drop_table("lottery_source_attempts", schema=SCHEMA)
    op.drop_index("ix_lottery_sources_lottery_role", table_name="lottery_sources", schema=SCHEMA)
    op.drop_table("lottery_sources", schema=SCHEMA)
    for name in [
        "sync_backoff_seconds",
        "sync_post_interval_minutes",
        "sync_live_interval_minutes",
        "sync_pre_interval_minutes",
        "sync_post_window_minutes",
        "sync_live_window_minutes",
        "sync_pre_window_minutes",
        "sync_timeout_seconds",
        "sync_priority",
        "flag_emoji",
        "operator_key",
        "country_code",
    ]:
        op.execute(sa.text(f"ALTER TABLE {SCHEMA}.lottery_lotteries DROP COLUMN IF EXISTS {name}"))
