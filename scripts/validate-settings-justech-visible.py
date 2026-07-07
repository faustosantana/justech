#!/usr/bin/env python3
"""Validate Configuración → Justech visibility for settings admins."""
import json
import sys

USER_LOGINS = ("it@justech.do",)
CLIENT_LOGIN = "portal_client_visibility_check@hellenia.local"


def main():
    report = {
        "settings_root_xmlid": "justech_admin.menu_justech_settings_root",
        "users": {},
        "checks": {},
    }
    settings_root = env.ref("justech_admin.menu_justech_settings_root")
    modules_menu = env.ref("justech_admin.menu_justech_modules")
    system_group = env.ref("base.group_system")
    parent_xml = env["ir.model.data"].search(
        [("model", "=", "ir.ui.menu"), ("res_id", "=", settings_root.parent_id.id)],
        limit=1,
    )
    report["checks"]["menu_parent"] = (
        f"{parent_xml.module}.{parent_xml.name}" if parent_xml else settings_root.parent_id.name
    )
    report["checks"]["menu_groups"] = settings_root.group_ids.mapped("full_name")
    report["checks"]["settings_app_view"] = bool(
        env.ref("justech_admin.res_config_settings_view_form_justech", raise_if_not_found=False)
    )
    view = env.ref("justech_admin.res_config_settings_view_form_justech", raise_if_not_found=False)
    if view:
        report["checks"]["settings_app_arch_has_justech"] = "string=\"Justech\"" in view.arch_db or "Justech" in (view.arch_db or "")

    for login in USER_LOGINS:
        user = env["res.users"].search([("login", "=", login)], limit=1)
        if not user:
            report["users"][login] = {"found": False}
            continue
        Menu = env["ir.ui.menu"].with_user(user)
        visible_ids = Menu._visible_menu_ids(False)
        menus = env["ir.ui.menu"].with_user(user).load_menus(debug=False)
        settings_node = menus.get("1") or menus.get(1) or {}
        children = settings_node.get("children") or []
        svc = env["justech.admin.access.service"].with_user(user)
        open_action = svc.action_open_client_modules()
        report["users"][login] = {
            "found": True,
            "has_group_system": user.has_group("base.group_system"),
            "settings_root_visible": settings_root.id in visible_ids,
            "modules_menu_visible": modules_menu.id in visible_ids,
            "settings_children_include_root": settings_root.id in children,
            "settings_children_include_modules": modules_menu.id in children,
            "open_action_model": open_action.get("res_model"),
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
    if client.has_group("base.group_system"):
        client_visible = (
            settings_root.id
            in env["ir.ui.menu"].with_user(client)._visible_menu_ids(False)
        )
    else:
        client_visible = False
    report["users"][CLIENT_LOGIN] = {
        "found": True,
        "has_group_system": client.has_group("base.group_system"),
        "settings_root_visible": client_visible,
    }

    ok = True
    for login in USER_LOGINS:
        data = report["users"].get(login, {})
        if not data.get("found"):
            ok = False
            continue
        if not data.get("settings_root_visible") or not data.get("modules_menu_visible"):
            ok = False
        if data.get("open_action_model") not in (
            "justech.admin.key.wizard",
            "justech.admin.key.setup.wizard",
            "justech.client.module.control",
        ):
            ok = False
    if report["users"].get(CLIENT_LOGIN, {}).get("settings_root_visible"):
        ok = False

    report["checks"]["menu_has_action"] = bool(settings_root.action)

    if not report["checks"].get("settings_app_view") or not report["checks"].get("settings_app_arch_has_justech"):
        ok = False
    report["status"] = "PASS" if ok else "FAIL"
    path = "/var/lib/odoo/settings-justech-visible-validation.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
