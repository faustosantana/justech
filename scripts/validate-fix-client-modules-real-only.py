#!/usr/bin/env python3
"""Validate real-only client modules screen."""
import json
import sys

USER_LOGINS = ("it@justech.do",)
FORBIDDEN_CODES = frozenset(
    {
        "crm",
        "ia",
        "rrhh",
        "activos_fijos",
        "marketplace",
        "manufactura",
        "nomina",
        "fiscal_rd",
    }
)


def main():
    report = {"phase": "fix-real-only", "users": {}, "checks": {}}
    control_view = env.ref(
        "justech_admin.view_justech_client_module_control_form", raise_if_not_found=False
    )
    manage_view = env.ref(
        "justech_admin.view_justech_client_module_manage_menu_form", raise_if_not_found=False
    )
    arch = control_view.arch_db or "" if control_view else ""
    manage_arch = manage_view.arch_db or "" if manage_view else ""

    report["checks"]["compact_header"] = "header_html" in arch
    report["checks"]["kanban_cards"] = "justech-cc-module-card" in arch
    report["checks"]["no_development_section"] = "En desarrollo" not in arch
    report["checks"]["filter_estado"] = 'string="Estado"' in arch
    report["checks"]["includes_panel"] = "includes_html" in manage_arch
    report["checks"]["audit_panel"] = "audit_html" in manage_arch

    rows = env["justech.license.service"].get_client_module_rows(view_only=True)
    main_codes = {r.get("main_module_code") for r in rows}
    report["checks"]["total_rows"] = len(rows)
    report["checks"]["no_forbidden_categories"] = not (main_codes & FORBIDDEN_CODES)
    report["checks"]["no_development_rows"] = not any(
        r.get("section") == "development" for r in rows
    )
    report["checks"]["has_fiscal_category"] = "contabilidad_fiscal_rd" in main_codes
    report["checks"]["includes_summary"] = all(r.get("includes_summary") for r in rows)
    report["checks"]["formatted_dates"] = all(
        "last_modified_display" in r for r in rows
    )

    pos_installed = env["justech.license.service"]._odoo_module_installed("hellenia_pos")
    report["checks"]["pos_matches_install"] = ("pos" in main_codes) == pos_installed

    for login in USER_LOGINS:
        user = env["res.users"].search([("login", "=", login)], limit=1)
        if not user:
            report["users"][login] = {"found": False}
            continue
        svc = env["justech.admin.access.service"].with_user(user)
        open_action = svc.action_open_client_modules()
        report["users"][login] = {
            "found": True,
            "no_popup": open_action.get("res_model") == "justech.client.module.control",
        }

    ok = all(
        report["checks"].get(key)
        for key in (
            "compact_header",
            "kanban_cards",
            "no_development_section",
            "filter_estado",
            "includes_panel",
            "no_forbidden_categories",
            "no_development_rows",
            "has_fiscal_category",
            "includes_summary",
            "formatted_dates",
            "pos_matches_install",
        )
    )
    for login in USER_LOGINS:
        if not report["users"].get(login, {}).get("no_popup"):
            ok = False

    report["status"] = "PASS" if ok else "FAIL"
    path = "/var/lib/odoo/fix-client-modules-real-only-validation.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
