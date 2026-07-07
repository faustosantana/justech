#!/usr/bin/env python3
"""Validate FASE 31.6 — Módulos del Cliente commercial UX."""
import json
import sys

USER_LOGINS = ("it@justech.do",)
CLIENT_LOGIN = "portal_client_visibility_check@hellenia.local"


def main():
    report = {"phase": "31.6", "users": {}, "checks": {}}
    control_view = env.ref(
        "justech_admin.view_justech_client_module_control_form", raise_if_not_found=False
    )
    manage_view = env.ref(
        "justech_admin.view_justech_client_module_manage_menu_form", raise_if_not_found=False
    )
    arch = control_view.arch_db or "" if control_view else ""
    report["checks"]["title_modulos_cliente"] = "Módulos del Cliente" in arch
    report["checks"]["client_selector"] = "license_id" in arch
    report["checks"]["commercial_table"] = all(
        x in arch
        for x in (
            "display_name",
            "companies_enabled_text",
            "action_open_administrar",
        )
    )
    report["checks"]["manage_panel"] = bool(
        manage_view and "companies_html" in (manage_view.arch_db or "")
    )
    clients = env["justech.license.service"].get_commercial_clients()
    report["checks"]["commercial_clients"] = len(clients)
    rows = env["justech.license.service"].get_client_module_rows(view_only=True)
    report["checks"]["commercial_rows"] = len(rows)
    report["checks"]["rows_have_icons"] = all(r.get("display_name") for r in rows[:5])

    for login in USER_LOGINS:
        user = env["res.users"].search([("login", "=", login)], limit=1)
        if not user:
            report["users"][login] = {"found": False}
            continue
        svc = env["justech.admin.access.service"].with_user(user)
        open_action = svc.action_open_client_modules()
        report["users"][login] = {
            "found": True,
            "open_action_model": open_action.get("res_model"),
            "open_action_name": open_action.get("name"),
            "no_popup": open_action.get("res_model") == "justech.client.module.control",
        }

    client = env["res.users"].search([("login", "=", CLIENT_LOGIN)], limit=1)
    if not client:
        client = env["res.users"].create(
            {"name": "Client", "login": CLIENT_LOGIN, "group_ids": [(6, 0, [])]}
        )
    report["users"][CLIENT_LOGIN] = {
        "found": True,
        "has_group_system": client.has_group("base.group_system"),
    }

    ok = True
    for key in (
        "title_modulos_cliente",
        "client_selector",
        "commercial_table",
        "manage_panel",
    ):
        if not report["checks"].get(key):
            ok = False
    if not report["checks"].get("commercial_rows"):
        ok = False
    for login in USER_LOGINS:
        data = report["users"].get(login, {})
        if not data.get("found") or not data.get("no_popup"):
            ok = False
        if data.get("open_action_name") != "Módulos del Cliente":
            ok = False

    report["status"] = "PASS" if ok else "FAIL"
    path = "/var/lib/odoo/fase-31-6-validation.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
