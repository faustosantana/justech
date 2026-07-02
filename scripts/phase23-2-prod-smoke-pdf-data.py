# -*- coding: utf-8 -*-
"""Fase 23.2 — Datos mínimos PROD solo para certificación PDF visual (P23-VISUAL)."""
from __future__ import annotations

import json
from datetime import date

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

REF = "P23-VISUAL-PDF"
report = {"phase": "23.2-prod-smoke-pdf-data", "created": {}, "ok": True}
company = env.company


def ensure_partner(name, **kw):
    p = env["res.partner"].search([("ref", "=", REF), ("name", "=", name)], limit=1)
    if not p:
        p = env["res.partner"].create({"name": name, "ref": REF, **kw})
        report["created"]["partner"] = name
    return p


product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
vendor = ensure_partner(f"{REF} Proveedor", supplier_rank=1, company_type="company")
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
tax_sale = env["account.tax"].search(
    [("type_tax_use", "=", "sale"), ("company_id", "=", company.id), ("amount", "=", 18)],
    limit=1,
)
tax_purchase = env["account.tax"].search(
    [("type_tax_use", "=", "purchase"), ("company_id", "=", company.id), ("amount", "=", 18)],
    limit=1,
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)

# NC borrador (solo PDF visual, sin publicar)
if not env["account.move"].search([("ref", "=", f"{REF}-NC"), ("move_type", "=", "out_refund")], limit=1):
    src = env["account.move"].search(
        [("move_type", "=", "out_invoice"), ("state", "=", "posted")], limit=1
    )
    if src and product:
        nc = env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": src.partner_id.id,
                "journal_id": journal_sale.id,
                "invoice_date": date.today(),
                "ref": f"{REF}-NC",
                "reversed_entry_id": src.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "price_unit": 1000.0,
                            "tax_ids": [Command.set(tax_sale.ids)] if tax_sale else [],
                        }
                    )
                ],
            }
        )
        report["created"]["nc_draft"] = nc.name

# ND borrador
if not env["account.move"].search([("ref", "=", f"{REF}-ND"), ("move_type", "=", "out_invoice")], limit=1):
    b03 = env["justech.do.fiscal.document.type"].search([("prefix", "=", "B03")], limit=1)
    if customer and product and journal_sale:
        nd = env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": customer.id,
                "journal_id": journal_sale.id,
                "invoice_date": date.today(),
                "ref": f"{REF}-ND",
                "justech_do_document_type_id": b03.id if b03 else False,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "price_unit": 500.0,
                            "tax_ids": [Command.set(tax_sale.ids)] if tax_sale else [],
                        }
                    )
                ],
            }
        )
        report["created"]["nd_draft"] = nd.name

# RFQ borrador
if not env["purchase.order"].search([("partner_ref", "=", f"{REF}-RFQ")], limit=1):
    rfq_po = env["purchase.order"].create(
        {
            "partner_id": vendor.id,
            "partner_ref": f"{REF}-RFQ",
            "date_order": date.today(),
            "order_line": [
                Command.create(
                    {
                        "product_id": product.id,
                        "product_qty": 1,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(tax_purchase.ids)] if tax_purchase else [],
                    }
                )
            ],
        }
    )
    report["created"]["rfq"] = rfq_po.name

# OC confirmada (+ recepción entrante)
oc_po = env["purchase.order"].search([("partner_ref", "=", f"{REF}-OC")], limit=1)
if not oc_po and product:
    oc_po = env["purchase.order"].create(
        {
            "partner_id": vendor.id,
            "partner_ref": f"{REF}-OC",
            "date_order": date.today(),
            "order_line": [
                Command.create(
                    {
                        "product_id": product.id,
                        "product_qty": 1,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(tax_purchase.ids)] if tax_purchase else [],
                    }
                )
            ],
        }
    )
    oc_po.button_confirm()
    report["created"]["oc"] = oc_po.name
    pick = env["stock.picking"].search(
        [("origin", "=", oc_po.name), ("picking_type_id.code", "=", "incoming")],
        limit=1,
    )
    if pick:
        report["created"]["incoming_picking"] = pick.name

env.cr.commit()
print(json.dumps(report, indent=2, ensure_ascii=False))
