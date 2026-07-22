"""Resuelve configuración Odoo desde UI (tenant_integration_settings) + .env."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.integration_settings import TenantIntegrationSetting
from app.services.credential_vault import decrypt_secret
from integrations.odoo.config import OdooConfig


@dataclass
class ResolvedOdooSettings:
    config: OdooConfig
    read_only: bool
    company_id: int | None
    source: str
    configured: bool
    url: str
    database: str
    username: str
    api_key_set: bool


def _parse_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if val in (None, ""):
        return False
    return str(val).lower() in ("1", "true", "yes", "on")


async def _integration_row(db: AsyncSession, tenant_id: uuid.UUID) -> TenantIntegrationSetting | None:
    result = await db.execute(
        select(TenantIntegrationSetting).where(
            TenantIntegrationSetting.tenant_id == tenant_id,
            TenantIntegrationSetting.provider == "odoo",
        )
    )
    return result.scalar_one_or_none()


async def resolve_odoo_settings(db: AsyncSession, tenant_id: uuid.UUID) -> ResolvedOdooSettings:
    row = await _integration_row(db, tenant_id)
    cfg = dict(row.config) if row else {}
    secrets = dict(row.secrets_encrypted) if row else {}
    source = "database" if row else "env"

    api_key = settings.odoo_api_key
    if secrets.get("api_key"):
        try:
            api_key = decrypt_secret(secrets["api_key"])
        except ValueError:
            pass

    url = (cfg.get("url") or settings.odoo_url or "").strip()
    database = (cfg.get("database") or settings.odoo_db or "").strip()
    username = (cfg.get("username") or settings.odoo_username or "").strip()

    read_only = settings.odoo_read_only
    if "read_only" in cfg:
        read_only = _parse_bool(cfg["read_only"])
    elif row is None and not settings.odoo_read_only:
        read_only = False

    company_id_raw = cfg.get("company_id")
    company_id: int | None = None
    if company_id_raw not in (None, ""):
        try:
            company_id = int(company_id_raw)
        except (TypeError, ValueError):
            company_id = None

    configured = bool(url and database and username and api_key)
    odoo_cfg = OdooConfig(url=url, database=database, username=username, api_key=api_key)

    return ResolvedOdooSettings(
        config=odoo_cfg,
        read_only=read_only,
        company_id=company_id,
        source=source,
        configured=configured,
        url=url,
        database=database,
        username=username,
        api_key_set=bool(api_key),
    )


async def resolve_odoo_config(db: AsyncSession, tenant_id: uuid.UUID) -> OdooConfig:
    return (await resolve_odoo_settings(db, tenant_id)).config


async def resolve_odoo_read_only(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
    return (await resolve_odoo_settings(db, tenant_id)).read_only
