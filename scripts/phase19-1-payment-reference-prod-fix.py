# -*- coding: utf-8 -*-
"""Fase 19.1 — Validación hellenia_payment_reference en register y flujo de pagos."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB not in ("hellenia_test", "hellenia_prod"):
    raise SystemExit(f"ABORT: solo hellenia_test o hellenia_prod, actual={DB}")

BASE, TOTAL, TOL = 10000.0, 11800.0, 0.02
PARTIAL = 5000.0

report = {
    "phase": "19.1-payment-reference-field-fix",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "root_cause": (
        "payment_partner_wizard envía hellenia_payment_reference (y campos método) "
        "a account.payment.register.create(), pero esos campos solo existían en "
        "hellenia_ux (no instalado en PROD)."
    ),
    "fix": "Campos de referencia/método añadidos en hellenia_account sobre register y payment.",
    "tests": {},
    "ok": True,
    "pass": False,
}


def check(key, ok, detail=""):
    report["tests"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["ok"] = False


def near(a, b, tol=TOL):
    return abs((a or 0.0) - (b or 0.0)) <= tol


mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
if mod and mod.state == "installed":
    mod.button_immediate_upgrade()
    env.cr.commit()
check("00_upgrade_hellenia_account", mod and mod.state == "installed", mod.latest_version if mod else "missing")

Register = env["account.payment.register"]
Payment = env["account.payment"]
required_register = (
    "hellenia_payment_reference",
    "hellenia_card_auth",
    "hellenia_card_batch",
    "hellenia_check_number",
    "hellenia_check_bank_id",
    "hellenia_check_date",
)
required_payment = required_register + (
    "hellenia_is_card",
    "hellenia_is_check",
    "hellenia_is_transfer",
)

for fname in required_register:
    check(f"01_register_field_{fname}", fname in Register._fields, fname)
for fname in required_payment:
    check(f"02_payment_field_{fname}", fname in Payment._fields, fname)

company = env.company
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
if not vendor:
    vendor = env["res.partner"].create(
        {"name": "Proveedor certificación Fase 19.1", "supplier_rank": 1, "company_type": "company"}
    )
    env.cr.commit()
product = env["product.product"].search([("sale_ok", "=", True), ("purchase_ok", "=", True)], limit=1)
tax_sale = env["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)], limit=1
)
tax_purchase = env["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)], limit=1
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)
Catalog = env["hellenia.withholding.catalog"]
Catalog.sync_catalog_from_taxes(company)
env.cr.commit()


def _cat(code):
    return Catalog.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)


def _inv(partner, journal, tax, move_type, ref):
    move = env["account.move"].create(
        {
            "move_type": move_type,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "invoice_date": date.today(),
            "ref": ref,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": BASE,
                        "tax_ids": [Command.set(tax.ids)],
                    }
                )
            ],
        }
    )
    move.action_post()
    return move


def _partner_wizard(partner, partner_type, ref):
    ml = (
        bnkd.inbound_payment_method_line_ids
        if partner_type == "customer"
        else bnkd.outbound_payment_method_line_ids
    )
    return env["hellenia.payment.partner.wizard"].create(
        {
            "partner_type": partner_type,
            "partner_id": partner.id,
            "journal_id": bnkd.id,
            "payment_method_line_id": ml[:1].id,
            "payment_date": date.today(),
            "hellenia_payment_reference": ref,
        }
    )


def _pay_via_wizard(partner, inv, partner_type, ref, amount=None, cats=None):
    wiz = _partner_wizard(partner, partner_type, ref)
    line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
    line.apply = True
    if amount is not None:
        line.amount_to_pay = amount
    if cats:
        line.withholding_catalog_ids = [Command.set([c.id for c in cats if c])]
    wiz.action_register_payments()
    env.cr.flush()
    pay = Payment.search([("partner_id", "=", partner.id)], order="id desc", limit=1)
    pay.invalidate_recordset()
    return pay


# --- Flujos solicitados ---
ref_tag = f"P191-{DB[-4:]}"
inv1 = _inv(customer, journal_sale, tax_sale, "out_invoice", f"{ref_tag}-FULL")
pay1 = _pay_via_wizard(customer, inv1, "customer", f"{ref_tag}-FULL-NOWH")
check("03_no_wh_payment", bool(pay1), pay1.name if pay1 else "")
check("03_no_wh_reference", pay1.hellenia_payment_reference == f"{ref_tag}-FULL-NOWH", pay1.hellenia_payment_reference)
check("03_no_wh_move", bool(pay1.move_id), pay1.move_id.name if pay1.move_id else "")
check("03_no_wh_reconciled", inv1.payment_state == "paid", inv1.payment_state)

inv2 = _inv(customer, journal_sale, tax_sale, "out_invoice", f"{ref_tag}-PART")
pay2 = _pay_via_wizard(customer, inv2, "customer", f"{ref_tag}-PART", amount=PARTIAL)
check("04_partial_payment", bool(pay2), pay2.name if pay2 else "")
check("04_partial_reference", pay2.hellenia_payment_reference == f"{ref_tag}-PART", pay2.hellenia_payment_reference)
check("04_partial_state", inv2.payment_state == "partial", inv2.payment_state)

cat_gov = _cat("RET-GOB-5")
inv3 = _inv(customer, journal_sale, tax_sale, "out_invoice", f"{ref_tag}-GOV")
pay3 = _pay_via_wizard(customer, inv3, "customer", f"{ref_tag}-GOV", cats=[cat_gov])
gov_wh = sum(pay3.hellenia_withholding_line_ids.mapped("amount"))
check("05_gov_payment", bool(pay3) and gov_wh > 0, f"wh={gov_wh}")
check("05_gov_reference", pay3.hellenia_payment_reference == f"{ref_tag}-GOV", pay3.hellenia_payment_reference)
check("05_gov_balanced", near(sum(pay3.move_id.line_ids.mapped("debit")), sum(pay3.move_id.line_ids.mapped("credit"))), "balanced")

cat_itbis = _cat("RET-ITBIS-100")
inv4 = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", f"{ref_tag}-ITBIS")
pay4 = _pay_via_wizard(vendor, inv4, "supplier", f"{ref_tag}-ITBIS", cats=[cat_itbis])
itbis_wh = sum(pay4.hellenia_withholding_line_ids.mapped("amount"))
check("06_itbis100_payment", bool(pay4) and itbis_wh > 0, f"wh={itbis_wh}")
check("06_itbis100_reference", pay4.hellenia_payment_reference == f"{ref_tag}-ITBIS", pay4.hellenia_payment_reference)

# 607 / 623 smoke
period_util = env["justech.do.dgii.period"]
period_code = period_util.default_period_code()
date_from, date_to = period_util.period_bounds_from_code(period_code)
exp607 = env["justech.do.dgii.607.exporter"]
moves607 = exp607._moves_for_period(company, date_from, date_to, only_valid=True)
check("07_607_exporter", True, f"moves={len(moves607)}")

exp623 = env["justech.do.dgii.623.exporter"]
moves623 = exp623._moves_for_period(company, date_from, date_to, only_valid=True)
check("08_623_exporter", True, f"moves={len(moves623)}")
if pay3:
    ref, ref_type, _bank = exp623._reference_data(inv3)
    check("08_623_reference_data", bool(ref), ref)

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
print(f"PHASE191:{json.dumps(report, ensure_ascii=False, default=str)}")
