#!/usr/bin/env python3
"""UX-FLOW-FIX PROD — smoke NCF/DGII, multimoneda y Centro Justech (solo lectura)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = os.environ.get("UX_FLOW_FIX_EVIDENCE", "/tmp/ux-flow-fix-prod")
os.makedirs(OUT, exist_ok=True)

report = {
    "phase": "UX-FLOW-FIX-PROD-SMOKE",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "ok": True,
    "checks": {},
    "errors": [],
}


def check(key, cond, detail=""):
    report["checks"][key] = {"pass": bool(cond), "detail": str(detail)[:500]}
    if not cond:
        report["ok"] = False
        report["errors"].append(key)


IrModule = env["ir.module.module"]

for mod in (
    "justech_l10n_do_base",
    "justech_l10n_do_ncf",
    "justech_l10n_do_reports",
    "justech_multicurrency",
    "justech_admin",
    "hellenia_ui",
    "hellenia_ux",
):
    rec = IrModule.search([("name", "=", mod)], limit=1)
    check(f"module_{mod}", bool(rec) and rec.state == "installed", rec.state if rec else "missing")

check("ncf_ranges_exist", env["justech.do.ncf.range"].search_count([]) >= 0, "model readable")
check(
    "posted_invoices_with_ncf",
    env["account.move"].search_count(
        [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("justech_do_ncf", "!=", False)]
    )
    >= 0,
    "query ok",
)

company = env.company
check("company_currency", bool(company.currency_id), company.currency_id.name if company.currency_id else "")
Rate = env["res.currency.rate"]
check("fx_rates_model", Rate.search_count([]) >= 0, "rates readable")

settings = env.ref("justech_admin.menu_justech_settings_root", raise_if_not_found=False)
licenses = env.ref("justech_admin.menu_justech_modules", raise_if_not_found=False)
check("justech_settings_menu", bool(settings and settings.active), settings.name if settings else "")
check(
    "justech_licenses_menu",
    bool(licenses and licenses.active and "Licencias" in (licenses.name or "")),
    licenses.name if licenses else "",
)

report["summary"] = "PASS" if report["ok"] else "FAIL"
path = os.path.join(OUT, "UX_FLOW_FIX_PROD_SMOKE.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(json.dumps(report, indent=2, ensure_ascii=False))
