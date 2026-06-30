#!/usr/bin/env python3
"""Fase 15 — Validación menús y smoke funcional en PROD (misma lógica que TEST)."""
# Copia de phase15-validate-test.py con DB prod
from __future__ import annotations

import json
from datetime import datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

IT_LOGIN = "it@justech.do"
USERS = {
    "it": IT_LOGIN,
    "admin": "admin",
    "accounting": "usuario.contabilidad.demo15",
    "sales": "usuario.ventas.demo15",
    "purchase": "usuario.compras.demo15",
    "inventory": "usuario.inventario.demo15",
    "normal": "usuario.normal.demo14",
}

ROLE_GROUPS = {
    "it": (
        "base.group_system", "base.group_erp_manager", "account.group_account_manager",
        "sales_team.group_sale_manager", "purchase.group_purchase_manager",
        "stock.group_stock_manager", "base.group_no_one",
        "justech_l10n_do_base.group_justech_do_fiscal_manager",
    ),
    "accounting": ("account.group_account_user", "justech_l10n_do_base.group_justech_do_fiscal_user"),
    "sales": ("sales_team.group_sale_salesman",),
    "purchase": ("purchase.group_purchase_user",),
    "inventory": ("stock.group_stock_user",),
    "normal": ("sales_team.group_sale_salesman",),
}

JUSTECH_MENUS_IT = (
    "justech_l10n_do_base.menu_justech_do_fiscal_root",
    "justech_l10n_do_reports.menu_justech_do_reports_root",
    "justech_l10n_do_reports.menu_justech_do_audit_root",
)

report = {
    "phase": "15",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "fixes": {},
    "validations": {},
    "functional": {},
    "ok": True,
    "errors": [],
}


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


def visible_menu_audit(user):
    Menu = env["ir.ui.menu"].with_user(user)
    visible = set(Menu._visible_menu_ids())
    finance = env.ref("account.menu_finance", raise_if_not_found=False)
    roots = Menu.search([("parent_id", "=", False), ("active", "=", True)]).filtered(
        lambda m: m.id in visible
    ).sorted("sequence")
    children = []
    first_child = None
    if finance and finance.id in visible:
        ch = Menu.search([("parent_id", "=", finance.id), ("active", "=", True)]).filtered(
            lambda m: m.id in visible
        ).sorted("sequence")
        children = ch.mapped("name")
        first_child = ch[0].name if ch else None
    justech = []
    for xid in JUSTECH_MENUS_IT:
        m = env.ref(xid, raise_if_not_found=False)
        if m and m.id in visible:
            justech.append(m.name)
    dup_roots = [n for n in roots.mapped("name") if n.lower() in ("facturación", "accounting", "invoicing")]
    return {
        "login": user.login,
        "groups": sorted(user.group_ids.mapped("full_name")),
        "root_menus": roots.mapped("name"),
        "sees_contabilidad": bool(finance and finance.id in visible),
        "contabilidad_children": children,
        "first_contabilidad_child": first_child,
        "finance_opens_settings": first_child in ("Settings", "Ajustes"),
        "finance_opens_dashboard": first_child in ("Dashboard", "Tablero"),
        "duplicate_accounting_roots": dup_roots,
        "justech_menus": justech,
        "sees_apps": bool(env.ref("base.menu_management", raise_if_not_found=False).id in visible),
    }


def ensure_user(login, name, group_xmlids):
    groups = [env.ref(x, raise_if_not_found=False) for x in group_xmlids]
    groups = [g for g in groups if g]
    user = env["res.users"].search([("login", "=", login)], limit=1)
    vals = {
        "name": name,
        "login": login,
        "email": f"{login.split('@')[0]}@hellenia.local",
        "group_ids": [Command.set([g.id for g in groups])],
    }
    if user:
        user.write(vals)
    else:
        user = env["res.users"].create(vals)
    return user


for mod in ("hellenia_ui", "justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports"):
    rec = env["ir.module.module"].search([("name", "=", mod)], limit=1)
    if rec and rec.state == "installed":
        rec.button_immediate_upgrade()
        env.cr.commit()

env["hellenia.ui.menu.customizer"].apply_all()
report["fixes"]["menu_customizer"] = True
env.cr.commit()

ensure_user(IT_LOGIN, "IT Justech", ROLE_GROUPS["it"])
for key in ("accounting", "sales", "purchase", "inventory", "normal"):
    ensure_user(USERS[key], f"Demo 15 {key}", ROLE_GROUPS[key])
env.cr.commit()

admin = env.ref("base.user_admin")
for key, login in USERS.items():
    user = env["res.users"].search([("login", "=", login)], limit=1) if login != "admin" else admin
    if user:
        report["validations"][key] = visible_menu_audit(user)

v = report["validations"]
expected_roots = ("Ventas", "Compras", "Inventario", "Contabilidad", "Contactos", "Configuración")
it_roots = set(v.get("it", {}).get("root_menus", []))
checks = {
    "it_sees_contabilidad": v.get("it", {}).get("sees_contabilidad"),
    "it_dashboard_not_settings": not v.get("it", {}).get("finance_opens_settings"),
    "it_dashboard_first": v.get("it", {}).get("finance_opens_dashboard"),
    "it_justech_menus": len(v.get("it", {}).get("justech_menus", [])) >= 3,
    "it_no_duplicate_roots": not v.get("it", {}).get("duplicate_accounting_roots"),
    "admin_sees_contabilidad": v.get("admin", {}).get("sees_contabilidad"),
    "normal_no_contabilidad": not v.get("normal", {}).get("sees_contabilidad"),
    "accounting_sees_justech": len(v.get("accounting", {}).get("justech_menus", [])) >= 2,
    "sales_no_contabilidad": not v.get("sales", {}).get("sees_contabilidad"),
    "normal_no_apps": not v.get("normal", {}).get("sees_apps"),
    "it_sees_apps": v.get("it", {}).get("sees_apps"),
    "it_has_core_modules": all(r in it_roots for r in expected_roots),
}
report["validations"]["checks"] = checks
for name, ok in checks.items():
    if not ok:
        err(f"validación menú fallida: {name}")

func = {}
company = env.company
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
partner = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
try:
    so = env["sale.order"].create({"partner_id": partner.id})
    env["sale.order.line"].create({"order_id": so.id, "product_id": product.id, "product_uom_qty": 1})
    func["sale_quotation"] = so.state == "draft"
except Exception as exc:  # noqa: BLE001
    func["sale_quotation"] = False
    err(f"ventas: {exc}")

try:
    vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
    po = env["purchase.order"].create({"partner_id": vendor.id})
    env["purchase.order.line"].create({"order_id": po.id, "product_id": product.id, "product_qty": 1, "price_unit": 100})
    func["purchase_rfq"] = po.state == "draft"
except Exception as exc:  # noqa: BLE001
    func["purchase_rfq"] = False
    err(f"compras: {exc}")

func["inventory_product"] = bool(product)
func["accounting_journal"] = bool(env["account.journal"].search([("type", "=", "sale")], limit=1))
func["justech_doc_types"] = env["justech.do.fiscal.document.type"].search_count([]) >= 5
func["justech_ncf_ranges"] = env["justech.do.ncf.range"].search_count([]) >= 1
func["justech_reports_wizard"] = "justech.do.fiscal.report.wizard" in env
func["modules_ok"] = all(
    env["ir.module.module"].search([("name", "=", m)], limit=1).state == "installed"
    for m in ("account", "sale_management", "purchase", "stock", "justech_l10n_do_reports", "hellenia_ui")
)
report["functional"] = func
for name, ok in func.items():
    if not ok:
        err(f"smoke funcional fallido: {name}")

report["final_menus_by_user"] = {k: val.get("root_menus", []) for k, val in v.items() if isinstance(val, dict) and "root_menus" in val}
report["final_groups_it"] = v.get("it", {}).get("groups", [])
report["final_contabilidad_it"] = {
    "children": v.get("it", {}).get("contabilidad_children", []),
    "first_child": v.get("it", {}).get("first_contabilidad_child"),
    "justech": v.get("it", {}).get("justech_menus", []),
}

print("PHASE15_VALIDATE:" + json.dumps(report, ensure_ascii=False, indent=2))
