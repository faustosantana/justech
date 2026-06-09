"""Consultas inteligentes Odoo — reglas, sin escritura."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.odoo import OdooQueryResponse
from app.services.odoo_service import OdooService


class OdooQueryService:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ):
        self.odoo = OdooService(db, tenant_id, user_id=user_id)

    async def _resolve_partner_id(self, name: str | None) -> int | None:
        if not name:
            return None
        customers = await self.odoo.list_customers(search=name, limit=1)
        if customers.items:
            return customers.items[0].id
        return None

    async def answer(self, question: str) -> OdooQueryResponse:
        q = question.strip()
        if not q:
            return OdooQueryResponse(
                question=q,
                answer="Escribe una pregunta sobre clientes, productos, precios o facturas.",
                query_type="empty",
            )

        health = await self.odoo.health()
        if not health.connected:
            return OdooQueryResponse(
                question=q,
                answer="Odoo no conectado. Configura ODOO_URL, ODOO_DB, ODOO_USERNAME y ODOO_API_KEY.",
                query_type="not_connected",
            )

        lowered = q.lower()
        partner = self._extract_entity(q, r"(?:a|al cliente|cliente)\s+([A-Za-zÁÉÍÓÚáéíóúñÑ0-9 .&-]+)")
        product = self._extract_entity(
            q,
            r"(?:art[ií]culo|producto)\s+([A-Za-zÁÉÍÓÚáéíóúñÑ0-9 .&-]+)",
        ) or self._extract_entity(q, r"vendi[oó]\s+(?:el |la )?([A-Za-zÁÉÍÓÚáéíóúñÑ0-9 .&-]+?)\s+a")

        if any(k in lowered for k in ("último precio", "ultimo precio")):
            result = await self.odoo.last_price(partner_name=partner, product_name=product)
            if not result.unit_price:
                return OdooQueryResponse(
                    question=q,
                    answer="No encontré ventas previas con esos criterios.",
                    query_type="last_price",
                )
            answer = (
                f"Último precio vendido: {result.unit_price} "
                f"({result.product_name or 'producto'} → {result.partner_name or 'cliente'}, "
                f"pedido {result.order_name or 'N/A'}, {result.order_date or ''})."
            )
            if result.min_price and result.max_price:
                answer += f" Rango: {result.min_price} — {result.max_price}."
            if result.average_price:
                answer += f" Precio promedio histórico: {result.average_price:.2f} ({result.sales_count} ventas)."
            return OdooQueryResponse(
                question=q,
                answer=answer,
                data=result.model_dump(mode="json"),
                query_type="last_price",
            )

        if "promedio" in lowered and ("precio" in lowered or "vendid" in lowered):
            result = await self.odoo.last_price(partner_name=partner, product_name=product)
            if not result.average_price:
                return OdooQueryResponse(
                    question=q,
                    answer="Sin historial de ventas para calcular promedio.",
                    query_type="average_price",
                )
            return OdooQueryResponse(
                question=q,
                answer=f"Precio promedio vendido: {result.average_price:.2f} en {result.sales_count} ventas.",
                data=result.model_dump(mode="json"),
                query_type="average_price",
            )

        if any(k in lowered for k in ("en cuánto", "en cuanto", "a cuánto", "a cuanto", "se le vendió", "se le vendio")):
            result = await self.odoo.last_price(partner_name=partner, product_name=product)
            if result.unit_price:
                return OdooQueryResponse(
                    question=q,
                    answer=(
                        f"Se vendió a {result.partner_name or partner or 'el cliente'} "
                        f"por {result.unit_price} (pedido {result.order_name}, {result.order_date or ''})."
                    ),
                    data=result.model_dump(mode="json"),
                    query_type="sold_price",
                )
            return OdooQueryResponse(
                question=q,
                answer="No encontré ventas de ese artículo a ese cliente.",
                query_type="sold_price",
            )

        if "margen" in lowered:
            history = await self.odoo.sales_history(limit=20)
            with_margin = [h for h in history.items if h.margin_pct]
            if not with_margin:
                return OdooQueryResponse(
                    question=q,
                    answer="No hay datos de margen en ventas anteriores (requiere costo en líneas de venta).",
                    query_type="margin",
                )
            top = with_margin[0]
            return OdooQueryResponse(
                question=q,
                answer=f"Última venta con margen: {top.product_name} a {top.partner_name} — margen {top.margin_pct:.1f}% ({top.margin}).",
                data=top.model_dump(mode="json"),
                query_type="margin",
            )

        if any(k in lowered for k in ("facturas vencidas", "vencidas", "vencida")):
            partner_id = await self._resolve_partner_id(partner)
            invoices = await self.odoo.overdue_invoices(partner_id=partner_id, limit=10)
            if not invoices.items:
                return OdooQueryResponse(
                    question=q,
                    answer=f"{'El cliente ' + partner if partner else 'No hay'} facturas vencidas pendientes.",
                    query_type="overdue_invoices",
                )
            lines = [f"{i.name}: {i.amount_residual} (vence {i.due_date})" for i in invoices.items[:5]]
            return OdooQueryResponse(
                question=q,
                answer=f"Facturas vencidas ({invoices.total}): " + "; ".join(lines),
                data={"invoices": [i.model_dump(mode="json") for i in invoices.items]},
                query_type="overdue_invoices",
            )

        if any(k in lowered for k in ("cotizaciones pendientes", "cotizacion pendiente", "cotizaciones")):
            partner_id = await self._resolve_partner_id(partner)
            quotes = await self.odoo.list_quotations(partner_id=partner_id, limit=10)
            if not quotes.items:
                return OdooQueryResponse(
                    question=q,
                    answer=f"Sin cotizaciones pendientes{' para ' + partner if partner else ''}.",
                    query_type="quotations",
                )
            lines = [f"{q2.name}: {q2.amount_total} ({q2.state})" for q2 in quotes.items[:5]]
            return OdooQueryResponse(
                question=q,
                answer="Cotizaciones pendientes: " + "; ".join(lines),
                data={"quotations": [item.model_dump(mode="json") for item in quotes.items]},
                query_type="quotations",
            )

        if any(k in lowered for k in ("qué cliente compró", "que cliente compro", "quién compró", "quien compro")):
            product_name = product or self._extract_entity(q, r"producto\s+([A-Za-zÁÉÍÓÚáéíóúñÑ0-9 .&-]+)")
            history = await self.odoo.sales_history(limit=50)
            if product_name:
                filtered = [h for h in history.items if product_name.lower() in h.product_name.lower()]
            else:
                filtered = list(history.items)
            if not filtered:
                return OdooQueryResponse(
                    question=q,
                    answer="No hay clientes registrados que hayan comprado ese producto.",
                    query_type="buyers",
                )
            clients = list(dict.fromkeys(h.partner_name for h in filtered))
            return OdooQueryResponse(
                question=q,
                answer=f"Clientes que compraron el producto: {', '.join(clients[:10])}.",
                data={"clients": clients},
                query_type="buyers",
            )

        if any(k in lowered for k in ("precio debo mantener", "precio recomendado", "qué precio")):
            result = await self.odoo.last_price(partner_name=partner, product_name=product)
            if result.average_price:
                return OdooQueryResponse(
                    question=q,
                    answer=f"Mantener cerca de {result.average_price:.2f} (promedio histórico). Último: {result.unit_price}.",
                    data=result.model_dump(mode="json"),
                    query_type="price_recommendation",
                )
            return OdooQueryResponse(
                question=q,
                answer="Sin historial suficiente para recomendar precio.",
                query_type="price_recommendation",
            )

        return OdooQueryResponse(
            question=q,
            answer=(
                "Puedo responder sobre: último precio vendido, precio promedio, ventas a un cliente, "
                "facturas vencidas, cotizaciones pendientes, margen y clientes que compraron un producto."
            ),
            query_type="help",
        )

    @staticmethod
    def _extract_entity(text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None
        value = match.group(1).strip().rstrip("?.")
        return value if len(value) > 2 else None
