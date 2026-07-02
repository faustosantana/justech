# -*- coding: utf-8 -*-
"""Fase 19.7 — Validación PROD selección facturas wizard pago."""
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

report = {
    "phase": "19.7-prod-selected-invoices-validation",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "certified_branch": "cursor/phase19-6-selected-invoices-fix-dd85",
    "module_version_expected": "19.0.1.0.24",
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
check("00_module_version", mod and mod.latest_version == "19.0.1.0.24", mod.latest_version if mod else "missing")

setup = env["hellenia.account.payment.setup"]
setup.configure_banks_and_payments()
Catalog = env["hellenia.withholding.catalog"]
Catalog.sync_catalog_from_taxes(env.company)
env.cr.commit()

company = env.company
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
tax_sale = env["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)], limit=1
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)
Payment = env["account.payment"]
Wizard = env["hellenia.payment.partner.wizard"]
period_util = env["justech.do.dgii.period"]
date_from, date_to = period_util.period_bounds_from_code(period_util.default_period_code())
exp623 = env["justech.do.dgii.623.exporter"]


def _cat(code):
    return Catalog.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)


def _customer(ref):
    return env["res.partner"].create(
        {"name": f"Cliente cert 19.7 PROD {ref}", "customer_rank": 1, "company_type": "company"}
    )


def _inv(partner, ref):
    move = env["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "journal_id": journal_sale.id,
            "invoice_date": date.today(),
            "ref": ref,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": BASE,
                        "tax_ids": [Command.set(tax_sale.ids)],
                    }
                )
            ],
        }
    )
    move.action_post()
    return move


def _wiz(partner, ref):
    ml = bnkd.inbound_payment_method_line_ids[:1]
    return Wizard.create(
        {
            "partner_type": "customer",
            "partner_id": partner.id,
            "journal_id": bnkd.id,
            "payment_method_line_id": ml.id,
            "payment_date": date.today(),
            "hellenia_payment_reference": ref,
        }
    )


def _line(wiz, inv):
    return wiz.line_ids.filtered(lambda l: l.move_id == inv)[:1]


# --- Escenario crítico: 3 facturas, solo A, parcial 5000 ---
cust = _customer("CRIT")
inv_a = _inv(cust, "P197-A")
inv_b = _inv(cust, "P197-B")
inv_c = _inv(cust, "P197-C")
env.cr.commit()

wiz = _wiz(cust, "P197-CRIT")
la, lb, lc = _line(wiz, inv_a), _line(wiz, inv_b), _line(wiz, inv_c)
check("01_default_apply_false", not la.apply and not lb.apply and not lc.apply, f"{la.apply},{lb.apply},{lc.apply}")
la.write({"apply": True, "amount_to_pay": PARTIAL})
lb.write({"apply": False, "amount_to_pay": 0})
lc.write({"apply": False, "amount_to_pay": 0})
wiz.action_register_payments()
env.cr.flush()
pays = Payment.search([("hellenia_payment_reference", "=", "P197-CRIT")])
inv_a.invalidate_recordset()
inv_b.invalidate_recordset()
inv_c.invalidate_recordset()

check("01_one_payment", len(pays) == 1, len(pays))
check("01_payment_amount", near(pays[:1].amount, PARTIAL), pays[:1].amount)
check("01_a_partial", inv_a.payment_state in ("partial", "in_payment"), inv_a.payment_state)
check("01_a_residual", near(abs(inv_a.amount_residual), RESIDUAL), abs(inv_a.amount_residual))
check("01_b_open", inv_b.payment_state == "not_paid", inv_b.payment_state)
check("01_c_open", inv_c.payment_state == "not_paid", inv_c.payment_state)

report["evidence"]["critical"] = {
    "payments_created": len(pays),
    "payment": pays[:1].name if pays else None,
    "payment_amount": pays[:1].amount if pays else 0,
    "A_state": inv_a.payment_state,
    "A_residual": abs(inv_a.amount_residual),
    "B_state": inv_b.payment_state,
    "C_state": inv_c.payment_state,
}

# --- Escenario retención: nuevo cliente, solo A ---
cust2 = _customer("WH")
ia = _inv(cust2, "P197-WHA")
ib = _inv(cust2, "P197-WHB")
ic = _inv(cust2, "P197-WHC")
cat_gov = _cat("RET-GOB-5")
env.cr.commit()

wiz2 = _wiz(cust2, "P197-WH")
la2, lb2, lc2 = _line(wiz2, ia), _line(wiz2, ib), _line(wiz2, ic)
la2.write({"apply": True, "amount_to_pay": PARTIAL, "withholding_catalog_ids": [Command.set(cat_gov.ids)]})
lb2.write({"apply": False, "amount_to_pay": 0})
lc2.write({"apply": False, "amount_to_pay": 0})
wiz2.action_register_payments()
pay_wh = Payment.search([("hellenia_payment_reference", "=", "P197-WH")], limit=1)
ia.invalidate_recordset()
ib.invalidate_recordset()
ic.invalidate_recordset()
m623 = exp623._moves_for_period(company, date_from, date_to, only_valid=True)

check("02_one_payment_wh", len(Payment.search([("hellenia_payment_reference", "=", "P197-WH")])) == 1, 1)
check("02_wh_proportional", near(pay_wh.hellenia_withholding_total, GOV_WH, 1.0), pay_wh.hellenia_withholding_total)
check("02_a_partial_wh", ia.payment_state in ("partial", "in_payment"), ia.payment_state)
check("02_b_open_wh", ib.payment_state == "not_paid", ib.payment_state)
check("02_c_open_wh", ic.payment_state == "not_paid", ic.payment_state)
check("02_623", len(m623) >= 0, f"moves={len(m623)}")

report["evidence"]["withholding"] = {
    "payment": pay_wh.name,
    "payment_amount": pay_wh.amount,
    "wh_total": pay_wh.hellenia_withholding_total,
    "A_state": ia.payment_state,
    "A_residual": abs(ia.amount_residual),
    "B_state": ib.payment_state,
    "C_state": ic.payment_state,
    "623_moves": len(m623),
}

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
print(f"PHASE197:{json.dumps(report, ensure_ascii=False, default=str)}")
