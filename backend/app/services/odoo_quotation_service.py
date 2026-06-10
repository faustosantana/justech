"""Búsqueda, detalle y PDF de cotizaciones Odoo (sale.order) — solo lectura."""

from __future__ import annotations

import uuid
from decimal import Decimal

from integrations.odoo.exceptions import OdooNotConfiguredError
from integrations.odoo.quotation_pdf import build_quotation_pdf
from integrations.odoo.normalize import (
    odoo_date,
    odoo_dec,
    odoo_float,
    odoo_m2m_ids,
    odoo_m2o_id,
    odoo_m2o_name,
    odoo_m2o_name_opt,
    odoo_str,
)

from app.schemas.odoo import (
    OdooListResponse,
    OdooQuotationDetailResponse,
    OdooQuotationLineResponse,
    OdooQuotationResponse,
    OdooQuotationSearchParams,
)
from app.services.odoo_service import OdooService

SALE_ORDER_FIELDS = [
    "name",
    "partner_id",
    "date_order",
    "amount_total",
    "currency_id",
    "state",
    "user_id",
    "company_id",
    "validity_date",
]

LINE_FIELDS = [
    "product_id",
    "name",
    "product_uom_qty",
    "price_unit",
    "discount",
    "price_subtotal",
    "tax_ids",
]


class OdooQuotationService:
    """Servicio especializado para cotizaciones Odoo con contexto multi-empresa."""

    def __init__(self, odoo: OdooService):
        self.odoo = odoo

    async def search(self, params: OdooQuotationSearchParams) -> OdooListResponse:
        client = await self.odoo._get_client()
        if not client.is_configured:
            return self.odoo._not_connected_list()

        domain: list = []
        if params.state:
            domain.append(("state", "=", params.state))
        else:
            domain.append(("state", "in", ["draft", "sent", "sale", "done"]))

        if params.quotation_number:
            domain.append(("name", "ilike", params.quotation_number.strip()))
        if params.customer:
            partner_ids = await self.odoo._partner_ids_for_search(params.customer)
            if partner_ids:
                domain.append(("partner_id", "in", partner_ids))
            else:
                domain.append(("partner_id.name", "ilike", params.customer.strip()))

        if params.salesperson:
            user_domain = self.odoo._domain(
                "res.users",
                ["|", ("name", "ilike", params.salesperson.strip()), ("login", "ilike", params.salesperson.strip())],
            )
            user_rows = await client.search_read("res.users", user_domain, ["id"], limit=50)
            user_ids = [r["id"] for r in user_rows if r.get("id")]
            if not user_ids:
                return self.odoo._list_response([], 0)
            domain.append(("user_id", "in", user_ids))

        if params.product:
            line_domain = self.odoo._domain(
                "sale.order.line",
                [("product_id.name", "ilike", params.product.strip())],
            )
            order_ids = await client.search_read(
                "sale.order.line",
                line_domain,
                ["order_id"],
                limit=200,
            )
            ids = list({odoo_m2o_id(r.get("order_id")) for r in order_ids if odoo_m2o_id(r.get("order_id"))})
            if not ids:
                return self.odoo._list_response([], 0)
            domain.append(("id", "in", ids))

        if params.date_from:
            domain.append(("date_order", ">=", params.date_from))
        if params.date_to:
            domain.append(("date_order", "<=", params.date_to))
        if params.amount_min is not None:
            domain.append(("amount_total", ">=", float(params.amount_min)))
        if params.amount_max is not None:
            domain.append(("amount_total", "<=", float(params.amount_max)))

        if params.q:
            partner_ids = await self.odoo._partner_ids_for_search(params.q)
            domain.extend(self.odoo._text_search_domain(params.q, partner_ids))

        if params.company_id is not None:
            domain.append(("company_id", "=", params.company_id))

        domain = self.odoo._domain("sale.order", domain)
        rows = await client.search_read(
            "sale.order",
            domain,
            SALE_ORDER_FIELDS,
            limit=params.limit,
            order="date_order desc",
        )
        items = [self._map_row(r) for r in rows]
        total = await client.search_count("sale.order", domain)
        return self.odoo._list_response(items, total)

    async def get_detail(self, quotation_id: int) -> OdooQuotationDetailResponse:
        client = await self.odoo._get_client()
        if not client.is_configured:
            return OdooQuotationDetailResponse(
                id=quotation_id,
                name="",
                partner_name="",
                amount_total=Decimal("0"),
                state="",
                connected=False,
                message="Odoo no conectado",
            )

        domain = self.odoo._domain("sale.order", [("id", "=", quotation_id)])
        rows = await client.search_read(
            "sale.order",
            domain,
            SALE_ORDER_FIELDS,
            limit=1,
        )
        if not rows:
            return OdooQuotationDetailResponse(
                id=quotation_id,
                name="",
                partner_name="",
                amount_total=Decimal("0"),
                state="",
                connected=True,
                message="Cotización no encontrada o fuera de su empresa",
            )

        row = rows[0]
        line_domain = self.odoo._domain(
            "sale.order.line",
            [("order_id", "=", quotation_id)],
        )
        line_rows = await client.search_read(
            "sale.order.line",
            line_domain,
            LINE_FIELDS,
            limit=500,
            order="sequence asc",
        )
        lines: list[OdooQuotationLineResponse] = []
        for lr in line_rows:
            tax_names: list[str] = []
            tax_ids = odoo_m2m_ids(lr.get("tax_ids"))
            if tax_ids:
                tax_rows = await client.search_read(
                    "account.tax",
                    [("id", "in", tax_ids)],
                    ["name"],
                    limit=10,
                )
                tax_names = [odoo_str(t.get("name")) for t in tax_rows if t.get("name")]
            lines.append(self._map_line(lr, tax_names=tax_names))
        base = self._map_row(row)
        return OdooQuotationDetailResponse(**base.model_dump(), lines=lines, connected=True)

    async def download_pdf(self, quotation_id: int) -> tuple[bytes, str]:
        """PDF de cotización — copia generada desde datos Odoo (RPC report es privado)."""
        detail = await self.get_detail(quotation_id)
        if not detail.connected or detail.message:
            raise ValueError(detail.message or "Cotización no encontrada o fuera de su empresa")
        pdf_bytes = build_quotation_pdf(detail)
        filename = f"{detail.name.replace('/', '-')}.pdf"
        return pdf_bytes, filename

    def _map_row(self, r: dict) -> OdooQuotationResponse:
        return OdooQuotationResponse(
            id=r["id"],
            name=odoo_str(r.get("name")),
            partner_id=odoo_m2o_id(r.get("partner_id")),
            partner_name=odoo_m2o_name(r.get("partner_id")),
            date_order=odoo_date(r.get("date_order")),
            amount_total=odoo_dec(r.get("amount_total")),
            currency=odoo_m2o_name(r.get("currency_id")) or "DOP",
            state=odoo_str(r.get("state")),
            user_id=odoo_m2o_id(r.get("user_id")),
            salesperson_name=odoo_m2o_name_opt(r.get("user_id")),
            company_id=odoo_m2o_id(r.get("company_id")),
            company_name=odoo_m2o_name_opt(r.get("company_id")),
            validity_date=odoo_date(r.get("validity_date")),
        )

    @staticmethod
    def _map_line(r: dict, *, tax_names: list[str] | None = None) -> OdooQuotationLineResponse:
        return OdooQuotationLineResponse(
            product_id=odoo_m2o_id(r.get("product_id")),
            product_name=odoo_m2o_name(r.get("product_id")) or odoo_str(r.get("name")),
            description=odoo_str(r.get("name")),
            quantity=odoo_float(r.get("product_uom_qty")),
            price_unit=odoo_dec(r.get("price_unit")),
            discount=odoo_float(r.get("discount")),
            subtotal=odoo_dec(r.get("price_subtotal")),
            taxes=tax_names or [],
        )
