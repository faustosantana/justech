# -*- coding: utf-8 -*-
"""Comparación paridad TEST vs PROD antes de promoción."""
from __future__ import annotations

import json
from datetime import datetime, timezone

report = {
    "phase": "test-prod-parity-before-promotion",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "test_db": "hellenia_test",
    "prod_db": "hellenia_prod",
    "differences": [],
    "ok": True,
    "pass": False,
}

KEY_MODULES = [
    "hellenia_account", "hellenia_base", "hellenia_ui", "hellenia_ux",
    "justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports",
    "account_accountant", "account_reports",
]

ACCOUNTING_MENUS = [
    "account.menu_action_move_journal_line_form",
    "account.menu_action_account_moves_all",
    "account.menu_finance_entries",
    "account.menu_finance_entries_accounting_miscellaneous",
]

IT_GROUP_XMLID = "base.group_user"  # fallback; search by name below


def _db_report(dbname):
    cr = env.registry.cursor(dbname)
    try:
        denv = env(cr=cr)
        mods = denv["ir.module.module"].search([("name", "in", KEY_MODULES)])
        mod_data = {m.name: {"state": m.state, "version": m.latest_version} for m in mods}
        menus = {}
        for xmlid in ACCOUNTING_MENUS:
            rec = denv.ref(xmlid, raise_if_not_found=False)
            menus[xmlid] = bool(rec and rec.active)
        it_group = denv["res.groups"].search([("name", "ilike", "it@justech")], limit=1)
        group_modules = {}
        if it_group:
            group_modules = {
                m.name: m.state
                for m in denv["ir.module.module"].search([("state", "=", "installed")])
                if m.name in KEY_MODULES
            }
        return {
            "modules": mod_data,
            "accounting_menus": menus,
            "it_group": it_group.name if it_group else None,
            "it_group_id": it_group.id if it_group else None,
        }
    finally:
        cr.close()


current_db = env.cr.dbname
if current_db != "hellenia_test":
    raise SystemExit(f"ABORT: ejecutar desde hellenia_test, actual={current_db}")

test_data = _db_report("hellenia_test")
try:
    prod_data = _db_report("hellenia_prod")
except Exception as exc:
    prod_data = {"error": str(exc)}
    report["differences"].append(f"PROD no accesible: {exc}")
    report["ok"] = False

report["test"] = test_data
report["prod"] = prod_data

if "error" not in prod_data:
    for mod in KEY_MODULES:
        t = test_data["modules"].get(mod, {})
        p = prod_data["modules"].get(mod, {})
        if t.get("state") != p.get("state") or t.get("version") != p.get("version"):
            report["differences"].append({
                "type": "module",
                "module": mod,
                "test": t,
                "prod": p,
            })
    for xmlid, t_active in test_data["accounting_menus"].items():
        p_active = prod_data["accounting_menus"].get(xmlid)
        if t_active != p_active:
            report["differences"].append({
                "type": "menu",
                "xmlid": xmlid,
                "test_active": t_active,
                "prod_active": p_active,
            })
    critical_menus = [
        "account.menu_action_move_journal_line_form",
        "account.menu_action_account_moves_all",
    ]
    for xmlid in critical_menus:
        if not prod_data["accounting_menus"].get(xmlid):
            report["differences"].append({
                "type": "critical_menu_missing_prod",
                "xmlid": xmlid,
                "message": "PROD no tiene menú contable requerido — promoción bloqueada",
            })
            report["ok"] = False

report["pass"] = report["ok"] and not report["differences"]
report["promotion_blocked"] = bool(report["differences"])
print(f"PARITY:{json.dumps(report, ensure_ascii=False, default=str)}")
