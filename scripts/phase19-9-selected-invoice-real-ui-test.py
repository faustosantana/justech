# -*- coding: utf-8 -*-
"""Fase 19.9 — Validación real UI/selección facturas wizard (TEST)."""
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
GOV_WH = round((BASE * (PARTIAL / TOTAL)) * 0.05, 2)
SMOKE_NAME = "SMOKE P13.4 CF"

report = {
    "phase": "19.9-selected-invoice-real-ui",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "root_cause": (
        "_load_pending_invoices precargaba amount_to_pay=residual en todas las líneas aunque "
        "apply=False; la UI editable no siempre persiste apply antes del botón; líneas no "
        "seleccionadas conservaban monto > 0 y podían procesarse si apply quedaba True en caché."
    ),
    "fix": (
        "amount_to_pay=0 al cargar; write() y guard servidor anulan montos/retenciones si apply=False; "
        "_selected_line_ids_sql() lee apply desde BD; validación de conteo de pagos; "
        "amount_to_pay readonly si not apply."
    ),
    "hypotheses": {},
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


def hypo(key, confirmed, detail=""):
    report["hypotheses"][key] = {"confirmed": confirmed, "detail": str(detail)[:500]}


def near(a, b, tol=TOL):
    return abs((a or 0.0) - (b or 0.0)) <= tol


mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
if mod:
    mod.button_immediate_upgrade()
    env.cr.commit()
check("00_upgrade", mod and mod.latest_version == "19.0.1.0.25", mod.latest_version if mod else "")

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
Line = env["hellenia.payment.partner.wizard.line"]


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


def _setup_smoke_three():
    partner = env["res.partner"].search([("name", "=", SMOKE_NAME)], limit=1)
    if not partner:
        partner = env["res.partner"].create(
            {"name": SMOKE_NAME, "customer_rank": 1, "company_type": "company"}
        )
    refs = ["P199-A", "P199-B", "P199-C"]
    invs = []
    for ref in refs:
        existing = env["account.move"].search(
            [("partner_id", "=", partner.id), ("ref", "=", ref), ("state", "=", "posted")], limit=1
        )
        invs.append(existing if existing else _inv(partner, ref))
    env.cr.commit()
    return partner, invs[0], invs[1], invs[2]


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


# H1: default apply False + amount 0 on load
partner, inv_a, inv_b, inv_c = _setup_smoke_three()
wiz_load = _wiz(partner, "P199-LOAD")
lines_load = wiz_load.line_ids.sorted("id")
check("01_three_lines", len(lines_load) == 3, len(lines_load))
check(
    "01_default_apply_false",
    all(not l.apply for l in lines_load),
    [l.apply for l in lines_load],
)
check(
    "01_default_amount_zero",
    all(near(l.amount_to_pay, 0) for l in lines_load),
    [l.amount_to_pay for l in lines_load],
)
hypo("h1_apply_true_server", any(l.apply for l in lines_load), "apply en carga")

# H2/H4: UI partial save — solo se escribe la línea editada (como hace el navegador)
wiz_ui = _wiz(partner, "P199-UI-PARTIAL")
la, lb, lc = wiz_ui.line_ids.sorted("id")
pay_before = Payment.search_count([])
# Simula guardado parcial del formulario: solo la primera línea en el write
wiz_ui.write(
    {
        "journal_id": bnkd.id,
        "payment_method_line_id": bnkd.inbound_payment_method_line_ids[:1].id,
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
    [wiz_ui.id],
)
sql_snapshot = env.cr.fetchall()
hypo("h2_partial_save_sql", len(sql_snapshot) == 3, sql_snapshot)
wiz_ui.with_context(hellenia_debug_payment_selection=True).action_register_payments()
env.cr.flush()
pays_ui = Payment.search([("hellenia_payment_reference", "=", "P199-UI-PARTIAL")])
inv_a.invalidate_recordset()
inv_b.invalidate_recordset()
inv_c.invalidate_recordset()
check("02_ui_partial_one_payment", len(pays_ui) == 1, len(pays_ui))
check("02_ui_partial_amount", near(pays_ui[:1].amount, PARTIAL), pays_ui[:1].amount)
check("02_ui_a_partial", inv_a.payment_state in ("partial", "in_payment"), inv_a.payment_state)
check("02_ui_b_open", inv_b.payment_state == "not_paid", inv_b.payment_state)
check("02_ui_c_open", inv_c.payment_state == "not_paid", inv_c.payment_state)
report["ui_evidence"]["partial_form_save"] = {
    "sql_before_action": sql_snapshot,
    "payments": len(pays_ui),
    "payment_amount": pays_ui[:1].amount,
    "A": inv_a.payment_state,
    "B": inv_b.payment_state,
    "C": inv_c.payment_state,
}

# H3: líneas con amount>0 pero apply=False no deben pagarse
partner2 = env["res.partner"].create({"name": "P199 H3", "customer_rank": 1})
ia, ib, ic = _inv(partner2, "P199-H3A"), _inv(partner2, "P199-H3B"), _inv(partner2, "P199-H3C")
env.cr.commit()
wiz_h3 = _wiz(partner2, "P199-H3")
la3, lb3, lc3 = wiz_h3.line_ids.sorted("id")
la3.write({"apply": True, "amount_to_pay": PARTIAL})
# Forzar monto residual en no seleccionadas (simula estado corrupto pre-fix)
lb3.write({"apply": False, "amount_to_pay": TOTAL})
lc3.write({"apply": False, "amount_to_pay": TOTAL})
wiz_h3._enforce_server_selection_guard()
check("03_guard_zeros_unselected", near(lb3.amount_to_pay, 0) and near(lc3.amount_to_pay, 0), f"{lb3.amount_to_pay},{lc3.amount_to_pay}")
wiz_h3.action_register_payments()
pays_h3 = Payment.search([("hellenia_payment_reference", "=", "P199-H3")])
check("03_one_payment_despite_old_amounts", len(pays_h3) == 1, len(pays_h3))
hypo("h3_amount_without_apply", len(pays_h3) > 1, len(pays_h3))

# web_save UI path (Odoo 19)
partner3 = env["res.partner"].create({"name": "P199 WEBSAVE", "customer_rank": 1})
i1, i2, i3 = _inv(partner3, "P199-WS1"), _inv(partner3, "P199-WS2"), _inv(partner3, "P199-WS3")
env.cr.commit()
wiz_ws = _wiz(partner3, "P199-WEBSAVE")
l1, l2, l3 = wiz_ws.line_ids.sorted("id")
ws_vals = {
    "journal_id": bnkd.id,
    "payment_method_line_id": bnkd.inbound_payment_method_line_ids[:1].id,
    "line_ids": [
        (1, l1.id, {"apply": True, "amount_to_pay": PARTIAL}),
        (1, l2.id, {"apply": False, "amount_to_pay": 0}),
        (1, l3.id, {"apply": False, "amount_to_pay": 0}),
    ],
}
try:
    wiz_ws.web_save(ws_vals, {})
    wiz_ws.action_register_payments()
    pays_ws = Payment.search([("hellenia_payment_reference", "=", "P199-WEBSAVE")])
    check("04_web_save_one_payment", len(pays_ws) == 1, len(pays_ws))
    report["ui_evidence"]["web_save"] = {"payments": len(pays_ws), "amount": pays_ws[:1].amount}
except AttributeError:
    wiz_ws.write(ws_vals)
    wiz_ws.action_register_payments()
    pays_ws = Payment.search([("hellenia_payment_reference", "=", "P199-WEBSAVE")])
    check("04_web_save_one_payment", len(pays_ws) == 1, len(pays_ws))
    report["ui_evidence"]["web_save"] = {"fallback_write": True, "payments": len(pays_ws)}

# Retención solo en A
cat_gov = Catalog.search([("code", "=", "RET-GOB-5"), ("company_id", "=", company.id)], limit=1)
partner4 = env["res.partner"].create({"name": "P199 WH", "customer_rank": 1})
wa, wb, wc = _inv(partner4, "P199-WHA"), _inv(partner4, "P199-WHB"), _inv(partner4, "P199-WHC")
env.cr.commit()
wiz_wh = _wiz(partner4, "P199-WH")
la4, lb4, lc4 = wiz_wh.line_ids.sorted("id")
wiz_wh.write(
    {
        "line_ids": [
            (
                1,
                la4.id,
                {
                    "apply": True,
                    "amount_to_pay": PARTIAL,
                    "withholding_catalog_ids": [Command.set(cat_gov.ids)],
                },
            ),
            (1, lb4.id, {"apply": False, "amount_to_pay": 0}),
            (1, lc4.id, {"apply": False, "amount_to_pay": 0}),
        ]
    }
)
wiz_wh.action_register_payments()
pay_wh = Payment.search([("hellenia_payment_reference", "=", "P199-WH")], limit=1)
check("05_wh_one_payment", len(Payment.search([("hellenia_payment_reference", "=", "P199-WH")])) == 1, 1)
check("05_wh_amount", near(pay_wh.hellenia_withholding_total, GOV_WH, 1.0), pay_wh.hellenia_withholding_total)

report["evidence"]["smoke_partner"] = SMOKE_NAME
report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
print(f"PHASE199:{json.dumps(report, ensure_ascii=False, default=str)}")
