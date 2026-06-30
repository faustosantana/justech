#!/usr/bin/env python3
"""Validar menú principal Hellenia en odoo shell (PROD).

Emite JSON con módulos, permisos it@justech.do y menús raíz visibles.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

IT_LOGIN = "it@justech.do"
EXPECTED_ROOTS = {
    "Ventas": ["sale.sale_menu_root"],
    "Compras": ["purchase.menu_purchase_root"],
    "Inventario": ["stock.menu_stock_root"],
    "Contabilidad": ["account.menu_finance"],
    "Contactos": ["contacts.menu_contacts"],
    "Configuración": ["base.menu_administration"],
}
HIDDEN = {
    "Apps": "base.menu_management",
    "Código de barras": "stock_barcode.stock_barcode_menu",
}

report = {
    "phase": "hellenia-ui-menu",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "modules": {},
    "user": {},
    "root_menus": [],
    "expected_roots": {},
    "hidden_menus": {},
    "ok": True,
    "errors": [],
}


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


for mod_name in ("sale", "sale_management", "hellenia_ui"):
    mod = env["ir.module.module"].search([("name", "=", mod_name)], limit=1)
    report["modules"][mod_name] = mod.state if mod else "not_found"
    if mod_name == "sale_management" and mod and mod.state != "installed":
        err(f"sale_management no instalado ({mod.state})")
    if mod_name == "hellenia_ui" and mod and mod.state != "installed":
        err("hellenia_ui no instalado")

user = env["res.users"].search([("login", "=", IT_LOGIN)], limit=1)
if not user:
    err(f"Usuario {IT_LOGIN} no encontrado")
else:
    groups = user.groups_id
    sale_mgr = env.ref("sales_team.group_sale_manager", raise_if_not_found=False)
    grp_system = env.ref("base.group_system", raise_if_not_found=False)
    report["user"] = {
        "login": user.login,
        "groups": sorted(groups.mapped("full_name")),
        "has_sale_manager": bool(sale_mgr and sale_mgr in user.groups_id),
        "has_group_system": bool(grp_system and grp_system in user.groups_id),
    }
    if not report["user"]["has_sale_manager"]:
        err("it@justech.do sin grupo Administrador de Ventas")

Menu = env["ir.ui.menu"]
lang = "es_DO"

for menu in Menu.search([("parent_id", "=", False), ("active", "=", True)]):
    name = menu.with_context(lang=lang).name or menu.name
    xmlid = menu.get_external_id().get(menu.id, "")
    report["root_menus"].append(
        {"name": name, "xmlid": xmlid, "id": menu.id, "sequence": menu.sequence}
    )

report["root_menus"].sort(key=lambda m: (m["sequence"], m["name"]))

for label, xmlids in EXPECTED_ROOTS.items():
    found = False
    for xid in xmlids:
        menu = env.ref(xid, raise_if_not_found=False)
        if menu and menu.active:
            visible = not menu.group_ids or bool(menu.group_ids & user.groups_id)
            display = menu.with_context(lang=lang).name or menu.name
            report["expected_roots"][label] = {
                "xmlid": xid,
                "active": menu.active,
                "visible_to_it": visible,
                "display_name": display,
            }
            if visible and label == "Contabilidad" and display not in ("Contabilidad",):
                err(f"Menú contabilidad muestra '{display}', esperado Contabilidad")
            found = visible
            break
    if not found:
        err(f"Menú raíz esperado no visible: {label}")
        report["expected_roots"][label] = {"visible_to_it": False}

for label, xid in HIDDEN.items():
    menu = env.ref(xid, raise_if_not_found=False)
    if not menu:
        report["hidden_menus"][label] = {"status": "not_found"}
        continue
    visible = menu.active and (not menu.group_ids or bool(menu.group_ids & user.groups_id))
    report["hidden_menus"][label] = {"active": menu.active, "visible_to_it": visible}
    if visible:
        err(f"Menú debería estar oculto para IT: {label}")

sale_root = env.ref("sale.sale_menu_root", raise_if_not_found=False)
if sale_root and not sale_root.active:
    err("sale.sale_menu_root inactivo — instalar sale_management")

env.cr.commit()
print("HELLENIA_UI_MENU:" + json.dumps(report, ensure_ascii=False, default=str))
