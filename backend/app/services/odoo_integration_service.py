"""Acciones Odoo desde Assistant, M365, WhatsApp y DGCP."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import JAIOSException
from app.schemas.odoo import (
    OdooCreateCustomerRequest,
    OdooCreateQuotationRequest,
    OdooQuotationLineRequest,
    OdooCreateTaskRequest,
    OdooIntegrationActionRequest,
    OdooIntegrationActionResponse,
)
from app.services.odoo_service import OdooService
from app.services.odoo_write_service import OdooWriteService


class OdooIntegrationService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.odoo = OdooService(db, tenant_id, user_id=user_id)

    async def _writer(self) -> OdooWriteService:
        ctx = await self.odoo._resolve_company()
        return OdooWriteService(
            self.db,
            self.tenant_id,
            self.user_id,
            odoo_client_factory=self.odoo._bare_client,
            company_context=ctx,
        )

    async def execute(self, req: OdooIntegrationActionRequest) -> OdooIntegrationActionResponse:
        action = req.action.strip().lower()
        payload = req.payload or {}
        source = req.source or "jaios"
        source_ref = req.source_ref

        try:
            if action == "search_customer_by_phone":
                phone = str(payload.get("phone", ""))
                row = await (await self._writer()).search_customer_by_phone(phone)
                return OdooIntegrationActionResponse(
                    ok=True,
                    action=action,
                    result={"customer": row},
                    message="Cliente encontrado" if row else "Cliente no encontrado",
                )

            if action == "create_customer":
                result = await (await self._writer()).create_customer(
                    OdooCreateCustomerRequest(
                        name=payload["name"],
                        email=payload.get("email"),
                        phone=payload.get("phone"),
                        vat=payload.get("vat"),
                        city=payload.get("city"),
                        is_company=payload.get("is_company"),
                        source=source,
                        source_ref=source_ref,
                    )
                )
                return OdooIntegrationActionResponse(ok=True, action=action, result=result.model_dump(mode="json"))

            if action in ("create_quotation", "create_quotation_request"):
                lines = [
                    OdooQuotationLineRequest(
                        product_id=ln.get("product_id"),
                        product_name=ln.get("product_name"),
                        description=ln.get("description"),
                        quantity=float(ln.get("quantity", 1)),
                        unit_price=ln.get("unit_price", 0),
                        discount=ln.get("discount"),
                    )
                    for ln in payload.get("lines", [])
                ]
                if not lines:
                    raise JAIOSException("Se requiere al menos una línea de cotización", code="VALIDATION_ERROR")
                result = await (await self._writer()).create_quotation(
                    OdooCreateQuotationRequest(
                        partner_id=int(payload["partner_id"]),
                        lines=lines,
                        company_id=payload.get("company_id"),
                        opportunity_id=payload.get("opportunity_id"),
                        currency_id=payload.get("currency_id"),
                        note=payload.get("note"),
                        origin=payload.get("origin") or f"JAIOS/{source}",
                        source=source,
                        source_ref=source_ref,
                    )
                )
                return OdooIntegrationActionResponse(ok=True, action=action, result=result.model_dump(mode="json"))

            if action == "create_task":
                result = await (await self._writer()).create_task(
                    OdooCreateTaskRequest(
                        name=payload["name"],
                        description=payload.get("description"),
                        project_id=payload.get("project_id"),
                        user_id=payload.get("user_id"),
                        partner_id=payload.get("partner_id"),
                        date_deadline=payload.get("date_deadline"),
                        opportunity_id=payload.get("opportunity_id"),
                        source=source,
                        source_ref=source_ref,
                    )
                )
                return OdooIntegrationActionResponse(ok=True, action=action, result=result.model_dump(mode="json"))

            raise JAIOSException(f"Acción no soportada: {action}", code="ODOO_ACTION_UNSUPPORTED")
        except JAIOSException as exc:
            return OdooIntegrationActionResponse(ok=False, action=action, message=exc.message, result={"code": exc.code})
