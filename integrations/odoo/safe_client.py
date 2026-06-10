"""Capa de seguridad read-only sobre OdooClient."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from integrations.odoo.client import OdooClient
from integrations.odoo.company_context import OdooCompanyContext
from integrations.odoo.constants import BLOCKED_METHOD_PREFIXES, READ_ONLY_METHODS
from integrations.odoo.exceptions import OdooReadOnlyError


AuditCallback = Callable[[str, str, dict[str, Any]], Awaitable[None]]


class SafeOdooClient:
    def __init__(
        self,
        client: OdooClient,
        *,
        read_only: bool = True,
        audit_callback: AuditCallback | None = None,
        company_context: OdooCompanyContext | None = None,
        jaios_user_id: uuid.UUID | None = None,
    ):
        self.client = client
        self.read_only = read_only
        self.audit_callback = audit_callback
        self.company_context = company_context
        self.jaios_user_id = jaios_user_id

    @property
    def is_configured(self) -> bool:
        return self.client.is_configured

    def _odoo_context(self) -> dict | None:
        if not self.company_context:
            return None
        return self.company_context.to_odoo_context()

    @staticmethod
    def _is_blocked_method(method: str) -> bool:
        if method in READ_ONLY_METHODS:
            return False
        lowered = method.lower()
        return any(
            lowered == prefix.rstrip("_")
            or lowered.startswith(prefix)
            for prefix in BLOCKED_METHOD_PREFIXES
        )

    async def _guard(self, model: str, method: str) -> None:
        if not self.read_only:
            return
        if self._is_blocked_method(method):
            details: dict[str, Any] = {
                "model": model,
                "method": method,
                "read_only": True,
            }
            if self.jaios_user_id:
                details["jaios_user_id"] = str(self.jaios_user_id)
            if self.company_context:
                details["company_id"] = self.company_context.company_id
            if self.audit_callback:
                await self.audit_callback("odoo.write_blocked", model, details)
            raise OdooReadOnlyError(method=method, model=model)

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: list | None = None,
        kwargs: dict | None = None,
    ) -> Any:
        await self._guard(model, method)
        return await self.client.execute_kw(
            model, method, args, kwargs, context=self._odoo_context()
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
    ) -> list[dict[str, Any]]:
        await self._guard(model, "search_read")
        return await self.client.search_read(
            model,
            domain,
            fields,
            limit=limit,
            offset=offset,
            order=order,
            context=self._odoo_context(),
        )

    async def search_count(self, model: str, domain: list | None = None) -> int:
        await self._guard(model, "search_count")
        return await self.client.search_count(model, domain, context=self._odoo_context())

    async def read_group(
        self,
        model: str,
        domain: list,
        fields: list[str],
        groupby: list[str],
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        await self._guard(model, "read_group")
        return await self.client.read_group(
            model, domain, fields, groupby, limit=limit, context=self._odoo_context()
        )

    async def test_connection(self) -> dict[str, Any]:
        return await self.client.test_connection()

    async def download_report_pdf(self, report_name: str, doc_id: int) -> bytes:
        return await self.client.download_report_pdf(report_name, doc_id)
