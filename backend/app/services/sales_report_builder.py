"""Construcción de reportes estructurados de ventas para el Assistant."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.schemas.odoo import OdooSaleHistoryItem
from app.services.assistant_actions import table_row

MESES_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

WARNING_DEFAULT = "La clasificación se hizo por nombre del producto en Odoo."


def _fmt_money(value: Decimal | float) -> str:
    return f"{float(value):,.2f}"


def _parse_date_parts(date_str: str | None) -> tuple[int, int, int] | None:
    if not date_str:
        return None
    raw = str(date_str)[:10]
    try:
        y, m, d = raw.split("-")
        return int(d), int(m), int(y)
    except ValueError:
        return None


def format_date_es(date_str: str | None) -> str:
    parts = _parse_date_parts(date_str)
    if not parts:
        return "—"
    d, m, y = parts
    if 1 <= m <= 12:
        return f"{d} de {MESES_ES[m - 1]} de {y}"
    return str(date_str)


def period_range_es(lines: list[OdooSaleHistoryItem]) -> str:
    dates = sorted(ln.order_date for ln in lines if ln.order_date)
    if not dates:
        return "todo el histórico disponible"
    if dates[0] == dates[-1]:
        return format_date_es(dates[0])
    return f"entre el {format_date_es(dates[0])} y el {format_date_es(dates[-1])}"


def build_sales_report(
    *,
    lines: list[OdooSaleHistoryItem],
    product_label: str,
    company_name: str | None,
    customer_label: str | None = None,
    intent: str,
) -> dict:
    total_qty = sum(ln.quantity for ln in lines)
    total_amount = sum((ln.subtotal for ln in lines), Decimal("0"))
    orders = {ln.order_name for ln in lines if ln.order_name}
    customers = {ln.partner_name for ln in lines if ln.partner_name}
    period = period_range_es(lines)

    by_product: dict[str, dict] = defaultdict(
        lambda: {"qty": 0.0, "amount": Decimal("0"), "prices": [], "last_date": None, "product_id": None}
    )
    by_customer: dict[str, dict] = defaultdict(
        lambda: {"qty": 0.0, "amount": Decimal("0"), "last_date": None, "partner_id": None}
    )

    for ln in lines:
        pname = ln.product_name or "—"
        bp = by_product[pname]
        bp["qty"] += ln.quantity
        bp["amount"] += ln.subtotal
        if ln.product_id:
            bp["product_id"] = ln.product_id
        if ln.unit_price:
            bp["prices"].append(float(ln.unit_price))
        if ln.order_date and (not bp["last_date"] or ln.order_date > bp["last_date"]):
            bp["last_date"] = ln.order_date

        cname = ln.partner_name or "—"
        bc = by_customer[cname]
        bc["qty"] += ln.quantity
        bc["amount"] += ln.subtotal
        if ln.partner_id:
            bc["partner_id"] = ln.partner_id
        if ln.order_date and (not bc["last_date"] or ln.order_date > bc["last_date"]):
            bc["last_date"] = ln.order_date

    top_product = max(by_product.items(), key=lambda x: x[1]["qty"])[0] if by_product else "—"
    sorted_lines = sorted(lines, key=lambda x: x.order_date or "", reverse=True)
    last_sale = sorted_lines[0] if sorted_lines else None
    avg_price = float(total_amount / Decimal(str(total_qty))) if total_qty else 0.0

    summary = _executive_summary(
        total_qty=total_qty,
        product_label=product_label,
        period=period,
        order_count=len(orders),
        line_count=len(lines),
        customer_label=customer_label,
        total_amount=total_amount,
        intent=intent,
    )

    metrics = [
        {"label": "Unidades vendidas", "value": f"{total_qty:g}"},
        {"label": "Monto total vendido", "value": _fmt_money(total_amount)},
        {"label": "Pedidos", "value": str(len(orders))},
        {"label": "Clientes únicos", "value": str(len(customers))},
        {"label": "Producto más vendido", "value": top_product},
        {
            "label": "Última venta",
            "value": (
                f"{format_date_es(last_sale.order_date)} — {last_sale.product_name}"
                if last_sale
                else "—"
            ),
        },
        {"label": "Precio promedio", "value": _fmt_money(avg_price) if avg_price else "—"},
        {"label": "Empresa", "value": company_name or "—"},
        {"label": "Período", "value": period},
    ]

    product_rows = []
    for name, agg in sorted(by_product.items(), key=lambda x: x[1]["qty"], reverse=True)[:15]:
        avg = sum(agg["prices"]) / len(agg["prices"]) if agg["prices"] else 0
        product_rows.append(
            table_row(
                [
                    name,
                    f"{agg['qty']:g}",
                    _fmt_money(agg["amount"]),
                    _fmt_money(avg) if avg else "—",
                    format_date_es(agg["last_date"]),
                ],
                entity_type="product" if agg.get("product_id") else None,
                entity_id=agg.get("product_id"),
            )
        )

    customer_rows = []
    for name, agg in sorted(by_customer.items(), key=lambda x: x[1]["amount"], reverse=True)[:15]:
        customer_rows.append(
            table_row(
                [
                    name,
                    f"{agg['qty']:g}",
                    _fmt_money(agg["amount"]),
                    format_date_es(agg["last_date"]),
                ],
                entity_type="customer" if agg.get("partner_id") else None,
                entity_id=agg.get("partner_id"),
            )
        )

    recent_rows = []
    for ln in sorted_lines[:12]:
        recent_rows.append(
            table_row(
                [
                    format_date_es(ln.order_date),
                    ln.partner_name or "—",
                    ln.product_name or "—",
                    f"{ln.quantity:g}",
                    _fmt_money(ln.unit_price),
                    _fmt_money(ln.subtotal),
                    ln.order_name or "—",
                ],
                entity_type="product" if ln.product_id else None,
                entity_id=ln.product_id,
            )
        )

    return {
        "type": "sales_report",
        "summary": summary,
        "metrics": metrics,
        "tables": [
            {
                "title": "Productos vendidos",
                "columns": ["Producto", "Cantidad", "Monto vendido", "Precio promedio", "Última fecha"],
                "rows": product_rows,
            },
            {
                "title": "Clientes compradores",
                "columns": ["Cliente", "Cantidad comprada", "Monto vendido", "Última compra"],
                "rows": customer_rows,
            },
            {
                "title": "Últimas ventas",
                "columns": ["Fecha", "Cliente", "Producto", "Cantidad", "Precio unitario", "Total", "Pedido"],
                "rows": recent_rows,
            },
        ],
        "warnings": [WARNING_DEFAULT],
    }


def _executive_summary(
    *,
    total_qty: float,
    product_label: str,
    period: str,
    order_count: int,
    line_count: int,
    customer_label: str | None,
    total_amount: Decimal,
    intent: str,
) -> str:
    noun = product_label.strip()
    if customer_label:
        if intent == "customer_sales_amount_query":
            return (
                f"Vendimos a {customer_label} por {_fmt_money(total_amount)} "
                f"({total_qty:g} unidades, {order_count} pedidos, {period})."
            )
        if intent == "customer_sales_list_query":
            return (
                f"Registramos {line_count} líneas de venta a {customer_label} "
                f"({total_qty:g} unidades, {order_count} pedidos, {period})."
            )
        return (
            f"Vendimos {total_qty:g} unidades de {noun} a {customer_label}, "
            f"por {_fmt_money(total_amount)}, en {order_count} pedidos ({period})."
        )

    if intent == "sales_amount_query":
        return (
            f"Vendimos {_fmt_money(total_amount)} en {noun} "
            f"({total_qty:g} unidades, {order_count} pedidos, {period})."
        )
    if intent == "buyers_query":
        return (
            f"Hay ventas de {noun} en {order_count} pedidos y {line_count} líneas ({period})."
        )

    return (
        f"Vendimos {total_qty:g} {noun} {period}, "
        f"en {order_count} pedidos y {line_count} líneas de venta."
    )


def empty_report_message(
    *,
    product_label: str | None,
    customer_label: str | None,
) -> str:
    if product_label and customer_label:
        return f"No encontré ventas de {product_label} a {customer_label} en el histórico disponible."
    if customer_label:
        return f"No encontré ventas registradas a {customer_label} en el histórico disponible."
    if product_label:
        return f"No encontré ventas de {product_label} en el histórico disponible."
    return "No encontré ventas que coincidan con la consulta."
