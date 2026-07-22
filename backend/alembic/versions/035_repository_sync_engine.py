"""Motor de sincronización de repositorios OneDrive — delta, logs, binding scope."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "035_repository_sync_engine"
down_revision = "034_dgcp_hist_similar_cache"
branch_labels = None
depends_on = None

SCHEMA = "jaios"


def upgrade() -> None:
    op.add_column(
        "integration_repository_bindings",
        sa.Column("repository_type", sa.String(64), nullable=False, server_default="general"),
        schema=SCHEMA,
    )
    op.add_column(
        "integration_repository_bindings",
        sa.Column("company_key", sa.String(64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "integration_repository_bindings",
        sa.Column("delta_link", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "integration_repository_bindings",
        sa.Column("last_error", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "integration_repository_bindings",
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=False, server_default="30"),
        schema=SCHEMA,
    )
    op.add_column(
        "m365_repository_files",
        sa.Column("binding_id", UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "m365_repository_files",
        sa.Column("content_hash", sa.String(128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "m365_repository_files",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_m365_repo_files_binding",
        "m365_repository_files",
        "integration_repository_bindings",
        ["binding_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_m365_repo_files_binding",
        "m365_repository_files",
        ["binding_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "repository_sync_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "binding_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.integration_repository_bindings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("trigger", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("files_synced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_indexed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("details", JSONB, nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index("ix_repo_sync_jobs_tenant", "repository_sync_jobs", ["tenant_id"], schema=SCHEMA)
    op.create_table(
        "licitador_company_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), nullable=False),
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
    op.add_column(
        "price_list_files",
        sa.Column("graph_file_id", sa.String(128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "price_list_files",
        sa.Column("processing_status", sa.String(32), nullable=False, server_default="indexed"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("price_list_files", "processing_status", schema=SCHEMA)
    op.drop_column("price_list_files", "graph_file_id", schema=SCHEMA)
    op.drop_table("licitador_company_profiles", schema=SCHEMA)
    op.drop_table("repository_sync_jobs", schema=SCHEMA)
    op.drop_constraint("fk_m365_repo_files_binding", "m365_repository_files", schema=SCHEMA, type_="foreignkey")
    op.drop_index("ix_m365_repo_files_binding", table_name="m365_repository_files", schema=SCHEMA)
    for col in ("is_deleted", "content_hash", "binding_id"):
        op.drop_column("m365_repository_files", col, schema=SCHEMA)
    for col in ("sync_interval_minutes", "last_error", "delta_link", "company_key", "repository_type"):
        op.drop_column("integration_repository_bindings", col, schema=SCHEMA)
