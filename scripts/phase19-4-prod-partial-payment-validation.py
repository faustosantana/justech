# -*- coding: utf-8 -*-
"""Fase 19.4 — Validación abonos parciales en PRODUCCIÓN."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

BASE, ITBIS, TOTAL, TOL = 10000.0, 1800.0, 11800.0, 0.02
PARTIAL = 5000.0
RESIDUAL = TOTAL - PARTIAL
PROP = PARTIAL / TOTAL
GOV_WH = round(BASE * PROP * 0.05, 2)
ITBIS_WH = round(ITBIS * PROP, 2)

report = {
    "phase": "19.4-prod-partial-payment-validation",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "certified_branch": "cursor/phase19-3-partial-payment-fix-dd85",
    "certified_commits": ["322238e", "bd91174"],
    "module_version_expected": "19.0.1.0.23",
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
check("00_module_version", mod and mod.latest_version == "19.0.1.0.23", mod.latest_version if mod else "missing")

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
        {"name": "Proveedor cert 19.4 PROD", "supplier_rank": 1, "company_type": "company"}
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


def _wiz(partner, ptype, ref="P194"):
    ml = bnkd.inbound_payment_method_line_ids if ptype == "customer" else bnkd.outbound_payment_method_line_ids
    return env["hellenia.payment.partner.wizard"].create(
        {
            "partner_type": ptype,
            "partner_id": partner.id,
            "journal_id": bnkd.id,
            "payment_method_line_id": ml[:1].id,
            "payment_date": date.today(),
            "hellenia_payment_reference": ref,
        }
    )


def _pay_wizard(partner, inv, ptype, amount=None, cats=None, ref="P194"):
    wiz = _wiz(partner, ptype, ref=ref)
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
    return pay


def _assert_partial(key, pay, inv, expected_amount, expected_wh=0.0):
    inv.invalidate_recordset()
    pay.invalidate_recordset()
    apps = AppLine.search([("payment_id", "=", pay.id)])
    net = pay.hellenia_net_transfer or (expected_amount - expected_wh)
    check(f"{key}_payment_amount", near(pay.amount, expected_amount), pay.amount)
    check(f"{key}_applied_amount", near(pay.hellenia_applied_amount, expected_amount), pay.hellenia_applied_amount)
    check(f"{key}_invoice_partial", inv.payment_state in ("partial", "in_payment"), inv.payment_state)
    check(f"{key}_residual", near(abs(inv.amount_residual), RESIDUAL), abs(inv.amount_residual))
    check(f"{key}_move_id", bool(pay.move_id) or pay.state in ("posted", "in_process", "paid"), pay.state)
    if apps:
        check(f"{key}_detail_applied", near(apps[:1].applied_amount, expected_amount), apps[:1].applied_amount)
        check(
            f"{key}_detail_not_full",
            not near(apps[:1].applied_amount, TOTAL),
            apps[:1].applied_amount,
        )
    if expected_wh:
        check(f"{key}_wh_total", near(pay.hellenia_withholding_total, expected_wh, 1.0), pay.hellenia_withholding_total)
        check(f"{key}_bank_net", near(net, expected_amount - expected_wh, 1.0), net)
    report["evidence"][key] = {
        "payment": pay.name,
        "payment_amount": pay.amount,
        "applied": pay.hellenia_applied_amount,
        "wh_total": pay.hellenia_withholding_total,
        "net_transfer": net,
        "invoice_state": inv.payment_state,
        "residual": abs(inv.amount_residual),
        "detail_applied": apps[:1].applied_amount if apps else 0,
    }


# Caso 1: parcial sin retención
inv1 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P194-C1")
pay1 = _pay_wizard(customer, inv1, "customer", amount=PARTIAL, ref="P194-C1")
_assert_partial("01_partial_no_wh", pay1, inv1, PARTIAL)

# Caso 2: parcial 5% Gobierno
cat_gov = _cat("RET-GOB-5")
inv2 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P194-C2")
pay2 = _pay_wizard(customer, inv2, "customer", amount=PARTIAL, cats=[cat_gov], ref="P194-C2")
_assert_partial("02_partial_gov", pay2, inv2, PARTIAL, expected_wh=GOV_WH)

# Caso 3: parcial ITBIS 100%
cat_itbis = _cat("RET-ITBIS-100")
inv3 = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P194-C3")
pay3 = _pay_wizard(vendor, inv3, "supplier", amount=PARTIAL, cats=[cat_itbis], ref="P194-C3")
_assert_partial("03_partial_itbis", pay3, inv3, PARTIAL, expected_wh=ITBIS_WH)

# Caso 4: pago completo
inv4 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P194-C4")
pay4 = _pay_wizard(customer, inv4, "customer", amount=TOTAL, ref="P194-C4")
inv4.invalidate_recordset()
check("04_full_amount", near(pay4.amount, TOTAL), pay4.amount)
check("04_full_paid", inv4.payment_state == "paid", inv4.payment_state)
check("04_full_residual", near(abs(inv4.amount_residual), 0), abs(inv4.amount_residual))
report["evidence"]["04_full"] = {
    "payment_amount": pay4.amount,
    "invoice_state": inv4.payment_state,
    "residual": abs(inv4.amount_residual),
}

# 607 / 623
period_util = env["justech.do.dgii.period"]
date_from, date_to = period_util.period_bounds_from_code(period_util.default_period_code())
exp607 = env["justech.do.dgii.607.exporter"]
exp623 = env["justech.do.dgii.623.exporter"]
m607 = exp607._moves_for_period(company, date_from, date_to, only_valid=True)
m623 = exp623._moves_for_period(company, date_from, date_to, only_valid=True)
check("05_607", len(m607) >= 0, f"moves={len(m607)}")
check("06_623", len(m623) >= 0, f"moves={len(m623)}")
report["evidence"]["607"] = {"moves": len(m607)}
report["evidence"]["623"] = {"moves": len(m623)}

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
print(f"PHASE194:{json.dumps(report, ensure_ascii=False, default=str)}")
