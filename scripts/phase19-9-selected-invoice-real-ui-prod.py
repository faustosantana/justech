# -*- coding: utf-8 -*-
"""Fase 19.9 — Validación PROD real SMOKE P13.4 CF selección facturas."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

SMOKE_NAME = "SMOKE P13.4 CF"
BASE, TOTAL, TOL = 10000.0, 11800.0, 0.02
PARTIAL = 5000.0
RESIDUAL = TOTAL - PARTIAL
GOV_WH = round((BASE * (PARTIAL / TOTAL)) * 0.05, 2)

report = {
    "phase": "19.9-prod-selected-invoice-real-ui",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "partner": SMOKE_NAME,
    "module_version_expected": "19.0.1.0.25",
    "tests": {},
    "evidence": {},
    "ui_evidence": {},
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
check("00_module_version", mod and mod.latest_version == "19.0.1.0.25", mod.latest_version if mod else "missing")

setup = env["hellenia.account.payment.setup"]
setup.configure_banks_and_payments()
Catalog = env["hellenia.withholding.catalog"]
Catalog.sync_catalog_from_taxes(env.company)
env.cr.commit()

partner = env["res.partner"].search([("name", "=", SMOKE_NAME)], limit=1)
check("01_smoke_partner", bool(partner), SMOKE_NAME)

company = env.company
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
tax_sale = env["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)], limit=1
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)
Payment = env["account.payment"]
Wizard = env["hellenia.payment.partner.wizard"]


def _inv(ref):
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


refs = ["P199-PROD-A", "P199-PROD-B", "P199-PROD-C"]
invs = []
for ref in refs:
    inv = env["account.move"].search(
        [("partner_id", "=", partner.id), ("ref", "=", ref), ("state", "=", "posted")], limit=1
    )
    if not inv or inv.payment_state == "paid":
        inv = _inv(ref)
    invs.append(inv)
env.cr.commit()
inv_a, inv_b, inv_c = invs

ml = bnkd.inbound_payment_method_line_ids[:1]
wiz = Wizard.create(
    {
        "partner_type": "customer",
        "partner_id": partner.id,
        "journal_id": bnkd.id,
        "payment_method_line_id": ml.id,
        "payment_date": date.today(),
        "hellenia_payment_reference": "P199-PROD-CRIT",
    }
)
lines = wiz.line_ids.sorted("id")
check("02_lines_loaded", len(lines) >= 3, len(lines))
check("02_none_marked", all(not l.apply for l in lines), [l.apply for l in lines])
check("02_amount_zero", all(near(l.amount_to_pay, 0) for l in lines), [l.amount_to_pay for l in lines])

la = lines.filtered(lambda l: l.move_id == inv_a)[:1]
# Simula guardado UI parcial
wiz.write(
    {
        "line_ids": [(1, la.id, {"apply": True, "amount_to_pay": PARTIAL})],
    }
)
env.cr.execute(
    """
    SELECT m.name, l.apply, l.amount_to_pay
    FROM hellenia_payment_partner_wizard_line l
    JOIN account_move m ON m.id = l.move_id
    WHERE l.wizard_id = %s ORDER BY l.id
    """,
    [wiz.id],
)
sql_before = env.cr.fetchall()
wiz.with_context(hellenia_debug_payment_selection=True).action_register_payments()
pays = Payment.search([("hellenia_payment_reference", "=", "P199-PROD-CRIT")])
inv_a.invalidate_recordset()
inv_b.invalidate_recordset()
inv_c.invalidate_recordset()

check("03_one_payment", len(pays) == 1, len(pays))
check("03_amount_5000", near(pays[:1].amount, PARTIAL), pays[:1].amount)
check("03_a_partial", inv_a.payment_state in ("partial", "in_payment"), inv_a.payment_state)
check("03_a_residual", near(abs(inv_a.amount_residual), RESIDUAL), abs(inv_a.amount_residual))
check("03_b_open", inv_b.payment_state == "not_paid", inv_b.payment_state)
check("03_c_open", inv_c.payment_state == "not_paid", inv_c.payment_state)
check("03_no_11800_payments", not Payment.search_count([("amount", "=", TOTAL), ("id", "in", pays.ids)]), pays.mapped("amount"))

report["ui_evidence"]["prod_partial_save"] = {
    "sql_before_action": sql_before,
    "payments_created": len(pays),
    "payment_names": pays.mapped("name"),
    "payment_amounts": pays.mapped("amount"),
}
report["evidence"]["critical"] = {
    "A_state": inv_a.payment_state,
    "A_residual": abs(inv_a.amount_residual),
    "B_state": inv_b.payment_state,
    "C_state": inv_c.payment_state,
}

# Retención
cat_gov = Catalog.search([("code", "=", "RET-GOB-5"), ("company_id", "=", company.id)], limit=1)
wiz2 = Wizard.create(
    {
        "partner_type": "customer",
        "partner_id": partner.id,
        "journal_id": bnkd.id,
        "payment_method_line_id": ml.id,
        "payment_date": date.today(),
        "hellenia_payment_reference": "P199-PROD-WH",
    }
)
la2 = wiz2.line_ids.filtered(lambda l: l.move_id == inv_a)[:1]
lb2 = wiz2.line_ids.filtered(lambda l: l.move_id == inv_b)[:1]
lc2 = wiz2.line_ids.filtered(lambda l: l.move_id == inv_c)[:1]
wiz2.write(
    {
        "line_ids": [
            (
                1,
                la2.id,
                {
                    "apply": True,
                    "amount_to_pay": PARTIAL,
                    "withholding_catalog_ids": [Command.set(cat_gov.ids)],
                },
            ),
            (1, lb2.id, {"apply": False, "amount_to_pay": 0}),
            (1, lc2.id, {"apply": False, "amount_to_pay": 0}),
        ]
    }
)
wiz2.action_register_payments()
pay_wh = Payment.search([("hellenia_payment_reference", "=", "P199-PROD-WH")], limit=1)
check("04_wh_one", len(Payment.search([("hellenia_payment_reference", "=", "P199-PROD-WH")])) == 1, 1)
check("04_wh_prop", near(pay_wh.hellenia_withholding_total, GOV_WH, 1.0), pay_wh.hellenia_withholding_total)
report["evidence"]["withholding"] = {"wh_total": pay_wh.hellenia_withholding_total}

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
print(f"PHASE199P:{json.dumps(report, ensure_ascii=False, default=str)}")
