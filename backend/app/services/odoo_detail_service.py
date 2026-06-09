"""Vistas de detalle Odoo — read-only."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.schemas.odoo import (
    OdooCustomerDetailResponse,
    OdooInvoiceDetailResponse,
    OdooInvoiceLineResponse,
    OdooInvoiceResponse,
    OdooOpportunityResponse,
    OdooProductBuyerItem,
    OdooProductDetailResponse,
    OdooProductPurchaseItem,
    OdooProductPurchasedItem,
    OdooProductSuppliedItem,
    OdooProjectResponse,
    OdooPurchaseHistoryItem,
    OdooQuotationResponse,
    OdooSaleHistoryItem,
    OdooVendorDetailResponse,
)
from app.services.odoo_service import OdooService
from app.services.odoo_url_helper import build_odoo_url
from integrations.odoo.normalize import (
    odoo_date,
    odoo_dec,
    odoo_float,
    odoo_m2m_ids,
    odoo_m2o_id,
    odoo_m2o_name,
    odoo_m2o_name_opt,
    odoo_str,
    odoo_str_opt,
)


def _odoo_form_url(model: str, record_id: int) -> str | None:
    return build_odoo_url(model, record_id)


def _line_margin(price: Decimal, cost: Decimal | None) -> tuple[Decimal | None, float | None]:
    if not cost or cost <= 0:
        return None, None
    margin = price - cost
    pct = float(margin / price * 100) if price else None
    return margin, pct


class OdooDetailService:
    def __init__(self, odoo: OdooService):
        self.odoo = odoo

    async def get_customer_detail(self, partner_id: int) -> OdooCustomerDetailResponse:
        client = await self.odoo._get_client()
        if not client.is_configured:
            return OdooCustomerDetailResponse(
                id=partner_id, name="", connected=False, message="Odoo no conectado"
            )

        rows = await client.search_read(
            "res.partner",
            [("id", "=", partner_id)],
            ["name", "email", "phone", "vat", "city", "user_id", "company_id"],
            limit=1,
        )
        if not rows:
            return OdooCustomerDetailResponse(
                id=partner_id, name="", connected=True, message="Cliente no encontrado"
            )
        p = rows[0]

        open_inv = await self.odoo.open_invoices(partner_id=partner_id, limit=20)
        overdue_inv = await self.odoo.overdue_invoices(partner_id=partner_id, limit=20)
        quotes = await self.odoo.list_quotations(partner_id=partner_id, limit=20)
        opps = await self.odoo.list_opportunities(partner_id=partner_id, limit=20)
        projects = await self.odoo.list_projects(partner_id=partner_id, limit=20)
        sales = await self.odoo.sales_history(partner_id=partner_id, limit=50)

        product_agg: dict[int, dict] = {}
        total_sales = Decimal("0")
        for s in sales.items:
            if not isinstance(s, OdooSaleHistoryItem):
                continue
            total_sales += s.subtotal
            pid = s.product_id or 0
            key = pid if pid else hash(s.product_name)
            if key not in product_agg:
                product_agg[key] = {
                    "product_id": pid or key,
                    "name": s.product_name,
                    "prices": [],
                    "qty": 0.0,
                }
            product_agg[key]["prices"].append(s.unit_price)
            product_agg[key]["qty"] += s.quantity

        products_purchased = sorted(
            [
                OdooProductPurchasedItem(
                    product_id=v["product_id"],
                    product_name=v["name"],
                    last_price=v["prices"][0] if v["prices"] else None,
                    average_price=sum(v["prices"]) / len(v["prices"]) if v["prices"] else None,
                    total_qty=v["qty"],
                    sales_count=len(v["prices"]),
                )
                for v in product_agg.values()
            ],
            key=lambda x: x.total_qty,
            reverse=True,
        )

        total_due = sum(
            (inv.amount_residual for inv in open_inv.items if isinstance(inv, OdooInvoiceResponse)),
            Decimal("0"),
        )
        total_overdue = sum(
            (inv.amount_residual for inv in overdue_inv.items if isinstance(inv, OdooInvoiceResponse)),
            Decimal("0"),
        )

        return OdooCustomerDetailResponse(
            id=partner_id,
            name=odoo_str(p.get("name")),
            email=odoo_str_opt(p.get("email")),
            phone=odoo_str_opt(p.get("phone")),
            vat=odoo_str_opt(p.get("vat")),
            city=odoo_str_opt(p.get("city")),
            salesperson=odoo_m2o_name_opt(p.get("user_id")),
            company_name=odoo_m2o_name_opt(p.get("company_id")),
            open_invoices=[i for i in open_inv.items if isinstance(i, OdooInvoiceResponse)],
            overdue_invoices=[i for i in overdue_inv.items if isinstance(i, OdooInvoiceResponse)],
            quotations=[i for i in quotes.items if isinstance(i, OdooQuotationResponse)],
            opportunities=[i for i in opps.items if isinstance(i, OdooOpportunityResponse)],
            projects=[i for i in projects.items if isinstance(i, OdooProjectResponse)],
            sales_history=[i for i in sales.items if isinstance(i, OdooSaleHistoryItem)],
            products_purchased=products_purchased,
            total_sales_historical=total_sales,
            total_due=total_due,
            total_overdue=total_overdue,
        )

    async def get_product_detail(self, product_id: int) -> OdooProductDetailResponse:
        client = await self.odoo._get_client()
        if not client.is_configured:
            return OdooProductDetailResponse(
                id=product_id, name="", connected=False, message="Odoo no conectado"
            )

        domain = self.odoo._domain("product.product", [("id", "=", product_id)], shared=True)
        rows = await client.search_read(
            "product.product",
            domain,
            ["name", "default_code", "list_price", "standard_price", "qty_available", "uom_id", "categ_id"],
            limit=1,
        )
        if not rows:
            return OdooProductDetailResponse(
                id=product_id, name="", connected=True, message="Producto no encontrado"
            )
        p = rows[0]
        sales = await self.odoo.sales_history(product_id=product_id, limit=50)
        purchases = await self.odoo.product_purchase_history(product_id=product_id, limit=50)
        last_price_res = await self.odoo.last_price(product_id=product_id)

        by_partner: dict[int, dict] = {}
        for s in sales.items:
            if not isinstance(s, OdooSaleHistoryItem):
                continue
            pid = s.partner_id or hash(s.partner_name)
            if pid not in by_partner:
                by_partner[pid] = {
                    "partner_id": s.partner_id or pid,
                    "name": s.partner_name,
                    "prices": [],
                }
            by_partner[pid]["prices"].append(s.unit_price)

        buyers = sorted(
            [
                OdooProductBuyerItem(
                    partner_id=v["partner_id"],
                    partner_name=v["name"],
                    last_price=v["prices"][0],
                    average_price=sum(v["prices"]) / len(v["prices"]),
                    sales_count=len(v["prices"]),
                )
                for v in by_partner.values()
            ],
            key=lambda x: x.sales_count,
            reverse=True,
        )

        purchase_items = [
            OdooProductPurchaseItem(
                id=ph.id,
                vendor_name=ph.partner_name,
                order_name=ph.order_name,
                order_date=ph.order_date,
                quantity=ph.quantity,
                unit_price=ph.unit_price,
                subtotal=ph.subtotal,
            )
            for ph in purchases.items
            if isinstance(ph, OdooPurchaseHistoryItem)
        ]

        std_price = odoo_dec(p.get("standard_price"))
        last_p = last_price_res.unit_price
        est_margin = None
        if last_p and std_price and std_price > 0 and last_p > 0:
            est_margin = float((last_p - std_price) / last_p * 100)

        return OdooProductDetailResponse(
            id=product_id,
            name=odoo_str(p.get("name")),
            default_code=odoo_str_opt(p.get("default_code")),
            category=odoo_m2o_name_opt(p.get("categ_id")),
            list_price=odoo_dec(p.get("list_price")),
            standard_price=std_price,
            qty_available=odoo_float(p.get("qty_available")),
            uom=odoo_m2o_name_opt(p.get("uom_id")),
            sales_history=[i for i in sales.items if isinstance(i, OdooSaleHistoryItem)],
            purchase_history=purchase_items,
            buyers=buyers,
            last_price=last_p,
            average_price=last_price_res.average_price,
            min_price=last_price_res.min_price,
            max_price=last_price_res.max_price,
            estimated_margin_pct=est_margin,
        )

    async def get_invoice_detail(self, invoice_id: int) -> OdooInvoiceDetailResponse:
        client = await self.odoo._get_client()
        if not client.is_configured:
            return OdooInvoiceDetailResponse(
                id=invoice_id,
                name="",
                partner_id=0,
                partner_name="",
                amount_total=Decimal("0"),
                amount_residual=Decimal("0"),
                state="",
                connected=False,
                message="Odoo no conectado",
            )

        domain = self.odoo._domain("account.move", [("id", "=", invoice_id), ("move_type", "=", "out_invoice")])
        rows = await client.search_read(
            "account.move",
            domain,
            [
                "name", "partner_id", "invoice_date", "invoice_date_due",
                "amount_total", "amount_residual", "currency_id", "state", "payment_state",
            ],
            limit=1,
        )
        if not rows:
            return OdooInvoiceDetailResponse(
                id=invoice_id,
                name="",
                partner_id=0,
                partner_name="",
                amount_total=Decimal("0"),
                amount_residual=Decimal("0"),
                state="",
                connected=True,
                message="Factura no encontrada",
            )
        inv = rows[0]
        partner_id = odoo_m2o_id(inv.get("partner_id")) or 0

        line_domain = self.odoo._domain(
            "account.move.line",
            [("move_id", "=", invoice_id), ("display_type", "=", "product")],
        )
        line_rows = await client.search_read(
            "account.move.line",
            line_domain,
            ["name", "product_id", "quantity", "price_unit", "discount", "price_subtotal", "tax_ids"],
            limit=200,
            order="sequence asc",
        )

        lines: list[OdooInvoiceLineResponse] = []
        total_margin = Decimal("0")
        margin_count = 0
        for lr in line_rows:
            product_id = odoo_m2o_id(lr.get("product_id"))
            cost: Decimal | None = None
            if product_id:
                prod = await client.search_read(
                    "product.product",
                    [("id", "=", product_id)],
                    ["standard_price"],
                    limit=1,
                )
                if prod:
                    cost = odoo_dec(prod[0].get("standard_price"))
            unit = odoo_dec(lr.get("price_unit"))
            margin, margin_pct = _line_margin(unit, cost)
            if margin:
                total_margin += margin * Decimal(str(odoo_float(lr.get("quantity"))))
                margin_count += 1
            tax_ids = odoo_m2m_ids(lr.get("tax_ids"))
            tax_names = None
            if tax_ids:
                taxes = await client.search_read(
                    "account.tax", [("id", "in", tax_ids)], ["name"], limit=10
                )
                tax_names = ", ".join(odoo_str(t.get("name")) for t in taxes)
            lines.append(
                OdooInvoiceLineResponse(
                    id=lr["id"],
                    product_id=product_id,
                    product_name=odoo_m2o_name(lr.get("product_id")) or odoo_str(lr.get("name")),
                    quantity=odoo_float(lr.get("quantity")),
                    unit_price=unit,
                    discount=odoo_float(lr.get("discount")),
                    tax_names=tax_names,
                    subtotal=odoo_dec(lr.get("price_subtotal")),
                    cost=cost,
                    margin=margin,
                    margin_pct=margin_pct,
                )
            )

        amount_total = odoo_dec(inv.get("amount_total"))
        inv_margin_pct = float(total_margin / amount_total * 100) if amount_total and margin_count else None

        return OdooInvoiceDetailResponse(
            id=invoice_id,
            name=odoo_str(inv.get("name")),
            partner_id=partner_id,
            partner_name=odoo_m2o_name(inv.get("partner_id")),
            invoice_date=odoo_date(inv.get("invoice_date")),
            due_date=odoo_date(inv.get("invoice_date_due")),
            amount_total=amount_total,
            amount_residual=odoo_dec(inv.get("amount_residual")),
            currency=odoo_m2o_name(inv.get("currency_id")) or "DOP",
            state=odoo_str(inv.get("state")),
            payment_state=odoo_str_opt(inv.get("payment_state")),
            lines=lines,
            total_margin=total_margin if margin_count else None,
            margin_pct=inv_margin_pct,
            odoo_url=_odoo_form_url("account.move", invoice_id),
        )

    async def get_vendor_detail(self, vendor_id: int) -> OdooVendorDetailResponse:
        client = await self.odoo._get_client()
        if not client.is_configured:
            return OdooVendorDetailResponse(
                id=vendor_id, name="", connected=False, message="Odoo no conectado"
            )

        rows = await client.search_read(
            "res.partner",
            [("id", "=", vendor_id)],
            ["name", "email", "phone", "vat", "city", "supplier_rank"],
            limit=1,
        )
        if not rows:
            return OdooVendorDetailResponse(
                id=vendor_id, name="", connected=True, message="Proveedor no encontrado"
            )
        v = rows[0]
        purchases = await self.odoo.purchase_history(partner_id=vendor_id, limit=50)

        po_domain = self.odoo._domain(
            "purchase.order",
            [("partner_id", "=", vendor_id), ("state", "in", ["purchase", "done"])],
        )
        try:
            po_rows = await client.search_read(
                "purchase.order",
                po_domain,
                ["name", "date_order", "amount_total", "state"],
                limit=20,
                order="date_order desc",
            )
        except Exception:
            po_rows = []

        ph_items = [i for i in purchases.items if isinstance(i, OdooPurchaseHistoryItem)]
        product_agg: dict[str, dict] = {}
        total_value = Decimal("0")
        for ph in ph_items:
            total_value += ph.subtotal
            key = ph.product_name
            if key not in product_agg:
                product_agg[key] = {"name": key, "costs": [], "qty": 0.0}
            product_agg[key]["costs"].append(ph.unit_price)
            product_agg[key]["qty"] += ph.quantity

        products_supplied = sorted(
            [
                OdooProductSuppliedItem(
                    product_id=i,
                    product_name=v["name"],
                    last_cost=v["costs"][0] if v["costs"] else None,
                    average_cost=sum(v["costs"]) / len(v["costs"]) if v["costs"] else None,
                    total_qty=v["qty"],
                    purchase_count=len(v["costs"]),
                )
                for i, (_, v) in enumerate(product_agg.items(), 1)
            ],
            key=lambda x: x.total_qty,
            reverse=True,
        )

        return OdooVendorDetailResponse(
            id=vendor_id,
            name=odoo_str(v.get("name")),
            email=odoo_str_opt(v.get("email")),
            phone=odoo_str_opt(v.get("phone")),
            vat=odoo_str_opt(v.get("vat")),
            city=odoo_str_opt(v.get("city")),
            purchase_history=ph_items,
            products_supplied=products_supplied,
            total_purchase_value=total_value,
            purchase_orders=[
                {
                    "name": odoo_str(r.get("name")),
                    "date": odoo_date(r.get("date_order")) or "",
                    "amount_total": str(odoo_dec(r.get("amount_total"))),
                    "state": odoo_str(r.get("state")),
                }
                for r in po_rows
            ],
        )
