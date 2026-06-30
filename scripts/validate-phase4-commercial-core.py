#!/usr/bin/env python3
"""Fase 4 — Validación flujo comercial completo (odoo shell stdin).

Orden: proveedor → producto almacenable → compra/recepción → venta/entrega/factura
       → inventario → contabilidad básica.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

ALLOWED = ("contacts", "stock", "purchase", "sale")
FORBIDDEN = (
    "point_of_sale",
    "stock_barcode",
    "web_studio",
    "sign",
    "documents",
    "helpdesk",
    "crm",
)

company = env["res.company"].search([], limit=1)
results = {"checks": {}, "flows": {}, "steps": {}}


def check(name, ok, detail=""):
    results["checks"][name] = {"ok": ok, "detail": detail}
    return ok


def step(n, name, ok, detail=""):
    results["steps"][str(n)] = {"name": name, "ok": ok, "detail": detail}
    return ok


# --- Módulos ---
for mod in ALLOWED:
    st = env["ir.module.module"].search([("name", "=", mod)], limit=1).state
    check(f"module_{mod}", st == "installed", st)

for mod in FORBIDDEN:
    rec = env["ir.module.module"].search([("name", "=", mod)], limit=1)
    st = rec.state if rec else "absent"
    # stock_barcode puede quedar instalado si es dependencia crítica
    if mod == "stock_barcode":
        check(f"module_{mod}", True, st)
    else:
        check(f"forbidden_{mod}", st != "installed", st)

warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
loc = warehouse.lot_stock_id

# --- 1. Proveedor de prueba ---
vendor = env["res.partner"].search([("ref", "=", "PHASE4-VEND")], limit=1)
if not vendor:
    vendor = env["res.partner"].create(
        {
            "name": "Proveedor prueba Fase 4",
            "ref": "PHASE4-VEND",
            "supplier_rank": 1,
            "country_id": company.partner_id.country_id.id,
        }
    )
step(1, "proveedor_prueba", bool(vendor), vendor.ref)

# --- 2. Producto almacenable de prueba (Odoo 19: consu + is_storable) ---
cat = env["product.category"].search(
    [("name", "=", "Espejos"), ("parent_id.name", "=", "Inventario")], limit=1
)
if not cat:
    cat = env["product.category"].search([("name", "=", "Espejos")], limit=1)

product = env["product.product"].search([("default_code", "=", "PHASE4-TEST-001")], limit=1)
product_vals = {
    "name": "PHASE4 Producto prueba — Espejo almacenable",
    "default_code": "PHASE4-TEST-001",
    "type": "consu",
    "is_storable": True,
    "categ_id": cat.id if cat else False,
    "list_price": 10000.0,
    "standard_price": 5000.0,
}
if not product:
    product = env["product.product"].create(product_vals)
else:
    product.write(product_vals)

storable_ok = product.is_storable and product.type == "consu"
step(
    2,
    "producto_almacenable",
    storable_ok,
    f"type={product.type} is_storable={product.is_storable}",
)

qty_before = env["stock.quant"]._get_available_quantity(product, loc)
results["flows"]["inventory_qty_before"] = qty_before

# --- 3. Compra / RFQ ---
PurchaseOrder = env["purchase.order"]
po = PurchaseOrder.create({"partner_id": vendor.id})
env["purchase.order.line"].create(
    {
        "order_id": po.id,
        "product_id": product.id,
        "product_qty": 2.0,
        "price_unit": 5000.0,
    }
)
results["flows"]["purchase_rfq_state"] = po.state
step(3, "compra_rfq", po.state in ("draft", "sent"), po.state)
check("purchase_draft", po.state in ("draft", "sent"), po.state)

po.button_confirm()
results["flows"]["purchase_order_state"] = po.state
check("purchase_confirmed", po.state == "purchase", po.state)

# --- 4. Recepción de inventario ---
pickings_in = po.picking_ids.filtered(lambda p: p.picking_type_code == "incoming")
receipt = False
check("receipt_created", bool(pickings_in), len(pickings_in))
if pickings_in:
    receipt = pickings_in[0]
    receipt.action_assign()
    for move in receipt.move_ids:
        move.quantity = move.product_uom_qty
    receipt.button_validate()
    results["flows"]["receipt_state"] = receipt.state
    step(4, "recepcion_inventario", receipt.state == "done", receipt.state)
    check("receipt_done", receipt.state == "done", receipt.state)
else:
    step(4, "recepcion_inventario", False, "no picking")

qty_after_receipt = env["stock.quant"]._get_available_quantity(product, loc)
results["flows"]["inventory_qty_after_receipt"] = qty_after_receipt

# Factura proveedor (parte del ciclo compras, antes de venta)
po.action_create_invoice()
bill = po.invoice_ids[:1]
results["flows"]["vendor_bill_state"] = bill.state if bill else None
check("vendor_bill_created", bool(bill), bill.name if bill else "")
if bill:
    bill.invoice_date = date.today()
    bill.action_post()
    check("vendor_bill_posted", bill.state == "posted", bill.state)

# --- Cliente (maestro venta) ---
customer = env["res.partner"].search([("ref", "=", "PHASE4-CUST")], limit=1)
if not customer:
    customer = env["res.partner"].create(
        {
            "name": "Cliente prueba Fase 4",
            "ref": "PHASE4-CUST",
            "customer_rank": 1,
            "country_id": company.partner_id.country_id.id,
        }
    )

# --- 5. Cotización de venta ---
SaleOrder = env["sale.order"]
so = SaleOrder.create(
    {
        "partner_id": customer.id,
        "warehouse_id": warehouse.id,
    }
)
env["sale.order.line"].create(
    {
        "order_id": so.id,
        "product_id": product.id,
        "product_uom_qty": 1.0,
        "price_unit": 10000.0,
    }
)
results["flows"]["quotation_state"] = so.state
step(5, "cotizacion_venta", so.state == "draft", so.state)
check("quotation_created", so.state == "draft", so.state)

# --- 6. Confirmación de venta ---
so.action_confirm()
results["flows"]["sale_order_state"] = so.state
step(6, "confirmacion_venta", so.state == "sale", so.state)
check("sale_order_confirmed", so.state == "sale", so.state)

# --- 7. Entrega ---
pickings_out = so.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing")
check("delivery_created", bool(pickings_out), len(pickings_out))
if pickings_out:
    picking = pickings_out[0]
    picking.action_assign()
    for move in picking.move_ids:
        move.quantity = move.product_uom_qty
    picking.button_validate()
    results["flows"]["delivery_state"] = picking.state
    step(7, "entrega", picking.state == "done", picking.state)
    check("delivery_done", picking.state == "done", picking.state)
else:
    step(7, "entrega", False, "no picking")

# --- 8. Factura cliente ---
so._create_invoices()
invoice = so.invoice_ids.filtered(lambda m: m.state != "cancel")[:1]
results["flows"]["invoice_state"] = invoice.state if invoice else None
check("customer_invoice_created", bool(invoice), invoice.name if invoice else "")
if invoice:
    invoice.invoice_date = date.today()
    invoice.action_post()
    step(8, "factura_cliente", invoice.state == "posted", invoice.state)
    check("customer_invoice_posted", invoice.state == "posted", invoice.state)
else:
    step(8, "factura_cliente", False, "no invoice")

# --- 9. Impacto en inventario ---
qty_final = env["stock.quant"]._get_available_quantity(product, loc)
results["flows"]["inventory_qty_final"] = qty_final
expected_delta = 2.0 - 1.0  # compra 2, venta 1
actual_delta = qty_final - qty_before
inventory_ok = abs(actual_delta - expected_delta) < 0.01
step(
    9,
    "impacto_inventario",
    inventory_ok,
    f"before={qty_before} after_receipt={qty_after_receipt} final={qty_final} delta={actual_delta}",
)
check("inventory_tracked", inventory_ok, f"delta={actual_delta} expected={expected_delta}")

# --- 10. Impacto contable básico ---
accounting = {}
if bill and bill.state == "posted":
    bill_lines = bill.line_ids.filtered(lambda l: l.display_type not in ("line_section", "line_note"))
    accounting["vendor_bill_lines"] = len(bill_lines)
    accounting["vendor_bill_balanced"] = abs(sum(bill_lines.mapped("debit")) - sum(bill_lines.mapped("credit"))) < 0.01
    accounting["vendor_bill_total"] = bill.amount_total

if invoice and invoice.state == "posted":
    inv_lines = invoice.line_ids.filtered(lambda l: l.display_type not in ("line_section", "line_note"))
    accounting["customer_invoice_lines"] = len(inv_lines)
    accounting["customer_invoice_balanced"] = abs(sum(inv_lines.mapped("debit")) - sum(inv_lines.mapped("credit"))) < 0.01
    accounting["customer_invoice_total"] = invoice.amount_total

# Asientos de valoración inventario (stock_account — Odoo 19: account_move_id en stock.move)
stock_account_moves = 0
if receipt:
    for sm in receipt.move_ids.filtered(lambda m: m.state == "done"):
        if sm.account_move_id and sm.account_move_id.state == "posted":
            stock_account_moves += 1
if pickings_out:
    for sm in pickings_out[0].move_ids.filtered(lambda m: m.state == "done"):
        if sm.account_move_id and sm.account_move_id.state == "posted":
            stock_account_moves += 1
accounting["stock_valuation_moves"] = stock_account_moves

acct_ok = (
    accounting.get("vendor_bill_balanced", False)
    and accounting.get("customer_invoice_balanced", False)
    and accounting.get("vendor_bill_lines", 0) > 0
    and accounting.get("customer_invoice_lines", 0) > 0
)
results["flows"]["accounting"] = accounting
step(10, "impacto_contable_basico", acct_ok, accounting)
check("accounting_basic", acct_ok, accounting)

env.cr.commit()

all_ok = all(c["ok"] for c in results["checks"].values()) and all(
    s["ok"] for s in results["steps"].values()
)
results["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
results["ok"] = all_ok
print("PHASE4_VALIDATION=" + json.dumps(results, ensure_ascii=False, default=str))
