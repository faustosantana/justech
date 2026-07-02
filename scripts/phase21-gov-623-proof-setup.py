#!/usr/bin/env python3
"""Fase 21 — Setup datos limpios PROD para prueba 623 (solo creación, sin pago)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

PARTNER_REF = "P21-GOV-623-PROOF"
PARTNER_NAME = "P21 GOV PROOF UNIQUE"
PARTNER_VAT = "101733934"
INVOICE_REF = "P21-GOV-INV-PROOF"
BASE = 10000.0

company = env.company
Partner = env["res.partner"]
Move = env["account.move"]

report = {
    "phase": "21-gov-623-setup",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "partner_ref": PARTNER_REF,
    "invoice_ref": INVOICE_REF,
    "ok": True,
}

partner = Partner.search([("ref", "=", PARTNER_REF)], limit=1)
if not partner:
    partner = Partner.create(
        {
            "name": PARTNER_NAME,
            "ref": PARTNER_REF,
            "vat": PARTNER_VAT,
            "company_type": "company",
            "customer_rank": 1,
        }
    )
report["partner_id"] = partner.id
report["partner_vat"] = partner.vat

product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
tax_sale = env["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)],
    limit=1,
)
journal_sale = env["account.journal"].search(
    [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
)
doc_type_02 = env["justech.do.fiscal.document.type"].search([("code", "=", "02")], limit=1)
ncf_range = env["justech.do.ncf.range"].search([("state", "=", "active"), ("prefix", "=", "B02")], limit=1)

inv = Move.search(
    [
        ("partner_id", "=", partner.id),
        ("ref", "=", INVOICE_REF),
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("payment_state", "in", ("not_paid", "partial")),
    ],
    limit=1,
)
if not inv:
    inv = Move.create(
        {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "journal_id": journal_sale.id,
            "invoice_date": date.today(),
            "ref": INVOICE_REF,
            "justech_do_document_type_id": doc_type_02.id if doc_type_02 else False,
            "justech_do_ncf_range_id": ncf_range.id if ncf_range else False,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": BASE,
                        "tax_ids": [Command.set(tax_sale.ids)],
                    }
                )
            ],
        }
    )
    inv.action_post()

report["invoice_id"] = inv.id
report["invoice_name"] = inv.name
report["invoice_total"] = inv.amount_total
report["invoice_residual"] = inv.amount_residual
report["invoice_ncf"] = inv.justech_do_ncf or ""
report["expected_gov_wh"] = round(BASE * 0.05, 2)

env.cr.commit()
print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
