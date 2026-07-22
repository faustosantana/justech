from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    lottery_module_enabled: bool = False
    lottery_sync_enabled: bool = False
    lottery_sync_write_enabled: bool = False
    lottery_sync_days_back: int = 3
    lottery_sync_request_delay: float = 2.5
    lottery_sync_max_retries: int = 4
    lottery_sync_schedule: str = "0 */6 * * *"
    lottery_sync_source: str = "api"
    lottery_export_max_rows: int = 5000
    lottery_max_range_days: int = 3660
    lottery_default_page_size: int = 50
    lottery_max_page_size: int = 500
    lottery_max_compare_lotteries: int = 10
    lottery_max_draw_count: int = 200
    lottery_max_days_window: int = 90
    lottery_max_stats_limit: int = 100
    lottery_chat_max_history_messages: int = 30
    lottery_chat_max_tool_calls: int = 8
    lottery_chat_timeout_seconds: int = 60
    lottery_chat_max_sessions_per_user: int = 100
    lottery_chat_max_result_rows: int = 500
    lottery_export_max_rows_csv: int = 100000
    lottery_export_max_rows_xlsx: int = 50000
    lottery_export_max_rows_pdf: int = 5000
    lottery_export_expiration_minutes: int = 30
    lottery_export_max_file_size_mb: int = 25
    lottery_exports_path: str = "/tmp/jaios-lottery-exports"
    lottery_scheduler_enabled: bool = False
    lottery_scheduler_mode: str = "disabled"  # disabled | observe | guarded_write
    lottery_scraping_enabled: bool = False
    lottery_share_max_ttl_hours: int = 168
    lottery_share_default_ttl_hours: int = 24
    lottery_share_max_views_default: int = 50
    lottery_sync_api_base_url: str = "https://api.elboletoganador.com/api"
    lottery_sync_user_agent: str = "JAIOS-LotterySync/0.1 (+staging; controlled-write)"
    lottery_sync_lock_ttl_seconds: int = 120
    lottery_sync_api_allowlist: str = "api.elboletoganador.com"
    lottery_sync_max_range_days_write: int = 7
    lottery_sync_automatic_write_enabled: bool = False
    lottery_sync_interval_minutes: int = 60
    lottery_sync_lookback_days: int = 3
    lottery_sync_max_range_days: int = 7
    lottery_sync_allowed_database: str = "jaios_lottery_staging"
    lottery_sync_allowed_port: int = 5434
    lottery_sync_max_new_per_run: int = 500
    lottery_sync_max_changed_per_run: int = 0
    lottery_sync_max_conflicts_per_run: int = 0
    lottery_sync_max_invalid_per_run: int = 10
    lottery_sync_require_dry_run: bool = True
    lottery_sync_require_reconciliation: bool = True
    lottery_sync_timezone: str = "America/Santo_Domingo"
    lottery_sync_circuit_failure_threshold: int = 3
    lottery_sync_write_flag_max_minutes: int = 15
    lottery_sync_max_run_minutes: int = 15
    lottery_sync_backup_max_age_hours: int = 24
    lottery_source_contract_version: str = "elboletoganador.historial.v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "JAIOS"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://jaios:jaios_secret@localhost:5432/jaios"

    jwt_secret_key: str = "change-me-jwt"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    qdrant_collection_prefix: str = "jaios_"

    redis_url: str = "redis://localhost:6379/0"

    search_cache_enabled: bool = True
    search_cache_ttl_seconds: int = 120
    search_cache_assistant_ttl_seconds: int = 60
    search_cache_odoo_ttl_seconds: int = 180
    search_cache_dgcp_ttl_seconds: int = 300
    search_index_enabled: bool = True
    search_analytics_enabled: bool = True

    n8n_webhook_url: str = "http://localhost:5678"
    n8n_api_key: str = ""

    llm_default_provider: str = "openai"
    llm_fallback_provider: str = "claude"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_default_model: str = "gpt-4o"

    anthropic_api_key: str = ""
    anthropic_default_model: str = "claude-sonnet-4-20250514"

    deepseek_huawei_api_key: str = ""
    deepseek_huawei_base_url: str = ""
    deepseek_huawei_default_model: str = "deepseek-chat"

    hermes_local_base_url: str = "http://localhost:11434"
    hermes_local_default_model: str = "hermes3"

    odoo_url: str = ""
    odoo_db: str = ""
    odoo_username: str = ""
    odoo_api_key: str = ""
    odoo_read_only: bool = True

    # Bid Center (justech_bid_center) — disabled by default; no secrets in git
    bid_center_enabled: bool = False
    bid_center_url: str = ""
    bid_center_api_key: str = ""
    bid_center_hmac_secret: str = ""
    bid_center_timeout: float = 15.0
    bid_center_odoo_web_base: str = ""

    # Bid analysis (Hermes / Huawei ModelArts) — DEV cost guards
    hermes_service_url: str = "http://hermes-service:8000"
    hermes_api_token: str = ""
    hermes_enabled: bool = True
    hermes_provider: str = "huawei_modelarts"
    hermes_model: str = "DeepSeek-V3.2"
    hermes_default_model: str = "DeepSeek-V3.2"
    hermes_analysis_model: str = "deepseek-v4-flash"
    bid_analysis_timeout: float = 300.0
    bid_analysis_temperature: float = 0.2
    bid_analysis_max_tokens: int = 3500
    bid_analysis_max_context_chars: int = 18000
    bid_analysis_daily_max_calls: int = 40
    bid_analysis_daily_max_tokens: int = 200000
    bid_analysis_daily_max_cost_usd: float = 5.0
    bid_analysis_cost_per_1k_tokens: float = 0.0008
    # Prefer primary Hermes model for structured bid JSON (flash can timeout)
    bid_analysis_model: str = ""

    m365_read_only: bool = True
    m365_tenant_id: str = ""
    m365_client_id: str = ""
    m365_client_secret: str = ""
    m365_redirect_uri: str = "http://localhost:8000/api/v1/m365/auth/callback"

    dgcp_api_base_url: str = "https://datosabiertos.dgcp.gob.do/api-dgcp/v1"
    dgcp_api_key: str = ""
    dgcp_sync_default_max_pages: int = 5
    dgcp_sync_default_page_size: int = 50

    documents_storage_path: str = "/var/jaios/documents"
    documents_scan_enabled: bool = True
    documents_intelligence_enabled: bool = True

    knowledge_source_enabled: bool = True
    knowledge_source_path: str = "/source/justechai"
    knowledge_source_provider: str = "filesystem"
    knowledge_sync_folders: str = (
        "00_DATOS_EMPRESAS,01_DOCUMENTOS_LEGALES,02_PLANTILLAS,"
        "03_PROVEEDORES,04_FICHAS_TECNICAS,05_COTIZACIONES"
    )
    knowledge_vigency_warning_days: int = 30

    expediente_storage_path: str = "/var/jaios/expedientes"
    dgcp_attachment_ingestion_enabled: bool = True

    price_list_root_folder: str = "03_PROVEEDORES"
    price_list_scan_all_subfolders: bool = True

    @property
    def knowledge_sync_folder_list(self) -> list[str]:
        return [f.strip() for f in self.knowledge_sync_folders.split(",") if f.strip()]

    @property
    def dgcp_api_base_url_resolved(self) -> str:
        url = self.dgcp_api_base_url.rstrip("/")
        if url.endswith("/api-dgcp/v1"):
            return url
        if url.endswith("/api-dgcp"):
            return f"{url}/v1"
        return f"{url}/api-dgcp/v1"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg2")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
