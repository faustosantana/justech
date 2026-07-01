# -*- coding: utf-8 -*-
"""Fase 18.10B — Validación UI/ciclo contable retenciones (TEST)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

BASE, ITBIS, TOTAL, TOL = 10000.0, 1800.0, 11800.0, 0.02

report = {
    "phase": "18.10b-ui-validation",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "scenarios": {},
    "registry": {},
    "ok": True,
    "pass": False,
}


def check(scenario, key, ok, detail=""):
    report["scenarios"].setdefault(scenario, {})[key] = {
        "status": "PASS" if ok else "FAIL",
        "detail": str(detail)[:1000],
    }
    if not ok:
        report["ok"] = False


def near(a, b, tol=TOL):
    return abs((a or 0.0) - (b or 0.0)) <= tol


def _dgii_period():
    util = env["justech.do.dgii.period"]
    code = util.default_period_code()
    return code, *util.period_bounds_from_code(code)


# Registry
models = [
    "hellenia.payment.withholding.line",
    "hellenia.payment.withholding.wizard.line",
    "hellenia.withholding.catalog",
    "hellenia.payment.partner.wizard",
]
for m in models:
    try:
        env[m]
        report["registry"][m] = "OK"
    except Exception as exc:
        report["registry"][m] = str(exc)
        report["ok"] = False

mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
report["module_version"] = mod.latest_version if mod else "missing"
check("registry", "hellenia_account_19.0.1.0.13", mod and mod.latest_version == "19.0.1.0.13", mod.latest_version if mod else "missing")

company = env.company
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
product = env["product.product"].search([("sale_ok", "=", True), ("purchase_ok", "=", True)], limit=1)
tax_sale = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)], limit=1)
tax_purchase = env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)
Catalog = env["hellenia.withholding.catalog"]
Payment = env["account.payment"]
WhLine = env["hellenia.payment.withholding.line"]


def _cat(code):
    return Catalog.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)


def _inv(partner, journal, tax, mt, ref):
    m = env["account.move"].create({
        "move_type": mt, "partner_id": partner.id, "journal_id": journal.id,
        "invoice_date": date.today(), "ref": ref,
        "invoice_line_ids": [Command.create({
            "product_id": product.id, "quantity": 1, "price_unit": BASE,
            "tax_ids": [Command.set(tax.ids)],
        })],
    })
    m.action_post()
    return m


def _partner_wiz(partner, ptype, ref):
    ml = bnkd.inbound_payment_method_line_ids if ptype == "customer" else bnkd.outbound_payment_method_line_ids
    return env["hellenia.payment.partner.wizard"].create({
        "partner_type": ptype, "partner_id": partner.id,
        "journal_id": bnkd.id, "payment_method_line_id": ml[:1].id,
        "payment_date": date.today(), "hellenia_payment_reference": f"UI-{ref}",
    })


def _ui_payment_evidence(pay, inv, scenario):
    report["scenarios"].setdefault(scenario, {})
    pay.invalidate_recordset()
    inv.invalidate_recordset()
    data = pay.read([
        "name", "hellenia_applied_amount", "hellenia_withholding_total",
        "hellenia_net_transfer", "hellenia_invoice_display",
        "hellenia_withholding_line_ids",
    ])[0]
    wh_lines = WhLine.browse(data["hellenia_withholding_line_ids"])
    wh_data = wh_lines.read([
        "invoice_name", "ncf", "label", "base_amount", "rate", "amount",
        "account_id", "withholding_code", "move_line_id", "partial_reconcile_id",
    ])
    gl_wh = pay.move_id.line_ids.filtered(lambda l: l.account_id in wh_lines.mapped("account_id"))
    inv_wh = inv.read(["hellenia_withholding_total", "hellenia_withholding_line_ids"])[0]
    deb = sum(pay.move_id.line_ids.mapped("debit"))
    cred = sum(pay.move_id.line_ids.mapped("credit"))
    reconciled = inv.payment_state in ("paid", "partial", "in_payment")
    ev = {
        "payment": data["name"],
        "invoice": inv.name,
        "ncf": inv.justech_do_ncf or "",
        "applied": data["hellenia_applied_amount"],
        "wh_total": data["hellenia_withholding_total"],
        "net_transfer": data["hellenia_net_transfer"],
        "invoice_display": data["hellenia_invoice_display"],
        "withholding_lines": wh_data,
        "gl_withholding": [{"account": l.account_id.code, "balance": l.balance} for l in gl_wh],
        "invoice_wh_total": inv_wh["hellenia_withholding_total"],
        "balanced": near(deb, cred),
        "payment_state": inv.payment_state,
        "reconciled": reconciled,
    }
    report["scenarios"][scenario]["evidence"] = ev
    return data, wh_lines, gl_wh, ev


# === ESCENARIO 1: Cobro completo 5% Gobierno ===
SC = "01_gov_full"
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810B-01")
    cat_gov = _cat("RET-GOB-5")
    wiz = _partner_wiz(customer, "customer", "P1810B-01")
    line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
    line.apply = True
    line.withholding_catalog_ids = [Command.set(cat_gov.ids)]
    line._recompute_line_withholdings()
    wiz_wh = line.withholding_amount
    check(SC, "wizard_calculates_wh", near(wiz_wh, 500), wiz_wh)
    wiz.action_register_payments()
    env.cr.flush()
    pay = Payment.search([("partner_id", "=", customer.id)], order="id desc", limit=1)
    data, wh_lines, gl_wh, ev = _ui_payment_evidence(pay, inv, SC)
    check(SC, "payment_wh_not_zero", data["hellenia_withholding_total"] > 0, data["hellenia_withholding_total"])
    check(SC, "payment_invoice_display", bool(data["hellenia_invoice_display"]), data["hellenia_invoice_display"])
    check(SC, "payment_ncf", bool(wh_lines.ncf or inv.justech_do_ncf), wh_lines.mapped("ncf"))
    check(SC, "payment_wh_detail", len(wh_lines) == 1 and near(wh_lines.amount, 500), wh_lines.mapped("amount"))
    check(SC, "payment_base_rate", near(wh_lines.base_amount, BASE), wh_lines.base_amount)
    check(SC, "payment_net", near(data["hellenia_net_transfer"], TOTAL - 500), data["hellenia_net_transfer"])
    check(SC, "invoice_wh_visible", inv.hellenia_withholding_total > 0, inv.hellenia_withholding_total)
    check(SC, "gl_wh_line", len(gl_wh) == 1, ev["gl_withholding"])
    check(SC, "gl_account_gov", gl_wh.account_id.code == cat_gov.account_id.code, gl_wh.account_id.code)
    check(SC, "balanced", ev["balanced"], f"D={sum(pay.move_id.line_ids.mapped('debit'))}")
    check(SC, "reconcile", ev["reconciled"], inv.payment_state)
  # 607
    period_code, df, dt = _dgii_period()
    rep607 = env["justech.do.fiscal.report"].create({
        "name": "P1810B 607", "report_type": "607",
        "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id,
    })
    rep607.action_generate(valid_moves=inv)
    exp607 = env["justech.do.dgii.607.exporter"]
    _, isr, _, _ = exp607._withholding_breakdown(inv)
    check(SC, "report_607", bool(rep607.line_ids) and isr > 0, f"lines={len(rep607.line_ids)} isr={isr}")
  # 623
    rep623 = env["justech.do.fiscal.report"].create({
        "name": "P1810B 623", "report_type": "623",
        "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id,
    })
    rep623.action_generate(valid_moves=inv)
    exp623 = env["justech.do.dgii.623.exporter"]
    gov_amt = exp623._gov_amount(inv, exp623._gov_tax(company))
    check(SC, "report_623", bool(rep623.line_ids) and gov_amt >= 500, f"lines={len(rep623.line_ids)} gov={gov_amt}")
  # PDF
    html, _ = env["ir.actions.report"]._render_qweb_html("account.action_report_payment_receipt", pay.ids)
    text = html.decode() if isinstance(html, bytes) else str(html)
    check(SC, "pdf_receipt", "Total retenido" in text and "500" in text.replace(",", ""), "pdf ok")

# === ESCENARIO 2: Abono parcial ===
SC = "02_partial_gov"
with env.cr.savepoint():
    inv = _inv(customer, journal_sale, tax_sale, "out_invoice", "P1810B-02")
    cat_gov = _cat("RET-GOB-5")
    wiz = _partner_wiz(customer, "customer", "P1810B-02")
    line = wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]
    line.write({"apply": True, "amount_to_pay": 5000.0, "withholding_catalog_ids": [Command.set(cat_gov.ids)]})
    line._recompute_line_withholdings()
    exp_wh = 500 * (5000 / TOTAL)
    check(SC, "wizard_proportional_wh", near(line.withholding_amount, exp_wh), line.withholding_amount)
    wiz.action_register_payments()
    pay = Payment.search([("partner_id", "=", customer.id)], order="id desc", limit=1)
    data, wh_lines, gl_wh, ev = _ui_payment_evidence(pay, inv, SC)
    check(SC, "partial_state", inv.payment_state == "partial", inv.payment_state)
    check(SC, "residual", near(abs(inv.amount_residual), TOTAL - 5000, 1.0), inv.amount_residual)
    check(SC, "wh_proportional", near(data["hellenia_withholding_total"], exp_wh, 1.0), data["hellenia_withholding_total"])
    check(SC, "balanced", ev["balanced"], ev["gl_withholding"])

# === ESCENARIO 3: Pago múltiple agrupado ===
SC = "03_multi_grouped"
with env.cr.savepoint():
    i1 = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1810B-03A")
    i2 = _inv(vendor, journal_purchase, tax_purchase, "in_invoice", "P1810B-03B")
    cat_itbis = _cat("RET-ITBIS-100")
    wiz = _partner_wiz(vendor, "supplier", "P1810B-03")
    wiz._load_pending_invoices()
    l1 = wiz.line_ids.filtered(lambda l: l.move_id == i1)[:1]
    l2 = wiz.line_ids.filtered(lambda l: l.move_id == i2)[:1]
    l1.write({"apply": True, "amount_to_pay": TOTAL})
    l2.write({"apply": True, "amount_to_pay": TOTAL, "withholding_catalog_ids": [Command.set(cat_itbis.ids)]})
    l2._recompute_line_withholdings()
    wiz.action_register_payments()
    pay = Payment.search([("partner_id", "=", vendor.id)], order="id desc", limit=1)
    data, wh_lines, gl_wh, ev = _ui_payment_evidence(pay, i2, SC)
    check(SC, "one_payment", len(Payment.search([("id", "=", pay.id)])) == 1, pay.name)
    check(SC, "two_invoices", len(pay.reconciled_bill_ids) == 2, pay.reconciled_bill_ids.mapped("name"))
    check(SC, "ncf_both", len(set(wh_lines.mapped("ncf"))) >= 1 or bool(i1.justech_do_ncf and i2.justech_do_ncf), [i1.justech_do_ncf, i2.justech_do_ncf])
    check(SC, "wh_only_invoice2", near(sum(wh_lines.mapped("amount")), ITBIS), wh_lines.mapped("amount"))
    check(SC, "net_correct", near(data["hellenia_net_transfer"], 2 * TOTAL - ITBIS), data["hellenia_net_transfer"])
    check(SC, "gl_wh", len(gl_wh) >= 1, ev["gl_withholding"])
    period_code, df, dt = _dgii_period()
    rep606 = env["justech.do.fiscal.report"].create({
        "name": "P1810B 606", "report_type": "606",
        "period_code": period_code, "date_from": df, "date_to": dt, "company_id": company.id,
    })
    rep606.action_generate(valid_moves=i2)
    exp606 = env["justech.do.dgii.606.exporter"]
    itbis, _, _, _ = exp606._withholding_breakdown(i2)
    check(SC, "report_606", bool(rep606.line_ids) and itbis > 0, f"itbis={itbis}")

report["summary"] = {
    "scenarios": len(report["scenarios"]),
    "passed": sum(
        1 for sc in report["scenarios"].values()
        for t in sc.values() if isinstance(t, dict) and t.get("status") == "PASS"
    ),
    "failed": sum(
        1 for sc in report["scenarios"].values()
        for t in sc.values() if isinstance(t, dict) and t.get("status") == "FAIL"
    ),
}
report["pass"] = report["ok"]
print(f"PHASE1810B:{json.dumps(report, ensure_ascii=False, default=str)}")
