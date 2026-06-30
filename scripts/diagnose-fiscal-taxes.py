#!/usr/bin/env python3
"""Fase 13.2 — Diagnóstico fiscal: impuestos, plan contable y causa raíz del 15%."""
from __future__ import annotations

import json
from datetime import datetime, timezone

report = {
    "phase": "13.2",
    "block": 1,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "company": {},
    "chart": {},
    "taxes": {"all": [], "sale": [], "purchase": [], "bad_15_percent": []},
    "products_with_15": [],
    "journals": [],
    "fiscal_positions": [],
    "modules": {},
    "root_cause": None,
    "ok": True,
    "recommendations": [],
}

company = env.company
partner = company.partner_id

report["company"] = {
    "id": company.id,
    "name": company.name,
    "vat": partner.vat or "",
    "country": partner.country_id.code or "",
    "currency": company.currency_id.name,
    "fiscal_enabled": bool(getattr(company, "justech_do_fiscal_enabled", False)),
}

account_count = env["account.account"].search_count([("company_id", "=", company.id)])
report["chart"]["account_count"] = account_count

# Detect chart template via company or tax xmlids
chart_hint = "unknown"
if account_count <= 60:
    chart_hint = "generic_coa"
elif account_count >= 200:
    chart_hint = "do"
report["chart"]["template_hint"] = chart_hint

Tax = env["account.tax"]
taxes = Tax.with_context(active_test=False).search([("company_id", "=", company.id)])
report["taxes"]["total_count"] = len(taxes)
report["taxes"]["active_count"] = len(taxes.filtered("active"))

for tax in taxes.sorted(lambda t: (t.type_tax_use, t.amount, t.name)):
    xmlid = ""
    data = env["ir.model.data"].search(
        [("model", "=", "account.tax"), ("res_id", "=", tax.id)], limit=1
    )
    if data:
        xmlid = f"{data.module}.{data.name}"
    entry = {
        "id": tax.id,
        "name": tax.name,
        "amount": tax.amount,
        "type_tax_use": tax.type_tax_use,
        "active": tax.active,
        "xmlid": xmlid,
    }
    report["taxes"]["all"].append(entry)
    if tax.type_tax_use == "sale":
        report["taxes"]["sale"].append(entry)
    elif tax.type_tax_use == "purchase":
        report["taxes"]["purchase"].append(entry)
    if tax.amount == 15.0 and tax.active:
        report["taxes"]["bad_15_percent"].append(entry)

# ITBIS availability
itbis_sale_18 = Tax.search(
    [
        ("company_id", "=", company.id),
        ("amount", "=", 18),
        ("type_tax_use", "=", "sale"),
        ("active", "=", True),
    ],
    limit=1,
)
itbis_exempt = Tax.search(
    [
        ("company_id", "=", company.id),
        ("amount", "=", 0),
        ("type_tax_use", "=", "sale"),
        ("active", "=", True),
        ("name", "ilike", "exempt"),
    ],
    limit=1,
)
report["taxes"]["itbis_18_sale"] = {
    "found": bool(itbis_sale_18),
    "id": itbis_sale_18.id if itbis_sale_18 else None,
    "name": itbis_sale_18.name if itbis_sale_18 else "",
}
report["taxes"]["itbis_exempt_sale"] = {
    "found": bool(itbis_exempt),
    "name": itbis_exempt.name if itbis_exempt else "",
}

# Products with 15% sale tax
Product = env["product.template"]
for pt in Product.search([]):
    bad = pt.taxes_id.filtered(lambda t: t.amount == 15.0 and t.active)
    if bad:
        report["products_with_15"].append(
            {
                "id": pt.id,
                "name": pt.name,
                "default_code": pt.default_code or "",
                "tax_ids": bad.ids,
                "tax_names": bad.mapped("name"),
            }
        )

# Journals
for journal in env["account.journal"].search([("company_id", "=", company.id)]):
    report["journals"].append(
        {
            "id": journal.id,
            "name": journal.name,
            "code": journal.code,
            "type": journal.type,
            "ncf": bool(getattr(journal, "justech_do_use_ncf", False)),
        }
    )

# Fiscal positions
for fp in env["account.fiscal.position"].search([("company_id", "=", company.id)]):
    report["fiscal_positions"].append({"id": fp.id, "name": fp.name, "active": fp.active})

# Modules
for mod_name in ("l10n_do", "justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports"):
    mod = env["ir.module.module"].search([("name", "=", mod_name)], limit=1)
    report["modules"][mod_name] = mod.state if mod else "missing"

# Company default taxes
if hasattr(company, "account_sale_tax_id"):
    report["company"]["account_sale_tax_id"] = (
        company.account_sale_tax_id.name if company.account_sale_tax_id else None
    )
if hasattr(company, "account_purchase_tax_id"):
    report["company"]["account_purchase_tax_id"] = (
        company.account_purchase_tax_id.name if company.account_purchase_tax_id else None
    )

# Root cause analysis
bad15 = report["taxes"]["bad_15_percent"]
if bad15 and chart_hint == "generic_coa":
    report["root_cause"] = (
        "Plan contable genérico (generic_coa) sin cargar l10n_do/do; "
        "impuestos plantilla Odoo 15% (account.*_tax_template) activos."
    )
    report["ok"] = False
elif bad15:
    report["root_cause"] = "Impuestos 15% activos fuera del estándar RD ITBIS 18%."
    report["ok"] = False
elif not itbis_sale_18:
    report["root_cause"] = "No existe impuesto ITBIS 18% venta activo."
    report["ok"] = False
elif report["products_with_15"]:
    report["root_cause"] = "Productos aún asignados a impuesto 15%."
    report["ok"] = False
else:
    report["root_cause"] = "Configuración fiscal RD correcta; sin impuesto 15% detectado."

if chart_hint == "generic_coa":
    report["recommendations"].append("Cargar plan contable dominicano: account.chart.template.try_loading('do', company)")
if bad15:
    report["recommendations"].append("Archivar/desactivar impuestos 15% (no eliminar por auditoría)")
if not itbis_sale_18:
    report["recommendations"].append("Instalar/actualizar l10n_do y cargar impuestos RD")
if report["products_with_15"]:
    report["recommendations"].append("Remapear productos a ITBIS 18% venta")

print("FISCAL_DIAGNOSIS:" + json.dumps(report, ensure_ascii=False, indent=2))
