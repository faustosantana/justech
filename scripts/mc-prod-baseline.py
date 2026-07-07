#!/usr/bin/env python3
"""MC-PROD — Baseline pre-despliegue (hellenia_prod)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

company = env.company
usd = env.ref("base.USD")
dop = env.ref("base.DOP")

baseline = {
    "phase": "MC-PROD-baseline",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "environment": "production",
    "url": "https://odoo.hellenia.cloud",
    "company": {
        "id": company.id,
        "name": company.name,
        "currency": company.currency_id.name,
    },
    "modules": {},
    "counts": {
        "posted_moves": env["account.move"].search_count([("state", "=", "posted")]),
        "accounts": env["account.account"].search_count([]),
        "products": env["product.template"].search_count([]),
    },
    "usd_active": usd.active,
    "dop_active": dop.active,
    "usd_rate_inverse": None,
    "multicurrency_installed": False,
}

for name in (
    "justech_multicurrency",
    "justech_modules",
    "justech_l10n_do_ncf",
    "justech_l10n_do_reports",
    "justech_l10n_do_base",
):
    mod = env["ir.module.module"].search([("name", "=", name)], limit=1)
    baseline["modules"][name] = mod.state if mod else "missing"

Rate = env["res.currency.rate"].sudo()
rate = Rate.search(
    [
        ("currency_id", "=", usd.id),
        ("company_id", "in", [company.id, False]),
    ],
    order="name desc, id desc",
    limit=1,
)
if rate:
    baseline["usd_rate_inverse"] = rate.inverse_company_rate

if baseline["modules"].get("justech_multicurrency") == "installed":
    baseline["multicurrency_installed"] = True

out = os.environ.get("MC_PROD_BASELINE_JSON", "/var/lib/odoo/mc-prod-baseline.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(baseline, f, indent=2, ensure_ascii=False)

print(json.dumps(baseline, indent=2, ensure_ascii=False))
print(f"\n--- MC_PROD_BASELINE_JSON={out} ---")
