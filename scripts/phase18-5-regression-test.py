# -*- coding: utf-8 -*-
"""Fase 18.5 — Validación cierre regresión 606/607 período mensual DGII."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

report = {
    "phase": "18.5-606-607-regression",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "checks": {},
    "ok": True,
    "pass": False,
    "cause": (
        "Scripts 18/18.2/18.3 usaban date_from=1-ene y date_to=hoy (rango YTD) "
        "sin period_code coherente. El wizard tomaba period_code=mes actual (YYYYMM) "
        "y validate_period_dates fallaba; fiscal.report derivaba period_code del 1-ene "
        "y _sync_dates_from_period_code reducía el rango a enero, excluyendo facturas de hoy."
    ),
    "fix": (
        "Usar período mensual DGII: period_code=default_period_code(), "
        "date_from/date_to=period_bounds_from_code(period_code), alineado con invoice_date=hoy."
    ),
}

TOL = 0.01


def check(key, ok, detail=""):
    report["checks"][key] = {"ok": bool(ok), "detail": str(detail)[:400]}
    if not ok:
        report["ok"] = False


period_util = env["justech.do.dgii.period"]
period_code = period_util.default_period_code()
date_from, date_to = period_util.period_bounds_from_code(period_code)
today = date.today()

check("period_code_current_month", period_code == today.strftime("%Y%m"), period_code)
check("period_bounds_month", date_from.day == 1 and date_to.month == today.month, f"{date_from} — {date_to}")

# Anti-patrón YTD debe fallar validación
try:
    period_util.validate_period_dates(
        today.replace(month=1, day=1), today, period_code
    )
    check("ytd_pattern_rejected", False, "no lanzó error")
except Exception as exc:
    check("ytd_pattern_rejected", True, str(exc)[:200])

company = env.company
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
product = env["product.product"].search([("purchase_ok", "=", True)], limit=1)
tax_purchase = env["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)],
    limit=1,
)
tax_sale = env["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)],
    limit=1,
)
journal_purchase = env["account.journal"].search(
    [("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1
)
journal_sale = env["account.journal"].search(
    [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
)


def _invoice(partner, journal, tax, move_type):
    inv = env["account.move"].create(
        {
            "move_type": move_type,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "invoice_date": today,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": 10000.0,
                        "tax_ids": [Command.set(tax.ids)] if tax else [],
                    }
                )
            ],
        }
    )
    inv.action_post()
    return inv


# Wizard 606/607 con período correcto
for rtype in ("606", "607"):
    try:
        wiz = env["justech.do.fiscal.report.wizard"].create(
            {
                "report_type": rtype,
                "period_code": period_code,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        check(f"wizard_{rtype}_period", wiz.period_code == period_code, wiz.period_code)
        check(
            f"wizard_{rtype}_dates",
            wiz.date_from == date_from and wiz.date_to == date_to,
            f"{wiz.date_from} — {wiz.date_to}",
        )
        wiz.action_validate()
        check(f"wizard_{rtype}_validate", wiz.validation_state in ("ok", "warning", "empty"), wiz.validation_state)
    except Exception as exc:
        check(f"wizard_{rtype}_validate", False, exc)

# fiscal.report con facturas del mes
bill = _invoice(vendor, journal_purchase, tax_purchase, "in_invoice")
sale = _invoice(customer, journal_sale, tax_sale, "out_invoice")

for rtype, move in (("606", bill), ("607", sale)):
    rep = env["justech.do.fiscal.report"].create(
        {
            "name": f"P185 {rtype} {period_code}",
            "report_type": rtype,
            "period_code": period_code,
            "date_from": date_from,
            "date_to": date_to,
            "company_id": company.id,
        }
    )
    check(f"report_{rtype}_period_sync", rep.date_from == date_from and rep.date_to == date_to, f"{rep.date_from}-{rep.date_to}")
    rep.action_generate()
    lines = rep.line_ids.filtered(lambda l: l.move_id == move)
    check(f"report_{rtype}_has_invoice", bool(lines), f"lines={len(lines)} move={move.name}")

report["pass"] = report["ok"]
print(f"PHASE185:{json.dumps(report, ensure_ascii=False)}")
