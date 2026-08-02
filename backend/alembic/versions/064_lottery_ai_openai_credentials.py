"""064 — Lottery AI Settings OpenAI credentials (encrypted).

Revision ID: 064_lottery_ai_openai_credentials
Revises: 063_lottery_ai_settings
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "064_lottery_ai_openai_credentials"
down_revision: Union[str, None] = "063_lottery_ai_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("lottery_ai_settings", schema=SCHEMA)}
    alters = [
        ("openai_api_key_encrypted", sa.Text()),
        ("openai_base_url", sa.String(512)),
        ("openai_organization", sa.String(128)),
        ("openai_project", sa.String(128)),
        ("credential_updated_at", sa.DateTime(timezone=True)),
        ("credential_updated_by", sa.UUID()),
    ]
    for name, coltype in alters:
        if name not in cols:
            op.add_column(
                "lottery_ai_settings",
                sa.Column(name, coltype, nullable=True),
                schema=SCHEMA,
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("lottery_ai_settings", schema=SCHEMA)}
    for name in (
        "credential_updated_by",
        "credential_updated_at",
        "openai_project",
        "openai_organization",
        "openai_base_url",
        "openai_api_key_encrypted",
    ):
        if name in cols:
            op.drop_column("lottery_ai_settings", name, schema=SCHEMA)
