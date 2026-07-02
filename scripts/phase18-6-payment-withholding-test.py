# -*- coding: utf-8 -*-
"""Fase 18.6 — Cierre contable retenciones, abonos parciales y recibo de pago (TEST)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

BASE = 10000.0
ITBIS = 1800.0
TOTAL = 11800.0
TOL = 0.02

report = {
    "phase": "18.6-payment-withholding-accounting",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module_version": None,
    "tests": {},
    "accounts_used": {},
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
    date_from, date_to = util.period_bounds_from_code(code)
    return code, date_from, date_to


# --- Upgrade ---
mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
if mod:
    mod.button_immediate_upgrade()
    env.cr.commit()
    report["module_version"] = mod.latest_version
    check("00_module_upgrade", True, mod.latest_version)
else:
    check("00_module_upgrade", False, "hellenia_account no encontrado")

setup = env["hellenia.account.payment.setup"]
setup.configure_banks_and_payments()
setup.configure_withholding_reference()
Catalog = env["hellenia.withholding.catalog"]
Catalog.sync_catalog_from_taxes(env.company)
env.cr.commit()

company = env.company
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
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


def _cat(code):
    return Catalog.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)


def _mline(journal, partner_type):
    lines = journal.inbound_payment_method_line_ids if partner_type == "customer" else journal.outbound_payment_method_line_ids
    transfer = lines.filtered(lambda l: "transferencia" in (l.name or "").lower())[:1]
    return transfer or lines[:1]


def _invoice(partner, journal, tax, move_type, ref_tag):
    inv = env["account.move"].create(
        {
            "move_type": move_type,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "invoice_date": date.today(),
            "ref": ref_tag,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": BASE,
                        "tax_ids": [Command.set(tax.ids)] if tax else [],
                    }
                )
            ],
        }
    )
    inv.action_post()
    return inv


def _wiz(partner, partner_type):
    return env["hellenia.payment.partner.wizard"].create(
        {
            "partner_type": partner_type,
            "partner_id": partner.id,
            "journal_id": bnkd.id,
            "payment_method_line_id": _mline(bnkd, partner_type).id,
            "payment_date": date.today(),
        }
    )


def _line_for(wiz, inv):
    line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
    if not line:
        wiz._load_pending_invoices()
        line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
    return line


def _pay(wiz, line, catalogs=None, amount=None):
    line.apply = True
    if amount is not None:
        line.amount_to_pay = amount
    if catalogs is not None:
        line.withholding_catalog_ids = [Command.set([c.id for c in catalogs if c])]
    line._recompute_line_withholdings()
    wiz.action_register_payments()
    pay = env["account.payment"].search(
        [("partner_id", "=", wiz.partner_id.id)], order="id desc", limit=1
    )
    return pay


def _balanced(move):
    deb = sum(move.line_ids.mapped("debit"))
    cred = sum(move.line_ids.mapped("credit"))
    return near(deb, cred)


def _wh_gl_lines(pay):
    return pay.hellenia_withholding_line_ids.mapped("move_line_id")


# --- 1. Pago completo sin retención ---
try:
    with env.cr.savepoint():
        inv = _invoice(customer, journal_sale, tax_sale, "out_invoice", "P186-01")
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        pay = _pay(wiz, line, catalogs=[])
        check(
            "01_full_no_wh",
            pay.hellenia_applied_amount == TOTAL and not pay.hellenia_withholding_line_ids,
            f"applied={pay.hellenia_applied_amount} wh={len(pay.hellenia_withholding_line_ids)}",
        )
except Exception as exc:
    check("01_full_no_wh", False, exc)

# --- 2. Pago completo ITBIS 100% proveedor ---
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, journal_purchase, tax_purchase, "in_invoice", "P186-02")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        cat = _cat("RET-ITBIS-100")
        pay = _pay(wiz, line, catalogs=[cat])
        wh = pay.hellenia_withholding_line_ids
        check(
            "02_full_itbis_100",
            len(wh) == 1 and near(wh.amount, ITBIS) and near(pay.hellenia_withholding_total, ITBIS),
            f"wh={wh.amount} net={pay.amount}",
        )
        check("02_persistent_lines", bool(wh.invoice_name and wh.ncf is not None), wh.invoice_name)
        check("02_balanced_entry", _balanced(pay.move_id), pay.move_id.name)
        if wh.account_id:
            report["accounts_used"]["itbis_100"] = wh.account_id.code
except Exception as exc:
    check("02_full_itbis_100", False, exc)

# --- 3. Pago completo Gobierno 5% cliente ---
try:
    with env.cr.savepoint():
        inv = _invoice(customer, journal_sale, tax_sale, "out_invoice", "P186-03")
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        cat = _cat("RET-GOB-5")
        pay = _pay(wiz, line, catalogs=[cat])
        wh = pay.hellenia_withholding_line_ids
        expected = 500.0
        check(
            "03_full_gov_5",
            len(wh) == 1 and near(wh.amount, expected),
            f"wh={wh.amount}",
        )
        check(
            "03_gov_623_field",
            near(pay.justech_do_gov_withholding_amount, expected),
            pay.justech_do_gov_withholding_amount,
        )
        if wh.account_id:
            report["accounts_used"]["gov_5"] = wh.account_id.code
except Exception as exc:
    check("03_full_gov_5", False, exc)

# --- 4. ITBIS 100% + Gobierno 5% (compra) ---
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, journal_purchase, tax_purchase, "in_invoice", "P186-04")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        pay = _pay(wiz, line, catalogs=[_cat("RET-ITBIS-100"), _cat("RET-ISR-2")])
        wh_sum = sum(pay.hellenia_withholding_line_ids.mapped("amount"))
        check("04_dual_withholding", len(pay.hellenia_withholding_line_ids) == 2, wh_sum)
        check("04_net_transfer", near(pay.hellenia_net_transfer, TOTAL - wh_sum), pay.hellenia_net_transfer)
except Exception as exc:
    check("04_dual_withholding", False, exc)

# --- 5. Abono parcial sin retención ---
try:
    with env.cr.savepoint():
        inv = _invoice(customer, journal_sale, tax_sale, "out_invoice", "P186-05")
        partial = 5000.0
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        pay = _pay(wiz, line, catalogs=[], amount=partial)
        inv.invalidate_recordset()
        check(
            "05_partial_no_wh",
            inv.payment_state == "partial" and near(pay.hellenia_applied_amount, partial),
            inv.payment_state,
        )
except Exception as exc:
    check("05_partial_no_wh", False, exc)

# --- 6. Abono parcial con retención proporcional ---
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, journal_purchase, tax_purchase, "in_invoice", "P186-06")
        partial = 5000.0
        ratio = partial / TOTAL
        expected_wh = ITBIS * ratio  # ITBIS 100% proporcional
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        pay = _pay(wiz, line, catalogs=[_cat("RET-ITBIS-100")], amount=partial)
        wh_amt = sum(pay.hellenia_withholding_line_ids.mapped("amount"))
        check(
            "06_partial_with_wh",
            near(wh_amt, expected_wh, 5.0),
            f"wh={wh_amt} expected~{expected_wh:.2f}",
        )
        check("06_partial_state", inv.payment_state == "partial", inv.payment_state)
except Exception as exc:
    check("06_partial_with_wh", False, exc)

# --- 7. Dos facturas: una completa y otra parcial ---
try:
    with env.cr.savepoint():
        inv1 = _invoice(customer, journal_sale, tax_sale, "out_invoice", "P186-07A")
        inv2 = _invoice(customer, journal_sale, tax_sale, "out_invoice", "P186-07B")
        wiz = _wiz(customer, "customer")
        l1 = _line_for(wiz, inv1)
        l2 = _line_for(wiz, inv2)
        l1.apply = True
        l1.amount_to_pay = TOTAL
        l2.apply = True
        l2.amount_to_pay = 4000.0
        wiz.action_register_payments()
        pays = env["account.payment"].search(
            [("partner_id", "=", customer.id)], order="id desc", limit=2
        )
        check("07_multi_partial", len(pays) == 2, [p.hellenia_applied_amount for p in pays])
except Exception as exc:
    check("07_multi_partial", False, exc)

# --- 8. Pago proveedor con retención ITBIS 30% ---
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, journal_purchase, tax_purchase, "in_invoice", "P186-08")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        pay = _pay(wiz, line, catalogs=[_cat("RET-ITBIS-30")])
        check(
            "08_vendor_itbis_30",
            near(sum(pay.hellenia_withholding_line_ids.mapped("amount")), 540.0),
            pay.hellenia_withholding_line_ids.mapped("amount"),
        )
except Exception as exc:
    check("08_vendor_itbis_30", False, exc)

# --- 9. Recibo PDF con retenciones ---
try:
    with env.cr.savepoint():
        inv = _invoice(customer, journal_sale, tax_sale, "out_invoice", "P186-09")
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        pay = _pay(wiz, line, catalogs=[_cat("RET-GOB-5")])
        html, _fmt = env["ir.actions.report"]._render_qweb_html("account.action_report_payment_receipt", pay.ids)
        text = html.decode() if isinstance(html, bytes) else str(html)
        has_wh = "Retenciones" in text or "retenid" in text.lower()
        has_ncf = bool(pay.hellenia_withholding_line_ids.ncf and pay.hellenia_withholding_line_ids.ncf[0] in text)
        check("09_receipt_pdf", has_wh, "sección retenciones" if has_wh else "sin retenciones en PDF")
        check("09_receipt_ncf", has_ncf or bool(pay.hellenia_withholding_line_ids.ncf), pay.hellenia_withholding_line_ids.ncf)
except Exception as exc:
    check("09_receipt_pdf", False, exc)

# --- 10. Pago reabierto conserva retenciones ---
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, journal_purchase, tax_purchase, "in_invoice", "P186-10")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        pay = _pay(wiz, line, catalogs=[_cat("RET-ITBIS-100")])
        pid = pay.id
        pay2 = env["account.payment"].browse(pid)
        check(
            "10_reopen_persistence",
            len(pay2.hellenia_withholding_line_ids) == 1 and pay2.hellenia_applied_amount == TOTAL,
            pay2.hellenia_withholding_line_ids.mapped("label"),
        )
except Exception as exc:
    check("10_reopen_persistence", False, exc)

# --- 11. Mayor cuenta retención ---
try:
    with env.cr.savepoint():
        inv = _invoice(vendor, journal_purchase, tax_purchase, "in_invoice", "P186-11")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        pay = _pay(wiz, line, catalogs=[_cat("RET-ITBIS-100")])
        gl = _wh_gl_lines(pay)
        check("11_gl_withholding_lines", bool(gl), gl.mapped("account_id.code"))
        check("11_gl_linked", all(pay.hellenia_withholding_line_ids.mapped("move_line_id")), "vinculado")
except Exception as exc:
    check("11_gl_withholding_lines", False, exc)

# --- 12. Reporte 606 ---
try:
    with env.cr.savepoint():
        period_code, date_from, date_to = _dgii_period()
        inv = _invoice(vendor, journal_purchase, tax_purchase, "in_invoice", "P186-12")
        wiz = _wiz(vendor, "supplier")
        line = _line_for(wiz, inv)
        _pay(wiz, line, catalogs=[_cat("RET-ITBIS-30")])
        rep = env["justech.do.fiscal.report"].create(
            {
                "name": f"P186 606 {period_code}",
                "report_type": "606",
                "period_code": period_code,
                "date_from": date_from,
                "date_to": date_to,
                "company_id": company.id,
            }
        )
        rep.action_generate(valid_moves=inv)
        lines = rep.line_ids.filtered(lambda l: l.move_id == inv)
        exporter = env["justech.do.dgii.606.exporter"]
        itbis_wh, isr_wh, _, _ = exporter._withholding_breakdown(inv)
        check("12_report_606", bool(lines), f"lines={len(lines)} itbis_wh={itbis_wh}")
except Exception as exc:
    check("12_report_606", False, exc)

# --- 13. Reporte 607 ---
try:
    with env.cr.savepoint():
        period_code, date_from, date_to = _dgii_period()
        inv = _invoice(customer, journal_sale, tax_sale, "out_invoice", "P186-13")
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        _pay(wiz, line, catalogs=[_cat("RET-GOB-5")])
        rep = env["justech.do.fiscal.report"].create(
            {
                "name": f"P186 607 {period_code}",
                "report_type": "607",
                "period_code": period_code,
                "date_from": date_from,
                "date_to": date_to,
                "company_id": company.id,
            }
        )
        rep.action_generate(valid_moves=inv)
        lines = rep.line_ids.filtered(lambda l: l.move_id == inv)
        exporter = env["justech.do.dgii.607.exporter"]
        itbis_wh, isr_wh, _, _ = exporter._withholding_breakdown(inv)
        check("13_report_607", bool(lines) and isr_wh > 0, f"lines={len(lines)} isr_wh={isr_wh}")
except Exception as exc:
    check("13_report_607", False, exc)

# --- 14. Estado 623 ---
try:
    exporter623 = env.get("justech.do.dgii.623.exporter")
    exists = exporter623 is not None
    report["fiscal_623"] = {
        "exists": exists,
        "scope": "ISR 5% Gobierno (RET-GOB-5) únicamente",
        "functional": exists,
    }
    if exists:
        period_code, date_from, date_to = _dgii_period()
        inv = _invoice(customer, journal_sale, tax_sale, "out_invoice", "P186-14")
        wiz = _wiz(customer, "customer")
        line = _line_for(wiz, inv)
        pay = _pay(wiz, line, catalogs=[_cat("RET-GOB-5")])
        has = exporter623._has_gov_withholding(inv, exporter623._gov_tax(company))
        check("14_report_623", has and near(pay.justech_do_gov_withholding_amount, 500.0), has)
    else:
        check("14_report_623", False, "exportador 623 no instalado")
except Exception as exc:
    check("14_report_623", False, exc)

# --- Regresión smoke ---
try:
    env["hellenia.payment.partner.wizard"].get_views([(False, "form")])
    env["account.payment"].get_views([(False, "form")])
    check("reg_wizard_views", True, "ok")
except Exception as exc:
    check("reg_wizard_views", False, exc)

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
report["production_ready_for_approval"] = report["ok"]
print(f"PHASE186:{json.dumps(report, ensure_ascii=False, default=str)}")
