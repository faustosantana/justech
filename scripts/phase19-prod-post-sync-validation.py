# -*- coding: utf-8 -*-
"""Fase 19 — Validación post-sincronización PRODUCCIÓN."""
from __future__ import annotations

import json
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

report = {
    "phase": "19-prod-post-sync-validation",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "tests": {},
    "ok": True,
    "pass": False,
}

MODULES = [
    "hellenia_account", "hellenia_ui", "hellenia_reports",
    "justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports",
]
MENUS = [
    "justech_l10n_do_reports.menu_justech_do_report_606",
    "justech_l10n_do_reports.menu_justech_do_report_607",
    "justech_l10n_do_reports.menu_justech_do_report_608",
    "justech_l10n_do_reports.menu_justech_do_report_623",
]


def check(key, ok, detail=""):
    report["tests"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]}
    if not ok:
        report["ok"] = False


# Módulos
for mod_name in MODULES:
    mod = env["ir.module.module"].search([("name", "=", mod_name)], limit=1)
    check(f"module_{mod_name}", mod and mod.state == "installed", mod.latest_version if mod else "missing")

# Campos críticos pagos
Payment = env["account.payment"]
for fname in ("hellenia_applied_amount", "hellenia_withholding_total", "hellenia_net_transfer"):
    check(f"field_payment_{fname}", fname in Payment._fields, fname)

# Menús DGII
for xid in MENUS:
    menu = env.ref(xid, raise_if_not_found=False)
    check(f"menu_{xid.split('.')[-1]}", bool(menu and menu.active), xid)

# Acciones DGII
for rtype in ("606", "607", "608", "623"):
    act = env.ref(f"justech_l10n_do_reports.action_justech_do_report_{rtype}", raise_if_not_found=False)
    check(f"action_{rtype}", bool(act), rtype)

# Modelos persistentes
check("model_wh_line", bool(env["ir.model"].search([("model", "=", "hellenia.payment.withholding.line")])), "wh")
check("model_app_line", bool(env["ir.model"].search([("model", "=", "hellenia.payment.application.line")])), "app")

# Diarios banco
bnkd = env["account.journal"].search([("code", "=", "BNKD")], limit=1)
check("journal_BNKD", bool(bnkd), bnkd.name if bnkd else "")

# Vistas sin error OWL
try:
    Payment.get_views([(False, "form")])
    env["account.move"].get_views([(False, "form")])
    check("views_owl", True, "ok")
except Exception as exc:
    check("views_owl", False, exc)

# Catálogo retenciones
cat = env["hellenia.withholding.catalog"].search([("code", "=", "RET-GOB-5")], limit=1)
check("catalog_gov_5", bool(cat) and bool(cat.account_id), cat.code if cat else "")

# Exportador 623
check("exporter_623", "justech.do.dgii.623.exporter" in env, "623")

report["summary"] = {
    "passed": sum(1 for t in report["tests"].values() if t["status"] == "PASS"),
    "failed": sum(1 for t in report["tests"].values() if t["status"] == "FAIL"),
    "total": len(report["tests"]),
}
report["pass"] = report["ok"]
print(f"PHASE19PROD:{json.dumps(report, ensure_ascii=False, default=str)}")
