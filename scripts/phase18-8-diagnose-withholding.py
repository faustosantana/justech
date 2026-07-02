# -*- coding: utf-8 -*-
"""Diagnóstico Fase 18.8 — trazabilidad retenciones en pagos."""
from __future__ import annotations

import json
from datetime import date

from odoo import Command

DB = env.cr.dbname
report = {"database": DB, "payments": [], "issues": []}

Payment = env["account.payment"]
WhLine = env["hellenia.account.payment.withholding"]

# últimos 10 pagos
for pay in Payment.search([], order="id desc", limit=10):
    lines = WhLine.search([("payment_id", "=", pay.id)])
    report["payments"].append({
        "id": pay.id,
        "name": pay.name,
        "applied": pay.hellenia_applied_amount,
        "wh_total_field": pay.hellenia_withholding_total,
        "wh_lines_db": len(lines),
        "wh_sum_db": sum(lines.mapped("amount")),
        "gov_field": pay.justech_do_gov_withholding_amount,
        "net": pay.hellenia_net_transfer,
    })

# crear pago test con retención y verificar persistencia inmediata
company = env.company
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
Catalog = env["hellenia.withholding.catalog"]
cat_gov = Catalog.search([("code", "=", "RET-GOB-5"), ("company_id", "=", company.id)], limit=1)
cat_itbis = Catalog.search([("code", "=", "RET-ITBIS-100"), ("company_id", "=", company.id)], limit=1)
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
tax_sale = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)

def _inv(partner, move_type):
    tax = tax_sale if move_type == "out_invoice" else env["account.tax"].search([("type_tax_use", "=", "purchase"), ("amount", "=", 18), ("company_id", "=", company.id)], limit=1)
    journal = journal_sale if move_type == "out_invoice" else env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
    m = env["account.move"].create({
        "move_type": move_type,
        "partner_id": partner.id,
        "journal_id": journal.id,
        "invoice_date": date.today(),
        "ref": f"P188-DIAG-{move_type}",
        "invoice_line_ids": [Command.create({"product_id": product.id, "quantity": 1, "price_unit": 10000.0, "tax_ids": [Command.set(tax.ids)]})],
    })
    m.action_post()
    return m

def _pay(partner, inv, cat, ptype):
    wiz = env["hellenia.payment.partner.wizard"].create({
        "partner_type": ptype,
        "partner_id": partner.id,
        "journal_id": bnkd.id,
        "payment_method_line_id": (bnkd.inbound_payment_method_line_ids if ptype == "customer" else bnkd.outbound_payment_method_line_ids)[:1].id,
    })
    line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
    line.apply = True
    if cat:
        line.withholding_catalog_ids = [Command.set(cat.ids)]
        line._recompute_line_withholdings()
    wiz.action_register_payments()
    return Payment.search([("partner_id", "=", partner.id)], order="id desc", limit=1)

try:
    with env.cr.savepoint():
        inv_c = _inv(customer, "out_invoice")
        pay_gov = _pay(customer, inv_c, cat_gov, "customer")
        env.cr.flush()
        pay_gov.invalidate_recordset()
        lines = WhLine.search([("payment_id", "=", pay_gov.id)])
        report["test_gov"] = {
            "pay_id": pay_gov.id,
            "wh_total_field": pay_gov.hellenia_withholding_total,
            "wh_lines_db": len(lines),
            "wh_sum_db": sum(lines.mapped("amount")),
            "gov_field": pay_gov.justech_do_gov_withholding_amount,
            "inv_gov": inv_c.justech_do_gov_withholding_amount,
            "move_lines_wh": pay_gov.move_id.line_ids.filtered(lambda l: l.account_id == cat_gov.account_id).mapped("balance"),
        }
        if pay_gov.hellenia_withholding_total == 0 and lines:
            report["issues"].append("STORED_COMPUTE_ZERO_BUT_LINES_EXIST")
        if not lines:
            report["issues"].append("NO_PERSISTENT_LINES_CREATED")
except Exception as exc:
    report["test_gov_error"] = str(exc)

print("DIAG188:" + json.dumps(report, default=str))
