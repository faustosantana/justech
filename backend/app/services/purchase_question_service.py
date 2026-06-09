"""Consultas de compras Odoo — read-only."""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.assistant import AssistantLink, AssistantQueryResponse
from app.schemas.odoo import OdooPurchaseHistoryItem
from app.services.assistant_actions import table_row
from app.services.business_answer_builder import build_business_answer, links_to_dict, not_found_summary
from app.services.business_intent_router import ParsedBusinessQuestion
from app.services.business_terms import matches_product_name
from app.services.odoo_service import OdooService
from app.services.sales_report_builder import format_date_es, period_range_es


class PurchaseQuestionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.odoo = OdooService(db, tenant_id, user_id=user_id)

    async def answer(
        self,
        question: str,
        parsed: ParsedBusinessQuestion,
    ) -> AssistantQueryResponse | None:
        health = await self.odoo.health()
        if not health.connected:
            return AssistantQueryResponse(
                question=question,
                answer="Odoo no está conectado. No puedo consultar compras.",
                sources=["odoo"],
                query_type="purchase_query",
            )

        lines: list[OdooPurchaseHistoryItem] = []
        vendor_display = parsed.supplier_label

        if parsed.supplier_label:
            lines, resolved = await self.odoo.search_purchases_by_vendor_name(parsed.supplier_label, limit=500)
            if resolved:
                vendor_display = resolved
            if parsed.product_terms:
                lines = [ln for ln in lines if matches_product_name(ln.product_name, parsed.product_terms)]
        elif parsed.product_terms:
            resp = await self.odoo.search_purchases_by_product_terms(parsed.product_terms, limit=500)
            lines = [
                ln for ln in resp.items
                if isinstance(ln, OdooPurchaseHistoryItem)
                and matches_product_name(ln.product_name, parsed.product_terms)
            ]

        entity = parsed.product_label or vendor_display or "la consulta"
        if not lines:
            return AssistantQueryResponse(
                question=question,
                answer=not_found_summary(entity, "odoo", kind="compras"),
                sources=["odoo"],
                query_type="purchase_query",
            )

        structured = self._build_report(lines, parsed, health.active_company_name, vendor_display)
        links = [
            AssistantLink(label=ln.partner_name, url="/odoo", type="vendor")
            for ln in lines[:3]
            if ln.partner_name
        ]
        structured["links"] = links_to_dict(links)

        return AssistantQueryResponse(
            question=question,
            answer=structured["summary"],
            sources=["odoo"],
            query_type="purchase_query",
            structured_data=structured,
            links=links,
        )

    def _build_report(
        self,
        lines: list[OdooPurchaseHistoryItem],
        parsed: ParsedBusinessQuestion,
        company_name: str | None,
        vendor_display: str | None,
    ) -> dict:
        total_qty = sum(ln.quantity for ln in lines)
        total_amount = sum((ln.subtotal for ln in lines), Decimal("0"))
        orders = {ln.order_name for ln in lines if ln.order_name}
        vendors = {ln.partner_name for ln in lines if ln.partner_name}
        period = period_range_es_from_purchases(lines)
        label = parsed.product_label or vendor_display or "compras"

        by_vendor: dict[str, dict] = defaultdict(lambda: {"qty": 0.0, "amount": Decimal("0"), "last_date": None})
        by_product: dict[str, dict] = defaultdict(lambda: {"qty": 0.0, "amount": Decimal("0"), "prices": [], "last_date": None})

        for ln in lines:
            v = by_vendor[ln.partner_name or "—"]
            v["qty"] += ln.quantity
            v["amount"] += ln.subtotal
            if ln.order_date and (not v["last_date"] or ln.order_date > v["last_date"]):
                v["last_date"] = ln.order_date

            p = by_product[ln.product_name or "—"]
            p["qty"] += ln.quantity
            p["amount"] += ln.subtotal
            if ln.unit_price:
                p["prices"].append(float(ln.unit_price))
            if ln.order_date and (not p["last_date"] or ln.order_date > p["last_date"]):
                p["last_date"] = ln.order_date

        sorted_lines = sorted(lines, key=lambda x: x.order_date or "", reverse=True)
        last = sorted_lines[0] if sorted_lines else None
        avg_price = float(total_amount / Decimal(str(total_qty))) if total_qty else 0.0
        top_vendor = max(by_vendor.items(), key=lambda x: x[1]["amount"])[0] if by_vendor else "—"

        summary = (
            f"Encontré {total_qty:g} unidades compradas de {label} "
            f"({total_amount:,.2f}, {len(orders)} pedidos, {period})."
        )

        metrics = [
            {"label": "Unidades compradas", "value": f"{total_qty:g}"},
            {"label": "Monto total", "value": f"{float(total_amount):,.2f}"},
            {"label": "Pedidos", "value": str(len(orders))},
            {"label": "Proveedores", "value": str(len(vendors))},
            {"label": "Proveedor principal", "value": top_vendor},
            {
                "label": "Última compra",
                "value": (
                    f"{format_date_es(last.order_date)} — {last.product_name}"
                    if last
                    else "—"
                ),
            },
            {"label": "Costo promedio", "value": f"{avg_price:,.2f}" if avg_price else "—"},
            {"label": "Empresa", "value": company_name or "—"},
            {"label": "Período", "value": period},
        ]

        product_rows = []
        for name, agg in sorted(by_product.items(), key=lambda x: x[1]["qty"], reverse=True)[:12]:
            avg = sum(agg["prices"]) / len(agg["prices"]) if agg["prices"] else 0
            product_rows.append([
                name,
                f"{agg['qty']:g}",
                f"{float(agg['amount']):,.2f}",
                f"{avg:,.2f}" if avg else "—",
                format_date_es(agg["last_date"]),
            ])

        vendor_rows = []
        for name, agg in sorted(by_vendor.items(), key=lambda x: x[1]["amount"], reverse=True)[:12]:
            vendor_rows.append([
                name,
                f"{agg['qty']:g}",
                f"{float(agg['amount']):,.2f}",
                format_date_es(agg["last_date"]),
            ])

        recent_rows = []
        for ln in sorted_lines[:10]:
            recent_rows.append([
                format_date_es(ln.order_date),
                ln.partner_name or "—",
                ln.product_name or "—",
                f"{ln.quantity:g}",
                f"{float(ln.unit_price):,.2f}",
                f"{float(ln.subtotal):,.2f}",
                ln.order_name or "—",
            ])

        return build_business_answer(
            intent="purchase_query",
            source="odoo",
            summary=summary,
            metrics=metrics,
            tables=[
                {
                    "title": "Productos comprados",
                    "columns": ["Producto", "Cantidad", "Monto", "Costo promedio", "Última compra"],
                    "rows": product_rows,
                },
                {
                    "title": "Proveedores",
                    "columns": ["Proveedor", "Cantidad", "Monto", "Última compra"],
                    "rows": vendor_rows,
                },
                {
                    "title": "Últimas compras",
                    "columns": ["Fecha", "Proveedor", "Producto", "Cantidad", "Costo unitario", "Total", "Pedido"],
                    "rows": recent_rows,
                },
            ],
            warnings=["Clasificación por nombre del producto en Odoo."],
        )


def period_range_es_from_purchases(lines: list[OdooPurchaseHistoryItem]) -> str:
    dates = sorted(ln.order_date for ln in lines if ln.order_date)
    if not dates:
        return "todo el histórico disponible"
    if dates[0] == dates[-1]:
        return format_date_es(dates[0])
    return f"entre el {format_date_es(dates[0])} y el {format_date_es(dates[-1])}"
