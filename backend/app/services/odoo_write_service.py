"""Escritura en Odoo — cotizaciones, tareas, clientes (con permisos Odoo)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import JAIOSException
from app.schemas.odoo import (
    OdooCreateCustomerRequest,
    OdooCreateCustomerResponse,
    OdooCreateQuotationRequest,
    OdooCreateQuotationResponse,
    OdooCreateTaskRequest,
    OdooCreateTaskResponse,
)
from app.services.audit_service import AuditService
from app.services.odoo_permission_service import OdooPermissionService
from app.services.odoo_url_helper import build_odoo_url
from integrations.odoo.company_context import OdooCompanyContext
from integrations.odoo.config import OdooConfig
from integrations.odoo.client import OdooClient


class OdooWriteService:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        odoo_client_factory,
        company_context: OdooCompanyContext | None = None,
        ip_address: str | None = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._odoo_client_factory = odoo_client_factory
        self.company_context = company_context
        self.ip_address = ip_address

    def _permissions(self) -> OdooPermissionService:
        return OdooPermissionService(
            self.db, self.tenant_id, self.user_id, odoo_client_factory=self._odoo_client_factory
        )

    def _raw_client(self) -> OdooClient:
        return OdooClient(
            str(self.tenant_id),
            OdooConfig(
                url=settings.odoo_url,
                database=settings.odoo_db,
                username=settings.odoo_username,
                api_key=settings.odoo_api_key,
            ),
        )

    def _ctx(self) -> dict | None:
        if not self.company_context:
            return None
        return self.company_context.to_odoo_context()

    async def _audit(self, action: str, details: dict) -> None:
        await AuditService(self.db).log(
            action=action,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="odoo_write",
            details={**details, "ip": self.ip_address},
        )
        await self.db.commit()

    async def create_quotation(self, payload: OdooCreateQuotationRequest) -> OdooCreateQuotationResponse:
        perm = self._permissions()
        mapping = await perm._get_mapping()
        await perm.require_permission("sale.order", "create")

        company_id = payload.company_id or (self.company_context.company_id if self.company_context else None)
        if company_id and mapping and mapping.allowed_company_ids and company_id not in mapping.allowed_company_ids:
            raise JAIOSException("Empresa no permitida para su usuario Odoo", code="ODOO_COMPANY_NOT_ALLOWED")

        lines = []
        for line in payload.lines:
            line_vals: dict = {
                "product_id": line.product_id,
                "name": line.description or line.product_name or "Línea",
                "product_uom_qty": line.quantity,
                "price_unit": float(line.unit_price),
            }
            if line.discount:
                line_vals["discount"] = float(line.discount)
            lines.append((0, 0, line_vals))

        vals: dict = {
            "partner_id": payload.partner_id,
            "order_line": lines,
        }
        if company_id:
            vals["company_id"] = company_id
        if payload.opportunity_id:
            vals["opportunity_id"] = payload.opportunity_id
        if payload.currency_id:
            vals["currency_id"] = payload.currency_id
        if payload.note:
            vals["note"] = payload.note
        if payload.origin:
            vals["origin"] = payload.origin

        client = self._raw_client()
        order_id = await client.execute_kw("sale.order", "create", [vals], context=self._ctx())
        rows = await client.search_read(
            "sale.order", [("id", "=", order_id)], ["name", "amount_total", "state"], limit=1, context=self._ctx()
        )
        row = rows[0] if rows else {"id": order_id, "name": f"SO{order_id}"}

        await self._audit(
            "odoo.quotation_created",
            {
                "odoo_user_id": mapping.odoo_user_id if mapping else None,
                "odoo_quotation_id": order_id,
                "partner_id": payload.partner_id,
                "company_id": company_id,
                "source": payload.source,
                "source_ref": payload.source_ref,
                "result": "ok",
            },
        )

        return OdooCreateQuotationResponse(
            id=order_id,
            name=row.get("name", f"SO{order_id}"),
            amount_total=Decimal(str(row.get("amount_total", 0))),
            state=row.get("state", "draft"),
            odoo_url=build_odoo_url("sale.order", order_id),
            company_id=company_id,
        )

    async def create_task(self, payload: OdooCreateTaskRequest) -> OdooCreateTaskResponse:
        perm = self._permissions()
        mapping = await perm._get_mapping()
        await perm.require_module("project")
        await perm.require_permission("project.task", "create")

        vals: dict = {"name": payload.name, "description": payload.description or ""}
        if payload.project_id:
            vals["project_id"] = payload.project_id
        if payload.user_id:
            vals["user_ids"] = [(6, 0, [payload.user_id])]
        if payload.partner_id:
            vals["partner_id"] = payload.partner_id
        if payload.date_deadline:
            vals["date_deadline"] = payload.date_deadline
        if payload.opportunity_id:
            vals["opportunity_id"] = payload.opportunity_id

        client = self._raw_client()
        task_id = await client.execute_kw("project.task", "create", [vals], context=self._ctx())

        await self._audit(
            "odoo.task_created",
            {
                "odoo_user_id": mapping.odoo_user_id if mapping else None,
                "odoo_task_id": task_id,
                "project_id": payload.project_id,
                "source": payload.source,
                "source_ref": payload.source_ref,
                "result": "ok",
            },
        )

        return OdooCreateTaskResponse(
            id=task_id,
            name=payload.name,
            odoo_url=build_odoo_url("project.task", task_id),
            project_id=payload.project_id,
        )

    async def create_customer(self, payload: OdooCreateCustomerRequest) -> OdooCreateCustomerResponse:
        perm = self._permissions()
        mapping = await perm._get_mapping()
        await perm.require_permission("res.partner", "create")

        vals: dict = {"name": payload.name, "customer_rank": 1}
        if payload.email:
            vals["email"] = payload.email
        if payload.phone:
            vals["phone"] = payload.phone
        if payload.vat:
            vals["vat"] = payload.vat
        if payload.is_company is not None:
            vals["is_company"] = payload.is_company
        if payload.city:
            vals["city"] = payload.city

        client = self._raw_client()
        partner_id = await client.execute_kw("res.partner", "create", [vals], context=self._ctx())

        await self._audit(
            "odoo.customer_created",
            {
                "odoo_user_id": mapping.odoo_user_id if mapping else None,
                "odoo_partner_id": partner_id,
                "source": payload.source,
                "source_ref": payload.source_ref,
                "result": "ok",
            },
        )

        return OdooCreateCustomerResponse(
            id=partner_id,
            name=payload.name,
            odoo_url=build_odoo_url("res.partner", partner_id),
        )

    async def search_customer_by_phone(self, phone: str) -> dict | None:
        await self._permissions().require_module("contacts")
        client = await self._odoo_client_factory()
        digits = "".join(c for c in phone if c.isdigit())[-10:]
        if len(digits) < 7:
            return None
        rows = await client.search_read(
            "res.partner",
            ["|", ("phone", "ilike", digits), ("mobile", "ilike", digits), ("customer_rank", ">", 0)],
            ["id", "name", "email", "phone", "mobile"],
            limit=5,
        )
        return rows[0] if rows else None
