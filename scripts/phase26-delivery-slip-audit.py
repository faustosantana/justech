# -*- coding: utf-8 -*-
"""Fase 26 — Auditoría campos Conduce de Entrega (solo TEST)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

MODELS = [
    "stock.picking",
    "stock.move",
    "stock.move.line",
    "sale.order",
    "account.move",
    "res.partner",
    "res.company",
]

report = {
    "phase": "26-delivery-slip-field-audit",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "models": {},
    "relationships": {},
    "sample_records": {},
    "field_map": {},
}


def field_info(model_name, fname):
    f = env[model_name]._fields.get(fname)
    if not f:
        return None
    return {
        "type": f.type,
        "string": f.string,
        "required": bool(getattr(f, "required", False)),
        "readonly": bool(getattr(f, "readonly", False)),
        "related": getattr(f, "related", None),
        "store": bool(getattr(f, "store", True)),
    }


def audit_model(name):
    Model = env[name]
    fields_of_interest = {}
    candidates = {
        "stock.picking": [
            "name", "origin", "state", "scheduled_date", "date_done", "date_deadline",
            "partner_id", "user_id", "sale_id", "group_id", "picking_type_id",
            "location_id", "location_dest_id", "carrier_id", "carrier_tracking_ref",
            "note", "move_ids", "move_line_ids", "backorder_id", "backorder_ids",
            "invoice_ids", "sale_order_id",
        ],
        "stock.move": [
            "name", "product_id", "product_uom", "product_uom_qty", "quantity",
            "state", "picking_id", "sale_line_id", "description_picking",
        ],
        "stock.move.line": [
            "product_id", "product_uom_id", "quantity", "qty_done", "lot_id",
            "lot_name", "package_id", "owner_id", "move_id", "picking_id",
        ],
        "sale.order": [
            "name", "partner_id", "partner_shipping_id", "user_id", "state",
            "order_line", "picking_ids", "invoice_ids", "note", "client_order_ref",
        ],
        "account.move": [
            "name", "partner_id", "partner_shipping_id", "invoice_user_id", "state",
            "invoice_line_ids", "invoice_origin", "stock_move_id", "picking_ids",
        ],
        "res.partner": [
            "name", "vat", "street", "street2", "city", "state_id", "country_id",
            "phone", "email", "child_ids",
        ],
        "res.company": [
            "name", "logo", "street", "city", "vat", "phone", "email", "website",
        ],
    }
    for fname in candidates.get(name, []):
        info = field_info(name, fname)
        if info:
            fields_of_interest[fname] = info
    report["models"][name] = {
        "exists": True,
        "fields": fields_of_interest,
        "missing_requested": [
            f for f in candidates.get(name, []) if f not in fields_of_interest
        ],
    }


for m in MODELS:
    audit_model(m)

# --- Relaciones reales (muestras) ---
picking = env["stock.picking"].search(
    [("picking_type_code", "=", "outgoing"), ("state", "in", ("assigned", "done"))],
    limit=1,
    order="id desc",
)
so = env["sale.order"].search([("state", "in", ("sale", "done"))], limit=1, order="id desc")
inv = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted")], limit=1, order="id desc"
)

rel = {}

if picking:
    rel["stock.picking_sample"] = {
        "id": picking.id,
        "name": picking.name,
        "sale_id": picking.sale_id.id if picking._fields.get("sale_id") and picking.sale_id else None,
        "sale_order_id": picking.sale_id.id if hasattr(picking, "sale_id") and picking.sale_id else (
            picking.sale_order_id.id if picking._fields.get("sale_order_id") and picking.sale_order_id else None
        ),
        "origin": picking.origin,
        "group_id": picking.group_id.id if picking._fields.get("group_id") and picking.group_id else None,
        "group_sale_id": (
            picking.group_id.sale_id.id
            if picking._fields.get("group_id") and picking.group_id
            and picking.group_id._fields.get("sale_id")
            and picking.group_id.sale_id
            else None
        ),
        "invoice_ids": (
            picking.invoice_ids.ids if picking._fields.get("invoice_ids") else []
        ),
    }
    if picking._fields.get("group_id") and picking.group_id and picking.group_id._fields.get("sale_id") and picking.group_id.sale_id:
        rel["picking_via_procurement_group"] = picking.group_id.sale_id.name

if so:
    rel["sale.order_sample"] = {
        "id": so.id,
        "name": so.name,
        "picking_ids": so.picking_ids.ids,
        "picking_names": so.picking_ids.mapped("name"),
        "invoice_ids": so.invoice_ids.ids,
        "invoice_names": so.invoice_ids.mapped("name"),
    }

if inv:
    rel["account.move_sample"] = {
        "id": inv.id,
        "name": inv.name,
        "invoice_origin": inv.invoice_origin,
        "stock_move_id": inv.stock_move_id.id if inv._fields.get("stock_move_id") and inv.stock_move_id else None,
        "picking_ids": inv.picking_ids.ids if inv._fields.get("picking_ids") else [],
    }
    if inv.invoice_origin:
        so_from_origin = env["sale.order"].search([("name", "=", inv.invoice_origin)], limit=1)
        rel["invoice_origin_resolves_so"] = bool(so_from_origin)
        if so_from_origin:
            rel["invoice_so_pickings"] = so_from_origin.picking_ids.mapped("name")

report["relationships"] = rel

# Field map for delivery slip
p = env["stock.picking"]
so_m = env["sale.order"]
am = env["account.move"]

report["field_map"] = {
    "conduce_number": {
        "stock.picking": "name",
        "sale.order": "name (prefijo COND-/ref cotización en contexto)",
        "account.move": "name (prefijo COND-/ref factura en contexto)",
    },
    "picking_number": {"stock.picking": "name"},
    "state": {
        "stock.picking": "state (+ selection_labels via fields_get)",
        "sale.order": "state",
        "account.move": "state",
    },
    "sale_order": {
        "stock.picking": "sale_id (Odoo 19) or group_id.sale_id",
        "sale.order": "self",
        "account.move": "invoice_origin → sale.order search OR line.sale_line_ids.order_id",
    },
    "invoice": {
        "stock.picking": "sale_id.invoice_ids or group_id.sale_id.invoice_ids",
        "sale.order": "invoice_ids",
        "account.move": "self (out_invoice)",
    },
    "customer": "partner_id",
    "delivery_address": {
        "stock.picking": "partner_id (dest) — check move partner on outgoing",
        "sale.order": "partner_shipping_id",
        "account.move": "partner_shipping_id or partner_id",
    },
    "scheduled_date": "scheduled_date (picking) / expected_date on moves",
    "effective_date": "date_done (picking)",
    "responsible": "user_id (picking) / create_uid fallback",
    "salesperson": {
        "stock.picking": "sale_id.user_id",
        "sale.order": "user_id",
        "account.move": "invoice_user_id",
    },
    "carrier": "carrier_id",
    "warehouse_origin": "picking_type_id.warehouse_id or location_id",
    "dest_location": "location_dest_id",
    "products_lines": {
        "stock.picking": "move_ids / move_line_ids",
        "sale.order": "order_line (product lines)",
        "account.move": "invoice_line_ids (product)",
    },
    "qty_requested": {
        "stock.picking": "move.product_uom_qty",
        "sale.order": "line.product_uom_qty",
        "account.move": "line.quantity",
    },
    "qty_delivered": {
        "stock.picking": "move.quantity (done) or move_line.quantity",
        "sale.order": "line.qty_delivered if exists else product_uom_qty",
        "account.move": "line.quantity",
    },
    "uom": "product_uom / product_uom_id",
    "lot_serial": "move_line.lot_id.name or lot_name",
    "observations": {
        "stock.picking": "note",
        "sale.order": "note",
        "account.move": "narration",
    },
}

# State labels picking
if picking:
    sel = p._fields["state"].selection
    if callable(sel):
        sel = sel(p)
    report["picking_state_selection"] = sel

out_path = "/tmp/phase26-delivery-slip-audit.json"
with open(out_path, "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False, default=str)

print(json.dumps({"ok": True, "path": out_path, "db": DB}, indent=2))
