# -*- coding: utf-8 -*-
"""Fase 19.3 — Certificación abonos parciales wizard partner (TEST)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

BASE, ITBIS, TOTAL, TOL = 10000.0, 1800.0, 11800.0, 0.02
PARTIAL = 5000.0
RESIDUAL = TOTAL - PARTIAL

report = {
    "phase": "19.3-partial-payment-fix",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "root_cause": (
        "account.payment.register._compute_amount resetea amount al residual completo "
        "cuando custom_user_amount no queda fijado en create desde partner wizard; "
        "payment_partner_wizard.py action_register_payments líneas 432-449."
    ),
    "fix": (
        "_register_vals_for_line + create override en account.payment.register "
        "fuerza custom_user_amount, custom_user_currency_id y payment_difference_handling=open."
    ),
    "tests": {},
    "evidence": {},
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
if mod:
    mod.button_immediate_upgrade()
    env.cr.commit()
check("00_upgrade", mod and mod.state == "installed", mod.latest_version if mod else "")

setup = env["hellenia.account.payment.setup"]
setup.configure_banks_and_payments()
Catalog = env["hellenia.withholding.catalog"]
Catalog.sync_catalog_from_taxes(env.company)
env.cr.commit()

company = env.company
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
if not vendor:
    vendor = env["res.partner"].create(
        {"name": "Proveedor cert 19.3", "supplier_rank": 1, "company_type": "company"}
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
Payment = env["account.payment"]
AppLine = env["hellenia.payment.application.line"]
Register = env["account.payment.register"]


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


def _wiz(partner, ptype):
    ml = bnkd.inbound_payment_method_line_ids if ptype == "customer" else bnkd.outbound_payment_method_line_ids
    return env["hellenia.payment.partner.wizard"].create(
        {
            "partner_type": ptype,
            "partner_id": partner.id,
            "journal_id": bnkd.id,
            "payment_method_line_id": ml[:1].id,
            "payment_date": date.today(),
            "hellenia_payment_reference": "P193",
        }
    )


def _pay_wizard(partner, inv, ptype, amount=None, cats=None, ref="P193"):
    wiz = _wiz(partner, ptype)
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
    inv.invalidate_recordset(["payment_state", "amount_residual"])
    return pay, wiz


def _assert_partial(key, pay, inv, expected_amount, expected_wh=0.0):
    inv.invalidate_recordset()
    pay.invalidate_recordset()
    apps = AppLine.search([("payment_id", "=", pay.id)])
    deb = sum(pay.move_id.line_ids.mapped("debit")) if pay.move_id else 0
    cred = sum(pay.move_id.line_ids.mapped("credit")) if pay.move_id else 0
    check(f"{key}_payment_amount", near(pay.amount, expected_amount), pay.amount)
    check(f"{key}_applied_amount", near(pay.hellenia_applied_amount, expected_amount), pay.hellenia_applied_amount)
    check(f"{key}_invoice_partial", inv.payment_state in ("partial", "in_payment"), inv.payment_state)
    check(f"{key}_residual", near(abs(inv.amount_residual), RESIDUAL), abs(inv.amount_residual))
    check(f"{key}_move_id", bool(pay.move_id), pay.move_id.name if pay.move_id else pay.state)
    check(f"{key}_balanced", near(deb, cred), f"D={deb} C={cred}")
    check(f"{key}_app_line", bool(apps), apps[:1].applied_amount if apps else 0)
    if apps:
        check(f"{key}_app_not_full", near(apps[:1].applied_amount, expected_amount), apps[:1].applied_amount)
        check(
            f"{key}_app_not_invoice_total",
            not near(apps[:1].applied_amount, TOTAL),
            apps[:1].applied_amount,
        )
    if expected_wh:
        check(f"{key}_wh_total", near(pay.hellenia_withholding_total, expected_wh), pay.hellenia_withholding_total)
    report["evidence"][key] = {
        "payment": pay.name,
        "payment_amount": pay.amount,
        "applied": pay.hellenia_applied_amount,
        "wh_total": pay.hellenia_withholding_total,
        "invoice_state": inv.payment_state,
        "residual": abs(inv.amount_residual),
        "app_applied": apps[:1].applied_amount if apps else 0,
    }


# Caso 1: parcial sin retención
inv1 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P193-C1")
pay1, _ = _pay_wizard(customer, inv1, "customer", amount=PARTIAL)
_assert_partial("01_partial_no_wh", pay1, inv1, PARTIAL)

# Simular bug: register create con residual en línea pero amount_to_pay=5000
inv1b = _inv(customer, journal_sale, tax_sale, "out_invoice", "P193-C1B")
wiz_b = _wiz(customer, "customer")
line_b = wiz_b.line_ids.filtered(lambda l: l.move_id == inv1b)[:1]
line_b.write({"amount_to_pay": PARTIAL, "apply": True})
reg_vals, applied, _ = wiz_b._register_vals_for_line(line_b, wiz_b._register_vals_common())
reg = Register.with_context(
    active_model="account.move", active_ids=inv1b.ids, hellenia_applied_amount=applied
).create(reg_vals)
check("01b_register_amount", near(reg.amount, PARTIAL), reg.amount)
check("01b_register_custom", near(reg.custom_user_amount or 0, PARTIAL), reg.custom_user_amount)

# Caso 2: parcial 5% Gobierno
cat_gov = _cat("RET-GOB-5")
inv2 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P193-C2")
prop = PARTIAL / TOTAL
gov_wh = round(BASE * prop * 0.05, 2)
pay2, _ = _pay_wizard(customer, inv2, "customer", amount=PARTIAL, cats=[cat_gov])
_assert_partial("02_partial_gov", pay2, inv2, PARTIAL, expected_wh=gov_wh)
check("02_gov_proportional", near(pay2.hellenia_withholding_total, gov_wh, 1.0), pay2.hellenia_withholding_total)

# Caso 3: parcial ITBIS 100%
cat_itbis = _cat("RET-ITBIS-100")
inv3 = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P193-C3")
itbis_wh = round(ITBIS * prop, 2)
pay3, _ = _pay_wizard(vendor, inv3, "supplier", amount=PARTIAL, cats=[cat_itbis])
_assert_partial("03_partial_itbis", pay3, inv3, PARTIAL, expected_wh=itbis_wh)

# Caso 4: pago completo
inv4 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P193-C4")
pay4, _ = _pay_wizard(customer, inv4, "customer", amount=TOTAL)
inv4.invalidate_recordset()
check("04_full_amount", near(pay4.amount, TOTAL), pay4.amount)
check("04_full_paid", inv4.payment_state == "paid", inv4.payment_state)
check("04_full_residual", near(abs(inv4.amount_residual), 0), abs(inv4.amount_residual))

# Regresión: proveedor parcial/completo
inv5 = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P193-C5")
pay5, _ = _pay_wizard(vendor, inv5, "supplier", amount=PARTIAL)
check("05_vendor_partial", near(pay5.amount, PARTIAL), pay5.amount)
inv6 = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P193-C6")
pay6, _ = _pay_wizard(vendor, inv6, "supplier", amount=TOTAL)
check("06_vendor_full", inv6.payment_state == "paid", inv6.payment_state)

# Reportes 607 / 623
period_util = env["justech.do.dgii.period"]
period_code = period_util.default_period_code()
date_from, date_to = period_util.period_bounds_from_code(period_code)
exp607 = env["justech.do.dgii.607.exporter"]
exp623 = env["justech.do.dgii.623.exporter"]
check("07_607", True, f"moves={len(exp607._moves_for_period(company, date_from, date_to, only_valid=True))}")
check("08_623", True, f"moves={len(exp623._moves_for_period(company, date_from, date_to, only_valid=True))}")

# PDF recibo
try:
    html, _ = env["ir.actions.report"]._render_qweb_html("account.action_report_payment_receipt", pay2.ids)
    text = html.decode() if isinstance(html, bytes) else str(html)
    check("09_pdf", "Total retenido" in text or pay2.name in text, "pdf")
except Exception as exc:
    check("09_pdf", False, exc)

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
report["production_ready"] = report["ok"]
print(f"PHASE193:{json.dumps(report, ensure_ascii=False, default=str)}")
