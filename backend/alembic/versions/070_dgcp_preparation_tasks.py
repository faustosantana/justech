"""070 — checklist operativo preparación (Mis Licitaciones)."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

revision: str = "070_dgcp_preparation_tasks"
down_revision: Union[str, None] = "069_dgcp_hist_identity_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if not insp.has_table("dgcp_checklist_templates", schema=SCHEMA):
        bind.execute(
            text(
                f"""
                CREATE TABLE {SCHEMA}.dgcp_checklist_templates (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL REFERENCES {SCHEMA}.tenants(id) ON DELETE CASCADE,
                    name VARCHAR(128) NOT NULL,
                    description TEXT,
                    is_default BOOLEAN NOT NULL DEFAULT false,
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    created_by_id UUID,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        bind.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_dgcp_checklist_templates_tenant "
                f"ON {SCHEMA}.dgcp_checklist_templates (tenant_id)"
            )
        )

    if not insp.has_table("dgcp_checklist_template_items", schema=SCHEMA):
        bind.execute(
            text(
                f"""
                CREATE TABLE {SCHEMA}.dgcp_checklist_template_items (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL REFERENCES {SCHEMA}.tenants(id) ON DELETE CASCADE,
                    template_id UUID NOT NULL REFERENCES {SCHEMA}.dgcp_checklist_templates(id) ON DELETE CASCADE,
                    item_key VARCHAR(64) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    priority VARCHAR(16) NOT NULL DEFAULT 'medium',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    default_offset_hours INTEGER,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    CONSTRAINT uq_dgcp_checklist_tpl_item_key UNIQUE (template_id, item_key)
                )
                """
            )
        )
        bind.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_dgcp_checklist_tpl_items_tpl "
                f"ON {SCHEMA}.dgcp_checklist_template_items (template_id)"
            )
        )

    if not insp.has_table("dgcp_preparation_tasks", schema=SCHEMA):
        bind.execute(
            text(
                f"""
                CREATE TABLE {SCHEMA}.dgcp_preparation_tasks (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL REFERENCES {SCHEMA}.tenants(id) ON DELETE CASCADE,
                    opportunity_id UUID NOT NULL REFERENCES {SCHEMA}.dgcp_opportunities(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    priority VARCHAR(16) NOT NULL DEFAULT 'medium',
                    assigned_user_id UUID REFERENCES {SCHEMA}.users(id) ON DELETE SET NULL,
                    due_at TIMESTAMPTZ,
                    template_id UUID,
                    template_item_key VARCHAR(64),
                    created_by_id UUID,
                    completed_by_id UUID,
                    completed_at TIMESTAMPTZ,
                    meta JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        bind.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_dgcp_prep_tasks_opp "
                f"ON {SCHEMA}.dgcp_preparation_tasks (tenant_id, opportunity_id)"
            )
        )
        bind.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_dgcp_prep_tasks_assignee_due "
                f"ON {SCHEMA}.dgcp_preparation_tasks (tenant_id, assigned_user_id, due_at)"
            )
        )
        bind.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_dgcp_prep_tasks_status "
                f"ON {SCHEMA}.dgcp_preparation_tasks (tenant_id, status)"
            )
        )

    if not insp.has_table("dgcp_prep_alert_logs", schema=SCHEMA):
        bind.execute(
            text(
                f"""
                CREATE TABLE {SCHEMA}.dgcp_prep_alert_logs (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL REFERENCES {SCHEMA}.tenants(id) ON DELETE CASCADE,
                    dedup_key VARCHAR(320) NOT NULL,
                    user_id UUID NOT NULL,
                    opportunity_id UUID NOT NULL,
                    task_id UUID,
                    alert_type VARCHAR(64) NOT NULL,
                    deadline_key VARCHAR(64) NOT NULL,
                    notification_id UUID,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    CONSTRAINT uq_dgcp_prep_alert_dedup UNIQUE (tenant_id, dedup_key)
                )
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    for t in (
        "dgcp_prep_alert_logs",
        "dgcp_preparation_tasks",
        "dgcp_checklist_template_items",
        "dgcp_checklist_templates",
    ):
        bind.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.{t} CASCADE"))
