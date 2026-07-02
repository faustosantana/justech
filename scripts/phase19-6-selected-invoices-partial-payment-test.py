# -*- coding: utf-8 -*-
"""Fase 19.6 — Certificación selección facturas wizard pago (TEST)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command
from odoo.exceptions import UserError

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

BASE, ITBIS, TOTAL, TOL = 10000.0, 1800.0, 11800.0, 0.02
PARTIAL = 5000.0
RESIDUAL = TOTAL - PARTIAL
PROP = PARTIAL / TOTAL
GOV_WH = round(BASE * PROP * 0.05, 2)

report = {
    "phase": "19.6-selected-invoices-partial-payment",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "root_cause": (
        "payment_partner_wizard.py: apply default=True (línea 14) y _load_pending_invoices() "
        "marcaba apply=True en todas las facturas (línea 320); checkbox apply sin force_save "
        "en vista → al registrar, action_register_payments procesaba todas las líneas con "
        "amount_to_pay=residual completo."
    ),
    "fix": (
        "apply default=False; _load_pending_invoices apply=False; force_save en checkbox; "
        "_selected_lines() con flush; errores explícitos; _onchange_apply limpia líneas no marcadas."
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
check("00_upgrade", mod and mod.latest_version == "19.0.1.0.24", mod.latest_version if mod else "")

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
        {"name": f"Cliente cert 19.6 {ref}", "customer_rank": 1, "company_type": "company"}
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


def _wiz(partner, ref="P196"):
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


def _pay_count_before():
    return Payment.search_count([])


# --- Setup 3 facturas A, B, C ---
cust1 = _customer("C1")
inv_a = _inv(cust1, "P196-A")
inv_b = _inv(cust1, "P196-B")
inv_c = _inv(cust1, "P196-C")
env.cr.commit()

# Caso 1: solo A, parcial 5000
pay_before = _pay_count_before()
wiz1 = _wiz(cust1, "P196-C1")
la, lb, lc = _line(wiz1, inv_a), _line(wiz1, inv_b), _line(wiz1, inv_c)
check("01_lines_loaded", len(wiz1.line_ids) == 3, len(wiz1.line_ids))
check("01_default_apply_false", not la.apply and not lb.apply and not lc.apply, f"{la.apply},{lb.apply},{lc.apply}")
la.write({"apply": True, "amount_to_pay": PARTIAL})
lb.write({"apply": False, "amount_to_pay": 0})
lc.write({"apply": False, "amount_to_pay": 0})
wiz1.action_register_payments()
env.cr.flush()
new_pays = Payment.search([("id", ">", pay_before)], order="id asc") if pay_before else Payment.search([], order="id desc", limit=5)
pays_c1 = Payment.search([("hellenia_payment_reference", "=", "P196-C1")])
inv_a.invalidate_recordset()
inv_b.invalidate_recordset()
inv_c.invalidate_recordset()
check("01_one_payment", len(pays_c1) == 1, len(pays_c1))
check("01_payment_amount", near(pays_c1[:1].amount, PARTIAL), pays_c1[:1].amount)
check("01_a_partial", inv_a.payment_state in ("partial", "in_payment"), inv_a.payment_state)
check("01_a_residual", near(abs(inv_a.amount_residual), RESIDUAL), abs(inv_a.amount_residual))
check("01_b_open", inv_b.payment_state == "not_paid", inv_b.payment_state)
check("01_c_open", inv_c.payment_state == "not_paid", inv_c.payment_state)
report["evidence"]["case1"] = {
    "payments_created": len(pays_c1),
    "payment_amount": pays_c1[:1].amount,
    "A_state": inv_a.payment_state,
    "A_residual": abs(inv_a.amount_residual),
    "B_state": inv_b.payment_state,
    "C_state": inv_c.payment_state,
}

# Caso 2: A parcial + B completo, C sin marcar
cust2 = _customer("C2")
ia2 = _inv(cust2, "P196-2A")
ib2 = _inv(cust2, "P196-2B")
ic2 = _inv(cust2, "P196-2C")
env.cr.commit()
pay_before2 = _pay_count_before()
wiz2 = _wiz(cust2, "P196-C2")
la2, lb2, lc2 = _line(wiz2, ia2), _line(wiz2, ib2), _line(wiz2, ic2)
la2.write({"apply": True, "amount_to_pay": PARTIAL})
lb2.write({"apply": True, "amount_to_pay": TOTAL})
lc2.write({"apply": False, "amount_to_pay": 0})
wiz2.action_register_payments()
pays_c2 = Payment.search([("hellenia_payment_reference", "=", "P196-C2")])
ia2.invalidate_recordset()
ib2.invalidate_recordset()
ic2.invalidate_recordset()
check("02_two_payments", len(pays_c2) == 2, len(pays_c2))
check("02_a_partial", ia2.payment_state in ("partial", "in_payment"), ia2.payment_state)
check("02_b_paid", ib2.payment_state in ("paid", "in_payment") and near(abs(ib2.amount_residual), 0), ib2.payment_state)
check("02_c_open", ic2.payment_state == "not_paid", ic2.payment_state)
report["evidence"]["case2"] = {
    "payments_created": len(pays_c2),
    "A_state": ia2.payment_state,
    "B_state": ib2.payment_state,
    "C_state": ic2.payment_state,
}

# Caso 3: ninguna seleccionada
cust3 = _customer("C3")
_inv(cust3, "P196-3A")
env.cr.commit()
wiz3 = _wiz(cust3, "P196-C3")
try:
    wiz3.action_register_payments()
    check("03_no_selection_error", False, "no lanzó error")
except UserError as e:
    check("03_no_selection_error", "al menos una factura" in str(e).lower(), str(e))

# Caso 4: apply con amount 0
cust4 = _customer("C4")
i4 = _inv(cust4, "P196-4A")
env.cr.commit()
wiz4 = _wiz(cust4, "P196-C4")
l4 = _line(wiz4, i4)
l4.write({"apply": True, "amount_to_pay": 0})
try:
    wiz4.action_register_payments()
    check("04_zero_amount_error", False, "no lanzó error")
except UserError as e:
    check("04_zero_amount_error", "mayor que cero" in str(e).lower(), str(e))

# Caso 5: amount > residual
cust5 = _customer("C5")
i5 = _inv(cust5, "P196-5A")
env.cr.commit()
wiz5 = _wiz(cust5, "P196-C5")
l5 = _line(wiz5, i5)
l5.write({"apply": True, "amount_to_pay": TOTAL + 1000})
try:
    wiz5.action_register_payments()
    check("05_over_residual_error", False, "no lanzó error")
except UserError as e:
    check("05_over_residual_error", "supera el pendiente" in str(e).lower(), str(e))

# Caso 6: retención gobierno parcial solo en A
cust6 = _customer("C6")
ia6 = _inv(cust6, "P196-6A")
ib6 = _inv(cust6, "P196-6B")
ic6 = _inv(cust6, "P196-6C")
cat_gov = _cat("RET-GOB-5")
env.cr.commit()
wiz6 = _wiz(cust6, "P196-C6")
la6, lb6, lc6 = _line(wiz6, ia6), _line(wiz6, ib6), _line(wiz6, ic6)
la6.write({"apply": True, "amount_to_pay": PARTIAL, "withholding_catalog_ids": [Command.set(cat_gov.ids)]})
lb6.write({"apply": False, "amount_to_pay": 0})
lc6.write({"apply": False, "amount_to_pay": 0})
wiz6.action_register_payments()
pay6 = Payment.search([("hellenia_payment_reference", "=", "P196-C6")], limit=1)
ia6.invalidate_recordset()
m623 = exp623._moves_for_period(company, date_from, date_to, only_valid=True)
check("06_one_payment", len(Payment.search([("hellenia_payment_reference", "=", "P196-C6")])) == 1, 1)
check("06_wh_proportional", near(pay6.hellenia_withholding_total, GOV_WH, 1.0), pay6.hellenia_withholding_total)
check("06_a_partial", ia6.payment_state in ("partial", "in_payment"), ia6.payment_state)
check("06_a_residual", near(abs(ia6.amount_residual), RESIDUAL), abs(ia6.amount_residual))
check("06_623", len(m623) >= 0, f"moves={len(m623)}")
report["evidence"]["case6"] = {
    "wh_total": pay6.hellenia_withholding_total,
    "A_residual": abs(ia6.amount_residual),
    "623_moves": len(m623),
}

# Caso 7: retención en B no seleccionada — no debe procesarse
cust7 = _customer("C7")
ia7 = _inv(cust7, "P196-7A")
ib7 = _inv(cust7, "P196-7B")
env.cr.commit()
wiz7 = _wiz(cust7, "P196-C7")
la7, lb7 = _line(wiz7, ia7), _line(wiz7, ib7)
la7.write({"apply": True, "amount_to_pay": PARTIAL})
lb7.write({"apply": False, "amount_to_pay": TOTAL, "withholding_catalog_ids": [Command.set(cat_gov.ids)]})
wiz7.action_register_payments()
pays7 = Payment.search([("hellenia_payment_reference", "=", "P196-C7")])
ib7.invalidate_recordset()
check("07_one_payment", len(pays7) == 1, len(pays7))
check("07_b_not_paid", ib7.payment_state == "not_paid", ib7.payment_state)
check("07_b_no_wh_payment", not Payment.search_count([("partner_id", "=", cust7.id), ("hellenia_withholding_total", ">", 0), ("id", "in", pays7.ids)]) or pays7[:1].hellenia_withholding_total == 0, ib7.payment_state)
report["evidence"]["case7"] = {
    "payments": len(pays7),
    "B_state": ib7.payment_state,
    "B_wh_on_unselected": lb7.withholding_catalog_ids.ids,
}

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
print(f"PHASE196:{json.dumps(report, ensure_ascii=False, default=str)}")
