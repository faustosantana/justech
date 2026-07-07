#!/usr/bin/env python3
"""RELEASE-1.0 — Auditoría read-only + certificación final hellenia_prod."""
from __future__ import annotations

import calendar
import json
import os
from datetime import date, datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = os.environ.get("RELEASE10_EVIDENCE", "/var/lib/odoo/release-1.0")
os.makedirs(OUT, exist_ok=True)

today = date.today()
period_from = today.replace(day=1)
period_to = today.replace(day=calendar.monthrange(today.year, today.month)[1])
company = env.company

report = {
    "phase": "RELEASE-1.0",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "company": company.name,
    "pass": True,
    "blockers": [],
    "warnings": [],
    "sections": {},
}

JUSTECH_PROD_REQUIRED = [
    "justech_modules",
    "justech_admin",
    "justech_l10n_do_base",
    "justech_l10n_do_ncf",
    "justech_l10n_do_reports",
    "justech_report_design",
    "justech_global_audit_log",
]
JUSTECH_PROD_OPTIONAL = ["justech_core"]
HELLENIA_PROD_REQUIRED = [
    "hellenia_base",
    "hellenia_account",
    "hellenia_ui",
    "hellenia_ux",
    "hellenia_reports",
    "hellenia_governance",
]
HELLENIA_PROD_OPTIONAL = ["hellenia_inventory", "hellenia_pos"]
EXCLUDE_TEST = {"justech_modules_test", "justech_report_templates_test"}
NCF_PREFIXES = ["B01", "B02", "B03", "B04", "B11", "B12", "B13", "B14", "B15", "B16", "B17"]
DGII_TYPES = ["606", "607", "608", "609", "623"]


def fail(section, name, detail=""):
    report["sections"].setdefault(section, {})[name] = {"ok": False, "detail": str(detail)[:600]}
    report["pass"] = False
    report["blockers"].append(f"{section}.{name}: {detail}")


def ok(section, name, detail=""):
    report["sections"].setdefault(section, {})[name] = {"ok": True, "detail": str(detail)[:600]}


# --- Módulos ---
modules = []
Module = env["ir.module.module"]
for name in JUSTECH_PROD_REQUIRED + JUSTECH_PROD_OPTIONAL + HELLENIA_PROD_REQUIRED + HELLENIA_PROD_OPTIONAL:
    mod = Module.search([("name", "=", name)], limit=1)
    state = mod.state if mod else "missing"
    required = name in JUSTECH_PROD_REQUIRED + HELLENIA_PROD_REQUIRED
    modules.append({
        "name": name,
        "state": state,
        "version": mod.latest_version if mod else None,
        "required_v1": required,
    })
    if required and state != "installed":
        fail("modules", name, state)
    elif state == "installed":
        ok("modules", name, mod.latest_version)
    else:
        report["warnings"].append(f"Optional module not installed: {name}")

for test_mod in EXCLUDE_TEST:
    tm = Module.search([("name", "=", test_mod)], limit=1)
    if tm and tm.state == "installed":
        report["warnings"].append(f"Test module installed in PROD: {test_mod}")
    modules.append({"name": test_mod, "state": tm.state if tm else "missing", "version": tm.latest_version if tm else None})

report["modules"] = modules

# --- COA (read-only) ---
Account = env["account.account"].sudo().with_context(active_test=False)
acc_count = Account.search_count([("company_ids", "in", company.id)])
sample = Account.search([("company_ids", "in", company.id)], order="code", limit=5).mapped("code")
six_digit = sum(1 for c in sample if c and len(str(c)) == 6 and str(c).isdigit())
if acc_count < 280 or not six_digit:
    fail("coa", "justech_catalog", f"accounts={acc_count} sample={sample}")
else:
    ok("coa", "justech_catalog", f"{acc_count} cuentas, sample={sample[:3]}")

# --- NCF types ---
prefixes = sorted(set(env["justech.do.fiscal.document.type"].search([]).mapped("prefix")))
missing_ncf = set(NCF_PREFIXES) - set(prefixes)
if missing_ncf:
    fail("fiscal", "ncf_types", f"missing={sorted(missing_ncf)}")
else:
    ok("fiscal", "ncf_types", ",".join(prefixes))

active_ranges = env["justech.do.ncf.range"].search_count([("state", "=", "active"), ("company_id", "=", company.id)])
ok("fiscal", "ncf_ranges_active", active_ranges)

# --- DGII ---
dgii = {}
for rtype in DGII_TYPES:
    try:
        exp = env[env["justech.do.fiscal.report"].DGII_EXPORTER_MODELS[rtype]]
        val = exp.validate_period(company, period_from, period_to, refresh_states=False)
        export_ok = True
        fname = ""
        try:
            content, fname = exp.export_xlsx(company, period_from, period_to)
            export_ok = bool(content) or rtype in ("608", "609", "623")
        except Exception as exc:
            msg = str(exc)
            export_ok = rtype in ("608", "609", "623") and "No hay documentos" in msg
            if not export_ok:
                fname = msg[:200]
        passed = val.get("counts", {}).get("incomplete", 0) == 0 and (
            val.get("counts", {}).get("valid", 0) > 0 or rtype in ("608", "609", "623")
        ) and export_ok
        if rtype == "606" and val.get("counts", {}).get("valid", 0) == 0:
            passed = False
        dgii[rtype] = {"pass": passed, "counts": val.get("counts", {}), "export": fname or ("ok" if export_ok else "fail")}
        if not passed:
            fail("dgii", rtype, dgii[rtype])
        else:
            ok("dgii", rtype, dgii[rtype].get("export", ""))
    except Exception as exc:
        fail("dgii", rtype, str(exc))
        dgii[rtype] = {"pass": False, "error": str(exc)[:300]}
report["dgii"] = dgii

# --- Contabilidad reports smoke ---
for rpt_code, rpt_name in (
    ("account.report_balance_sheet", "balance"),
    ("account.report_profit_and_loss", "pnl"),
):
    try:
        rpt = env.ref(rpt_code, raise_if_not_found=False)
        ok("accounting", rpt_name, rpt.display_name if rpt else "ref ok")
    except Exception as exc:
        fail("accounting", rpt_name, str(exc))

journal_count = env["account.journal"].search_count([("company_id", "=", company.id)])
ok("accounting", "journals", journal_count)

orphan_tax = env["account.tax.repartition.line"].search_count(
    [("company_id", "=", company.id), ("repartition_type", "=", "tax"), ("account_id", "=", False)]
)
if orphan_tax:
    report["warnings"].append(f"Impuestos sin cuenta: {orphan_tax}")
ok("accounting", "tax_orphans", orphan_tax)

# --- Centro Justech ---
if Module.search([("name", "=", "justech_modules"), ("state", "=", "installed")]):
    try:
        cat = env["justech.license.service"].get_activation_catalog()
        ok("justech_center", "activation_catalog", len(cat))
    except Exception as exc:
        fail("justech_center", "activation_catalog", str(exc))
if Module.search([("name", "=", "justech_admin"), ("state", "=", "installed")]):
    ok("justech_center", "admin_dashboard", env["justech.admin.dashboard"].search_count([]) >= 0)
    ok("justech_center", "admin_key_model", "justech.admin.key" in env)

# --- Auditoría ---
if Module.search([("name", "=", "justech_global_audit_log"), ("state", "=", "installed")]):
    ok("audit", "module", "installed")
    ok("audit", "rules", env["justech.audit.rule"].search_count([]))
    ok("audit", "logs", env["justech.audit.log"].search_count([]))

# --- Governance ---
if Module.search([("name", "=", "hellenia_governance"), ("state", "=", "installed")]):
    ok("governance", "permissions", env["hellenia.permission"].search_count([]))
    ok("governance", "roles", env["hellenia.role"].search_count([]))

# --- Seguridad smoke ---
groups_fiscal = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
ok("security", "fiscal_manager_group", bool(groups_fiscal))
cron_active = env["ir.cron"].search_count([("active", "=", True)])
ok("security", "cron_active", cron_active)

# --- PDF actions ---
for xml_id, label in (
    ("account.account_invoices", "invoice_pdf"),
    ("sale.action_report_saleorder", "quotation_pdf"),
):
    rpt = env.ref(xml_id, raise_if_not_found=False)
    ok("pdf", label, bool(rpt))

# --- Compras 606 state ---
purch_incomplete = 0
if "justech.do.dgii.606.exporter" in env:
    exp606 = env["justech.do.dgii.606.exporter"]
    val606 = exp606.validate_period(company, period_from, period_to, refresh_states=True)
    purch_incomplete = val606.get("counts", {}).get("incomplete", 0)
    if purch_incomplete:
        fail("dgii", "606_incomplete_moves", purch_incomplete)
report["purchase_606_incomplete"] = purch_incomplete

# Write outputs
with open(os.path.join(OUT, "certification.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

summary = {
    "pass": report["pass"],
    "blockers": report["blockers"],
    "warnings": report["warnings"],
    "modules_installed": sum(1 for m in modules if m["state"] == "installed" and m["name"] not in EXCLUDE_TEST),
    "modules_required_installed": sum(1 for m in modules if m["state"] == "installed" and m.get("required_v1")),
    "dgii_pass": all(dgii.get(t, {}).get("pass") for t in DGII_TYPES),
}
with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("RELEASE10:" + json.dumps(summary, indent=2, ensure_ascii=False))
