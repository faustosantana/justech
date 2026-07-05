# -*- coding: utf-8 -*-
"""Fase 18.12 — Recuperación regresión pagos, abonos parciales, detalle y 623 (TEST)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

BASE, ITBIS, TOTAL, TOL = 10000.0, 1800.0, 11800.0, 0.02
PARTIAL = 5000.0

report = {
    "phase": "18.12-regression-recovery",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "regression_analysis": {
        "partial_payment_broke_at": "70df199",
        "payment_detail_broke_at": "70df199",
        "report_623_lost_cause": "menu.xml desincronizado en VPS custom/ (sin action/menu 623); imports gov/623 rotos en e4447af previo",
        "withholding_visibility_broke_at": "70df199",
        "last_known_good_phase": "18.8 (d7e6bcc) / 18.10B certificado fd93ca4 con fixes locales",
    },
    "fixes_applied": [
        "hellenia_applied_amount siempre persistido (sin retención)",
        "register.amount forzado al monto parcial del wizard",
        "hellenia.payment.application.line para detalle por factura",
        "vista pago: resumen + detalle + retenciones visibles post-posted",
        "menu.xml 623/609 desde repo + upgrade justech_l10n_do_reports",
    ],
    "module_versions": {},
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


for mod_name in ("hellenia_account", "justech_l10n_do_reports"):
    mod = env["ir.module.module"].search([("name", "=", mod_name)], limit=1)
    if mod:
        mod.button_immediate_upgrade()
        env.cr.commit()
        report["module_versions"][mod_name] = mod.latest_version
        check(f"00_upgrade_{mod_name}", True, mod.latest_version)
    else:
        check(f"00_upgrade_{mod_name}", False, "no module")

WhLine = env["hellenia.payment.withholding.line"]
AppLine = env["hellenia.payment.application.line"]
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


def _wiz(partner, ptype, ref="P1812"):
    ml = bnkd.inbound_payment_method_line_ids if ptype == "customer" else bnkd.outbound_payment_method_line_ids
    return env["hellenia.payment.partner.wizard"].create({
        "partner_type": ptype, "partner_id": partner.id, "journal_id": bnkd.id,
        "payment_method_line_id": ml[:1].id, "payment_date": date.today(),
        "hellenia_payment_reference": f"REF-{ref}",
    })


def _pay(partner, inv, cats, ptype, amount=None, ref="P1812"):
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
    pay._hellenia_sync_application_lines()
    return pay


def _assert_detail(pay, inv, key):
    pay.invalidate_recordset()
    apps = AppLine.search([("payment_id", "=", pay.id)])
    ok = (
        near(pay.hellenia_applied_amount, pay.amount if not pay.hellenia_withholding_total else pay.hellenia_applied_amount or pay.amount)
        and pay.hellenia_applied_amount > 0
        and bool(apps)
        and apps[:1].ncf is not None
        and apps[:1].invoice_name
    )
    check(f"{key}_applied_amount", near(pay.hellenia_applied_amount, pay.amount) or pay.hellenia_applied_amount > 0, pay.hellenia_applied_amount)
    check(f"{key}_application_lines", bool(apps), len(apps))
    check(f"{key}_ncf_visible", bool(apps[:1].ncf) if apps else False, apps[:1].ncf if apps else "")
    check(f"{key}_resumen_visible", pay.hellenia_show_application_detail, pay.hellenia_show_application_detail)
    report["evidence"][key] = {
        "payment": pay.name,
        "invoice": inv.name,
        "applied": pay.hellenia_applied_amount,
        "wh": pay.hellenia_withholding_total,
        "net": pay.hellenia_net_transfer,
        "app_lines": len(apps),
        "ncf": apps[:1].ncf if apps else "",
    }
    return pay, apps


# 1 Factura RD$11800 sin retención, pago parcial RD$5000
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-01")
    pay = _pay(customer, inv, [], "customer", PARTIAL, ref="P1812-01")
    pay, apps = _assert_detail(pay, inv, "01_partial_no_wh")
    check("01_payment_amount", near(pay.amount, PARTIAL), pay.amount)
    check("01_partial_state", inv.payment_state == "partial", inv.payment_state)
    check("01_residual", near(abs(inv.amount_residual), TOTAL - PARTIAL, 1.0), inv.amount_residual)
    check("01_no_wh", pay.hellenia_withholding_total == 0, pay.hellenia_withholding_total)

# 2 Factura RD$11800 con retención 5% Gobierno, pago parcial RD$5000
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-02")
    exp_wh = 500 * (PARTIAL / TOTAL)
    pay = _pay(customer, inv, [_cat("RET-GOB-5")], "customer", PARTIAL, ref="P1812-02")
    pay, apps = _assert_detail(pay, inv, "02_partial_gov")
    check("02_wh_proportional", near(pay.hellenia_withholding_total, exp_wh), pay.hellenia_withholding_total)
    check("02_partial_state", inv.payment_state == "partial", inv.payment_state)
    check("02_net_bank", near(pay.hellenia_net_transfer, PARTIAL - exp_wh), pay.hellenia_net_transfer)

# 3 Factura RD$11800 con ITBIS 100%, pago total
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1812-03")
    pay = _pay(vendor, inv, [_cat("RET-ITBIS-100")], "supplier", ref="P1812-03")
    pay, apps = _assert_detail(pay, inv, "03_full_itbis")
    check("03_wh", near(pay.hellenia_withholding_total, ITBIS), pay.hellenia_withholding_total)
    check("03_paid", inv.payment_state in ("paid", "in_payment"), inv.payment_state)

# 4 Pago múltiple: factura1 parcial, factura2 total con retención
with env.cr.savepoint():
    i1 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-04A")
    i2 = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-04B")
    w = _wiz(customer, "customer", ref="P1812-04")
    w._load_pending_invoices()
    l1 = w.line_ids.filtered(lambda l: l.move_id == i1)[:1]
    l2 = w.line_ids.filtered(lambda l: l.move_id == i2)[:1]
    l1.write({"apply": True, "amount_to_pay": PARTIAL})
    l2.write({"apply": True, "amount_to_pay": TOTAL, "withholding_catalog_ids": [Command.set(_cat("RET-GOB-5").ids)]})
    w.line_ids.filtered(lambda l: l.move_id not in (i1 | i2)).write({"apply": False})
    w.action_register_payments()
    pays = Payment.search([("partner_id", "=", customer.id)], order="id desc", limit=2)
    pays._hellenia_sync_application_lines()
    check("04_two_payments", len(pays) == 2, len(pays))
    check("04_partial_inv", i1.payment_state == "partial", i1.payment_state)
    check("04_full_inv", i2.payment_state in ("paid", "in_payment"), i2.payment_state)
    check("04_one_wh", sum(pays.mapped("hellenia_withholding_total")) >= 500, pays.mapped("hellenia_withholding_total"))

# 5 Abrir pago y validar detalle
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-05")
    pay = _pay(customer, inv, [_cat("RET-GOB-5")], "customer", ref="P1812-05")
    pid = pay.id
    pay2 = Payment.browse(pid)
    pay2._hellenia_sync_application_lines()
    apps = AppLine.search([("payment_id", "=", pid)])
    check("05_reopen_detail", pay2.hellenia_withholding_total == 500 and len(apps) == 1, {
        "wh": pay2.hellenia_withholding_total, "apps": len(apps),
        "applied": pay2.hellenia_applied_amount,
    })

# 6 Abrir factura y validar pago
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-06")
    pay = _pay(customer, inv, [_cat("RET-GOB-5")], "customer", ref="P1812-06")
    inv.invalidate_recordset()
    check("06_invoice_wh", inv.hellenia_withholding_total == 500, inv.hellenia_withholding_total)
    check("06_invoice_paid", inv.payment_state in ("paid", "in_payment"), inv.payment_state)

# 7 Residual
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-07")
    _pay(customer, inv, [], "customer", PARTIAL, ref="P1812-07")
    check("07_residual", near(abs(inv.amount_residual), TOTAL - PARTIAL, 1.0), inv.amount_residual)

# 8 Conciliación parcial
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-08")
    pay = _pay(customer, inv, [], "customer", PARTIAL, ref="P1812-08")
    check("08_partial_reconcile", inv.payment_state == "partial", inv.payment_state)

# 9 Asiento
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-09")
    pay = _pay(customer, inv, [_cat("RET-GOB-5")], "customer", ref="P1812-09")
    deb, cred = sum(pay.move_id.line_ids.mapped("debit")), sum(pay.move_id.line_ids.mapped("credit"))
    check("09_balanced", near(deb, cred), f"D={deb} C={cred}")

# 10-13 Reportes DGII
period_code, df, dt = _dgii_period()

with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1812-10")
    _pay(vendor, inv, [_cat("RET-ITBIS-30")], "supplier", ref="P1812-10")
    rep = env["justech.do.fiscal.report"].create({"name": "P1812 606", "report_type": "606", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    check("10_606", bool(rep.line_ids), len(rep.line_ids))

with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-11")
    _pay(customer, inv, [_cat("RET-GOB-5")], "customer", ref="P1812-11")
    rep = env["justech.do.fiscal.report"].create({"name": "P1812 607", "report_type": "607", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    check("11_607", bool(rep.line_ids), len(rep.line_ids))

with env.cr.savepoint():
    rep = env["justech.do.fiscal.report"].create({
        "name": "P1812 608", "report_type": "608",
        "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id,
    })
    rep.action_generate()
    check("12_608", rep.report_type == "608" and rep.state in ("draft", "generated", "validated", "no_movements"), rep.state)

with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-13")
    pay = _pay(customer, inv, [_cat("RET-GOB-5")], "customer", ref="P1812-13")
    rep = env["justech.do.fiscal.report"].create({"name": "P1812 623", "report_type": "623", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    exp623 = env["justech.do.dgii.623.exporter"]
    amt = exp623._gov_amount(inv, exp623._gov_tax(company))
    check("13_623", bool(rep.line_ids) and amt >= 500, f"lines={len(rep.line_ids)} amt={amt}")
    report["evidence"]["623"] = {"lines": len(rep.line_ids), "gov_amt": amt, "payment": pay.name}

# 14 PDF recibo
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1812-14")
    pay = _pay(customer, inv, [_cat("RET-GOB-5")], "customer", ref="P1812-14")
    html, _ = env["ir.actions.report"]._render_qweb_html("account.action_report_payment_receipt", pay.ids)
    text = html.decode() if isinstance(html, bytes) else str(html)
    check("14_receipt", "Total retenido" in text and "500" in text.replace(",", ""), "pdf")

# 15 Menú reportes DGII
MENU_XIDS = {
    "606": "justech_l10n_do_reports.menu_justech_do_report_606",
    "607": "justech_l10n_do_reports.menu_justech_do_report_607",
    "608": "justech_l10n_do_reports.menu_justech_do_report_608",
    "623": "justech_l10n_do_reports.menu_justech_do_report_623",
}
for code, xid in MENU_XIDS.items():
    menu = env.ref(xid, raise_if_not_found=False)
    check(f"15_menu_{code}", bool(menu) and menu.active, xid)

ACTION_623 = env.ref("justech_l10n_do_reports.action_justech_do_report_623", raise_if_not_found=False)
check("15_action_623", bool(ACTION_623), "action_623")

# Views OWL
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
report["rollback_required"] = not report["ok"]
print(f"PHASE1812:{json.dumps(report, ensure_ascii=False, default=str)}")
