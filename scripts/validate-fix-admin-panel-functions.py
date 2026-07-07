#!/usr/bin/env python3
"""Validate commercial Administrar panel with ON/OFF feature toggles."""
import json
import sys

USER_LOGINS = ("it@justech.do",)


def main():
    report = {"phase": "fix-admin-panel-functions", "users": {}, "checks": {}}
    panel_view = env.ref(
        "justech_admin.view_justech_client_module_admin_panel_form",
        raise_if_not_found=False,
    )
    legacy_view = env.ref(
        "justech_admin.view_justech_client_module_manage_menu_form",
        raise_if_not_found=False,
    )
    arch = panel_view.arch_db or "" if panel_view else ""
    legacy_active = legacy_view.active if legacy_view else False

    report["checks"]["commercial_panel_view"] = bool(panel_view)
    report["checks"]["legacy_view_disabled"] = legacy_active is False
    report["checks"]["feature_toggle_list"] = "boolean_toggle" in arch
    report["checks"]["no_includes_json_field"] = 'name="includes"' not in arch
    report["checks"]["no_technical_status_field"] = (
        'name="technical_status_text"' not in arch
    )
    report["checks"]["feature_flag_model"] = bool(
        env["justech.client.module.feature.flag"]._name
    )

    license_svc = env["justech.license.service"]
    feature_rows = license_svc.get_commercial_feature_rows(
        "fiscal_rd", company=env.company
    )
    report["checks"]["fiscal_features_defined"] = len(feature_rows) >= 10
    report["fiscal_feature_labels"] = [r["label"] for r in feature_rows[:5]]

    control_action = env["justech.client.module.control"].action_open()
    control = env["justech.client.module.control"].browse(control_action["res_id"])
    line = control.line_ids.filtered(lambda l: l.main_module_code == "fiscal_rd")[:1]
    if line:
        admin_action = line.action_open_administrar()
        report["checks"]["administrar_opens_panel"] = (
            admin_action.get("res_model") == "justech.client.module.admin.panel"
        )
        report["checks"]["administrar_not_line_form"] = (
            admin_action.get("res_model") != "justech.client.module.line"
        )
        panel = env["justech.client.module.admin.panel"].browse(admin_action["res_id"])
        report["checks"]["panel_has_feature_lines"] = bool(panel.feature_line_ids)
        report["checks"]["panel_has_toggle_fields"] = any(
            "NCF" in (f.label or "") for f in panel.feature_line_ids
        )
        form_action = line.get_formview_action()
        report["checks"]["line_form_redirects"] = (
            form_action.get("res_model") == "justech.client.module.admin.panel"
        )
    else:
        report["checks"]["administrar_opens_panel"] = False
        report["checks"]["administrar_not_line_form"] = False
        report["checks"]["panel_has_feature_lines"] = False
        report["checks"]["panel_has_toggle_fields"] = False
        report["checks"]["line_form_redirects"] = False

    for login in USER_LOGINS:
        user = env["res.users"].search([("login", "=", login)], limit=1)
        if not user:
            report["users"][login] = {"found": False}
            continue
        svc = env["justech.admin.access.service"].with_user(user)
        open_action = svc.action_open_client_modules()
        rec = env["justech.client.module.control"].browse(open_action["res_id"])
        line = rec.line_ids[:1]
        admin = line.action_open_administrar() if line else {}
        report["users"][login] = {
            "found": True,
            "admin_model": admin.get("res_model"),
            "feature_count": len(
                env["justech.client.module.admin.panel"]
                .browse(admin.get("res_id"))
                .feature_line_ids
            )
            if admin.get("res_id")
            else 0,
        }

    ok = all(
        report["checks"].get(k)
        for k in (
            "commercial_panel_view",
            "legacy_view_disabled",
            "feature_toggle_list",
            "no_includes_json_field",
            "no_technical_status_field",
            "feature_flag_model",
            "fiscal_features_defined",
            "administrar_opens_panel",
            "administrar_not_line_form",
            "panel_has_feature_lines",
            "panel_has_toggle_fields",
            "line_form_redirects",
        )
    )
    for login, data in report["users"].items():
        if not data.get("found"):
            ok = False
        if data.get("admin_model") != "justech.client.module.admin.panel":
            ok = False

    report["status"] = "PASS" if ok else "FAIL"
    path = "/var/lib/odoo/fix-admin-panel-functions-validation.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
