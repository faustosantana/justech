#!/usr/bin/env python3
"""Validate Justech real customizations screen (no native Odoo / future modules)."""
import json
import sys

USER_LOGINS = ("it@justech.do",)
FORBIDDEN_IN_NAMES = (
    "crm",
    " ia",
    "rrhh",
    "marketplace",
    "manufactura",
    "nómina",
    "nomina",
    "activos fijos",
    "ventas",
    "compras",
    "inventario",
)


def main():
    license_svc = env["justech.license.service"]
    report = {"phase": "fix-justech-real-customizations", "users": {}, "checks": {}}
    control_view = env.ref(
        "justech_admin.view_justech_client_module_control_form", raise_if_not_found=False
    )
    manage_view = env.ref(
        "justech_admin.view_justech_client_module_manage_menu_form", raise_if_not_found=False
    )
    arch = control_view.arch_db or "" if control_view else ""
    manage_arch = manage_view.arch_db or "" if manage_view else ""

    report["checks"]["kanban_ui"] = "justech-cc-module-card" in arch
    report["checks"]["no_development_section"] = "En desarrollo" not in arch
    report["checks"]["manage_commercial_panel"] = "commercial_status_html" in manage_arch
    report["checks"]["manage_technical_panel"] = "technical_status_html" in manage_arch
    report["checks"]["manage_includes"] = "includes_html" in manage_arch

    summary = license_svc.get_visible_justech_customizations_report()
    rows = license_svc.get_client_module_rows(view_only=True)
    names_blob = " ".join(r.get("name", "") for r in rows).lower()

    report["visible_customizations"] = summary["visible"]
    report["visible_count"] = summary["visible_count"]
    report["hidden_forbidden_labels"] = summary["hidden_forbidden_labels"]

    report["checks"]["max_five_cards"] = summary["visible_count"] <= 5
    report["checks"]["at_least_one_real"] = summary["visible_count"] >= 1
    report["checks"]["fiscal_rd_present"] = any(
        v["code"] == "fiscal_rd" for v in summary["visible"]
    )
    report["checks"]["reportes_present"] = any(
        v["code"] == "reportes_corporativos" for v in summary["visible"]
    )
    report["checks"]["no_forbidden_names"] = not any(
        f in names_blob for f in FORBIDDEN_IN_NAMES
    )
    report["checks"]["no_native_odoo_rows"] = not any(
        r.get("main_module_code") in ("ventas", "compras", "inventario")
        for r in rows
    )

    pos_installed = license_svc._odoo_module_installed("hellenia_pos")
    pos_visible = any(r.get("main_module_code") == "pos_fiscal" for r in rows)
    if not pos_installed:
        report["checks"]["pos_matches_install"] = not pos_visible
    else:
        product = license_svc._sudo_internal()["justech.commercial.product"].search(
            [("code", "=", "punto_de_venta")], limit=1
        )
        configured = license_svc._product_configured(
            product, license_svc._sudo_internal()
        )
        report["checks"]["pos_matches_install"] = pos_visible == configured

    for login in USER_LOGINS:
        user = env["res.users"].search([("login", "=", login)], limit=1)
        if not user:
            report["users"][login] = {"found": False}
            continue
        svc = env["justech.admin.access.service"].with_user(user)
        open_action = svc.action_open_client_modules()
        control = env["justech.client.module.control"].browse(open_action["res_id"])
        report["users"][login] = {
            "found": True,
            "no_popup": open_action.get("res_model") == "justech.client.module.control",
            "visible_lines": len(control.line_ids),
            "line_names": control.line_ids.mapped("name"),
        }

    ok = all(
        report["checks"].get(k)
        for k in (
            "kanban_ui",
            "no_development_section",
            "manage_commercial_panel",
            "manage_technical_panel",
            "manage_includes",
            "max_five_cards",
            "at_least_one_real",
            "fiscal_rd_present",
            "reportes_present",
            "no_forbidden_names",
            "no_native_odoo_rows",
            "pos_matches_install",
        )
    )
    for login in USER_LOGINS:
        u = report["users"].get(login, {})
        if not u.get("found") or not u.get("no_popup"):
            ok = False
        if u.get("visible_lines", 99) > 5:
            ok = False

    report["status"] = "PASS" if ok else "FAIL"
    path = "/var/lib/odoo/fix-justech-real-customizations-validation.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
