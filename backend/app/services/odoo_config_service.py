"""Estado de configuración Odoo — diagnóstico sin exponer secretos."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.odoo_config_resolver import resolve_odoo_settings
from integrations.odoo.client import OdooClient
from integrations.odoo.exceptions import OdooConnectionError, OdooNotConfiguredError


class OdooConfigService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def status(self) -> dict:
        resolved = await resolve_odoo_settings(self.db, self.tenant_id)
        missing: list[str] = []
        if not resolved.url:
            missing.append("URL de Odoo")
        if not resolved.database:
            missing.append("Base de datos")
        if not resolved.username:
            missing.append("Usuario API")
        if not resolved.api_key_set:
            missing.append("API Key")

        configured = resolved.configured
        if configured:
            message = (
                "Odoo configurado desde la interfaz"
                if resolved.source == "database"
                else "Odoo configurado (variables de entorno)"
            )
        else:
            message = (
                "Configure Odoo en Configuración → Integraciones → Odoo"
                if not missing
                else f"Faltan credenciales: {', '.join(missing)}"
            )

        return {
            "configured": configured,
            "read_only": resolved.read_only,
            "url_set": bool(resolved.url),
            "database": resolved.database or None,
            "username_set": bool(resolved.username),
            "api_key_set": resolved.api_key_set,
            "missing": missing,
            "message": message,
            "source": resolved.source,
            "admin_config_url": "/configuracion/integraciones/odoo",
        }

    async def test_connection(self) -> dict:
        base = await self.status()
        if not base["configured"]:
            return {
                **base,
                "connected": False,
                "version": None,
                "error": base["message"],
            }
        resolved = await resolve_odoo_settings(self.db, self.tenant_id)
        client = OdooClient(str(self.tenant_id), resolved.config)
        try:
            result = await client.test_connection()
            connected = bool(result.get("connected"))
            return {
                **base,
                "connected": connected,
                "version": result.get("version"),
                "database": result.get("database") or resolved.database,
                "error": result.get("error"),
                "message": "Conexión exitosa" if connected else result.get("error", "Error de conexión"),
            }
        except (OdooConnectionError, OdooNotConfiguredError) as exc:
            return {**base, "connected": False, "version": None, "error": str(exc), "message": str(exc)}
