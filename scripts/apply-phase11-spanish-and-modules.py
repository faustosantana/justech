#!/usr/bin/env python3
"""Fase 11 — Idioma es_DO, módulos oficiales Hellenia y auditoría de traducciones.

Ejecutar vía odoo shell en DEV o TEST únicamente.
No toca producción (odoo-pecv).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

COMPANY_LANG = "es_DO"
FALLBACK_LANG = "es_419"

# Módulos operativos requeridos (nombres técnicos Odoo 19 EE)
REQUIRED_MODULES = {
    "account": "Contabilidad",
    "account_accountant": "Contabilidad (EE)",
    "account_reports": "Informes contables",
    "spreadsheet_dashboard_account": "Tablero contable",
    "sale": "Ventas",
    "contacts": "Contactos",
    "purchase": "Compras",
    "stock": "Inventario",
    "l10n_do": "Localización RD",
    "justech_l10n_do_base": "Justech fiscal base",
    "justech_l10n_do_ncf": "Justech NCF",
    "justech_l10n_do_reports": "Justech reportes DGII",
}

# CRM: no forma parte del flujo comercial Hellenia (solo sale + crm.team vía sales_team)
OPTIONAL_MODULES = {
    "crm": "CRM (no requerido — flujo cotización/pedido sin pipeline CRM)",
}

EXCLUDED_MODULES = [
    "point_of_sale",
    "website_sale",
    "mrp",
    "sale_renting",
    "sale_subscription",
    "helpdesk",
    "project",
    "industry_fsm",
]

# Traducciones menús custom Justech (configuración, no desarrollo)
JUSTECH_MENU_TRANSLATIONS = {
    "Dominican Fiscal": "Fiscal Dominicano",
    "Document Types": "Tipos de documento",
    "NCF Ranges": "Rangos NCF",
    "NCF Consumption": "Consumo NCF",
    "DGII Reports": "Reportes DGII",
    "Generate Report": "Generar reporte",
    "Report History": "Historial de reportes",
    "Fiscal Document Types": "Tipos de documento fiscal",
}

ENGLISH_HINT = re.compile(
    r"\b(the|and|invoice|customer|vendor|stock|sales|purchase|payment|journal|report|dashboard|settings)\b",
    re.I,
)

report = {
    "phase": 11,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": env.cr.dbname,
    "language": {},
    "modules": {"required": {}, "optional": {}, "excluded": {}},
    "translations": {"updated_modules": [], "justech_menus": []},
    "english_remainders": [],
    "justech_integrity": {},
    "ok": True,
    "errors": [],
}


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


def ensure_lang(code: str) -> None:
    Lang = env["res.lang"]
    Lang._activate_lang(code)
    lang = Lang.with_context(active_test=False).search([("code", "=", code)], limit=1)
    if lang and not lang.active:
        lang.active = True


def set_default_language() -> None:
    ensure_lang(COMPANY_LANG)
    ensure_lang(FALLBACK_LANG)

    company = env.company
    if company.partner_id.lang != COMPANY_LANG:
        company.partner_id.lang = COMPANY_LANG

    users = env["res.users"].search([("active", "=", True), ("share", "=", False)])
    non_es = users.filtered(lambda u: u.lang != COMPANY_LANG)
    if non_es:
        non_es.write({"lang": COMPANY_LANG})

    # Parámetro idioma por defecto nuevos usuarios (Odoo 19)
    ICP = env["ir.config_parameter"].sudo()
    for key in ("base.default_lang", "auth_signup.default_lang"):
        ICP.set_param(key, COMPANY_LANG)

    lang = env["res.lang"].search([("code", "=", COMPANY_LANG)], limit=1)
    report["language"] = {
        "es_DO_active": bool(lang and lang.active),
        "company_lang": company.partner_id.lang,
        "users_total": len(users),
        "users_es_DO": len(users.filtered(lambda u: u.lang == COMPANY_LANG)),
        "default_params_set": True,
    }


def update_module_translations() -> None:
    Mod = env["ir.module.module"]
    lang = env["res.lang"].search([("code", "=", COMPANY_LANG)], limit=1)
    if not lang:
        return
    priority = list(REQUIRED_MODULES.keys()) + [
        "sale_stock",
        "purchase_stock",
        "stock_account",
        "account_payment",
        "l10n_do_reports",
    ]
    for name in priority:
        mod = Mod.search([("name", "=", name), ("state", "=", "installed")], limit=1)
        if not mod:
            continue
        try:
            mod._update_translations([COMPANY_LANG])
            report["translations"]["updated_modules"].append(mod.name)
        except Exception as exc:  # noqa: BLE001
            report["english_remainders"].append(
                {"type": "translation_update", "module": name, "detail": str(exc)[:200]}
            )


def upsert_menu_translation(menu, src: str, value: str) -> None:
    # Odoo 19: traducción vía contexto de idioma (ir.translation no expuesto en ORM shell)
    menu.with_context(lang=COMPANY_LANG).write({"name": value})
    report["translations"]["justech_menus"].append(
        {"src": src, "value": value, "menu_id": menu.id}
    )


def translate_justech_menus() -> None:
    Menu = env["ir.ui.menu"]
    for src, value in JUSTECH_MENU_TRANSLATIONS.items():
        menus = Menu.search([("name", "=", src)])
        for menu in menus:
            upsert_menu_translation(menu, src, value)


def install_required_modules() -> None:
    Mod = env["ir.module.module"]
    to_install = Mod.browse()
    for name in REQUIRED_MODULES:
        rec = Mod.search([("name", "=", name)], limit=1)
        state = rec.state if rec else "not_found"
        report["modules"]["required"][name] = {
            "label": REQUIRED_MODULES[name],
            "state": state,
            "action": None,
        }
        if not rec:
            err(f"Módulo requerido no encontrado en Apps: {name}")
        elif rec.state == "uninstalled":
            to_install |= rec
            report["modules"]["required"][name]["action"] = "install"
        elif rec.state == "to install":
            to_install |= rec
            report["modules"]["required"][name]["action"] = "install_pending"

    if to_install:
        to_install.button_immediate_install()
        env.cr.commit()
        for name in REQUIRED_MODULES:
            rec = Mod.search([("name", "=", name)], limit=1)
            if rec:
                report["modules"]["required"][name]["state"] = rec.state

    for name, label in OPTIONAL_MODULES.items():
        rec = Mod.search([("name", "=", name)], limit=1)
        report["modules"]["optional"][name] = {
            "label": label,
            "state": rec.state if rec else "not_found",
            "installed": False,
            "reason": "Flujo Hellenia: ventas por pedido, sin pipeline CRM",
        }

    for name in EXCLUDED_MODULES:
        rec = Mod.search([("name", "=", name)], limit=1)
        state = rec.state if rec else "not_found"
        report["modules"]["excluded"][name] = state
        if rec and rec.state == "installed":
            err(f"Módulo fuera de alcance instalado: {name}")


def audit_spanish_surface() -> None:
    """Documenta etiquetas aún en inglés en áreas clave."""
    env_ctx = env(context=dict(env.context, lang=COMPANY_LANG))

    def check_records(model, domain, label, limit=30):
        for rec in env_ctx[model].search(domain, limit=limit):
            name = (rec.display_name or rec.name or "").strip()
            if not name:
                continue
            if ENGLISH_HINT.search(name) and not any(
                c in name for c in "áéíóúñÁÉÍÓÚÑ"
            ):
                report["english_remainders"].append(
                    {
                        "type": label,
                        "model": model,
                        "id": rec.id,
                        "name": name,
                        "note": "Revisar traducción es_DO o renombrar si es configuración local",
                    }
                )

    check_records("account.journal", [("company_id", "=", env.company.id)], "journal")
    check_records("account.payment.term", [], "payment_term", limit=20)
    check_records("account.tax", [("company_id", "=", env.company.id)], "tax", limit=40)
    check_records("ir.ui.menu", [], "menu", limit=80)

    # Menús Justech en contexto es_DO
    Menu = env["ir.ui.menu"]
    for src, expected in JUSTECH_MENU_TRANSLATIONS.items():
        for menu in Menu.search([("name", "in", [src, expected])]):
            xml_id = menu.get_external_id().get(menu.id) or ""
            if "justech" not in xml_id:
                continue
            displayed = menu.with_context(lang=COMPANY_LANG).name
            if displayed != expected:
                report["english_remainders"].append(
                    {
                        "type": "justech_menu",
                        "menu_id": menu.id,
                        "expected": expected,
                        "displayed": displayed,
                    }
                )


def validate_justech_localization() -> None:
    company = env.company
    fiscal_ok = bool(company.justech_do_fiscal_enabled)
    report["justech_integrity"]["fiscal_enabled"] = fiscal_ok
    if not fiscal_ok:
        err("justech_do_fiscal_enabled desactivado en compañía")

    for mod in (
        "justech_l10n_do_base",
        "justech_l10n_do_ncf",
        "justech_l10n_do_reports",
    ):
        rec = env["ir.module.module"].search([("name", "=", mod)], limit=1)
        st = rec.state if rec else "not_found"
        report["justech_integrity"][mod] = st
        if st != "installed":
            err(f"Módulo Justech no instalado: {mod} ({st})")

    doc_count = env["justech.do.fiscal.document.type"].search_count([])
    report["justech_integrity"]["document_types"] = doc_count
    if doc_count < 6:
        err(f"Tipos documento fiscal incompletos: {doc_count}")


# --- Ejecución ---
set_default_language()
install_required_modules()
update_module_translations()
translate_justech_menus()
validate_justech_localization()
audit_spanish_surface()

report["summary"] = {
    "required_installed": all(
        v.get("state") == "installed" for v in report["modules"]["required"].values()
    ),
    "excluded_clean": not any(
        s == "installed" for s in report["modules"]["excluded"].values()
    ),
    "english_items_found": len(report["english_remainders"]),
    "crm_skipped_by_design": True,
}

print("PHASE11_CONFIG:" + json.dumps(report, ensure_ascii=False, default=str))
