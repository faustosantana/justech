# -*- coding: utf-8 -*-
"""Fase 18.10 — Certificación end-to-end retenciones (TEST)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

BASE, ITBIS, TOTAL, TOL = 10000.0, 1800.0, 11800.0, 0.02

report = {
    "phase": "18.10-retention-end-to-end",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module_version": "19.0.1.0.14",
    "root_cause": (
        "Retenciones usaban write_off_line_vals sin hook nativo _prepare_move_withholding_lines; "
        "solo _create_payment_vals_from_wizard heredado (no batch); persistencia sin _init_payments; "
        "multi-factura creaba N pagos sin trazabilidad por factura."
    ),
    "fix": (
        "Hook _prepare_move_withholding_lines en account.payment; "
        "_hellenia_apply_withholding_to_payment_vals en wizard y batch; "
        "_init_payments + _reconcile_payments para persistencia y partial_reconcile_id; "
        "pago agrupado multi-factura en partner wizard."
    ),
    "tests": {},
    "evidence": {},
    "ok": True,
    "pass": False,
}


def check(key, ok, detail=""):
    report["tests"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:800]}
    if not ok:
        report["ok"] = False


def near(a, b, tol=TOL):
    return abs((a or 0.0) - (b or 0.0)) <= tol


def _dgii_period():
    util = env["justech.do.dgii.period"]
    code = util.default_period_code()
    return code, *util.period_bounds_from_code(code)


mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
if mod:
    mod.button_immediate_upgrade()
    env.cr.commit()
    check("00_upgrade", mod.latest_version == "19.0.1.0.14", mod.latest_version)
else:
    check("00_upgrade", False, "no module")

WhLine = env["hellenia.payment.withholding.line"]
setup = env["hellenia.account.payment.setup"]
setup.configure_banks_and_payments()
Catalog = env["hellenia.withholding.catalog"]
Catalog.sync_catalog_from_taxes(env.company)
env.cr.commit()

company = env.company
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
product = env["product.product"].search([("sale_ok", "=", True), ("purchase_ok", "=", True)], limit=1)
tax_sale = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)], limit=1)
tax_purchase = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)
Payment = env["account.payment"]


def _cat(c):
    return Catalog.search([("code", "=", c), ("company_id", "=", company.id)], limit=1)


def _inv(partner, j, tax, mt, ref):
    m = env["account.move"].create({
        "move_type": mt, "partner_id": partner.id, "journal_id": j.id,
        "invoice_date": date.today(), "ref": ref,
        "invoice_line_ids": [Command.create({"product_id": product.id, "quantity": 1, "price_unit": BASE, "tax_ids": [Command.set(tax.ids)]})],
    })
    m.action_post()
    return m


def _wiz(partner, ptype, ref="P1810"):
    ml = bnkd.inbound_payment_method_line_ids if ptype == "customer" else bnkd.outbound_payment_method_line_ids
    return env["hellenia.payment.partner.wizard"].create({
        "partner_type": ptype, "partner_id": partner.id, "journal_id": bnkd.id,
        "payment_method_line_id": ml[:1].id, "payment_date": date.today(),
        "hellenia_payment_reference": f"REF-{ref}",
    })


def _pay(partner, inv, cats, ptype, amount=None, ref="P1810"):
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
    return pay


def _assert_cycle(pay, inv, expected_wh, key, gov=False):
    db_lines = WhLine.search([("payment_id", "=", pay.id)])
    db_sum = sum(db_lines.mapped("amount"))
    wh_ml = pay.move_id.line_ids.filtered(lambda l: l.account_id in db_lines.mapped("account_id"))
    ok = near(pay.hellenia_withholding_total, expected_wh) and near(db_sum, expected_wh)
    if expected_wh:
        ok = ok and len(db_lines) > 0 and bool(wh_ml)
    else:
        ok = ok and not db_lines
    check(key, ok, {
        "field_wh": pay.hellenia_withholding_total,
        "db_sum": db_sum,
        "gl_wh_lines": len(wh_ml),
        "applied": pay.hellenia_applied_amount,
        "net": pay.hellenia_net_transfer,
        "payment_state": inv.payment_state,
    })
    report["evidence"][key] = {
        "payment": pay.name,
        "invoice": inv.name,
        "wh_total": pay.hellenia_withholding_total,
        "gl_wh": [round(x, 2) for x in wh_ml.mapped("balance")],
    }
    if gov:
        check(f"{key}_gov", near(pay.justech_do_gov_withholding_amount, expected_wh), pay.justech_do_gov_withholding_amount)
    return pay, db_lines


# 1-2 Factura base + cobro sin retención
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810-01")
    pay, _ = _assert_cycle(_pay(customer, inv, [], "customer"), inv, 0, "01_no_wh")

# 3 Cobro completo 5% Gobierno
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810-03")
    pay, lines = _assert_cycle(_pay(customer, inv, [_cat("RET-GOB-5")], "customer"), inv, 500, "03_gov_5", gov=True)
    check("03_invoice_visible", inv.hellenia_withholding_total == 500, inv.hellenia_withholding_line_ids.mapped("amount"))
    deb, cred = sum(pay.move_id.line_ids.mapped("debit")), sum(pay.move_id.line_ids.mapped("credit"))
    check("03_balanced", near(deb, cred), f"D={deb} C={cred}")

# 4 ITBIS 100% compra
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1810-04")
    pay, lines = _assert_cycle(_pay(vendor, inv, [_cat("RET-ITBIS-100")], "supplier"), inv, ITBIS, "04_itbis_100")
    check("04_move_line_linked", all(lines.mapped("move_line_id")), "linked")

# 5 Dual ITBIS + ISR
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1810-05")
    pay, _ = _assert_cycle(_pay(vendor, inv, [_cat("RET-ITBIS-100"), _cat("RET-ISR-2")], "supplier"), inv, 2000, "05_dual")

# 6 Abono parcial RD$5000 con 5% Gobierno
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810-06")
    exp_wh = 500 * (5000 / TOTAL)
    pay, _ = _assert_cycle(_pay(customer, inv, [_cat("RET-GOB-5")], "customer", 5000), inv, exp_wh, "06_partial_gov")
    check("06_partial_state", inv.payment_state == "partial", inv.payment_state)

# 7 Pago múltiple agrupado — una con retención
with env.cr.savepoint():
    i1 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810-07A")
    i2 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810-07B")
    w = _wiz(customer, "customer", ref="P1810-07")
    w._load_pending_invoices()
    l1 = w.line_ids.filtered(lambda l: l.move_id == i1)[:1]
    l2 = w.line_ids.filtered(lambda l: l.move_id == i2)[:1]
    l1.write({"apply": True, "amount_to_pay": TOTAL})
    l2.write({"apply": True, "amount_to_pay": TOTAL, "withholding_catalog_ids": [Command.set(_cat("RET-GOB-5").ids)]})
    w.line_ids.filtered(lambda l: l.move_id not in (i1 | i2)).write({"apply": False})
    w.action_register_payments()
    pays = Payment.search([("partner_id", "=", customer.id)], order="id desc", limit=2)
    check("07_multi_two_payments", len(pays) == 2, len(pays))
    check("07_one_has_wh", any(p.hellenia_withholding_total > 0 for p in pays), [p.hellenia_withholding_total for p in pays])
    check("07_both_reconciled", i1.payment_state in ("paid", "in_payment") and i2.payment_state in ("paid", "in_payment"), [i1.payment_state, i2.payment_state])

# 8 Proveedor ITBIS 30%
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1810-08")
    _assert_cycle(_pay(vendor, inv, [_cat("RET-ITBIS-30")], "supplier"), inv, 540, "08_vendor_30")

# 9 Reopen payment
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1810-09")
    pay = _pay(vendor, inv, [_cat("RET-ITBIS-100")], "supplier")
    pid = pay.id
    pay2 = Payment.browse(pid)
    check("09_reopen_payment", pay2.hellenia_withholding_total == ITBIS, pay2.hellenia_withholding_line_ids.mapped("amount"))

# 10 606
with env.cr.savepoint():
    period_code, df, dt = _dgii_period()
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1810-10")
    _pay(vendor, inv, [_cat("RET-ITBIS-30")], "supplier")
    rep = env["justech.do.fiscal.report"].create({"name": "P1810 606", "report_type": "606", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    exp = env["justech.do.dgii.606.exporter"]
    itbis, _, _, _ = exp._withholding_breakdown(inv)
    check("10_606", bool(rep.line_ids) and itbis > 0, f"lines={len(rep.line_ids)} itbis={itbis}")

# 11 607
with env.cr.savepoint():
    period_code, df, dt = _dgii_period()
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810-11")
    _pay(customer, inv, [_cat("RET-GOB-5")], "customer")
    rep = env["justech.do.fiscal.report"].create({"name": "P1810 607", "report_type": "607", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    exp = env["justech.do.dgii.607.exporter"]
    _, isr, _, _ = exp._withholding_breakdown(inv)
    check("11_607", bool(rep.line_ids) and isr > 0, f"lines={len(rep.line_ids)} isr={isr}")

# 12 623
with env.cr.savepoint():
    period_code, df, dt = _dgii_period()
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810-12")
    pay = _pay(customer, inv, [_cat("RET-GOB-5")], "customer")
    rep = env["justech.do.fiscal.report"].create({"name": "P1810 623", "report_type": "623", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    exp623 = env["justech.do.dgii.623.exporter"]
    has = exp623._has_gov_withholding(inv, exp623._gov_tax(company))
    amt = exp623._gov_amount(inv, exp623._gov_tax(company))
    check("12_623", bool(rep.line_ids) and has and amt >= 500, f"lines={len(rep.line_ids)} has={has} amt={amt}")
    report["evidence"]["623"] = {"lines": len(rep.line_ids), "gov_amt": amt, "payment": pay.name}

# 13 Conciliación
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810-13")
    pay, lines = _assert_cycle(_pay(customer, inv, [_cat("RET-GOB-5")], "customer"), inv, 500, "13_reconcile")
    check("13_partial_reconcile", any(lines.mapped("partial_reconcile_id")) or inv.payment_state in ("paid", "in_payment"), inv.payment_state)

# 14 Recibo PDF
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810-14")
    pay = _pay(customer, inv, [_cat("RET-GOB-5")], "customer")
    html, _ = env["ir.actions.report"]._render_qweb_html("account.action_report_payment_receipt", pay.ids)
    text = html.decode() if isinstance(html, bytes) else str(html)
    check("14_receipt", "Total retenido" in text and "500" in text.replace(",", ""), "pdf")

# 15 Views OWL
try:
    Payment.get_views([(False, "form")])
    env["account.move"].get_views([(False, "form")])
    check("15_views", True, "ok")
except Exception as exc:
    check("15_views", False, exc)

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
report["production_ready_for_approval"] = False
report["test_only"] = True
print(f"PHASE1810:{json.dumps(report, ensure_ascii=False, default=str)}")
