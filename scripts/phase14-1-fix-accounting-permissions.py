#!/usr/bin/env python3
"""Fase 14.1 — Auditoría y corrección menús Contabilidad + permisos it@justech.do."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB not in ("hellenia_test", "hellenia_prod"):
    raise SystemExit(f"ABORT: solo hellenia_test o hellenia_prod, actual={DB}")

IT_LOGIN = "it@justech.do"
NORMAL_LOGIN = "usuario.normal.demo14"

REQUIRED_MODULES = (
    "account",
    "account_accountant",
    "account_reports",
    "sale_management",
    "purchase",
    "stock",
    "contacts",
    "hellenia_ui",
)

IT_GROUP_XMLIDS = (
    "base.group_system",
    "base.group_erp_manager",
    "account.group_account_manager",
    "sales_team.group_sale_manager",
    "purchase.group_purchase_manager",
    "stock.group_stock_manager",
    "base.group_no_one",
    "justech_l10n_do_base.group_justech_do_fiscal_manager",
)

EXPECTED_ROOTS_IT = ("Ventas", "Compras", "Inventario", "Contactos", "Contabilidad", "Configuración")

report = {
    "phase": "14.1",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "audit_before": {},
    "fixes": {},
    "validations": {},
    "ok": True,
    "errors": [],
}


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


def visible_roots(user):
    Menu = env["ir.ui.menu"].with_user(user)
    return Menu.search([("parent_id", "=", False), ("active", "=", True)]).sorted("sequence")


def audit_user(label, user):
    if not user:
        return {"found": False}
    finance = env.ref("account.menu_finance", raise_if_not_found=False)
    roots = visible_roots(user)
    root_names = roots.mapped("name")
    children = []
    if finance:
        children = env["ir.ui.menu"].with_user(user).search([("parent_id", "=", finance.id)]).mapped("name")
    return {
        "found": True,
        "login": user.login,
        "groups": sorted(user.group_ids.mapped("full_name")),
        "root_menus": root_names,
        "contabilidad_children": children,
        "contabilidad_children_count": len(children),
        "sees_contabilidad": finance and finance.id in roots.ids if finance else False,
        "duplicate_accounting_roots": [n for n in root_names if n.lower() in ("accounting", "facturación", "invoicing")],
    }


# --- Auditoría inicial ---
it_user = env["res.users"].search([("login", "=", IT_LOGIN)], limit=1)
admin = env.ref("base.user_admin")
normal = env["res.users"].search([("login", "=", NORMAL_LOGIN)], limit=1)

report["audit_before"]["it"] = audit_user("it", it_user)
report["audit_before"]["admin"] = audit_user("admin", admin)
report["audit_before"]["modules"] = {
    mod: env["ir.module.module"].search([("name", "=", mod)], limit=1).state
    for mod in REQUIRED_MODULES
}

finance = env.ref("account.menu_finance", raise_if_not_found=False)
if finance:
    db_children = env["ir.ui.menu"].search([("parent_id", "=", finance.id), ("active", "=", True)])
    report["audit_before"]["finance_menu"] = {
        "id": finance.id,
        "name": finance.name,
        "db_children_count": len(db_children),
        "db_children": db_children.mapped("name"),
    }

# --- Corrección hellenia_ui ---
ensure_mod = env["ir.module.module"].search([("name", "=", "hellenia_ui")], limit=1)
if ensure_mod and ensure_mod.state != "installed":
    ensure_mod.button_immediate_install()
    env.cr.commit()

customizer = env["hellenia.ui.menu.customizer"]
customizer.apply_menu_labels()
customizer.hide_unused_menus()
customizer.repair_accounting_menu_tree()
report["fixes"]["hellenia_ui_applied"] = True
env.cr.commit()

# --- Grupos it@justech.do ---
group_ids = []
for xid in IT_GROUP_XMLIDS:
    g = env.ref(xid, raise_if_not_found=False)
    if g:
        group_ids.append(g.id)
if it_user:
    it_user.write({"group_ids": [Command.set(group_ids)], "active": True})
    report["fixes"]["it_groups_updated"] = len(group_ids)
else:
    err(f"Usuario {IT_LOGIN} no encontrado")

# --- Usuario normal ficticio (solo ventas básicas) ---
sale_user = env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)
if not normal and sale_user:
    normal = env["res.users"].create(
        {
            "name": "Usuario Normal Demo 14.1",
            "login": NORMAL_LOGIN,
            "email": "normal.demo@hellenia.local",
            "group_ids": [Command.link(sale_user.id)],
        }
    )
    report["fixes"]["normal_user_created"] = True
elif normal:
    normal.write({"group_ids": [Command.set([sale_user.id])] if sale_user else []})
    report["fixes"]["normal_user_updated"] = True

env.cr.commit()

# --- Validaciones ---
it_user = env["res.users"].search([("login", "=", IT_LOGIN)], limit=1)
normal = env["res.users"].search([("login", "=", NORMAL_LOGIN)], limit=1)
report["validations"]["it"] = audit_user("it", it_user)
report["validations"]["admin"] = audit_user("admin", admin)
report["validations"]["normal"] = audit_user("normal", normal)

it_val = report["validations"]["it"]
report["validations"]["it_sees_contabilidad"] = it_val.get("sees_contabilidad") and it_val.get("contabilidad_children_count", 0) >= 5
report["validations"]["admin_sees_contabilidad"] = report["validations"]["admin"].get("contabilidad_children_count", 0) >= 5
report["validations"]["normal_no_contabilidad"] = not report["validations"]["normal"].get("sees_contabilidad", True)
report["validations"]["no_duplicate_accounting"] = not it_val.get("duplicate_accounting_roots")
report["validations"]["pos_hidden"] = not any(
    n.lower() in ("point of sale", "punto de venta") for n in it_val.get("root_menus", [])
)
report["validations"]["modules_installed"] = all(
    report["audit_before"]["modules"].get(m) == "installed" for m in REQUIRED_MODULES
)

for key in (
    "it_sees_contabilidad",
    "admin_sees_contabilidad",
    "normal_no_contabilidad",
    "no_duplicate_accounting",
    "pos_hidden",
    "modules_installed",
):
    if not report["validations"].get(key):
        err(f"validación fallida: {key}")

report["final_groups_it"] = sorted(it_user.group_ids.mapped("full_name")) if it_user else []
report["final_menus_it"] = it_val.get("root_menus", [])
report["final_contabilidad_children_it"] = it_val.get("contabilidad_children", [])

print("PHASE14_1:" + json.dumps(report, ensure_ascii=False, indent=2))
