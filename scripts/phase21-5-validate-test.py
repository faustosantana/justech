# -*- coding: utf-8 -*-
"""Fase 21.5 — Validación RPC 623 + menú DGII + apertura reportes en TEST."""
from __future__ import annotations

from datetime import date

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

report_data = {"checks": {}, "ok": True, "passed": 0, "total": 0, "pass": False}
DGII_TYPES = ("606", "607", "608", "609", "623")


def check(key, ok, detail=""):
    report_data["checks"][key] = {"ok": bool(ok), "detail": str(detail)[:300]}
    report_data["total"] += 1
    if ok:
        report_data["passed"] += 1
    else:
        report_data["ok"] = False


Wizard = env["justech.do.fiscal.report.wizard"]
selection = dict(Wizard._fields["report_type"].selection)
for rtype in DGII_TYPES:
    check(f"selection_wizard_{rtype}", rtype in selection, selection.get(rtype, "missing"))

Report = env["justech.do.fiscal.report"]
report_sel = dict(Report._fields["report_type"].selection)
for rtype in DGII_TYPES:
    check(f"selection_report_{rtype}", rtype in report_sel, report_sel.get(rtype, "missing"))

company = env.company
period_util = env["justech.do.dgii.period"]
period_code = date.today().strftime("%Y%m")
date_from, date_to = period_util.period_bounds_from_code(period_code)

for rtype in DGII_TYPES:
    wiz = Wizard.create(
        {
            "report_type": rtype,
            "period_code": period_code,
            "date_from": date_from,
            "date_to": date_to,
            "company_id": company.id,
        }
    )
    check(f"wizard_create_{rtype}", wiz.report_type == rtype, wiz.report_type)
    views = Wizard.get_views([(False, "form")])
    check(f"wizard_get_views_{rtype}", bool(views.get("views")), "form ok")
    wiz.unlink()

action_xmlids = {
    "606": "justech_l10n_do_reports.action_justech_do_report_606",
    "607": "justech_l10n_do_reports.action_justech_do_report_607",
    "608": "justech_l10n_do_reports.action_justech_do_report_608",
    "609": "justech_l10n_do_reports.action_justech_do_report_609",
    "623": "justech_l10n_do_reports.action_justech_do_report_623",
    "history": "justech_l10n_do_reports.action_justech_do_fiscal_report",
    "review": "justech_l10n_do_reports.action_justech_do_fiscal_review",
}
for key, xid in action_xmlids.items():
    act = env.ref(xid, raise_if_not_found=False)
    check(f"action_{key}", bool(act), xid)
    if act:
        check(f"action_{key}_model", act.res_model in (
            "justech.do.fiscal.report.wizard",
            "justech.do.fiscal.report",
        ), act.res_model)

removed_menus = [
    "menu_justech_do_report_606_list",
    "menu_justech_do_report_607_list",
    "menu_justech_do_report_608_list",
    "menu_justech_do_report_609_list",
    "menu_justech_do_report_623_list",
]
for mid in removed_menus:
    menu = env.ref(f"justech_l10n_do_reports.{mid}", raise_if_not_found=False)
    check(f"menu_removed_{mid}", not menu, "still exists" if menu else "removed")

history_menu = env.ref("justech_l10n_do_reports.menu_justech_do_reports_history", False)
check("menu_history", bool(history_menu), history_menu.name if history_menu else "missing")

# 623 vacío — mensaje amigable
report623_empty = Report.create(
    {
        "name": f"623 vacío QA {period_code}",
        "report_type": "623",
        "period_code": period_code,
        "date_from": date_from,
        "date_to": date_to,
        "company_id": company.id,
    }
)
report623_empty.action_load_review_lines()
report623_empty.action_validate_period()
check("623_empty_state", report623_empty.state == "no_movements", report623_empty.state)
expected = "No hay movimientos para este reporte en el período seleccionado."
check(
    "623_empty_message",
    expected in (report623_empty.validation_log or ""),
    report623_empty.validation_log,
)

# 623 con retención Gobierno

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
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
demo623 = env["account.move"].search([("ref", "=", "PHASE214-GOV-623")], limit=1)
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
    if hasattr(demo623, "_justech_sync_gov_withholding_from_tax"):
        demo623._justech_sync_gov_withholding_from_tax()

if demo623 and demo623.justech_do_gov_withholding_amount > 0:
    check("623_gov_amount", True, demo623.justech_do_gov_withholding_amount)
    report623 = Report.create(
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
    check("623_has_lines", len(report623.line_ids) >= 1, len(report623.line_ids))
    exp623 = env["justech.do.dgii.623.exporter"]
    export623 = report623._get_exportable_lines()
    if export623:
        content623, fname623 = exp623.export_xlsx(
            company, date_from, date_to, moves=export623.mapped("move_id")
        )
        check("623_excel", bool(content623), fname623)
else:
    check("623_gov_amount", False, demo623.justech_do_gov_withholding_amount if demo623 else "no demo")

report_data["pass"] = report_data["ok"]
print(f"PHASE215:{report_data['passed']}/{report_data['total']}:{'PASS' if report_data['pass'] else 'FAIL'}")
for key, val in report_data["checks"].items():
    if not val["ok"]:
        print(f"  FAIL {key}: {val['detail']}")
