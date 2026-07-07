#!/usr/bin/env python3
"""Validate modern dashboard UX for Administrar personalización panel."""
import json
import sys

USER_LOGINS = ("it@justech.do",)


def main():
    report = {"phase": "fix-admin-panel-dashboard-ux", "users": {}, "checks": {}}
    view = env.ref(
        "justech_admin.view_justech_client_module_admin_panel_form",
        raise_if_not_found=False,
    )
    arch = view.arch_db or "" if view else ""

    report["checks"]["dashboard_view"] = "justech-cc-admin-dashboard" in arch
    report["checks"]["no_list_view"] = "<list" not in arch
    report["checks"]["kanban_features"] = "justech-dash-feature-kanban" in arch
    report["checks"]["feature_toggles"] = "boolean_toggle" in arch
    report["checks"]["header_badges"] = "dashboard_header_html" in arch
    report["checks"]["companies_section"] = "companies_dashboard_html" in arch
    report["checks"]["timeline_section"] = "justech-dash-timeline" in arch or "audit_html" in arch
    report["checks"]["danger_actions"] = "btn-outline-danger" in arch
    report["checks"]["no_technical_fields_visible"] = 'name="product_code"' not in arch.replace(
        " invisible=", " "
    )

    license_svc = env["justech.license.service"]
    sections = license_svc.get_commercial_feature_sections(
        "fiscal_rd", company=env.company
    )
    section_labels = [s["section_label"] for s in sections]
    report["section_labels"] = section_labels
    report["checks"]["fiscal_sections"] = all(
        label in section_labels
        for label in ("COMPROBANTES", "DGII", "IMPUESTOS", "VALIDACIONES")
    )
    report["checks"]["features_have_descriptions"] = all(
        f.get("description") for s in sections for f in s["features"]
    )

    control = env["justech.client.module.control"].action_open()
    rec = env["justech.client.module.control"].browse(control["res_id"])
    line = rec.line_ids.filtered(lambda l: l.main_module_code == "fiscal_rd")[:1]
    if line:
        admin = line.action_open_administrar()
        panel = env["justech.client.module.admin.panel"].browse(admin["res_id"])
        report["checks"]["panel_has_header_html"] = bool(panel.dashboard_header_html)
        report["checks"]["panel_has_kpi"] = "justech-dash-kpi" in (
            panel.dashboard_header_html or ""
        )
        report["checks"]["features_in_cards"] = all(
            line.description for line in panel.feature_line_ids
        )
        report["checks"]["grouped_sections"] = len(
            set(panel.feature_line_ids.mapped("section_label"))
        ) >= 4
    else:
        report["checks"]["panel_has_header_html"] = False
        report["checks"]["panel_has_kpi"] = False
        report["checks"]["features_in_cards"] = False
        report["checks"]["grouped_sections"] = False

    for login in USER_LOGINS:
        user = env["res.users"].search([("login", "=", login)], limit=1)
        if not user:
            report["users"][login] = {"found": False}
            continue
        svc = env["justech.admin.access.service"].with_user(user)
        open_action = svc.action_open_client_modules()
        ctrl = env["justech.client.module.control"].browse(open_action["res_id"])
        ln = ctrl.line_ids.filtered(lambda l: l.main_module_code == "fiscal_rd")[:1]
        admin = ln.action_open_administrar() if ln else {}
        pnl = (
            env["justech.client.module.admin.panel"].browse(admin["res_id"])
            if admin.get("res_id")
            else env["justech.client.module.admin.panel"]
        )
        report["users"][login] = {
            "found": True,
            "admin_model": admin.get("res_model"),
            "feature_sections": len(set(pnl.feature_line_ids.mapped("section_label")))
            if pnl
            else 0,
        }

    ok = all(
        report["checks"].get(k)
        for k in (
            "dashboard_view",
            "no_list_view",
            "kanban_features",
            "feature_toggles",
            "header_badges",
            "companies_section",
            "timeline_section",
            "danger_actions",
            "fiscal_sections",
            "features_have_descriptions",
            "panel_has_header_html",
            "panel_has_kpi",
            "features_in_cards",
            "grouped_sections",
        )
    )
    for data in report["users"].values():
        if not data.get("found") or data.get("admin_model") != "justech.client.module.admin.panel":
            ok = False

    report["status"] = "PASS" if ok else "FAIL"
    path = "/var/lib/odoo/fix-admin-panel-dashboard-ux-validation.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
