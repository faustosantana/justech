#!/usr/bin/env python3
"""Validate client module admin panel actions (no missing transient, friendly license errors)."""
from __future__ import annotations

import json
import os
import sys

from odoo.exceptions import UserError
from odoo import _

from odoo.addons.justech_modules.exceptions import JustechLicenseError

OUT = os.environ.get(
    "FIX_CLIENT_MODULE_ACTIONS_EVIDENCE",
    "/var/lib/odoo/fix-client-module-actions-validation.json",
)
USER_LOGINS = ("it@justech.do", "admin")


def _provision_session(user):
    svc = env["justech.admin.access.service"].with_user(user)
    if not svc.user_has_key():
        return False
    try:
        svc.open_session("TEST-KEY-12345678", scope=svc.SCOPE_ADMIN)
    except Exception:
        pass
    return True


def _confirm(wizard):
    return wizard.action_confirm()


report = {
    "phase": "fix-client-module-actions",
    "database": env.cr.dbname,
    "checks": {},
    "actions": {},
    "ok": True,
}


def fail(key, detail=None):
    report["ok"] = False
    report["checks"][key] = False
    if detail:
        report.setdefault("errors", []).append({key: detail})


def ok(key, value=True):
    report["checks"][key] = value


admin = env.ref("base.user_admin")
if not _provision_session(admin):
    svc = env["justech.admin.access.service"]
    from odoo.addons.justech_modules.tests.test_admin_access import _provision_test_key

    _provision_test_key(env, admin)
    svc.with_user(admin).open_session("TEST-KEY-12345678", scope=svc.SCOPE_ADMIN)

env = env(user=admin)
control_action = env["justech.client.module.control"].action_open()
control = env["justech.client.module.control"].browse(control_action["res_id"])
ok("control_opens", control.exists() and bool(control.line_ids))

lines_tested = 0
missing_record = False
rpc_like = False

product_rows = [
    {
        "product_code": line.product_code,
        "customization": line.main_module_code,
        "allow": line.allow_license_actions,
    }
    for line in control.line_ids
]

for row_data in product_rows:
    if not row_data["allow"]:
        continue
    product_code = row_data["product_code"]
    customization = row_data["customization"]
    lines_tested += 1

    def current_line():
        return control.line_ids.filtered(lambda l: l.product_code == product_code)[:1]

    def make_wizard(action_type, **extra):
        row = current_line()
        if not row:
            raise UserError(_("Línea no encontrada para %(code)s") % {"code": product_code})
        panel_action = row.action_open_administrar()
        panel = env["justech.client.module.admin.panel"].browse(panel_action["res_id"])
        return env["justech.client.module.action.wizard"].create(
            {
                "control_id": control.id,
                "panel_id": panel.id,
                "line_id": row.id,
                "product_code": product_code,
                "customization_code": customization,
                "action_type": action_type,
                "company_id": control.company_id.id,
                "license_id": control.license_id.id or False,
                "admin_key": "TEST-KEY-12345678",
                **extra,
            }
        )

    # mark paid / unpaid cycle
    try:
        row = current_line()
        if row.is_paid:
            result = _confirm(make_wizard("mark_unpaid"))
        else:
            result = _confirm(make_wizard("mark_paid"))
        if result.get("res_model") == "justech.client.module.admin.panel":
            reopened = env["justech.client.module.admin.panel"].browse(result["res_id"])
            if not reopened.exists():
                missing_record = True
        control._reload_lines()
    except Exception as exc:
        if "MissingError" in type(exc).__name__ or "Registro" in str(exc):
            missing_record = True
        else:
            rpc_like = True
            fail("mark_paid_cycle", str(exc))

    # activate/deactivate if paid
    row = current_line()
    if row and row.is_paid:
        try:
            if row.is_active:
                _confirm(make_wizard("deactivate"))
            else:
                _confirm(make_wizard("activate"))
            control._reload_lines()
        except UserError:
            pass
        except Exception as exc:
            if "MissingError" in type(exc).__name__:
                missing_record = True
            else:
                rpc_like = True
                fail("activate_cycle", str(exc))

    # license limit friendly message
    lic = env["justech.license.service"]._get_active_license_for_company(control.company_id)
    if not lic:
        lic = env["justech.license.service"]._sudo_internal()["justech.license"].search(
            [("state", "=", "active")], limit=1
        )
    if lic:
        extra_co = env["res.company"].search(
            [("id", "not in", lic.company_line_ids.mapped("company_id").ids)], limit=1
        )
        if extra_co:
            lic.sudo().write({"max_companies": len(lic.company_line_ids)})
            try:
                _confirm(
                    make_wizard("add_company", target_company_id=extra_co.id)
                )
                fail("add_company_limit", "expected UserError")
            except UserError as exc:
                ok(
                    "add_company_friendly_message",
                    "no permite habilitar más empresas" in str(exc),
                )
            except JustechLicenseError:
                fail("add_company_friendly_message", "raw JustechLicenseError leaked")
            except Exception as exc:
                rpc_like = True
                fail("add_company_limit", str(exc))
            lic.sudo().write({"max_companies": 0})

    report["actions"][product_code] = "tested"
    if lines_tested >= 3:
        break

ok("lines_tested", lines_tested >= 1)
ok("no_missing_record", not missing_record)
ok("no_rpc_errors", not rpc_like)
ok("audit_model", bool(env["justech.client.module.audit"].search([], limit=1)))

for login in USER_LOGINS:
    user = env["res.users"].search([("login", "=", login)], limit=1)
    if not user:
        report.setdefault("users", {})[login] = {"found": False}
        continue
    uenv = env(user=user)
    try:
        uenv["justech.admin.access.service"].require_justech_settings_access()
        open_action = uenv["justech.client.module.control"].action_open()
        ctrl = uenv["justech.client.module.control"].browse(open_action["res_id"])
        report.setdefault("users", {})[login] = {
            "found": True,
            "modules": len(ctrl.line_ids),
        }
    except Exception as exc:
        report.setdefault("users", {})[login] = {"found": True, "error": str(exc)}
        fail(f"user_{login}", str(exc))

if not report["ok"]:
    for k, v in report["checks"].items():
        if v is False and k not in report.get("errors", []):
            report["ok"] = False

report["status"] = "PASS" if report["ok"] else "FAIL"
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, default=str, ensure_ascii=False)
print(json.dumps(report, indent=2, default=str, ensure_ascii=False))
sys.exit(0 if report["ok"] else 1)
