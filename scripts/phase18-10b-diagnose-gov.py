# -*- coding: utf-8 -*-
"""Diagnóstico rápido pago gobierno + 623."""
from __future__ import annotations
import json
from datetime import date
from odoo import Command

company = env.company
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
tax_sale = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)
cat_gov = env["hellenia.withholding.catalog"].search([("code", "=", "RET-GOB-5"), ("company_id", "=", company.id)], limit=1)

with env.cr.savepoint():
    inv = env["account.move"].create({
        "move_type": "out_invoice", "partner_id": customer.id, "journal_id": journal_sale.id,
        "invoice_date": date.today(), "ref": "DIAG-1810B",
        "invoice_line_ids": [Command.create({"product_id": product.id, "quantity": 1, "price_unit": 10000.0, "tax_ids": [Command.set(tax_sale.ids)]})],
    })
    inv.action_post()
    wiz = env["hellenia.payment.partner.wizard"].create({
        "partner_type": "customer", "partner_id": customer.id, "journal_id": bnkd.id,
        "payment_method_line_id": bnkd.inbound_payment_method_line_ids[:1].id,
        "hellenia_payment_reference": "DIAG-REF-623",
    })
    line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
    line.write({"apply": True, "withholding_catalog_ids": [Command.set(cat_gov.ids)]})
    wiz.action_register_payments()
    pay = env["account.payment"].search([], order="id desc", limit=1)
    lines = pay.move_id.line_ids
    result = {
        "invoice": inv.name,
        "total": inv.amount_total,
        "residual": inv.amount_residual,
        "payment_state": inv.payment_state,
        "pay_amount": pay.amount,
        "applied": pay.hellenia_applied_amount,
        "wh_total": pay.hellenia_withholding_total,
        "net": pay.hellenia_net_transfer,
        "move_lines": [(l.account_id.code, l.debit, l.credit, l.balance) for l in lines],
        "wh_lines_db": pay.hellenia_withholding_line_ids.read(["amount", "move_line_id"]),
    }
    period = env["justech.do.dgii.period"].default_period_code()
    df, dt = env["justech.do.dgii.period"].period_bounds_from_code(period)
    rep = env["justech.do.fiscal.report"].create({
        "name": "DIAG 623", "report_type": "623", "period_code": period,
        "date_from": df, "date_to": dt, "company_id": company.id,
    })
    collected = rep._collect_lines(valid_moves=inv)
    rep.action_generate(valid_moves=inv)
    result["623_collected"] = len(collected)
    result["623_lines"] = len(rep.line_ids)
    exp = env["justech.do.dgii.623.exporter"]
    result["623_has"] = exp._has_gov_withholding(inv, exp._gov_tax(company))
    result["623_amt"] = exp._gov_amount(inv, exp._gov_tax(company))
    print("DIAG1810B:" + json.dumps(result, default=str))
