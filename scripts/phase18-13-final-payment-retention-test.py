# -*- coding: utf-8 -*-
"""Fase 18.13 — Certificación estricta pagos, abonos parciales y retenciones (TEST)."""
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
    "phase": "18.13-final-payment-retention",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "root_cause": (
        "Retenciones no cerraban ciclo: compute UI sin recálculo server-side; "
        "totales no almacenados; stamp 623 antes de conciliación; "
        "623 filtraba solo affects_623; register sin selector catálogo; "
        "parcial sin custom_user_amount nativo."
    ),
    "architecture": (
        "Hook nativo _prepare_move_withholding_lines; payment.amount=bruto; "
        "hellenia.payment.withholding.line persistente; stamp gov post-reconcile; "
        "tres caminos convergen en account.payment.register."
    ),
    "odoo_methods_analyzed": [
        "account.payment.register._create_payment_vals_from_wizard",
        "account.payment.register._init_payments",
        "account.payment.register._reconcile_payments",
        "account.payment._prepare_move_withholding_lines",
        "account.payment._prepare_move_lines_per_type",
        "account.payment.create",
    ],
    "module_versions": {},
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
WhLine = env["hellenia.payment.withholding.line"]
AppLine = env["hellenia.payment.application.line"]


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


def _wiz(partner, ptype, ref="P1813"):
    ml = bnkd.inbound_payment_method_line_ids if ptype == "customer" else bnkd.outbound_payment_method_line_ids
    return env["hellenia.payment.partner.wizard"].create({
        "partner_type": ptype, "partner_id": partner.id, "journal_id": bnkd.id,
        "payment_method_line_id": ml[:1].id, "payment_date": date.today(),
        "hellenia_payment_reference": f"REF-{ref}",
    })


def _pay_partner(partner, inv, cats, ptype, amount=None, ref="P1813"):
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


def _pay_invoice(inv, cats, amount=None, ref="P1813-INV"):
    cat_gov = _cat("RET-GOB-5")
    ml = bnkd.inbound_payment_method_line_ids if inv.move_type == "out_invoice" else bnkd.outbound_payment_method_line_ids
    reg_vals = {
        "journal_id": bnkd.id,
        "payment_method_line_id": ml[:1].id,
        "payment_date": date.today(),
        "communication": ref,
        "hellenia_payment_reference": f"REF-{ref}",
    }
    if amount is not None:
        reg_vals["amount"] = amount
        if amount < abs(inv.amount_residual) - 0.01:
            reg_vals["custom_user_amount"] = amount
    if cats:
        reg_vals["hellenia_withholding_catalog_ids"] = [Command.set([c.id for c in cats if c])]
    register = env["account.payment.register"].with_context(
        active_model="account.move", active_ids=inv.ids
    ).create(reg_vals)
    pay = register._create_payments()
    env.cr.flush()
    pay.invalidate_recordset()
    return pay


def _assert_payment_cycle(pay, inv, expected_wh, key, partial=False):
    pay.invalidate_recordset()
    db_lines = WhLine.search([("payment_id", "=", pay.id)])
    db_sum = sum(db_lines.mapped("amount"))
    wh_accounts = db_lines.mapped("account_id")
    gl_wh = pay.move_id.line_ids.filtered(lambda l: l.account_id in wh_accounts) if pay.move_id else env["account.move.line"]
    gl_sum = sum(abs(x.balance) for x in gl_wh)
    apps = AppLine.search([("payment_id", "=", pay.id)])

    ok = (
        near(pay.hellenia_withholding_total, expected_wh)
        and near(db_sum, expected_wh)
        and pay.hellenia_applied_amount > 0
        and bool(apps)
        and apps[:1].ncf
    )
    if expected_wh > 0:
        ok = ok and len(db_lines) > 0 and gl_sum > 0 and near(gl_sum, expected_wh)
        ok = ok and all(db_lines.mapped("move_line_id"))
    deb, cred = sum(pay.move_id.line_ids.mapped("debit")), sum(pay.move_id.line_ids.mapped("credit"))
    ok = ok and near(deb, cred)

    check(f"{key}_wh_total", near(pay.hellenia_withholding_total, expected_wh), pay.hellenia_withholding_total)
    check(f"{key}_gl_wh", gl_sum > 0 if expected_wh else gl_sum == 0, gl_sum)
    check(f"{key}_persisted", near(db_sum, expected_wh), db_sum)
    check(f"{key}_applied", pay.hellenia_applied_amount > 0, pay.hellenia_applied_amount)
    check(f"{key}_detail", bool(apps) and apps[:1].ncf, len(apps))
    check(f"{key}_balanced", near(deb, cred), f"D={deb} C={cred}")

    if partial:
        check(f"{key}_partial", inv.payment_state == "partial", inv.payment_state)
        check(f"{key}_residual", near(abs(inv.amount_residual), TOTAL - PARTIAL, 1.0), inv.amount_residual)
    elif expected_wh >= 0 and not partial:
        check(f"{key}_paid", inv.payment_state in ("paid", "in_payment"), inv.payment_state)

    report["evidence"][key] = {
        "payment": pay.name,
        "invoice": inv.name,
        "ncf": apps[:1].ncf if apps else "",
        "applied": pay.hellenia_applied_amount,
        "wh_total": pay.hellenia_withholding_total,
        "net": pay.hellenia_net_transfer,
        "gl_wh": round(gl_sum, 2),
        "db_lines": len(db_lines),
    }
    return pay, db_lines


# 1 Base invoice
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-BASE")
    check("01_invoice_total", near(inv.amount_total, TOTAL), inv.amount_total)

# 2 Pago completo sin retención
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-02")
    pay, _ = _assert_payment_cycle(_pay_partner(customer, inv, [], "customer"), inv, 0, "02_full_no_wh")

# 3 Pago parcial sin retención
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-03")
    pay, _ = _assert_payment_cycle(_pay_partner(customer, inv, [], "customer", PARTIAL), inv, 0, "03_partial_no_wh", partial=True)
    check("03_payment_amount", near(pay.amount, PARTIAL), pay.amount)

# 4 Pago completo 5% Gobierno
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-04")
    pay, _ = _assert_payment_cycle(_pay_partner(customer, inv, [_cat("RET-GOB-5")], "customer"), inv, 500, "04_full_gov")
    check("04_gov_field", near(pay.justech_do_gov_withholding_amount, 500), pay.justech_do_gov_withholding_amount)

# 5 Pago parcial 5% Gobierno
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-05")
    exp_wh = 500 * (PARTIAL / TOTAL)
    pay, _ = _assert_payment_cycle(_pay_partner(customer, inv, [_cat("RET-GOB-5")], "customer", PARTIAL), inv, exp_wh, "05_partial_gov", partial=True)

# 6 ITBIS 100% compra total
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1813-06")
    pay, _ = _assert_payment_cycle(_pay_partner(vendor, inv, [_cat("RET-ITBIS-100")], "supplier"), inv, ITBIS, "06_itbis_100")

# 7 Dual Gobierno + ITBIS (compra: solo ITBIS aplica normalmente; gobierno es venta)
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-07")
    pay, _ = _assert_payment_cycle(_pay_partner(customer, inv, [_cat("RET-GOB-5")], "customer"), inv, 500, "07_gov_only")

# 8 Pago proveedor con retención ITBIS 30%
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1813-08")
    pay, _ = _assert_payment_cycle(_pay_partner(vendor, inv, [_cat("RET-ITBIS-30")], "supplier"), inv, 540, "08_vendor_30")

# 9 Pago desde factura (register nativo)
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-09")
    pay, _ = _assert_payment_cycle(_pay_invoice(inv, [_cat("RET-GOB-5")]), inv, 500, "09_from_invoice")

# 10 Pago desde Clientes → Pagos (partner wizard)
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-10")
    pay, _ = _assert_payment_cycle(_pay_partner(customer, inv, [_cat("RET-GOB-5")], "customer", ref="P1813-10"), inv, 500, "10_from_customer_menu")

# 11 Pago desde Proveedores → Pagos
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1813-11")
    pay, _ = _assert_payment_cycle(_pay_partner(vendor, inv, [_cat("RET-ITBIS-100")], "supplier", ref="P1813-11"), inv, ITBIS, "11_from_vendor_menu")

# 12 Reabrir pago — detalle persiste
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-12")
    pay = _pay_partner(customer, inv, [_cat("RET-GOB-5")], "customer")
    pid = pay.id
    pay2 = Payment.browse(pid)
    pay2.invalidate_recordset()
    check("12_reopen_wh", pay2.hellenia_withholding_total == 500, pay2.hellenia_withholding_total)
    check("12_reopen_apps", len(AppLine.search([("payment_id", "=", pid)])) == 1, AppLine.search_count([("payment_id", "=", pid)]))

# 13 Factura muestra pago/retención
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-13")
    _pay_partner(customer, inv, [_cat("RET-GOB-5")], "customer")
    inv.invalidate_recordset()
    check("13_invoice_wh", inv.hellenia_withholding_total == 500, inv.hellenia_withholding_total)

# 14 Asiento contable con línea retención
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-14")
    pay = _pay_partner(customer, inv, [_cat("RET-GOB-5")], "customer")
    wh_acc = _cat("RET-GOB-5").account_id
    gl = pay.move_id.line_ids.filtered(lambda l: l.account_id == wh_acc)
    check("14_gl_line", len(gl) == 1 and near(abs(gl.balance), 500), gl.mapped("balance"))

# 15 Conciliación parcial
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-15")
    _pay_partner(customer, inv, [], "customer", PARTIAL)
    check("15_partial_reconcile", inv.payment_state == "partial", inv.payment_state)

# 16 Conciliación total
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-16")
    _pay_partner(customer, inv, [], "customer")
    check("16_full_reconcile", inv.payment_state in ("paid", "in_payment"), inv.payment_state)

period_code, df, dt = _dgii_period()

# 17 606
with env.cr.savepoint():
    inv = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1813-17")
    _pay_partner(vendor, inv, [_cat("RET-ITBIS-30")], "supplier")
    rep = env["justech.do.fiscal.report"].create({"name": "P1813 606", "report_type": "606", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    check("17_606", bool(rep.line_ids), len(rep.line_ids))

# 18 607
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-18")
    _pay_partner(customer, inv, [_cat("RET-GOB-5")], "customer")
    rep = env["justech.do.fiscal.report"].create({"name": "P1813 607", "report_type": "607", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    check("18_607", bool(rep.line_ids), len(rep.line_ids))

# 19 623 — retención 5% Gobierno visible
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-19")
    pay = _pay_partner(customer, inv, [_cat("RET-GOB-5")], "customer")
    rep = env["justech.do.fiscal.report"].create({"name": "P1813 623", "report_type": "623", "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id})
    rep.action_generate(valid_moves=inv)
    exp623 = env["justech.do.dgii.623.exporter"]
    gov_amt = exp623._gov_amount(inv, exp623._gov_tax(company))
    line623 = rep.line_ids.filtered(lambda l: l.move_id == inv)
    check("19_623_lines", bool(rep.line_ids) and gov_amt >= 500, f"lines={len(rep.line_ids)} gov={gov_amt}")
    check("19_623_amount_col", line623 and near(line623[:1].amount_total, gov_amt), line623[:1].amount_total if line623 else 0)
    check("19_623_menu", bool(env.ref("justech_l10n_do_reports.menu_justech_do_report_623", False)), "menu")
    report["evidence"]["623"] = {"payment": pay.name, "gov_amt": gov_amt, "lines": len(rep.line_ids)}

# 20 PDF recibo
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1813-20")
    pay = _pay_partner(customer, inv, [_cat("RET-GOB-5")], "customer")
    html, _ = env["ir.actions.report"]._render_qweb_html("account.action_report_payment_receipt", pay.ids)
    text = html.decode() if isinstance(html, bytes) else str(html)
    check("20_receipt", "Total retenido" in text and "500" in text.replace(",", ""), "pdf")

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
report["recommendation"] = "continuar" if report["ok"] else "revisar antes de continuar"
report["production_ready"] = False
print(f"PHASE1813:{json.dumps(report, ensure_ascii=False, default=str)}")
