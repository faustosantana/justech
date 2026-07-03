# -*- coding: utf-8 -*-
"""Fase 28B — Validación UX factura cliente (pestaña líneas, retenciones fuera del header)."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB not in ("hellenia_test", "hellenia_prod"):
    raise SystemExit(f"ABORT: solo hellenia_test/hellenia_prod, actual={DB}")

ENV = "test" if DB == "hellenia_test" else "prod"
OUT = f"/tmp/phase28b-invoice-form-ux-fix-{ENV}"
os.makedirs(OUT, exist_ok=True)

Move = env["account.move"]
SaleOrder = env["sale.order"]
arch = Move.get_view(view_type="form").get("arch", "")

report = {
    "phase": f"28b-invoice-form-ux-fix-{ENV}",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_versions": {},
    "checks": {},
    "errors": [],
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


mod_ux = env["ir.module.module"].search([("name", "=", "hellenia_ux")], limit=1)
mod_ncf = env["ir.module.module"].search([("name", "=", "justech_l10n_do_ncf")], limit=1)
mod_report = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
report["module_versions"] = {
    "hellenia_ux": mod_ux.latest_version,
    "justech_l10n_do_ncf": mod_ncf.latest_version,
    "justech_report_design": mod_report.latest_version,
}
check("module_ux_version", mod_ux.latest_version == "19.0.1.2.0", mod_ux.latest_version)
check("report_design_unchanged", mod_report.latest_version == "19.0.7.3.1", mod_report.latest_version)
check("ncf_logic_unchanged", mod_ncf.latest_version == "19.0.1.5.1", mod_ncf.latest_version)

# Orden de pestañas (vista completa; la primera operativa debe ser invoice_tab)
page_names = re.findall(r'<page[^>]*name="([^"]+)"', arch)
main_tabs = []
for name in page_names:
    if name == "other_info" and main_tabs and main_tabs[-1] == "other_info":
        break  # pestañas del formulario de asiento contable
    main_tabs.append(name)
    if name == "hellenia_withholding_tab":
        break

check("invoice_tab_exists", "invoice_tab" in main_tabs, main_tabs[:8])
check("default_tab_is_invoice_lines", main_tabs and main_tabs[0] == "invoice_tab", main_tabs[:8])
check("withholding_tab_exists", "hellenia_withholding_tab" in main_tabs, main_tabs)
if "invoice_tab" in main_tabs and "hellenia_fiscal_info_tab" in main_tabs:
    check(
        "fiscal_tab_after_invoice_tab",
        main_tabs.index("hellenia_fiscal_info_tab") > main_tabs.index("invoice_tab"),
        main_tabs,
    )
if "other_info" in main_tabs and "hellenia_fiscal_info_tab" in main_tabs:
    check(
        "fiscal_tab_after_other_info",
        main_tabs.index("hellenia_fiscal_info_tab") > main_tabs.index("other_info"),
        main_tabs,
    )
if "hellenia_withholding_tab" in main_tabs and "hellenia_fiscal_info_tab" in main_tabs:
    check(
        "withholding_tab_after_fiscal",
        main_tabs.index("hellenia_withholding_tab") > main_tabs.index("hellenia_fiscal_info_tab"),
        main_tabs,
    )
check("fiscal_tab_exists", "hellenia_fiscal_info_tab" in arch, True)
check("header_two_columns", "hellenia-invoice-header-row" in arch, True)

# Retenciones NO en encabezado (antes del notebook)
pre_nb = arch.split("<notebook", 1)[0] if "<notebook" in arch else arch
check(
    "withholdings_not_in_header",
    'string="Retenciones"' not in pre_nb and "hellenia_ret_isr_gov" not in pre_nb,
    'string="Retenciones"' in pre_nb or "hellenia_ret_isr_gov" in pre_nb,
)
check(
    "withholdings_in_tab",
    "hellenia_withholding_tab" in arch and "hellenia_ret_isr_gov" in arch,
    True,
)

# Campos fiscales avanzados fuera del header izquierdo principal
header_left = re.search(
    r'id="header_left_group"(.*?)</group>\s*<group id="header_right_group"',
    arch,
    re.DOTALL,
)
header_snip = header_left.group(1) if header_left else ""
for fname in ["justech_do_ncf_modified", "justech_do_dgii_line_status"]:
    hidden = f'name="{fname}"' in header_snip and "out_invoice', 'out_refund')" in header_snip
    check(f"header_fiscal_hidden_{fname}", hidden, hidden)

# Líneas de factura intactas
check("invoice_lines_tab_content", 'name="invoice_line_ids"' in arch, True)
check("add_line_controls", "invoice_line_ids" in arch, True)

# Regresión onchange sin partner
so_new = SaleOrder.new({"partner_id": False})
try:
    so_new._onchange_partner_justech_do_document_type()
    check("quotation_empty_partner_onchange", True, True)
except Exception as exc:
    check("quotation_empty_partner_onchange", False, str(exc))

inv_new = Move.new({"move_type": "out_invoice", "partner_id": False})
try:
    inv_new._onchange_partner_justech_do_document_type()
    check("invoice_empty_partner_onchange", True, True)
except Exception as exc:
    check("invoice_empty_partner_onchange", False, str(exc))

doc_b01 = env.ref("justech_l10n_do_base.doc_type_b01")
partner = env["res.partner"].search([("justech_do_default_document_type_id", "=", doc_b01.id)], limit=1)
if not partner:
    partner = env["res.partner"].create(
        {
            "name": "P28B UX Cliente",
            "vat": "131793916",
            "justech_do_default_document_type_id": doc_b01.id,
        }
    )
elif not partner.vat:
    partner.vat = "131793916"

inv_with = Move.new({"move_type": "out_invoice", "partner_id": partner.id})
inv_with._onchange_partner_justech_do_document_type()
check(
    "invoice_partner_inherits_default",
    inv_with.justech_do_document_type_id == doc_b01,
    inv_with.justech_do_document_type_id.display_name if inv_with.justech_do_document_type_id else False,
)

Product = env["product.product"]
Tax = env["account.tax"]
Journal = env["account.journal"]
product = Product.search([("sale_ok", "=", True)], limit=1)
tax = Tax.search([("company_id", "=", env.company.id), ("type_tax_use", "=", "sale")], limit=1)
journal = Journal.search([("type", "=", "sale"), ("company_id", "=", env.company.id)], limit=1)

doc_for_post = doc_b01
ncf_range = env["justech.do.ncf.range"].search(
    [("state", "=", "active"), ("company_id", "=", env.company.id), ("document_type_id", "=", doc_b01.id)],
    limit=1,
)
if not ncf_range:
    ncf_range = env["justech.do.ncf.range"].search(
        [("state", "=", "active"), ("company_id", "=", env.company.id)],
        limit=1,
    )
    if ncf_range:
        doc_for_post = ncf_range.document_type_id

draft_no_partner = Move.create({"move_type": "out_invoice", "journal_id": journal.id})
check("create_invoice_no_partner", draft_no_partner.state == "draft" and not draft_no_partner.partner_id, draft_no_partner.id)

draft_with_partner = Move.create(
    {
        "move_type": "out_invoice",
        "partner_id": partner.id,
        "journal_id": journal.id,
        "invoice_date": date.today(),
        "justech_do_document_type_id": doc_for_post.id,
        "invoice_line_ids": [
            Command.create(
                {
                    "product_id": product.id if product else False,
                    "name": "Línea P28B UX",
                    "quantity": 1,
                    "price_unit": 100.0,
                    "tax_ids": [Command.set(tax.ids)] if tax else [],
                }
            )
        ],
    }
)
check(
    "add_product_line",
    len(draft_with_partner.invoice_line_ids) == 1 and draft_with_partner.invoice_line_ids[0].price_unit == 100.0,
    len(draft_with_partner.invoice_line_ids),
)

try:
    draft_with_partner.action_post()
    check(
        "confirm_invoice",
        draft_with_partner.state == "posted",
        draft_with_partner.justech_do_ncf or draft_with_partner.name,
    )
except Exception as exc:
    check("confirm_invoice", False, str(exc))

report["functional_ids"] = {
    "draft_no_partner": draft_no_partner.id,
    "posted_invoice": draft_with_partner.id,
}
report["tab_order"] = main_tabs

with open(os.path.join(OUT, "form_ui_snippet.txt"), "w", encoding="utf-8") as fh:
    idx = arch.find("<notebook")
    fh.write(arch[idx : idx + 2800] if idx >= 0 else arch[:2800])

report["status"] = "PASS" if not report["errors"] else "FAIL"
with open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "env": ENV, "errors": report["errors"], "tabs": main_tabs}))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
