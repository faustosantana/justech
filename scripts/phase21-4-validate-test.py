# -*- coding: utf-8 -*-
"""Fase 21.4 — Validación 609 vacío + 623 retenciones Gobierno en TEST."""
from __future__ import annotations

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

# --- 609 vacío amigable ---
exp609 = env["justech.do.dgii.609.exporter"]
report609_empty = env["justech.do.fiscal.report"].create(
    {
        "name": f"609 vacío QA {period_code}",
        "report_type": "609",
        "period_code": period_code,
        "date_from": date_from,
        "date_to": date_to,
        "company_id": company.id,
    }
)
report609_empty.action_load_review_lines()
check("609_review_loaded", report609_empty.review_loaded, report609_empty.review_loaded)
report609_empty.action_validate_period()
check("609_empty_state", report609_empty.state == "no_movements", report609_empty.state)
check(
    "609_empty_message",
    "exterior" in (report609_empty.validation_log or "").lower(),
    report609_empty.validation_log,
)
diag609 = report609_empty._get_export_diagnostics()
check("609_not_not_loaded", not diag609["not_loaded"], diag609["not_loaded"])
check("609_no_movements_flag", diag609["no_movements"], diag609["no_movements"])

# --- 609 demo con datos ---
usa = env["res.country"].search([("code", "=", "US")], limit=1)
partner_foreign = env["res.partner"].search(
    [("name", "=", "PHASE214 Foreign Vendor")], limit=1
)
if not partner_foreign:
    partner_foreign = env["res.partner"].create(
        {"name": "PHASE214 Foreign Vendor", "country_id": usa.id, "supplier_rank": 1}
    )
journal_purchase = env["account.journal"].search(
    [("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1
)
product = env["product.product"].search([("purchase_ok", "=", True)], limit=1)
demo609 = env["account.move"].search(
    [("justech_do_foreign_document_ref", "=", "PHASE214-DEMO")], limit=1
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
            "justech_do_foreign_document_ref": "PHASE214-DEMO",
            "justech_do_foreign_payment_date": date_to,
            "justech_do_foreign_exchange_rate": 1.0,
            "invoice_line_ids": [
                Command.create(
                    {"product_id": product.id, "quantity": 1, "price_unit": 750.0}
                )
            ],
        }
    )
    demo609.action_post()
else:
    demo609.write(
        {
            "invoice_date": date_to,
            "justech_do_foreign_service_type": "02",
            "justech_do_foreign_exchange_rate": 1.0,
        }
    )

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
check("609_has_lines", len(report609.line_ids) >= 1, len(report609.line_ids))
export609 = report609._get_exportable_lines()
if export609:
    content609, fname609 = exp609.export_xlsx(
        company, date_from, date_to, moves=export609.mapped("move_id")
    )
    check("609_excel", bool(content609), fname609)

# --- 623 demo retención Gobierno ---
exp623 = env["justech.do.dgii.623.exporter"]
gov_partner = env["res.partner"].search([("name", "=", "PHASE214 Gov Entity")], limit=1)
if not gov_partner:
    gov_partner = env["res.partner"].create(
        {
            "name": "PHASE214 Gov Entity",
            "vat": "401007576",
            "customer_rank": 1,
        }
    )
journal_sale = env["account.journal"].search(
    [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
)
tax_18 = env["account.tax"].search(
    [
        ("type_tax_use", "=", "sale"),
        ("amount", "=", 18.0),
        ("company_id", "=", company.id),
    ],
    limit=1,
)
gov_tax = env["account.tax"].search(
    [
        ("name", "=", "-5% ISR Gov."),
        ("type_tax_use", "=", "sale"),
        ("company_id", "=", company.id),
    ],
    limit=1,
)
demo623 = env["account.move"].search(
    [("ref", "=", "PHASE214-GOV-623")], limit=1
)
if not demo623:
    line_taxes = tax_18 | gov_tax if tax_18 and gov_tax else tax_18
    demo623 = env["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": gov_partner.id,
            "journal_id": journal_sale.id,
            "invoice_date": date_to,
            "ref": "PHASE214-GOV-623",
            "justech_do_gov_retention_ref": "TRF-PHASE214",
            "justech_do_gov_retention_ref_type": "2",
            "justech_do_gov_retention_date": date_to,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": 10000.0,
                        "tax_ids": [Command.set(line_taxes.ids)] if line_taxes else [],
                    }
                )
            ],
        }
    )
    demo623.action_post()
else:
    demo623.write(
        {
            "invoice_date": date_to,
            "justech_do_gov_retention_date": date_to,
            "justech_do_gov_retention_ref": "TRF-PHASE214",
            "justech_do_gov_retention_ref_type": "2",
        }
    )
    demo623._justech_sync_gov_withholding_from_tax()

check("623_gov_amount", demo623.justech_do_gov_withholding_amount > 0, demo623.justech_do_gov_withholding_amount)

report623 = env["justech.do.fiscal.report"].create(
    {
        "name": f"623 QA {period_code}",
        "report_type": "623",
        "period_code": period_code,
        "date_from": date_from,
        "date_to": date_to,
        "company_id": company.id,
    }
)
report623.action_load_review_lines()
report623.action_validate_period()
check("623_review_lines", len(report623.line_ids) >= 1, len(report623.line_ids))
export623 = report623._get_exportable_lines()
if export623:
    content623, fname623 = exp623.export_xlsx(
        company, date_from, date_to, moves=export623.mapped("move_id")
    )
    check("623_excel", bool(content623), fname623)
else:
    check("623_excel", False, report623.validation_log)

check("623_exporter_model", "justech.do.dgii.623.exporter" in env, "623")
check("623_menu", bool(env.ref("justech_l10n_do_reports.action_justech_do_report_623", False)), "menu")

report_data["pass"] = report_data["ok"]
print(f"PHASE214:{report_data['passed']}/{report_data['total']}:{'PASS' if report_data['pass'] else 'FAIL'}")
for key, val in report_data["checks"].items():
    if not val["ok"]:
        print(f"  FAIL {key}: {val['detail']}")
