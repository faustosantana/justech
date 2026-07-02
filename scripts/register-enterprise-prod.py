#!/usr/bin/env python3
"""Registrar suscripción Enterprise Odoo en hellenia_prod (odoo shell).

Requiere SUBSCRIPTION_CODE (ej. M260616306091776).
Flujo oficial: set_param database.enterprise_code + publisher_warranty.contract.update_notification
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

code = os.environ.get("SUBSCRIPTION_CODE", "").strip()
report = {
    "phase": "enterprise-registration",
    "database": env.cr.dbname,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "ok": False,
    "subscription_code_set": False,
    "enterprise_code": None,
    "expiration_date": None,
    "expiration_reason": None,
    "already_linked": False,
    "errors": [],
}

if not code:
    report["errors"].append("SUBSCRIPTION_CODE not set")
    print("REGISTER_ENTERPRISE:" + json.dumps(report, ensure_ascii=False))
    raise SystemExit(2)

ICP = env["ir.config_parameter"].sudo()
old_exp = ICP.get_param("database.expiration_date")
ICP.set_param("database.enterprise_code", code)
report["subscription_code_set"] = True
env.cr.commit()

try:
    env["publisher_warranty.contract"].sudo().update_notification(cron_mode=False)
except Exception as exc:  # noqa: BLE001
    report["errors"].append(f"update_notification: {exc}")

linked_url = ICP.get_param("database.already_linked_subscription_url")
new_exp = ICP.get_param("database.expiration_date")
ee_code = ICP.get_param("database.enterprise_code")

report["enterprise_code"] = ee_code
report["expiration_date"] = new_exp
report["expiration_reason"] = ICP.get_param("database.expiration_reason")
report["already_linked"] = bool(linked_url)

if linked_url:
    report["errors"].append(
        f"subscription already linked: {ICP.get_param('database.already_linked_email') or 'unknown'}"
    )
elif new_exp and new_exp != old_exp:
    report["ok"] = True
elif ee_code and ee_code != code:
    # Odoo puede reemplazar subscription code por enterprise_code interno
    report["ok"] = True
else:
    report["errors"].append("registration did not update expiration_date — verify manually in UI")

env.cr.commit()
print("REGISTER_ENTERPRISE:" + json.dumps(report, ensure_ascii=False, default=str))
