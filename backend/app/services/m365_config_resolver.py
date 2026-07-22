"""Resuelve configuración M365 desde .env y overrides en tenant.settings."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import Tenant
from app.services.credential_vault import decrypt_secret, encrypt_secret
from integrations.microsoft365.config import M365Config


def _masked(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "****"
    return f"{secret[:4]}…{secret[-4:]}"


async def resolve_m365_config(db: AsyncSession, tenant_id: uuid.UUID) -> tuple[M365Config, dict]:
    """Retorna M365Config y metadatos para admin (sin exponer secretos)."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    overrides = (tenant.settings or {}).get("m365", {}) if tenant else {}

    tenant_id_val = overrides.get("tenant_id") or settings.m365_tenant_id
    client_id = overrides.get("client_id") or settings.m365_client_id
    client_secret = settings.m365_client_secret
    if overrides.get("client_secret_encrypted"):
        client_secret = decrypt_secret(overrides["client_secret_encrypted"])

    redirect_uri = overrides.get("redirect_uri") or settings.m365_redirect_uri
    webhook_url = overrides.get("webhook_url") or settings.m365_webhook_url
    webhook_state = overrides.get("webhook_client_state") or settings.m365_webhook_client_state

    cfg = M365Config(
        tenant_id=tenant_id_val,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        read_only=settings.m365_read_only,
    )
    meta = {
        "tenant_id": tenant_id_val,
        "client_id": client_id,
        "client_secret_configured": bool(client_secret.strip()),
        "client_secret_masked": _masked(client_secret),
        "redirect_uri": redirect_uri,
        "webhook_url": webhook_url,
        "webhook_client_state_configured": bool(webhook_state.strip()),
        "read_only": settings.m365_read_only,
        "oauth_ready": cfg.is_configured(),
        "source": "tenant_override" if overrides else "env",
    }
    return cfg, meta


async def update_m365_tenant_overrides(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    client_secret: str | None = None,
    webhook_client_state: str | None = None,
) -> dict:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise ValueError("Tenant no encontrado")
    settings_json = dict(tenant.settings or {})
    m365 = dict(settings_json.get("m365", {}))
    if client_secret is not None:
        m365["client_secret_encrypted"] = encrypt_secret(client_secret)
    if webhook_client_state is not None:
        m365["webhook_client_state"] = webhook_client_state
    settings_json["m365"] = m365
    tenant.settings = settings_json
    await db.flush()
    _, meta = await resolve_m365_config(db, tenant_id)
    return meta
