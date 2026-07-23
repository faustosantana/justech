"""060 — Lottery AI alerting closeout: alerts lifecycle, thresholds, tone prefs.

Revision ID: 060_lottery_ai_alerting_closeout
Revises: 059_lottery_ai_admin_center
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "060_lottery_ai_alerting_closeout"
down_revision: Union[str, None] = "059_lottery_ai_admin_center"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("lottery_ai_alerts", schema=SCHEMA)}

    add = [
        ("status", sa.Column("status", sa.String(32), server_default="open", nullable=False)),
        ("fingerprint", sa.Column("fingerprint", sa.String(128))),
        ("component", sa.Column("component", sa.String(64))),
        ("title", sa.Column("title", sa.String(255))),
        ("first_detected_at", sa.Column("first_detected_at", sa.DateTime(timezone=True))),
        ("last_detected_at", sa.Column("last_detected_at", sa.DateTime(timezone=True))),
        ("occurrence_count", sa.Column("occurrence_count", sa.Integer(), server_default="1", nullable=False)),
        ("acknowledged_at", sa.Column("acknowledged_at", sa.DateTime(timezone=True))),
        ("acknowledged_by", sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True))),
        ("resolved_at", sa.Column("resolved_at", sa.DateTime(timezone=True))),
        ("resolved_by", sa.Column("resolved_by", postgresql.UUID(as_uuid=True))),
        ("silenced_until", sa.Column("silenced_until", sa.DateTime(timezone=True))),
        ("resolution_note", sa.Column("resolution_note", sa.Text())),
        ("prompt_version", sa.Column("prompt_version", sa.String(64))),
        ("model_name", sa.Column("model_name", sa.String(128))),
        ("tool_name", sa.Column("tool_name", sa.String(128))),
        ("metric_name", sa.Column("metric_name", sa.String(64))),
        ("metric_value", sa.Column("metric_value", sa.Float())),
        ("threshold_value", sa.Column("threshold_value", sa.Float())),
        ("auto_resolved", sa.Column("auto_resolved", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("updated_at", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"))),
    ]
    for name, col in add:
        if name not in cols:
            op.add_column("lottery_ai_alerts", col, schema=SCHEMA)

    # Backfill status from legacy acknowledged boolean
    if "status" not in cols:
        op.execute(
            sa.text(
                f"""
                UPDATE {SCHEMA}.lottery_ai_alerts
                SET status = CASE WHEN acknowledged THEN 'acknowledged' ELSE 'open' END
                WHERE status IS NULL OR status = 'open'
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                UPDATE {SCHEMA}.lottery_ai_alerts
                SET status = 'acknowledged'
                WHERE acknowledged IS TRUE AND status = 'open'
                """
            )
        )

    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.lottery_ai_alerts
            SET fingerprint = COALESCE(fingerprint, code || ':' || COALESCE(tenant_id::text, 'global'))
            WHERE fingerprint IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.lottery_ai_alerts
            SET first_detected_at = COALESCE(first_detected_at, created_at),
                last_detected_at = COALESCE(last_detected_at, created_at)
            WHERE first_detected_at IS NULL OR last_detected_at IS NULL
            """
        )
    )

    op.create_index(
        "ix_lottery_ai_alerts_status_code",
        "lottery_ai_alerts",
        ["status", "code"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_lottery_ai_alerts_fingerprint",
        "lottery_ai_alerts",
        ["tenant_id", "fingerprint", "status"],
        schema=SCHEMA,
        if_not_exists=True,
    )

    # Drop unfinished draft table from partial 060 if present
    existing = {t for t in sa.inspect(bind).get_table_names(schema=SCHEMA)}
    if "lottery_ai_alert_thresholds" not in existing:
        op.create_table(
            "lottery_ai_alert_thresholds",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
            sa.Column("version_label", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column("changelog", sa.Text()),
            sa.Column("author_user_id", postgresql.UUID(as_uuid=True)),
            sa.Column("previous_version_id", postgresql.UUID(as_uuid=True)),
            sa.Column("published_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_lottery_ai_alert_thresholds_status",
            "lottery_ai_alert_thresholds",
            ["status"],
            schema=SCHEMA,
        )

    if "lottery_ai_tone_preferences" not in existing:
        op.create_table(
            "lottery_ai_tone_preferences",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
            sa.Column("user_id", postgresql.UUID(as_uuid=True)),
            sa.Column("tone_key", sa.String(32), nullable=False, server_default="analitico"),
            sa.Column("allow_user_override", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("payload", postgresql.JSONB()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("tenant_id", "user_id", name="uq_lottery_ai_tone_tenant_user"),
            schema=SCHEMA,
        )


def downgrade() -> None:
    op.drop_table("lottery_ai_tone_preferences", schema=SCHEMA)
    op.drop_table("lottery_ai_alert_thresholds", schema=SCHEMA)
    for idx in ("ix_lottery_ai_alerts_fingerprint", "ix_lottery_ai_alerts_status_code"):
        op.drop_index(idx, table_name="lottery_ai_alerts", schema=SCHEMA)
    for col in (
        "updated_at",
        "auto_resolved",
        "threshold_value",
        "metric_value",
        "metric_name",
        "tool_name",
        "model_name",
        "prompt_version",
        "resolution_note",
        "silenced_until",
        "resolved_by",
        "resolved_at",
        "acknowledged_by",
        "acknowledged_at",
        "occurrence_count",
        "last_detected_at",
        "first_detected_at",
        "title",
        "component",
        "fingerprint",
        "status",
    ):
        op.drop_column("lottery_ai_alerts", col, schema=SCHEMA)
