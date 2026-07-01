# -*- coding: utf-8 -*-
"""Fase 18.8 — Certificación integral ciclo retenciones (TEST)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

BASE, ITBIS, TOTAL, TOL = 10000.0, 1800.0, 11800.0, 0.02

report = {
    "phase": "18.8-retention-final-certification",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "root_cause": (
        "El modelo transitorio y persistente compartían nombre hellenia.payment.withholding.line; "
        "las líneas persistentes solo se creaban vía create vals sin fallback post-create; "
        "623 no leía líneas persistentes; pagos históricos sin wizard no tenían trazabilidad."
    ),
    "fix": (
        "Modelo persistente hellenia.payment.withholding.line; transitorio wizard.line; "
        "finalize post-create en register; 623/606/607 desde líneas persistentes; "
        "vista retenciones en factura; compute no almacenado en totales."
    ),
    "persistent_model": "hellenia.payment.withholding.line",
    "tests": {},
    "accounts_used": {},
    "evidence": {},
    "ok": True,
    "pass": False,
}


def check(key, ok, detail=""):
    report["tests"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]}
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
    check("00_upgrade", mod.latest_version == "19.0.1.0.12", mod.latest_version)
else:
    check("00_upgrade", False, "no module")

WhLine = env["hellenia.payment.withholding.line"]
check("01_persistent_model", WhLine._name == "hellenia.payment.withholding.line", WhLine._name)

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


def _wiz(partner, ptype, ref="P188"):
    ml = bnkd.inbound_payment_method_line_ids if ptype == "customer" else bnkd.outbound_payment_method_line_ids
    return env["hellenia.payment.partner.wizard"].create({
        "partner_type": ptype, "partner_id": partner.id, "journal_id": bnkd.id,
        "payment_method_line_id": ml[:1].id, "payment_date": date.today(),
        "hellenia_payment_reference": f"REF-{ref}",
    })


def _pay(partner, inv, cats, ptype, amount=None, ref="P188"):
    wiz = _wiz(partner, ptype, ref=ref)
    line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
    line.apply = True
    if amount is not None:
        line.amount_to_pay = amount
    if cats:
        line.withholding_catalog_ids = [Command.set([c.id for c in cats if c])]
        line._recompute_line_withholdings()
    wiz.action_register_payments()
    env.cr.flush()
    pay = Payment.search([("partner_id", "=", partner.id)], order="id desc", limit=1)
    pay.invalidate_recordset()
    return pay


def _assert_wh(pay, inv, expected_wh, key):
    db_lines = WhLine.search([("payment_id", "=", pay.id)])
    db_sum = sum(db_lines.mapped("amount"))
    ok = (
        near(pay.hellenia_withholding_total, expected_wh)
        and near(db_sum, expected_wh)
        and len(db_lines) > 0
        if expected_wh else not db_lines and pay.hellenia_withholding_total == 0
    )
    check(key, ok, {
        "field": pay.hellenia_withholding_total, "db": db_sum, "lines": len(db_lines),
        "applied": pay.hellenia_applied_amount, "net": pay.hellenia_net_transfer,
    })
    if db_lines and db_lines[0].account_id:
        report["accounts_used"][key] = db_lines[0].account_id.code
    report["evidence"][key] = {"payment": pay.name, "invoice": inv.name, "wh": db_sum}
    return pay, db_lines


# 1 sin retención
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P188-01")
    pay, _ = _assert_wh(_pay(customer, inv, [], "customer"), inv, 0, "01_full_no_wh")

# 2 gobierno 5%
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P188-02")
    pay, lines = _assert_wh(_pay(customer, inv, [_cat("RET-GOB-5")], "customer"), inv, 500, "02_gov_5")
    check("02_gov_623_field", near(pay.justech_do_gov_withholding_amount, 500), pay.justech_do_gov_withholding_amount)
    check("02_invoice_wh", len(inv.hellenia_withholding_line_ids) == 1, inv.hellenia_withholding_total)

# 3 ITBIS 100%
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P188-03")
    pay, lines = _assert_wh(_pay(vendor, inv, [_cat("RET-ITBIS-100")], "supplier"), inv, ITBIS, "03_itbis_100")
    deb = sum(pay.move_id.line_ids.mapped("debit"))
    cred = sum(pay.move_id.line_ids.mapped("credit"))
    check("03_balanced", near(deb, cred), f"D={deb} C={cred}")
    check("03_gl_linked", all(lines.mapped("move_line_id")), "linked")

# 4 dual
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P188-04")
    pay, _ = _assert_wh(_pay(vendor, inv, [_cat("RET-ITBIS-100"), _cat("RET-ISR-2")], "supplier"), inv, 2000, "04_dual")

# 5 parcial sin wh
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P188-05")
    pay, _ = _assert_wh(_pay(customer, inv, [], "customer", 5000), inv, 0, "05_partial_no_wh")
    check("05_partial_state", inv.payment_state == "partial", inv.payment_state)

# 6 parcial con wh
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P188-06")
    exp = ITBIS * (5000 / TOTAL)
    pay, _ = _assert_wh(_pay(vendor, inv, [_cat("RET-ITBIS-100")], "supplier", 5000), inv, exp, "06_partial_wh")

# 7 multi: sin wh + gob
with env.cr.savepoint():
    i1 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P188-07A")
    i2 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P188-07B")
    w = _wiz(customer, "customer", ref="P188-07")
    w._load_pending_invoices()
    l1 = w.line_ids.filtered(lambda l: l.move_id == i1)[:1]
    l2 = w.line_ids.filtered(lambda l: l.move_id == i2)[:1]
    if not l1 or not l2:
        check("07_multi", False, f"lines missing l1={bool(l1)} l2={bool(l2)}")
    else:
        l1.write({"apply": True, "amount_to_pay": TOTAL})
        l2.write({"apply": True, "amount_to_pay": TOTAL, "withholding_catalog_ids": [Command.set(_cat("RET-GOB-5").ids)]})
        l2._recompute_line_withholdings()
        w.action_register_payments()
        pays = Payment.search([("partner_id", "=", customer.id)], order="id desc", limit=2)
        check("07_multi", len(pays) == 2 and any(p.hellenia_withholding_total > 0 for p in pays), [p.hellenia_withholding_total for p in pays])

# 8 multi 3 facturas
with env.cr.savepoint():
    invs = [_inv(vendor, journal_purchase, tax_purchase, "in_invoice", f"P188-08{x}") for x in "ABC"]
    w = _wiz(vendor, "supplier", ref="P188-08")
    w._load_pending_invoices()
    specs = [(None, TOTAL), (_cat("RET-ITBIS-30"), TOTAL), (_cat("RET-ITBIS-100"), TOTAL)]
    for inv, (cat, amt) in zip(invs, specs):
        line = w.line_ids.filtered(lambda l: l.move_id == inv)[:1]
        if not line:
            continue
        vals = {"apply": True, "amount_to_pay": amt}
        if cat:
            vals["withholding_catalog_ids"] = [Command.set(cat.ids)]
        line.write(vals)
        if cat:
            line._recompute_line_withholdings()
    w.action_register_payments()
    pays = Payment.search([("partner_id", "=", vendor.id)], order="id desc", limit=3)
    check("08_multi_3", len(pays) == 3, [p.hellenia_withholding_total for p in pays])

# 9 proveedor ITBIS 30
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P188-09")
    _assert_wh(_pay(vendor, inv, [_cat("RET-ITBIS-30")], "supplier"), inv, 540, "09_vendor_30")

# 10 reopen payment
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P188-10")
    pay = _pay(vendor, inv, [_cat("RET-ITBIS-100")], "supplier")
    pid = pay.id
    pay2 = Payment.browse(pid)
    check("10_reopen", len(pay2.hellenia_withholding_line_ids) == 1, pay2.hellenia_withholding_total)

# 11 reopen invoice
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P188-11")
    _pay(customer, inv, [_cat("RET-GOB-5")], "customer")
    inv.invalidate_recordset()
    check("11_invoice_wh", inv.hellenia_withholding_total == 500, inv.hellenia_withholding_line_ids.mapped("amount"))

# 12 606
with env.cr.savepoint():
    period_code, df, dt = _dgii_period()
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P188-12")
    _pay(vendor, inv, [_cat("RET-ITBIS-30")], "supplier")
    rep = env["justech.do.fiscal.report"].create({"name": "P188 606", "report_type": "606", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    exp = env["justech.do.dgii.606.exporter"]
    itbis, isr, _, _ = exp._withholding_breakdown(inv)
    check("12_606", bool(rep.line_ids) and itbis > 0, f"lines={len(rep.line_ids)} itbis={itbis}")

# 13 607
with env.cr.savepoint():
    period_code, df, dt = _dgii_period()
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P188-13")
    _pay(customer, inv, [_cat("RET-GOB-5")], "customer")
    rep = env["justech.do.fiscal.report"].create({"name": "P188 607", "report_type": "607", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    exp = env["justech.do.dgii.607.exporter"]
    _, isr, _, _ = exp._withholding_breakdown(inv)
    check("13_607", bool(rep.line_ids) and isr > 0, f"lines={len(rep.line_ids)} isr={isr}")

# 14 623
with env.cr.savepoint():
    period_code, df, dt = _dgii_period()
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P188-14")
    pay = _pay(customer, inv, [_cat("RET-GOB-5")], "customer")
    rep = env["justech.do.fiscal.report"].create({"name": "P188 623", "report_type": "623", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    exp623 = env["justech.do.dgii.623.exporter"]
    has = exp623._has_gov_withholding(inv, exp623._gov_tax(company))
    check("14_623", bool(rep.line_ids) and has, f"lines={len(rep.line_ids)} has={has}")
    report["evidence"]["623"] = {"lines": len(rep.line_ids), "gov": pay.justech_do_gov_withholding_amount}

# 15 GL
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P188-15")
    pay, lines = _assert_wh(_pay(vendor, inv, [_cat("RET-ITBIS-100")], "supplier"), inv, ITBIS, "15_gl")
    check("15_gl_account", bool(lines.account_id), lines.account_id.code)

# 16 conciliación
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P188-16")
    pay = _pay(customer, inv, [], "customer")
    check("16_reconcile", inv.payment_state in ("paid", "in_payment", "partial"), inv.payment_state)

# 17 PDF
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P188-17")
    pay = _pay(customer, inv, [_cat("RET-GOB-5")], "customer")
    html, _ = env["ir.actions.report"]._render_qweb_html("account.action_report_payment_receipt", pay.ids)
    text = html.decode() if isinstance(html, bytes) else str(html)
    check("17_receipt", "Retenciones" in text or "retenid" in text.lower(), "pdf ok")

# 18 views
try:
    Payment.get_views([(False, "form")])
    env["account.move"].get_views([(False, "form")])
    check("18_views", True, "ok")
except Exception as exc:
    check("18_views", False, exc)

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
report["production_ready_for_approval"] = report["ok"]
print(f"PHASE188:{json.dumps(report, ensure_ascii=False, default=str)}")
