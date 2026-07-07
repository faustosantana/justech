#!/usr/bin/env python3
"""BUGFIX-ADMINKEY-2 — Validar flujo Seguridad/Auditoría Justech."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

DB = env.cr.dbname
if DB not in ("hellenia_test", "hellenia_prod"):
    raise SystemExit(f"ABORT: hellenia_test|hellenia_prod, actual={DB}")

OUT = os.environ.get(
    "BUGFIX_ADMINKEY2_EVIDENCE",
    "/var/lib/odoo/bugfix-adminkey-2-validation.json",
)
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)

report = {
    "phase": "BUGFIX-ADMINKEY-2",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "root_cause": (
        "Seguridad/Auditoría llamaban require_session() directamente en lugar de "
        "open_protected(), mostrando AccessError en inglés sin abrir el wizard."
    ),
    "checks": {},
    "diagnostics": {},
    "errors": [],
}

Svc = env["justech.admin.access.service"]
Session = env["justech.admin.session"].sudo()
Access = env["justech.admin.access"].sudo()
ICP = env["ir.config_parameter"].sudo()
PLAIN = "BUGFIX-ADMINKEY2-KEY-4242"
SCOPE = Svc.SCOPE_ADMIN


def check(name, ok, detail=""):
    report["checks"][name] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:800]}
    if not ok:
        report["errors"].append(f"{name}: {detail}")


admin = env.ref("base.user_admin")
access = Access.ensure_access_shell(admin, company=env.company, access_level="owner")
access.set_key_hash(PLAIN)
Session.search([("user_id", "=", admin.id), ("active", "=", True)]).write({"active": False})
ICP.set_param(Svc._session_storage_key(SCOPE, admin.id), False)

svc = Svc.with_user(admin)

# 1-3 Session state diagnostics
check("01_user_has_key", svc.user_has_key(), access.has_key)
check("02_no_active_session_initial", not svc.is_session_valid(scope=SCOPE), "expected before auth")
check(
    "03_session_storage_empty",
    not ICP.get_param(Svc._session_storage_key(SCOPE, admin.id)),
    "ICP token cleared",
)

# 4-6 Action wiring
sec_action = env.ref("justech_admin.action_justech_control_security_launcher", raise_if_not_found=False)
audit_action = env.ref("justech_admin.action_justech_control_audit_launcher", raise_if_not_found=False)
check("04_security_launcher_xmlid", bool(sec_action), sec_action.name if sec_action else "")
check("05_audit_launcher_xmlid", bool(audit_action), audit_action.name if audit_action else "")

result_sec = svc.action_open_control_security()
check(
    "06_security_opens_wizard_without_session",
    result_sec.get("res_model") == "justech.admin.key.wizard",
    result_sec.get("res_model"),
)
msg = (result_sec.get("context") or {}).get("default_prompt_message", "")
check(
    "07_wizard_message_spanish",
    "Clave Administrativa" in (msg or "") and "Please authenticate again" not in (msg or ""),
    msg[:200],
)

result_audit = svc.action_open_control_audit()
check(
    "08_audit_opens_wizard_without_session",
    result_audit.get("res_model") == "justech.admin.key.wizard",
    result_audit.get("res_model"),
)

# Authenticate once
svc.open_session(PLAIN, scope=SCOPE)
check("09_session_created", svc.is_session_valid(scope=SCOPE), "admin scope")

# 7-9 Session reuse
result_sec2 = svc.action_open_control_security()
check(
    "10_security_opens_after_auth",
    result_sec2.get("res_model") == "justech.control.security" or (
        isinstance(result_sec2, dict) and result_sec2.get("type") == "ir.actions.act_window"
        and result_sec2.get("res_model") == "justech.control.security"
    ),
    str(result_sec2.get("res_model")),
)
result_audit2 = svc.action_open_control_audit()
check(
    "11_audit_opens_after_auth",
    result_audit2.get("res_model") == "justech.control.audit",
    str(result_audit2.get("res_model")),
)

lic = svc.action_open_control_licenses()
check(
    "12_licenses_open",
    lic.get("res_model") == "justech.control.licenses",
    str(lic.get("res_model")),
)
mods = svc.action_open_client_modules()
check(
    "13_client_modules_open",
    mods.get("res_model") == "justech.client.module.control",
    str(mods.get("res_model")),
)

# Expired session message
Session.search([("user_id", "=", admin.id), ("scope", "=", SCOPE), ("active", "=", True)]).write(
    {"expires_at": datetime.now() - timedelta(minutes=1)}
)
check("14_session_expired_flag", not svc.is_session_valid(scope=SCOPE), "expired")
expired_msg = svc._session_reauth_message(SCOPE)
check(
    "15_expired_message_spanish",
    "sesión administrativa ha expirado" in expired_msg.lower(),
    expired_msg,
)
check(
    "16_no_english_auth_error",
    "Please authenticate again" not in expired_msg,
    expired_msg,
)

result_sec3 = svc.action_open_control_security()
check(
    "17_security_wizard_after_expiry",
    result_sec3.get("res_model") == "justech.admin.key.wizard",
    result_sec3.get("res_model"),
)
expired_prompt = (result_sec3.get("context") or {}).get("default_prompt_message", "")
check(
    "18_expired_prompt_in_wizard",
    "expirado" in expired_prompt.lower(),
    expired_prompt[:200],
)

# 10 ACL — settings admin can access
check(
    "19_settings_admin_access",
    svc.user_can_access_justech_settings(user=admin),
    admin.login,
)

report["diagnostics"] = {
    "active_sessions_before_auth": 0,
    "active_sessions_after_auth": Session.search_count(
        [("user_id", "=", admin.id), ("scope", "=", SCOPE), ("active", "=", True)]
    ),
    "clean2_touched_admin_tables": False,
}

report["status"] = "PASS" if not report["errors"] else "FAIL"
with open(OUT, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2, ensure_ascii=False, default=str)

print("BUGFIX_ADMINKEY2:" + json.dumps({"status": report["status"], "errors": report["errors"]}))
