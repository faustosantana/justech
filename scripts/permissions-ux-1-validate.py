#!/usr/bin/env python3
"""PERMISSIONS-UX-1 — Validar Centro de Permisos."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB not in ("hellenia_test", "hellenia_prod"):
    raise SystemExit(f"ABORT: hellenia_test|hellenia_prod, actual={DB}")

OUT = os.environ.get(
    "PERMISSIONS_UX_EVIDENCE",
    "/var/lib/odoo/permissions-ux-validation.json",
)
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)

report = {
    "phase": "PERMISSIONS-UX-1",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "checks": {},
    "metrics": {},
    "errors": [],
}

Users = env["res.users"]
Svc = env["justech.admin.access.service"]
Wizard = env["hellenia.permissions.internal.wizard"]
admin = env.ref("base.user_admin")
PLAIN = "PERMISSIONS-UX-KEY-4242"


def check(name, ok, detail=""):
    report["checks"][name] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:800]}
    if not ok:
        report["errors"].append(f"{name}: {detail}")


registry = Users._permissions_ux_registry()
categories = Users._permissions_ux_categories()
report["metrics"]["permissions_reorganized"] = len(registry)
report["metrics"]["categories"] = len(categories)
report["metrics"]["tooltips"] = len(registry)

check("01_ten_permissions_registry", len(registry) == 10, len(registry))
check("02_five_categories", len(categories) == 5, [c["label"] for c in categories])

view = env.ref("hellenia_governance.view_users_form_permissions_ux", raise_if_not_found=False)
arch = view.arch_db if view else ""
check("03_view_loaded", bool(view), view.id if view else "")
check("04_view_has_finanzas", "FINANZAS" in (arch or ""), "FINANZAS" in arch)
check("05_view_has_internal_section", "USO INTERNO JUSTECH" in (arch or ""), True)
check("06_view_has_tooltips", arch.count("help=") >= 8, arch.count("help="))
check("07_view_has_internal_badges", "Exclusivo Justech" in arch and "Solo soporte autorizado" in arch, True)

import uuid

login = f"permissions_ux_validate_{uuid.uuid4().hex[:8]}@hellenia.cloud"
test_user = Users.create(
    {
        "name": "Permissions UX Validate",
        "login": login,
        "group_ids": [(4, env.ref("base.group_user").id)],
    }
)

purchase_user = env.ref("purchase.group_purchase_user", raise_if_not_found=False)
if purchase_user:
    test_user._apply_permissions_ux_level("purchase", "user")
    test_user.invalidate_recordset()
    env.flush_all()
    check("08_normal_permission_activate", purchase_user in test_user.group_ids, list(test_user.group_ids.ids))
    test_user._apply_permissions_ux_level("purchase", "none")
    test_user.invalidate_recordset()
    env.flush_all()
    check("09_normal_permission_deactivate", purchase_user not in test_user.group_ids, True)

justech_admin = env.ref("justech_admin.group_justech_admin_user", raise_if_not_found=False)
justech_platform = env.ref("justech_modules.group_justech_license_user", raise_if_not_found=False)
blocked = False
try:
    test_user.write({"group_ids": [(4, justech_admin.id)]})
except Exception as exc:
    blocked = "Justech Admin" in str(exc) or "Clave Administrativa" in str(exc)
check("10_block_direct_justech_admin", blocked, blocked)

action = test_user.with_context(
    permission_code="justech_admin", target_level="on"
).action_permissions_ux_activate_internal()
check(
    "11_wizard_without_session",
    action.get("res_model") == "hellenia.permissions.internal.wizard",
    action.get("res_model"),
)

access = env["justech.admin.access"].sudo().ensure_access_shell(admin, company=env.company)
access.set_key_hash(PLAIN)
Session = env["justech.admin.session"].sudo()
Session.search([("user_id", "=", admin.id), ("active", "=", True)]).write({"active": False})
env["ir.config_parameter"].sudo().set_param(Svc._session_storage_key(Svc.SCOPE_ADMIN, admin.id), False)

svc = Svc.with_user(admin)
svc.open_session(PLAIN, scope=Svc.SCOPE_ADMIN)
check("12_admin_session_valid", svc.is_session_valid(scope=Svc.SCOPE_ADMIN), True)

test_user.with_user(admin).with_context(
    permission_code="justech_platform", target_level="user"
).action_permissions_ux_activate_internal()
check(
    "13_platform_with_session",
    justech_platform and justech_platform in test_user.group_ids,
    test_user.perm_ux_justech_platform,
)

Session.search([("user_id", "=", admin.id), ("scope", "=", Svc.SCOPE_ADMIN), ("active", "=", True)]).write(
    {"expires_at": datetime.now() - __import__("datetime").timedelta(minutes=1)}
)
check("14_session_expired", not svc.is_session_valid(scope=Svc.SCOPE_ADMIN), True)
action2 = test_user.with_context(
    permission_code="justech_admin", target_level="on"
).with_user(admin).action_permissions_ux_activate_internal()
check(
    "15_wizard_after_expiry",
    action2.get("res_model") == "hellenia.permissions.internal.wizard",
    action2.get("res_model"),
)

report["status"] = "PASS" if not report["errors"] else "FAIL"
with open(OUT, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2, ensure_ascii=False, default=str)

print("PERMISSIONS_UX:" + json.dumps({"status": report["status"], "errors": report["errors"], "metrics": report["metrics"]}))
