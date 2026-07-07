#!/usr/bin/env python3
"""Validate FIX FINAL UX — Módulos del Cliente / Clave Justech."""
import json
import sys

USER_LOGINS = ("it@justech.do",)
CLIENT_LOGIN = "portal_client_visibility_check@hellenia.local"


def main():
    report = {
        "fix": "client-modules-ux",
        "users": {},
        "checks": {},
    }
    settings_root = env.ref("justech_admin.menu_justech_settings_root")
    modules_menu = env.ref("justech_admin.menu_justech_modules")
    system_group = env.ref("base.group_system")
    view = env.ref("justech_admin.res_config_settings_view_form_justech", raise_if_not_found=False)
    control_view = env.ref(
        "justech_admin.view_justech_client_module_control_form", raise_if_not_found=False
    )

    report["checks"]["settings_app_view"] = bool(view)
    report["checks"]["control_view_has_summary"] = bool(
        control_view and "summary_html" in (control_view.arch_db or "")
    )
    report["checks"]["control_view_has_admin_menu"] = bool(
        control_view and "action_open_manage_menu" in (control_view.arch_db or "")
    )
    report["checks"]["control_view_has_panel"] = bool(
        control_view and "panel_html" in (control_view.arch_db or "")
    )
    report["checks"]["open_action_is_admin_center"] = False
    report["checks"]["control_view_has_key_banner"] = bool(
        control_view and "key_banner_html" in (control_view.arch_db or "")
    )
    report["checks"]["menu_groups_system_only"] = all(
        g.id == system_group.id for g in settings_root.group_ids
    )

    for login in USER_LOGINS:
        user = env["res.users"].search([("login", "=", login)], limit=1)
        if not user:
            report["users"][login] = {"found": False}
            continue
        svc = env["justech.admin.access.service"].with_user(user)
        open_action = svc.action_open_client_modules()
        settings_root_visible = False
        modules_menu_visible = False
        try:
            Menu = env["ir.ui.menu"].with_user(user)
            visible_ids = Menu._visible_menu_ids(False)
            settings_root_visible = settings_root.id in visible_ids
            modules_menu_visible = modules_menu.id in visible_ids
        except Exception as exc:
            report.setdefault("warnings", []).append(
                f"{login}: menu visibility check skipped ({exc.__class__.__name__})"
            )
            settings_root_visible = user.has_group("base.group_system")
            modules_menu_visible = settings_root_visible
        report["users"][login] = {
            "found": True,
            "has_group_system": user.has_group("base.group_system"),
            "settings_root_visible": settings_root_visible,
            "modules_menu_visible": modules_menu_visible,
            "open_action_model": open_action.get("res_model"),
            "open_action_name": open_action.get("name"),
            "no_popup_on_open": open_action.get("res_model") == "justech.client.module.control",
            "admin_center_title": open_action.get("name") == "Centro de Administración Justech",
        }

    client = env["res.users"].search([("login", "=", CLIENT_LOGIN)], limit=1)
    if not client:
        client = env["res.users"].create(
            {
                "name": "Client Visibility Check",
                "login": CLIENT_LOGIN,
                "group_ids": [(6, 0, [])],
            }
        )
    client_visible = False
    try:
        client_visible = (
            settings_root.id
            in env["ir.ui.menu"].with_user(client)._visible_menu_ids(False)
            if not client.has_group("base.group_system")
            else True
        )
    except Exception:
        client_visible = client.has_group("base.group_system")
    report["users"][CLIENT_LOGIN] = {
        "found": True,
        "has_group_system": client.has_group("base.group_system"),
        "settings_root_visible": client_visible,
    }

    admin = env.ref("base.user_admin")
    rows = env["justech.license.service"].with_user(admin).get_client_module_rows(
        company=env.company, view_only=True
    )
    report["checks"]["commercial_rows"] = len(rows)
    report["checks"]["no_technical_names_in_rows"] = all(
        r.get("name")
        and "justech" not in (r.get("name") or "").lower()
        and "hellenia" not in (r.get("name") or "").lower()
        for r in rows[:5]
    )

    ok = True
    for login in USER_LOGINS:
        data = report["users"].get(login, {})
        if not data.get("found"):
            ok = False
            continue
        if not data.get("no_popup_on_open") or not data.get("admin_center_title"):
            ok = False
        if not data.get("settings_root_visible") or not data.get("modules_menu_visible"):
            ok = False
    if report["users"].get(CLIENT_LOGIN, {}).get("settings_root_visible"):
        ok = False
    for key in (
        "control_view_has_summary",
        "control_view_has_admin_menu",
        "control_view_has_panel",
        "control_view_has_key_banner",
    ):
        if not report["checks"].get(key):
            ok = False
    if not report["checks"].get("commercial_rows"):
        ok = False

    report["status"] = "PASS" if ok else "FAIL"
    path = "/var/lib/odoo/fix-client-modules-ux-validation.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
