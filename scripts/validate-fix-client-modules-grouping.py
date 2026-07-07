#!/usr/bin/env python3
"""Validate FIX F31.6 — group client modules into main commercial products."""
import json
import sys

USER_LOGINS = ("it@justech.do",)
HIDDEN_MAIN_CODES = frozenset(
    {
        "comprobantes_fiscales",
        "ux_fiscal",
        "contabilidad_rd",
        "marketplace",
        "ia",
    }
)
FISCAL_INCLUDES = (
    "Comprobantes Fiscales",
    "NCF",
    "DGII",
    "ITBIS",
    "Retenciones",
    "Reportes Fiscales",
    "Experiencia Fiscal",
)


def main():
    report = {"phase": "fix-f31.6-grouping", "users": {}, "checks": {}}
    control_view = env.ref(
        "justech_admin.view_justech_client_module_control_form", raise_if_not_found=False
    )
    manage_view = env.ref(
        "justech_admin.view_justech_client_module_manage_menu_form", raise_if_not_found=False
    )
    arch = control_view.arch_db or "" if control_view else ""
    manage_arch = manage_view.arch_db or "" if manage_view else ""

    report["checks"]["title_modulos_cliente"] = "Módulos del Cliente" in arch
    report["checks"]["section_available"] = "Módulos disponibles" in arch
    report["checks"]["section_development"] = "En desarrollo" in arch
    report["checks"]["administrar_button"] = "action_open_administrar" in arch
    report["checks"]["view_information_button"] = "action_view_information" in arch
    report["checks"]["includes_panel"] = "includes_html" in manage_arch
    report["checks"]["dev_actions_hidden"] = 'invisible="is_development"' in manage_arch

    rows = env["justech.license.service"].get_client_module_rows(view_only=True)
    main_codes = {r.get("main_module_code") for r in rows}
    available = [r for r in rows if r.get("section") == "available"]
    development = [r for r in rows if r.get("section") == "development"]

    report["checks"]["total_rows"] = len(rows)
    report["checks"]["available_count"] = len(available)
    report["checks"]["development_count"] = len(development)
    report["checks"]["few_main_modules"] = len(available) <= 7
    report["checks"]["fiscal_rd_present"] = "fiscal_rd" in main_codes
    report["checks"]["no_hidden_as_main"] = not (
        main_codes & {"comprobantes_fiscales", "ux_fiscal", "contabilidad_rd"}
    )
    report["checks"]["no_internal_product_rows"] = not any(
        r.get("main_module_code") in {"comprobantes_fiscales", "ux_fiscal"}
        for r in available
    )

    fiscal = next((r for r in rows if r.get("main_module_code") == "fiscal_rd"), {})
    includes = fiscal.get("includes") or []
    report["checks"]["fiscal_groups_ncf_dgii"] = all(x in includes for x in FISCAL_INCLUDES)

    report["checks"]["dev_not_active"] = all(not r.get("is_active") for r in development)
    report["checks"]["dev_coming_soon"] = all(
        r.get("status") == "coming_soon" for r in development
    )

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

    ok = True
    for key in (
        "title_modulos_cliente",
        "section_available",
        "section_development",
        "administrar_button",
        "view_information_button",
        "includes_panel",
        "dev_actions_hidden",
        "few_main_modules",
        "fiscal_rd_present",
        "no_hidden_as_main",
        "no_internal_product_rows",
        "fiscal_groups_ncf_dgii",
        "dev_not_active",
        "dev_coming_soon",
    ):
        if not report["checks"].get(key):
            ok = False
    for login in USER_LOGINS:
        data = report["users"].get(login, {})
        if not data.get("found") or not data.get("no_popup"):
            ok = False
        if data.get("open_action_name") != "Módulos del Cliente":
            ok = False

    report["status"] = "PASS" if ok else "FAIL"
    path = "/var/lib/odoo/fix-client-modules-grouping-validation.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
