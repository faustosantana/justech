# -*- coding: utf-8 -*-
"""Fase 21.3 — Validación rápida 607/608/609 en TEST."""
from __future__ import annotations

import base64
import io
from datetime import date

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

report_data = {"checks": {}, "ok": True, "passed": 0, "total": 0, "pass": False}


def check(key, ok, detail=""):
    report_data["checks"][key] = {"ok": bool(ok), "detail": str(detail)[:300]}
    report_data["total"] += 1
    if ok:
        report_data["passed"] += 1
    else:
        report_data["ok"] = False


company = env.company
period_util = env["justech.do.dgii.period"]
period_code = date.today().strftime("%Y%m")
date_from, date_to = period_util.period_bounds_from_code(period_code)
check("period_bounds", date_from.day == 1 and date_to >= date_from, f"{date_from}..{date_to}")

# --- 607 ---
check("607_exporter", "justech.do.dgii.607.exporter" in env, "607")
exp607 = env["justech.do.dgii.607.exporter"]
result607 = exp607.validate_period(company, date_from, date_to)
summary607 = exp607.format_validation_summary(result607)
check("607_summary_es", "Resumen validación 607" in summary607, summary607[:80])
report607 = env["justech.do.fiscal.report"].create(
    {
        "name": f"607 QA {period_code}",
        "report_type": "607",
        "period_code": period_code,
        "date_from": date_from,
        "date_to": date_to,
        "company_id": company.id,
    }
)
report607.action_load_review_lines()
report607.action_validate_period()
counts607 = report607._get_fiscal_counts()
check("607_review_lines", len(report607.line_ids) == counts607["all"], counts607)
export607 = report607._get_exportable_lines()
if export607:
    content607, fname607 = exp607.export_xlsx(
        company, date_from, date_to, moves=export607.mapped("move_id")
    )
    check("607_excel", bool(content607) and fname607.endswith(".xlsx"), fname607)
    try:
        import xlsxwriter  # noqa: F401
        check("607_xlsx_bytes", len(base64.b64decode(content607 or b"")) > 100, len(content607 or ""))
    except Exception as exc:
        check("607_xlsx_bytes", False, exc)
else:
    check("607_excel", True, "sin documentos exportables en período")

# --- 608 ---
check("608_exporter", "justech.do.dgii.608.exporter" in env, "608")
exp608 = env["justech.do.dgii.608.exporter"]
domain608 = exp608._dgii_base_period_domain(company, date_from, date_to)
check("608_domain_void_date", "justech_do_ncf_void_date" in str(domain608), domain608)
result608 = exp608.validate_period(company, date_from, date_to)
report608 = env["justech.do.fiscal.report"].create(
    {
        "name": f"608 QA {period_code}",
        "report_type": "608",
        "period_code": period_code,
        "date_from": date_from,
        "date_to": date_to,
        "company_id": company.id,
    }
)
report608.action_load_review_lines()
report608.action_validate_period()
counts608 = report608._get_fiscal_counts()
check("608_review_loaded", counts608["all"] == len(report608.line_ids), counts608)
summary608 = exp608.format_validation_summary(result608)
check("608_summary_es", "608" in summary608 and "Resumen" in summary608, summary608[:80])
export608 = report608._get_exportable_lines()
if export608:
    content608, fname608 = exp608.export_xlsx(
        company, date_from, date_to, moves=export608.mapped("move_id")
    )
    check("608_excel", bool(content608), fname608)
else:
    check("608_excel", True, "sin anulados exportables en período")

# --- 609 demo + validación ---
usa = env["res.country"].search([("code", "=", "US")], limit=1)
if not usa:
    usa = env["res.country"].create({"name": "Estados Unidos", "code": "US"})
partner_foreign = env["res.partner"].search(
    [("name", "=", "PHASE213 Foreign Vendor"), ("country_id", "=", usa.id)],
    limit=1,
)
if not partner_foreign:
    partner_foreign = env["res.partner"].create(
        {"name": "PHASE213 Foreign Vendor", "country_id": usa.id, "supplier_rank": 1}
    )
journal_purchase = env["account.journal"].search(
    [("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1
)
product = env["product.product"].search([("purchase_ok", "=", True)], limit=1)
demo609 = env["account.move"].search(
    [
        ("partner_id", "=", partner_foreign.id),
        ("justech_do_foreign_document_ref", "=", "PHASE213-DEMO"),
        ("company_id", "=", company.id),
    ],
    limit=1,
)
if not demo609:
    demo609 = env["account.move"].create(
        {
            "move_type": "in_invoice",
            "partner_id": partner_foreign.id,
            "journal_id": journal_purchase.id,
            "invoice_date": date_to,
            "justech_do_foreign_609": True,
            "justech_do_foreign_service_type": "02",
            "justech_do_foreign_document_ref": "PHASE213-DEMO",
            "justech_do_foreign_payment_date": date_to,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": 500.0,
                    }
                )
            ],
        }
    )
    demo609.action_post()
else:
    demo609.write(
        {
            "justech_do_foreign_609": True,
            "justech_do_foreign_service_type": "02",
            "justech_do_foreign_document_ref": "PHASE213-DEMO",
            "justech_do_foreign_payment_date": date_to,
            "invoice_date": date_to,
        }
    )

check("609_exporter", "justech.do.dgii.609.exporter" in env, "609")
exp609 = env["justech.do.dgii.609.exporter"]
result609 = exp609.validate_period(company, date_from, date_to)
check("609_demo_in_period", demo609 in result609["buckets"]["all"], demo609.name)
report609 = env["justech.do.fiscal.report"].create(
    {
        "name": f"609 QA {period_code}",
        "report_type": "609",
        "period_code": period_code,
        "date_from": date_from,
        "date_to": date_to,
        "company_id": company.id,
    }
)
report609.action_load_review_lines()
report609.action_validate_period()
counts609 = report609._get_fiscal_counts()
check("609_review_lines", len(report609.line_ids) >= 1, counts609)
summary609 = exp609.format_validation_summary(result609)
check("609_summary_es", "609" in summary609 and "exterior" in summary609.lower(), summary609[:80])
export609 = report609._get_exportable_lines()
if export609:
    content609, fname609 = exp609.export_xlsx(
        company, date_from, date_to, moves=export609.mapped("move_id")
    )
    check("609_excel", bool(content609), fname609)
else:
    check("609_excel", False, "sin pagos exterior exportables")

# Framework común
for model in (
    "justech.do.dgii.608.exporter",
    "justech.do.dgii.609.exporter",
):
    check(f"model_{model.split('.')[-2]}", model in env, model)

Action = env["ir.actions.act_window"]
for xmlid in (
    "justech_l10n_do_reports.action_justech_do_report_609",
    "justech_l10n_do_reports.action_justech_do_fiscal_report_608",
    "justech_l10n_do_reports.action_justech_do_fiscal_report_609",
):
    try:
        act = env.ref(xmlid)
        views = act.get_views([], options={})
        check(f"action_{xmlid.split('.')[-1]}", "views" in views, xmlid)
    except Exception as exc:
        check(f"action_{xmlid.split('.')[-1]}", False, exc)

report_data["pass"] = report_data["ok"]
print(f"PHASE213:{report_data['passed']}/{report_data['total']}:{'PASS' if report_data['pass'] else 'FAIL'}")
for key, val in report_data["checks"].items():
    if not val["ok"]:
        print(f"  FAIL {key}: {val['detail']}")
