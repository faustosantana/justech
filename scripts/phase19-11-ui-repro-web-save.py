# -*- coding: utf-8 -*-
"""Fase 19.11 — Reproduce payload UI (web_save) antes de action_register_payments."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

DB = env.cr.dbname
SMOKE = "SMOKE P13.4 CF"
report = {
    "phase": "19.11-ui-web-save-repro",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "tests": {},
    "ok": True,
}

def check(k, ok, detail=""):
    report["tests"][k] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:800]}
    if not ok:
        report["ok"] = False

mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
check("module", bool(mod), mod.installed_version if mod else "missing")

partner = env["res.partner"].search([("name", "=", SMOKE)], limit=1)
check("partner", bool(partner), SMOKE)

Wizard = env["hellenia.payment.partner.wizard"]
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", env.company.id)], limit=1)
ml = bnkd.inbound_payment_method_line_ids[:1]

wiz = Wizard.create(
    {
        "partner_type": "customer",
        "partner_id": partner.id,
        "journal_id": bnkd.id,
        "payment_method_line_id": ml.id,
        "payment_date": date.today(),
    }
)
lines = wiz.line_ids.sorted("id")
check("create_apply_false", all(not l.apply for l in lines), [l.apply for l in lines])
check("create_amount", [l.amount_to_pay for l in lines], [l.amount_to_pay for l in lines])

# Simula editable list: Odoo envía TODAS las filas al guardar (comportamiento típico UI)
la = lines[0]
ui_vals = {
    "line_ids": [
        (
            1,
            line.id,
            {
                "apply": line.id == la.id,
                "amount_to_pay": 5000.0 if line.id == la.id else line.amount_to_pay,
            },
        )
        for line in lines
    ]
}
Wizard.browse(wiz.id).write(ui_vals)
env.cr.execute(
    """
    SELECT m.name, l.apply, l.amount_to_pay
    FROM hellenia_payment_partner_wizard_line l
    JOIN account_move m ON m.id = l.move_id
    WHERE l.wizard_id = %s ORDER BY l.id
    """,
    [wiz.id],
)
after_partial = env.cr.fetchall()
report["sql_after_partial_ui_save"] = after_partial

# Caso bug reportado: UI marca todas apply=True con monto residual
bug_vals = {
    "line_ids": [
        (1, line.id, {"apply": True, "amount_to_pay": line.amount_residual})
        for line in lines
    ]
}
wiz2 = Wizard.create(
    {
        "partner_type": "customer",
        "partner_id": partner.id,
        "journal_id": bnkd.id,
        "payment_method_line_id": ml.id,
        "payment_date": date.today(),
    }
)
lines2 = wiz2.line_ids.sorted("id")
Wizard.browse(wiz2.id).write(bug_vals)
selected = wiz2._selected_lines()
check("bug_all_selected_count", len(selected) == len(lines2), len(selected))
check("bug_would_pay_all", len(selected) > 1, selected.mapped("move_id.name"))

# Caso v23: apply=False pero amount_to_pay=residual (carga inicial)
wiz3 = Wizard.create(
    {
        "partner_type": "customer",
        "partner_id": partner.id,
        "journal_id": bnkd.id,
        "payment_method_line_id": ml.id,
    }
)
l3 = wiz3.line_ids.sorted("id")
check(
    "v23_load_amount_residual_with_apply_false",
    any((not l.apply and l.amount_to_pay > 0) for l in l3),
    [(l.apply, l.amount_to_pay) for l in l3],
)

report["pass"] = report["ok"]
print(f"PHASE1911WEB:{json.dumps(report, ensure_ascii=False, default=str)}")
