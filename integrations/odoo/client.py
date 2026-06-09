"""Odoo JSON-RPC client — consultas de solo lectura."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from integrations.odoo.config import OdooConfig
from integrations.odoo.exceptions import OdooConnectionError, OdooNotConfiguredError
from integrations.odoo.schemas import OdooConnectionStatus


class OdooClient:
    def __init__(self, tenant_id: str, config: OdooConfig | None = None):
        self.tenant_id = tenant_id
        self.config = config or OdooConfig(
            url=settings.odoo_url,
            database=settings.odoo_db,
            username=settings.odoo_username,
            api_key=settings.odoo_api_key,
        )
        self._uid: int | None = None

    @property
    def is_configured(self) -> bool:
        return bool(
            self.config.url
            and self.config.database
            and self.config.username
            and self.config.api_key
        )

    @staticmethod
    def health() -> dict[str, str]:
        return {"status": "ready", "connector": "odoo", "version": "0.3.0"}

    async def test_connection(self) -> dict[str, Any]:
        if not self.is_configured:
            return OdooConnectionStatus(
                connected=False,
                error="Odoo no conectado — credenciales incompletas",
            ).model_dump()

        try:
            version = await self._jsonrpc("common", "version", [])
            uid = await self._authenticate()
            return OdooConnectionStatus(
                connected=True,
                database=self.config.database,
                version=str(version.get("server_version", version.get("server_serie", ""))),
                uid=uid,
            ).model_dump()
        except Exception as exc:
            return OdooConnectionStatus(connected=False, error=str(exc)).model_dump()

    async def _authenticate(self) -> int:
        if self._uid is not None:
            return self._uid
        uid = await self._jsonrpc(
            "common",
            "authenticate",
            [
                self.config.database,
                self.config.username,
                self.config.api_key,
                {},
            ],
        )
        if not uid:
            raise OdooConnectionError("Autenticación Odoo fallida")
        self._uid = int(uid)
        return self._uid

    async def _jsonrpc(self, service: str, method: str, args: list) -> Any:
        if not self.config.url:
            raise OdooNotConfiguredError()
        url = f"{self.config.url.rstrip('/')}/jsonrpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"service": service, "method": method, "args": args},
            "id": 1,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        if data.get("error"):
            err = data["error"]
            msg = err.get("data", {}).get("message") or err.get("message", str(err))
            raise OdooConnectionError(msg)
        return data.get("result")

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: list | None = None,
        kwargs: dict | None = None,
        *,
        context: dict | None = None,
    ) -> Any:
        if not self.is_configured:
            raise OdooNotConfiguredError()
        uid = await self._authenticate()
        call_kwargs = dict(kwargs or {})
        if context:
            merged = dict(call_kwargs.get("context") or {})
            merged.update(context)
            call_kwargs["context"] = merged
        return await self._jsonrpc(
            "object",
            "execute_kw",
            [
                self.config.database,
                uid,
                self.config.api_key,
                model,
                method,
                args or [],
                call_kwargs,
            ],
        )

    async def search_read(
        self,
        model: str,
        domain: list | None = None,
        fields: list[str] | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
        order: str | None = None,
        context: dict | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"limit": limit, "offset": offset}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order
        result = await self.execute_kw(model, "search_read", [domain or []], kwargs, context=context)
        return list(result or [])

    async def search_count(
        self,
        model: str,
        domain: list | None = None,
        *,
        context: dict | None = None,
    ) -> int:
        result = await self.execute_kw(model, "search_count", [domain or []], context=context)
        return int(result or 0)

    async def read_group(
        self,
        model: str,
        domain: list,
        fields: list[str],
        groupby: list[str],
        *,
        limit: int | None = None,
        context: dict | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"lazy": False}
        if limit:
            kwargs["limit"] = limit
        result = await self.execute_kw(
            model, "read_group", [domain, fields, groupby], kwargs, context=context
        )
        return list(result or [])
