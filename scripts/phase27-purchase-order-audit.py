# -*- coding: utf-8 -*-
"""Fase 27 — Auditoría campos Orden de Compra (solo TEST)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

report = {
    "phase": "27-purchase-order-field-audit",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "models": {},
    "field_map": {},
    "sample": {},
}


def field_info(model_name, fname):
    f = env[model_name]._fields.get(fname)
    if not f:
        return None
    return {
        "type": f.type,
        "string": f.string,
        "required": bool(getattr(f, "required", False)),
        "store": bool(getattr(f, "store", True)),
    }


PO_FIELDS = [
    "name", "state", "partner_id", "dest_address_id", "partner_ref",
    "date_order", "date_approve", "date_planned", "user_id",
    "payment_term_id", "currency_id", "incoterm_id", "incoterm_location",
    "note", "order_line", "amount_untaxed", "amount_tax", "amount_total",
    "company_id",
]
POL_FIELDS = [
    "product_id", "name", "product_qty", "product_uom_id", "price_unit",
    "discount", "tax_ids", "price_subtotal", "date_planned", "display_type",
]

for fname in PO_FIELDS:
    info = field_info("purchase.order", fname)
    if info:
        report["models"].setdefault("purchase.order", {})[fname] = info

report["models"]["purchase.order"]["missing"] = [
    f for f in PO_FIELDS if f not in report["models"].get("purchase.order", {})
]

for fname in POL_FIELDS:
    info = field_info("purchase.order.line", fname)
    if info:
        report["models"].setdefault("purchase.order.line", {})[fname] = info

report["models"]["purchase.order.line"]["missing"] = [
    f for f in POL_FIELDS if f not in report["models"].get("purchase.order.line", {})
]

po = env["purchase.order"].search([], limit=1, order="id desc")
if po:
    report["sample"] = {
        "name": po.name,
        "state": po.state,
        "partner": po.partner_id.name,
        "currency": po.currency_id.name,
        "lines": len(po.order_line),
        "amount_total": po.amount_total,
    }

report["field_map"] = {
    "order_number": "purchase.order.name",
    "state": "purchase.order.state",
    "vendor": "purchase.order.partner_id",
    "vendor_address": "partner_id (+ dest_address_id si dropship)",
    "vendor_vat": "partner_id.vat",
    "vendor_phone": "partner_id.phone",
    "vendor_email": "partner_id.email",
    "order_date": "purchase.order.date_order",
    "expected_date": "purchase.order.date_planned (o min line.date_planned)",
    "buyer": "purchase.order.user_id",
    "payment_terms": "purchase.order.payment_term_id",
    "currency": "purchase.order.currency_id",
    "incoterm": "purchase.order.incoterm_id + incoterm_location",
    "vendor_reference": "purchase.order.partner_ref",
    "observations": "purchase.order.note",
    "line_product": "purchase.order.line.product_id",
    "line_description": "purchase.order.line.name",
    "line_qty": "purchase.order.line.product_qty",
    "line_uom": "purchase.order.line.product_uom_id",
    "line_price": "purchase.order.line.price_unit",
    "line_discount": "purchase.order.line.discount",
    "line_taxes": "purchase.order.line.tax_ids",
    "line_subtotal": "purchase.order.line.price_subtotal",
    "subtotal": "purchase.order.amount_untaxed",
    "taxes": "purchase.order.amount_tax",
    "total": "purchase.order.amount_total",
}

out = "/tmp/phase27-purchase-order/audit.json"
import os
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(json.dumps({"ok": True, "path": out}))
