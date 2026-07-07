#!/usr/bin/env python3
"""Validate Módulos del Cliente shows only REAL_JUSTECH_CUSTOMIZATIONS."""
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
    "en desarrollo",
)
EXPECTED_CODES = frozenset(
    {
        "fiscal_rd",
        "ux_fiscal_contactos_facturas",
        "reportes_documentos_corporativos",
        "pos_fiscal_si_instalado",
        "control_justech_interno",
    }
)


def main():
    license_svc = env["justech.license.service"]
    report = {
        "phase": "fix-real-justech-customizations-only",
        "users": {},
        "checks": {},
    }
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
    report["checks"]["manage_includes"] = "includes_html" in manage_arch
    report["checks"]["real_catalog_defined"] = bool(
        getattr(license_svc, "REAL_JUSTECH_CUSTOMIZATIONS", ())
    )

    rows = license_svc.get_client_module_rows(view_only=True)
    summary = license_svc.get_visible_justech_customizations_report()
    names_blob = " ".join(r.get("name", "") for r in rows).lower()
    codes = {r.get("main_module_code") for r in rows}

    report["visible_customizations"] = summary["visible"]
    report["visible_count"] = summary["visible_count"]
    report["visible_codes"] = sorted(codes)
    report["visible_names"] = [r.get("name") for r in rows]

    report["checks"]["max_five_cards"] = summary["visible_count"] <= 5
    report["checks"]["at_least_one_real"] = summary["visible_count"] >= 1
    report["checks"]["fiscal_rd_present"] = "fiscal_rd" in codes
    report["checks"]["reportes_present"] = "reportes_documentos_corporativos" in codes
    report["checks"]["ux_fiscal_present"] = "ux_fiscal_contactos_facturas" in codes
    report["checks"]["only_expected_codes"] = codes.issubset(EXPECTED_CODES)
    report["checks"]["no_forbidden_names"] = not any(
        f in names_blob for f in FORBIDDEN_IN_NAMES
    )
    report["checks"]["no_native_odoo_rows"] = not any(
        r.get("main_module_code") in ("ventas", "compras", "inventario", "crm", "ia")
        for r in rows
    )
    report["checks"]["all_rows_have_includes"] = all(r.get("includes") for r in rows)

    pos_installed = license_svc._odoo_module_installed("hellenia_pos")
    pos_visible = "pos_fiscal_si_instalado" in codes
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
        line_names = control.line_ids.mapped("name")
        forbidden_hit = any(
            f in " ".join(line_names).lower() for f in FORBIDDEN_IN_NAMES
        )
        report["users"][login] = {
            "found": True,
            "no_popup": open_action.get("res_model") == "justech.client.module.control",
            "visible_lines": len(control.line_ids),
            "line_names": line_names,
            "no_forbidden": not forbidden_hit,
        }

    ok = all(
        report["checks"].get(k)
        for k in (
            "kanban_ui",
            "no_development_section",
            "manage_includes",
            "real_catalog_defined",
            "max_five_cards",
            "at_least_one_real",
            "fiscal_rd_present",
            "reportes_present",
            "ux_fiscal_present",
            "only_expected_codes",
            "no_forbidden_names",
            "no_native_odoo_rows",
            "all_rows_have_includes",
            "pos_matches_install",
        )
    )
    for login in USER_LOGINS:
        u = report["users"].get(login, {})
        if not u.get("found") or not u.get("no_popup") or not u.get("no_forbidden"):
            ok = False
        if u.get("visible_lines", 99) > 5:
            ok = False

    report["status"] = "PASS" if ok else "FAIL"
    path = "/var/lib/odoo/fix-real-justech-customizations-only-validation.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
