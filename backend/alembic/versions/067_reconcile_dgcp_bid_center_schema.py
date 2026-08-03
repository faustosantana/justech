"""Reconcile remaining DGCP Bid Center tables (033/034/035 fragments) — idempotent.

Creates missing historical awards, similar-cache, and licitador company profiles
that were skipped when Alembic advanced past stubbed early revisions.
Also widens alembic_version.version_num to VARCHAR(64).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "067_reconcile_dgcp_bid"
down_revision: Union[str, None] = "066_reconcile_dgcp_opp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "jaios"


def _insp():
    return inspect(op.get_bind())


def _table_exists(name: str) -> bool:
    return _insp().has_table(name, schema=SCHEMA)


def _index_exists(table: str, index_name: str) -> bool:
    return any(i["name"] == index_name for i in _insp().get_indexes(table, schema=SCHEMA))


def upgrade() -> None:
    bind = op.get_bind()

    # Widen alembic_version for long revision ids (DEV drift).
    bind.execute(
        text(
            """
            ALTER TABLE jaios.alembic_version
            ALTER COLUMN version_num TYPE VARCHAR(64)
            """
        )
    )

    if not _table_exists("dgcp_historical_awards"):
        op.create_table(
            "dgcp_historical_awards",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tenant_id",
                UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("process_code", sa.String(128), nullable=False),
            sa.Column("contract_code", sa.String(128), nullable=True),
            sa.Column("buyer_institution", sa.String(512), nullable=False),
            sa.Column("buyer_institution_code", sa.String(64), nullable=True),
            sa.Column("award_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("contract_object", sa.Text(), nullable=True),
            sa.Column("item_description", sa.Text(), nullable=True),
            sa.Column("item_description_user", sa.Text(), nullable=True),
            sa.Column("supplier_name", sa.String(512), nullable=True),
            sa.Column("supplier_rpe", sa.String(64), nullable=True),
            sa.Column("awarded_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("currency", sa.String(8), nullable=False, server_default="DOP"),
            sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
            sa.Column("unit_price", sa.Numeric(18, 4), nullable=True),
            sa.Column("total_line_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("unit_measure", sa.String(64), nullable=True),
            sa.Column("modality", sa.String(128), nullable=True),
            sa.Column("objeto_proceso", sa.String(128), nullable=True),
            sa.Column("award_status", sa.String(128), nullable=True),
            sa.Column("process_url", sa.Text(), nullable=True),
            sa.Column("contract_url", sa.Text(), nullable=True),
            sa.Column("source", sa.String(32), nullable=False, server_default="dgcp_contratos"),
            sa.Column("unspsc_family", sa.String(32), nullable=True),
            sa.Column("unspsc_class", sa.String(32), nullable=True),
            sa.Column("unspsc_subclass", sa.String(32), nullable=True),
            sa.Column("search_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("raw_payload", JSONB, nullable=False, server_default="{}"),
            sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint(
                "tenant_id",
                "process_code",
                "contract_code",
                "item_description_user",
                name="uq_dgcp_hist_award_line",
            ),
            schema=SCHEMA,
        )
        op.create_index("ix_dgcp_hist_awards_tenant", "dgcp_historical_awards", ["tenant_id"], schema=SCHEMA)
        op.create_index(
            "ix_dgcp_hist_awards_institution", "dgcp_historical_awards", ["buyer_institution"], schema=SCHEMA
        )
        op.create_index("ix_dgcp_hist_awards_process", "dgcp_historical_awards", ["process_code"], schema=SCHEMA)
        op.create_index("ix_dgcp_hist_awards_supplier", "dgcp_historical_awards", ["supplier_name"], schema=SCHEMA)
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_dgcp_hist_awards_search_gin ON {SCHEMA}.dgcp_historical_awards "
            f"USING gin (to_tsvector('spanish', search_text))"
        )

    if not _table_exists("dgcp_historical_index_jobs"):
        op.create_table(
            "dgcp_historical_index_jobs",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tenant_id",
                UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("status", sa.String(32), nullable=False, server_default="running"),
            sa.Column("pages_indexed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("contracts_indexed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("items_indexed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            schema=SCHEMA,
        )

    if not _table_exists("dgcp_process_historical_similar_results"):
        op.create_table(
            "dgcp_process_historical_similar_results",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tenant_id",
                UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "opportunity_id",
                UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.dgcp_opportunities.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("process_code", sa.String(128), nullable=False),
            sa.Column("buyer_institution", sa.String(512), nullable=False),
            sa.Column("keywords_used", JSONB, nullable=False, server_default="[]"),
            sa.Column("searched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("results", JSONB, nullable=False, server_default="{}"),
            sa.Column("source", sa.String(64), nullable=False, server_default="dgcp_api_on_demand"),
            sa.Column("status", sa.String(32), nullable=False, server_default="searched"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("pages_scanned", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("candidates_scanned", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("refresh_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("tenant_id", "opportunity_id", name="uq_dgcp_hist_similar_cache_opp"),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_dgcp_hist_similar_cache_tenant",
            "dgcp_process_historical_similar_results",
            ["tenant_id"],
            schema=SCHEMA,
        )
        op.create_index(
            "ix_dgcp_hist_similar_cache_expires",
            "dgcp_process_historical_similar_results",
            ["expires_at"],
            schema=SCHEMA,
        )

    if not _table_exists("licitador_company_profiles"):
        op.create_table(
            "licitador_company_profiles",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tenant_id",
                UUID(as_uuid=True),
                sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("company_key", sa.String(64), nullable=False),
            sa.Column("razon_social", sa.String(512), nullable=True),
            sa.Column("nombre_comercial", sa.String(512), nullable=True),
            sa.Column("rnc", sa.String(32), nullable=True),
            sa.Column("direccion", sa.Text(), nullable=True),
            sa.Column("telefono", sa.String(64), nullable=True),
            sa.Column("correo", sa.String(255), nullable=True),
            sa.Column("representante_legal", sa.String(255), nullable=True),
            sa.Column("cedula_representante", sa.String(32), nullable=True),
            sa.Column("cargo_representante", sa.String(128), nullable=True),
            sa.Column("raw_json", JSONB, nullable=False, server_default="{}"),
            sa.Column("missing_fields", JSONB, nullable=False, server_default="[]"),
            sa.Column("completeness_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("graph_file_id", sa.String(128), nullable=True),
            sa.Column("source_filename", sa.String(512), nullable=True),
            sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_licitador_company_profiles_tenant_key",
            "licitador_company_profiles",
            ["tenant_id", "company_key"],
            unique=True,
            schema=SCHEMA,
        )

    # Post-validation
    for table in (
        "dgcp_historical_awards",
        "dgcp_process_historical_similar_results",
        "licitador_company_profiles",
    ):
        if not _table_exists(table):
            raise RuntimeError(f"067_reconcile_dgcp_bid: table {table} still missing")


def downgrade() -> None:
    op.execute(text("SELECT 1 -- 067_reconcile_dgcp_bid: intentional no-op downgrade"))
