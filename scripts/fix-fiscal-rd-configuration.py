#!/usr/bin/env python3
"""Fase 13.2 — Corregir configuración fiscal RD (plan do, ITBIS 18%, desactivar 15%).

Idempotente. No elimina impuestos históricos; archiva/desactiva el 15% genérico.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

DRY_RUN = env.context.get("dry_run", False)

report = {
    "phase": "13.2",
    "block": 2,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "dry_run": DRY_RUN,
    "actions": [],
    "before": {},
    "after": {},
    "ok": True,
    "errors": [],
}


def log(action: str, detail: str = "") -> None:
    report["actions"].append({"action": action, "detail": detail})
    print(f"[fix-fiscal] {action}: {detail}")


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)
    log("ERROR", msg)


company = env.company
Tax = env["account.tax"]
Product = env["product.template"]

account_count_before = env["account.account"].search_count([("company_id", "=", company.id)])
taxes_before = Tax.with_context(active_test=False).search([("company_id", "=", company.id)])
bad15_before = taxes_before.filtered(lambda t: t.amount == 15.0 and t.active)
report["before"] = {
    "account_count": account_count_before,
    "tax_count": len(taxes_before),
    "bad_15_count": len(bad15_before),
    "bad_15_names": bad15_before.mapped("name"),
}

# Ensure l10n_do module installed
mod = env["ir.module.module"].search([("name", "=", "l10n_do")], limit=1)
if mod and mod.state != "installed":
    err(f"l10n_do no instalado (state={mod.state}); instalar antes de continuar")

# Ensure country DO
if company.partner_id.country_id.code != "DO":
    country = env["res.country"].search([("code", "=", "DO")], limit=1)
    if country and not DRY_RUN:
        company.partner_id.country_id = country.id
        log("country_set", "DO")

# Load Dominican chart if generic/small
if account_count_before < 100:
    if DRY_RUN:
        log("chart_load_skipped_dry_run", "would try_loading('do')")
    else:
        try:
            env["account.chart.template"].try_loading("do", company, install_demo=False)
            env.cr.commit()
            log("chart_loaded", "do")
        except Exception as exc:
            err(f"try_loading('do') failed: {exc}")

account_count_after_load = env["account.account"].search_count([("company_id", "=", company.id)])

# Find RD taxes
tax_18_sale = Tax.search(
    [
        ("company_id", "=", company.id),
        ("amount", "=", 18),
        ("type_tax_use", "=", "sale"),
        ("active", "=", True),
    ],
    limit=1,
)
tax_18_purchase = Tax.search(
    [
        ("company_id", "=", company.id),
        ("amount", "=", 18),
        ("type_tax_use", "=", "purchase"),
        ("active", "=", True),
    ],
    limit=1,
)
tax_exempt_sale = Tax.search(
    [
        ("company_id", "=", company.id),
        ("amount", "=", 0),
        ("type_tax_use", "=", "sale"),
        ("active", "=", True),
        ("name", "ilike", "exempt"),
    ],
    limit=1,
)

if not tax_18_sale:
    err("ITBIS 18% venta no encontrado tras cargar plan do")

# Deactivate 15% generic taxes (archive)
bad15 = Tax.with_context(active_test=False).search(
    [("company_id", "=", company.id), ("amount", "=", 15.0), ("active", "=", True)]
)
for tax in bad15:
    if DRY_RUN:
        log("deactivate_tax_dry_run", tax.name)
    else:
        tax.active = False
        log("deactivate_tax", f"{tax.name} (id={tax.id})")

# Company defaults
if tax_18_sale and hasattr(company, "account_sale_tax_id"):
    if DRY_RUN:
        log("company_sale_tax_dry_run", tax_18_sale.name)
    elif company.account_sale_tax_id != tax_18_sale:
        company.account_sale_tax_id = tax_18_sale.id
        log("company_sale_tax", tax_18_sale.name)

if tax_18_purchase and hasattr(company, "account_purchase_tax_id"):
    if DRY_RUN:
        log("company_purchase_tax_dry_run", tax_18_purchase.name)
    elif company.account_purchase_tax_id != tax_18_purchase:
        company.account_purchase_tax_id = tax_18_purchase.id
        log("company_purchase_tax", tax_18_purchase.name)

# Product categories
Cat = env["product.category"]
for cat in Cat.search([]):
    needs_sale = not cat.taxes_id or cat.taxes_id.filtered(lambda t: t.amount == 15.0 or not t.active)
    if needs_sale and tax_18_sale:
        if DRY_RUN:
            log("category_tax_dry_run", cat.name)
        else:
            cat.taxes_id = [(6, 0, tax_18_sale.ids)]
            log("category_tax", cat.name)
    if tax_18_purchase and (not cat.supplier_taxes_id or cat.supplier_taxes_id.filtered(lambda t: t.amount == 15.0)):
        if DRY_RUN:
            log("category_supplier_tax_dry_run", cat.name)
        else:
            cat.supplier_taxes_id = [(6, 0, tax_18_purchase.ids)]

# Products — remap 15% or empty sale taxes
remapped = 0
for pt in Product.search([]):
    bad = pt.taxes_id.filtered(lambda t: t.amount == 15.0 or not t.active)
    if bad or (not pt.taxes_id and tax_18_sale):
        if DRY_RUN:
            remapped += 1
        elif tax_18_sale:
            pt.taxes_id = [(6, 0, tax_18_sale.ids)]
            remapped += 1
log("products_remapped", str(remapped))

if not DRY_RUN:
    env.cr.commit()

taxes_after = Tax.with_context(active_test=False).search([("company_id", "=", company.id)])
bad15_after = taxes_after.filtered(lambda t: t.amount == 15.0 and t.active)
products_bad = Product.search([]).filtered(
    lambda p: p.taxes_id.filtered(lambda t: t.amount == 15.0 and t.active)
)

report["after"] = {
    "account_count": env["account.account"].search_count([("company_id", "=", company.id)]),
    "tax_count": len(taxes_after),
    "bad_15_count": len(bad15_after),
    "itbis_18_sale": tax_18_sale.name if tax_18_sale else "",
    "products_with_15": len(products_bad),
    "remapped_products": remapped,
}

if bad15_after or products_bad:
    report["ok"] = False
    err("Persisten impuestos/productos con 15% activo")
elif not tax_18_sale:
    report["ok"] = False

print("FISCAL_FIX:" + json.dumps(report, ensure_ascii=False, indent=2))
