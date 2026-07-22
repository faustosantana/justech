"""Resuelve credenciales Ingram desde tenant_integration_settings + .env."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.integration_settings import TenantIntegrationSetting
from app.services.credential_vault import decrypt_secret
from integrations.suppliers.config import IngramConnectorConfig


def _parse_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if val in (None, ""):
        return False
    return str(val).lower() in ("1", "true", "yes", "on")


async def resolve_ingram_config(db: AsyncSession, tenant_id: uuid.UUID) -> IngramConnectorConfig:
    result = await db.execute(
        select(TenantIntegrationSetting).where(
            TenantIntegrationSetting.tenant_id == tenant_id,
            TenantIntegrationSetting.provider == "ingram",
        )
    )
    row = result.scalar_one_or_none()
    cfg = dict(row.config) if row else {}
    secrets = dict(row.secrets_encrypted) if row else {}
    source = "database" if row else "env"

    def secret(key: str, env_attr: str = "") -> str:
        if secrets.get(key):
            try:
                return decrypt_secret(secrets[key])
            except ValueError:
                pass
        if env_attr:
            return getattr(settings, env_attr, "") or ""
        return ""

    enabled = _parse_bool(cfg.get("enabled", settings.ingram_enabled))
    demo = _parse_bool(cfg.get("demo_mode", settings.ingram_demo_mode))

    return IngramConnectorConfig(
        enabled=enabled,
        use_sandbox=_parse_bool(cfg.get("use_sandbox", settings.ingram_use_sandbox)),
        api_base_url=(cfg.get("api_base_url") or settings.ingram_api_base_url or "").strip(),
        portal_url=(cfg.get("portal_url") or settings.ingram_portal_url or "").strip(),
        client_id=(cfg.get("client_id") or settings.ingram_client_id or "").strip(),
        client_secret=secret("client_secret", "ingram_client_secret"),
        customer_number=(cfg.get("customer_number") or settings.ingram_customer_number or "").strip(),
        country_code=(cfg.get("country_code") or settings.ingram_country_code or "US").strip(),
        sender_id=(cfg.get("sender_id") or settings.ingram_sender_id or "JAIOS").strip(),
        username=(cfg.get("username") or settings.ingram_username or "").strip(),
        password=secret("password", "ingram_password"),
        rate_limit_per_minute=int(cfg.get("rate_limit_per_minute") or settings.ingram_rate_limit_per_minute),
        cache_ttl_seconds=int(cfg.get("cache_ttl_seconds") or settings.ingram_cache_ttl_seconds),
        demo_mode=demo,
        source=source,
    )
