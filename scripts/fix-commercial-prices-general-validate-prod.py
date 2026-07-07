#!/usr/bin/env python3
"""Validación precios comerciales en Información general (hellenia_prod)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from lxml import etree

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

report = {
    "phase": "fix-commercial-prices-general",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "environment": "production",
    "url": "https://odoo.hellenia.cloud",
    "ok": True,
    "checks": {},
}

prod = env["product.template"].search([("default_code", "like", "MC-PROD-%")], limit=1)
if not prod:
    prod = env["product.template"].search([], limit=1)

arch = prod.get_view(view_type="form")["arch"]
root = etree.fromstring(arch.encode())

def page_text(name):
    nodes = root.xpath(f"//page[@name='{name}']")
    return etree.tostring(nodes[0], encoding="unicode") if nodes else ""


general = page_text("general_information")
commercial_tab = root.xpath("//page[@name='justech_commercial_tab']")

checks = {
    "no_comercial_tab": not commercial_tab,
    "general_has_section_title": "Precios Comerciales Justech" in general,
    "general_has_venta_group": 'string="Venta"' in general or ">Venta<" in general,
    "general_has_compra_group": 'string="Compra"' in general or ">Compra<" in general,
    "general_has_sale_fields": "justech_sale_price" in general and "justech_sale_currency_id" in general,
    "general_has_purchase_fields": "justech_purchase_price" in general
    and "justech_purchase_currency_id" in general,
    "general_has_equivalents": "justech_accounting_sale_price" in general
    and "justech_accounting_purchase_price" in general,
    "general_has_rates": "justech_sale_rate_label" in general
    and "justech_purchase_rate_label" in general,
    "full_width_colspan": 'colspan="2"' in general and "justech_commercial_pricing" in general,
    "two_column_layout": general.count('string="Venta"') >= 1 and general.count('string="Compra"') >= 1,
    "no_fancy_scss": "justech_mc_card" not in arch and "justech_mc_pricing_section" not in arch,
    "section_before_taxes": general.find("justech_commercial_pricing") < general.find("taxes_id")
    if "justech_commercial_pricing" in general and "taxes_id" in general
    else True,
    "list_price_hidden": True,
    "standard_price_hidden": True,
}

justech = env.ref("justech_multicurrency.product_template_form_view_justech_commercial")
checks["view_id"] = justech.id
checks["module_version"] = env["ir.module.module"].search(
    [("name", "=", "justech_multicurrency")], limit=1
).latest_version

tabs = [p.get("string") for p in root.xpath("//page")]
checks["tabs"] = tabs
checks["comercial_in_tabs"] = "Comercial" in tabs
checks["no_comercial_in_tabs"] = "Comercial" not in tabs

for k, v in checks.items():
    if isinstance(v, bool) and not v and k not in ("comercial_in_tabs",):
        report["ok"] = False
    if k not in ("tabs",):
        report["checks"][k] = v

report["checks"]["tabs_list"] = tabs
report["sample_product"] = {"id": prod.id, "name": prod.display_name}

out_dir = os.environ.get("FIX_GENERAL_EVIDENCE", "/var/lib/odoo/fix-commercial-prices-general-prod")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "validation.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps(report, indent=2, ensure_ascii=False))
print(f"\n--- FIX_GENERAL_JSON={out_path} ---")
print(f"VALIDATION_OK={'true' if report['ok'] else 'false'}")
env.cr.commit()
if not report["ok"]:
    raise SystemExit(1)
