# -*- coding: utf-8 -*-
"""Fase 19 — Auditoría paridad TEST vs PRODUCCIÓN."""
from __future__ import annotations

import json
from datetime import datetime, timezone

TARGET_MODULES = [
    "hellenia_account",
    "hellenia_ui",
    "hellenia_reports",
    "justech_l10n_do_base",
    "justech_l10n_do_ncf",
    "justech_l10n_do_reports",
]

DGII_MENUS = {
    "606": "justech_l10n_do_reports.menu_justech_do_report_606",
    "607": "justech_l10n_do_reports.menu_justech_do_report_607",
    "608": "justech_l10n_do_reports.menu_justech_do_report_608",
    "623": "justech_l10n_do_reports.menu_justech_do_report_623",
}

KEY_FIELDS = [
    ("account.payment", "hellenia_applied_amount"),
    ("account.payment", "hellenia_withholding_total"),
    ("account.payment", "hellenia_withholding_line_ids"),
    ("hellenia.payment.withholding.line", "move_line_id"),
    ("hellenia.payment.application.line", "applied_amount"),
]

report = {
    "phase": "19-test-prod-parity-audit",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "certified_commit_recommended": "bbaf113",
    "certified_branch": "cursor/phase18-13-native-payment-rebuild-dd85",
    "certified_evidence": "evidence/phase18-13-final-payment-retention-test.json",
    "test_db": "hellenia_test",
    "prod_db": "hellenia_prod",
    "differences": [],
    "module_diff": [],
    "menu_diff": [],
    "field_diff": [],
    "ok": True,
    "pass": False,
    "promotion_ready": False,
}


def _snapshot(dbname):
    cr = env.registry.cursor(dbname)
    try:
        denv = env(cr=cr)
        mods = denv["ir.module.module"].search([("name", "in", TARGET_MODULES)])
        mod_data = {m.name: {"state": m.state, "version": m.latest_version} for m in mods}
        menus = {}
        for code, xid in DGII_MENUS.items():
            m = denv.ref(xid, raise_if_not_found=False)
            menus[code] = {"exists": bool(m), "active": bool(m and m.active)}
        fields_ok = {}
        for model, fname in KEY_FIELDS:
            f = denv[model]._fields.get(fname)
            fields_ok[f"{model}.{fname}"] = bool(f)
        wh_model = denv["ir.model"].search([("model", "=", "hellenia.payment.withholding.line")], limit=1)
        app_model = denv["ir.model"].search([("model", "=", "hellenia.payment.application.line")], limit=1)
        journals = denv["account.journal"].search([("code", "in", ("BNKD", "BNKU", "CSH1"))])
        return {
            "modules": mod_data,
            "dgii_menus": menus,
            "fields": fields_ok,
            "models": {
                "hellenia.payment.withholding.line": bool(wh_model),
                "hellenia.payment.application.line": bool(app_model),
            },
            "bank_journals": {j.code: j.name for j in journals},
        }
    finally:
        cr.close()


if env.cr.dbname != "hellenia_test":
    raise SystemExit(f"ABORT: ejecutar en hellenia_test, actual={env.cr.dbname}")

test_snap = _snapshot("hellenia_test")
prod_snap = _snapshot("hellenia_prod")

report["test"] = test_snap
report["prod"] = prod_snap

for mod in TARGET_MODULES:
    t = test_snap["modules"].get(mod, {})
    p = prod_snap["modules"].get(mod, {})
    if t != p:
        entry = {"module": mod, "test": t, "prod": p}
        report["module_diff"].append(entry)
        report["differences"].append({"type": "module", **entry})
        if mod == "hellenia_account" and p.get("state") != "installed":
            report["ok"] = False

for code in DGII_MENUS:
    t = test_snap["dgii_menus"].get(code, {})
    p = prod_snap["dgii_menus"].get(code, {})
    if t != p:
        entry = {"menu": code, "test": t, "prod": p}
        report["menu_diff"].append(entry)
        report["differences"].append({"type": "menu", **entry})
        if not p.get("exists"):
            report["ok"] = False

for key in test_snap["fields"]:
    if test_snap["fields"].get(key) and not prod_snap["fields"].get(key):
        report["field_diff"].append({"field": key, "test": True, "prod": False})
        report["differences"].append({"type": "field", "field": key})
        if "hellenia" in key:
            report["ok"] = False

for model in test_snap["models"]:
    if test_snap["models"][model] and not prod_snap["models"].get(model):
        report["differences"].append({"type": "model", "model": model, "prod": False})
        report["ok"] = False

report["pass"] = report["ok"]
report["promotion_ready"] = bool(report["module_diff"] or report["menu_diff"] or report["field_diff"])
report["summary"] = {
    "module_diffs": len(report["module_diff"]),
    "menu_diffs": len(report["menu_diff"]),
    "field_diffs": len(report["field_diff"]),
    "total_differences": len(report["differences"]),
}
print(f"PHASE19AUDIT:{json.dumps(report, ensure_ascii=False, default=str)}")
