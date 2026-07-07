#!/usr/bin/env python3
"""MC-PROD — Configurar política comercial USD/DOP."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from odoo import fields

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

if "justech.multicurrency.policy" not in env:
    raise SystemExit("ABORT: justech_multicurrency no instalado")

TS = datetime.now(timezone.utc).isoformat()
TODAY = fields.Date.today()
company = env.company
usd = env.ref("base.USD")
dop = env.ref("base.DOP")
usd.active = True
dop.active = True

Policy = env["justech.multicurrency.policy"]
Rate = env["res.currency.rate"].sudo()

TARGET_RATE = float(os.environ.get("MC_PROD_USD_RATE", "58.0"))

report = {
    "phase": "MC-PROD-config",
    "timestamp_utc": TS,
    "database": DB,
    "ok": True,
    "errors": [],
    "policy": {},
}

policy = Policy.get_policy(company)
policy.write(
    {
        "commercial_currency_id": usd.id,
        "default_customer_currency_id": usd.id,
        "default_supplier_currency_id": usd.id,
    }
)
policy.invalidate_recordset()
public_pl = Policy._find_or_create_public_pricelist(company, usd)

existing = Rate.search(
    [
        ("currency_id", "=", usd.id),
        ("name", "=", TODAY),
        ("company_id", "in", [company.id, False]),
    ],
    order="id desc",
    limit=1,
)
rate_vals = {
    "inverse_company_rate": TARGET_RATE,
    "company_id": company.id,
    "justech_rate_origin": "manual",
    "justech_archived": False,
}
if existing:
    existing.write(rate_vals)
    rate_rec = existing
else:
    rate_rec = Rate.create({"name": TODAY, "currency_id": usd.id, **rate_vals})

checks = {
    "accounting_currency_dop": company.currency_id == dop,
    "commercial_currency_usd": policy.commercial_currency_id == usd,
    "default_customer_usd": policy.default_customer_currency_id == usd,
    "default_supplier_usd": policy.default_supplier_currency_id == usd,
    "public_usd_pricelist": bool(public_pl) and public_pl.currency_id == usd,
    "default_pricelist_usd": policy.default_pricelist_id.currency_id == usd,
    "default_product_pricelist_usd": policy.default_product_pricelist_id.currency_id == usd,
    "usd_rate_set": bool(rate_rec.inverse_company_rate),
}

for key, ok in checks.items():
    if not ok:
        report["ok"] = False
        report["errors"].append(key)

report["policy"] = {
    "company_id": company.id,
    "accounting_currency": company.currency_id.name,
    "commercial_currency": policy.commercial_currency_id.name,
    "default_customer_currency": policy.default_customer_currency_id.name,
    "default_supplier_currency": policy.default_supplier_currency_id.name,
    "default_pricelist": policy.default_pricelist_id.display_name,
    "default_product_pricelist": policy.default_product_pricelist_id.display_name,
    "public_usd_pricelist_id": public_pl.id,
    "public_usd_pricelist_name": public_pl.display_name,
    "usd_rate_inverse": rate_rec.inverse_company_rate,
    "checks": {k: bool(v) for k, v in checks.items()},
}

out = os.environ.get("MC_PROD_CONFIG_JSON", "/var/lib/odoo/mc-prod-config.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps(report, indent=2, ensure_ascii=False))
print(f"\n--- MC_PROD_CONFIG_JSON={out} ---")
print(f"CONFIG_OK={'true' if report['ok'] else 'false'}")
env.cr.commit()
if not report["ok"]:
    raise SystemExit(1)
