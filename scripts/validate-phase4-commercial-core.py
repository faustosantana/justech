#!/usr/bin/env python3
"""Fase 4 — Validación flujo comercial completo (odoo shell stdin)."""
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
results = {"checks": {}, "flows": {}}


def check(name, ok, detail=""):
    results["checks"][name] = {"ok": ok, "detail": detail}
    return ok


# --- Módulos ---
for mod in ALLOWED:
    st = env["ir.module.module"].search([("name", "=", mod)], limit=1).state
    check(f"module_{mod}", st == "installed", st)

for mod in FORBIDDEN:
    rec = env["ir.module.module"].search([("name", "=", mod)], limit=1)
    st = rec.state if rec else "absent"
    check(f"forbidden_{mod}", st != "installed", st)

# --- Maestros prueba ---
cat = env["product.category"].search(
    [("name", "=", "Espejos"), ("parent_id.name", "=", "Inventario")], limit=1
)
if not cat:
    cat = env["product.category"].search([("name", "=", "Espejos")], limit=1)

product = env["product.product"].search([("default_code", "=", "PHASE4-TEST-001")], limit=1)
if not product:
    product = env["product.product"].create(
        {
            "name": "PHASE4 Producto prueba — Espejo único",
            "default_code": "PHASE4-TEST-001",
            "type": "consu",
            "is_storable": True,
            "categ_id": cat.id if cat else False,
            "list_price": 10000.0,
            "standard_price": 5000.0,
        }
    )
else:
    product.write(
        {
            "list_price": 10000.0,
            "standard_price": 5000.0,
            "type": "consu",
            "is_storable": True,
        }
    )

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

warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
if not warehouse:
    warehouse = env["stock.warehouse"].create(
        {"name": "Hellenia", "code": "HEL", "company_id": company.id}
    )

# Ajustar stock inicial para entrega
loc = warehouse.lot_stock_id
env["stock.quant"]._update_available_quantity(product, loc, 5.0)

# --- VENTAS: Cotización → Pedido → Entrega → Factura ---
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
check("quotation_created", so.state == "draft", so.state)

so.action_confirm()
results["flows"]["sale_order_state"] = so.state
check("sale_order_confirmed", so.state == "sale", so.state)

pickings_out = so.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing")
check("delivery_created", bool(pickings_out), len(pickings_out))
if pickings_out:
    picking = pickings_out[0]
    picking.action_assign()
    for move in picking.move_ids:
        move.quantity = move.product_uom_qty
    picking.button_validate()
    results["flows"]["delivery_state"] = picking.state
    check("delivery_done", picking.state == "done", picking.state)

# Facturación cliente
so._create_invoices()
invoice = so.invoice_ids[:1]
results["flows"]["invoice_state"] = invoice.state if invoice else None
check("customer_invoice_created", bool(invoice), invoice.name if invoice else "")
if invoice:
    invoice.invoice_date = date.today()
    invoice.action_post()
    check("customer_invoice_posted", invoice.state == "posted", invoice.state)

# --- COMPRAS: PO → Recepción → Factura proveedor ---
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
check("purchase_draft", po.state in ("draft", "sent"), po.state)

po.button_confirm()
results["flows"]["purchase_order_state"] = po.state
check("purchase_confirmed", po.state == "purchase", po.state)

pickings_in = po.picking_ids.filtered(lambda p: p.picking_type_code == "incoming")
check("receipt_created", bool(pickings_in), len(pickings_in))
if pickings_in:
    receipt = pickings_in[0]
    receipt.action_assign()
    for move in receipt.move_ids:
        move.quantity = move.product_uom_qty
    receipt.button_validate()
    results["flows"]["receipt_state"] = receipt.state
    check("receipt_done", receipt.state == "done", receipt.state)

po.action_create_invoice()
bill = po.invoice_ids[:1]
results["flows"]["vendor_bill_state"] = bill.state if bill else None
check("vendor_bill_created", bool(bill), bill.name if bill else "")
if bill:
    bill.invoice_date = date.today()
    bill.action_post()
    check("vendor_bill_posted", bill.state == "posted", bill.state)

# --- Inventario ---
qty = env["stock.quant"]._get_available_quantity(product, loc)
results["flows"]["inventory_qty"] = qty
check("inventory_tracked", qty >= 0, qty)

env.cr.commit()

all_ok = all(c["ok"] for c in results["checks"].values())
results["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
results["ok"] = all_ok
print("PHASE4_VALIDATION=" + json.dumps(results, ensure_ascii=False, default=str))
