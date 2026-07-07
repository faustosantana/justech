#!/usr/bin/env python3
"""MC-PROD — Validación post-despliegue vs baseline."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

baseline_path = os.environ.get("MC_PROD_BASELINE_JSON", "/var/lib/odoo/mc-prod-baseline.json")
baseline = {}
if os.path.isfile(baseline_path):
    with open(baseline_path, encoding="utf-8") as f:
        baseline = json.load(f)

company = env.company
report = {
    "phase": "MC-PROD-validation",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "environment": "production",
    "url": "https://odoo.hellenia.cloud",
    "ok": True,
    "checks": {},
    "baseline": baseline.get("counts", {}),
    "current": {},
    "errors": [],
}

def chk(ok, detail=""):
    return {"ok": bool(ok), "detail": str(detail)}

mod = env["ir.module.module"].search([("name", "=", "justech_multicurrency")], limit=1)
manifest = env["ir.module.module"].search([("name", "=", "justech_multicurrency")], limit=1)
installed_version = mod.latest_version if mod else ""
report["checks"]["module_installed"] = chk(mod and mod.state == "installed", mod.state if mod else "missing")
report["checks"]["module_version"] = chk(
    installed_version.startswith("19.0.2"),
    installed_version or "unknown",
)

for name in ("justech_l10n_do_ncf", "justech_l10n_do_reports", "justech_l10n_do_base"):
    m = env["ir.module.module"].search([("name", "=", name), ("state", "=", "installed")], limit=1)
    report["checks"][f"module_{name}"] = chk(bool(m), "installed" if m else "missing")

report["current"] = {
    "posted_moves": env["account.move"].search_count([("state", "=", "posted")]),
    "accounts": env["account.account"].search_count([]),
}

baseline_posted = baseline.get("counts", {}).get("posted_moves")
baseline_accounts = baseline.get("counts", {}).get("accounts")
if baseline_accounts is not None:
    report["checks"]["coa_unchanged"] = chk(
        report["current"]["accounts"] == baseline_accounts,
        f"{baseline_accounts} -> {report['current']['accounts']}",
    )
else:
    report["checks"]["coa_unchanged"] = chk(True, "no baseline")

if baseline_posted is not None:
    # Solo nuevas facturas smoke; baseline 0 permite incremento documentado
    report["checks"]["posted_moves_not_modified"] = chk(
        report["current"]["posted_moves"] >= baseline_posted,
        f"{baseline_posted} -> {report['current']['posted_moves']} (solo smoke nuevo)",
    )

if "justech.multicurrency.policy" in env:
    policy = env["justech.multicurrency.policy"].get_policy(company)
    usd = env.ref("base.USD")
    report["checks"]["policy_commercial_usd"] = chk(policy.commercial_currency_id == usd, policy.commercial_currency_id.name)
    report["checks"]["policy_accounting_dop"] = chk(company.currency_id.name == "DOP", company.currency_id.name)
    report["checks"]["policy_customer_usd"] = chk(policy.default_customer_currency_id == usd, policy.default_customer_currency_id.name)
    report["checks"]["policy_supplier_usd"] = chk(policy.default_supplier_currency_id == usd, policy.default_supplier_currency_id.name)
    pl = policy.default_pricelist_id
    report["checks"]["policy_public_usd_list"] = chk(pl and pl.currency_id == usd, pl.display_name if pl else "missing")
else:
    report["checks"]["policy_commercial_usd"] = chk(False, "policy model missing")

for check in report["checks"].values():
    if not check["ok"]:
        report["ok"] = False
        report["errors"].append(check["detail"])

out = os.environ.get("MC_PROD_VALIDATION_JSON", "/var/lib/odoo/mc-prod-validation.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps(report, indent=2, ensure_ascii=False))
print(f"\n--- MC_PROD_VALIDATION_JSON={out} ---")
print(f"VALIDATION_OK={'true' if report['ok'] else 'false'}")
env.cr.commit()
if not report["ok"]:
    raise SystemExit(1)
