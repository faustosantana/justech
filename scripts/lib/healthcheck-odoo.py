#!/usr/bin/env python3
"""Healthcheck Odoo interno — módulos, NCF, DGII, PDF (sin modificar datos)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

report = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "checks": {},
    "ok": True,
    "errors": [],
}


def fail(key: str, msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)
    report["checks"][key] = {"ok": False, "detail": msg}


def pass_check(key: str, detail: str = "ok") -> None:
    report["checks"][key] = {"ok": True, "detail": detail}


# --- Módulos Justech / Hellenia ---
required_modules = [
    "justech_l10n_do_base",
    "justech_l10n_do_ncf",
    "justech_l10n_do_reports",
    "hellenia_base",
    "hellenia_reports",
]
Module = env["ir.module.module"]
for mod_name in required_modules:
    mod = Module.search([("name", "=", mod_name)], limit=1)
    if not mod or mod.state != "installed":
        fail(f"module_{mod_name}", f"{mod_name} no instalado (state={mod.state if mod else 'missing'})")
    else:
        pass_check(f"module_{mod_name}")

# --- NCF ---
ncf_seq = env["justech.do.ncf.range"].search(
    [("company_id", "=", env.company.id), ("state", "=", "active")], limit=1
)
if ncf_seq:
    pass_check("ncf_sequence", ncf_seq.name or "active range")
else:
    fail("ncf_sequence", "Sin rango NCF activo (justech.do.ncf.range)")

# --- Reportes DGII (acciones existen) ---
dgii_actions = [
    ("report_606", "justech_l10n_do_ncf.action_606_report"),
    ("report_607", "justech_l10n_do_ncf.action_607_report"),
    ("report_608", "justech_l10n_do_ncf.action_608_report"),
]
for key, xmlid in dgii_actions:
    try:
        env.ref(xmlid)
        pass_check(key)
    except Exception as exc:
        fail(key, f"{xmlid}: {exc}")

# --- PDF corporativo (layout QWeb) ---
try:
    layout = env.ref("hellenia_reports.external_layout_hellenia", raise_if_not_found=False)
    if layout:
        pass_check("pdf_layout", layout.name)
    else:
        fail("pdf_layout", "hellenia_reports.external_layout_hellenia no encontrado")
except Exception as exc:
    fail("pdf_layout", str(exc))

# --- Assets (bundle report) ---
try:
    bundle = env["ir.qweb"]._get_asset_bundle("web.report_assets_common", assets_params={})
    if bundle:
        pass_check("assets_report", "bundle loadable")
    else:
        fail("assets_report", "bundle vacío")
except Exception as exc:
    fail("assets_report", str(exc))

# --- Contabilidad básica ---
try:
    env["account.account"].search_count([("company_id", "=", env.company.id)])
    pass_check("accounting", "chart accessible")
except Exception as exc:
    fail("accounting", str(exc))

out = os.environ.get("HEALTHCHECK_JSON_OUT", "")
if out:
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
else:
    print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    raise SystemExit(1)
