from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
