#!/usr/bin/env python3
"""Fase 15 — Auditoría completa de menús, navegación y localización Justech."""
from __future__ import annotations

import json
from datetime import datetime, timezone

DB = env.cr.dbname
if DB not in ("hellenia_test", "hellenia_prod"):
    raise SystemExit(f"ABORT: solo hellenia_test o hellenia_prod, actual={DB}")

USERS = {
    "it": "it@justech.do",
    "admin": "admin",
    "normal": "usuario.normal.demo14",
}

JUSTECH_MENUS = (
    "justech_l10n_do_base.menu_justech_do_fiscal_root",
    "justech_l10n_do_base.menu_justech_do_document_types",
    "justech_l10n_do_ncf.menu_justech_do_ncf_ranges",
    "justech_l10n_do_reports.menu_justech_do_reports_root",
    "justech_l10n_do_reports.menu_justech_do_report_606",
    "justech_l10n_do_reports.menu_justech_do_audit_root",
)

report = {
    "phase": "15",
    "block": "audit",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "menu_tree": {},
    "issues": [],
    "users": {},
    "modules": {},
    "ok": True,
}


def issue(msg: str) -> None:
    report["ok"] = False
    report["issues"].append(msg)


def menu_xid(menu):
    data = env["ir.model.data"].search([("model", "=", "ir.ui.menu"), ("res_id", "=", menu.id)], limit=1)
    return f"{data.module}.{data.name}" if data else None


def audit_user(key, login):
    user = env["res.users"].search([("login", "=", login)], limit=1) if login != "admin" else env.ref("base.user_admin")
    if not user:
        return {"found": False}
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
    justech_visible = []
    for xid in JUSTECH_MENUS:
        m = env.ref(xid, raise_if_not_found=False)
        if m and m.id in visible:
            justech_visible.append(m.name)
    return {
        "found": True,
        "login": user.login,
        "groups": sorted(user.group_ids.mapped("full_name")),
        "root_menus": roots.mapped("name"),
        "sees_contabilidad": bool(finance and finance.id in visible),
        "contabilidad_children": children,
        "first_contabilidad_child": first_child,
        "justech_menus_visible": justech_visible,
        "sees_apps": bool(env.ref("base.menu_management", raise_if_not_found=False).id in visible),
    }


# Módulos requeridos
for mod in (
    "account", "account_accountant", "account_reports", "sale_management", "purchase",
    "stock", "contacts", "hellenia_ui", "justech_l10n_do_base", "justech_l10n_do_ncf",
    "justech_l10n_do_reports",
):
    rec = env["ir.module.module"].search([("name", "=", mod)], limit=1)
    report["modules"][mod] = rec.state if rec else "missing"

finance = env.ref("account.menu_finance", raise_if_not_found=False)
if finance:
    db_children = env["ir.ui.menu"].search([("parent_id", "=", finance.id), ("active", "=", True)]).sorted("sequence")
    report["menu_tree"]["finance_root"] = {
        "id": finance.id,
        "name": finance.name,
        "action": finance.action.name if finance.action else None,
        "children": [(c.name, c.sequence, menu_xid(c)) for c in db_children],
    }
    first = db_children[0] if db_children else None
    if first and first.name in ("Settings", "Ajustes"):
        issue(f"Contabilidad abre Ajustes: primer hijo={first.name} (seq={first.sequence})")
    elif first and first.name not in ("Dashboard", "Tablero"):
        issue(f"Contabilidad no abre tablero: primer hijo={first.name}")

    dup_names = [n for n in db_children.mapped("name") if db_children.mapped("name").count(n) > 1]
    if dup_names:
        issue(f"Submenús duplicados bajo Contabilidad: {sorted(set(dup_names))}")

# Raíces duplicadas contabilidad
admin = env.ref("base.user_admin")
roots_all = env["ir.ui.menu"].search([("parent_id", "=", False), ("active", "=", True)])
dup_roots = roots_all.filtered(
    lambda m: m.name.lower() in ("accounting", "contabilidad", "facturación", "invoicing")
)
if len(dup_roots) > 1:
    issue(f"Raíces contables duplicadas: {dup_roots.mapped('name')}")

# Menús huérfanos
orphans = env["ir.ui.menu"].search(
    [
        ("parent_id", "=", False),
        ("active", "=", True),
        ("name", "in", ["Accounting", "Facturación", "Invoicing"]),
    ]
)
if orphans:
    issue(f"Menús huérfanos activos: {orphans.mapped('name')}")

# Settings como hijo directo de finance
if finance:
    settings = env.ref("account.menu_account_config", raise_if_not_found=False)
    if settings and settings.parent_id == finance:
        issue("account.menu_account_config es hijo directo de Contabilidad (abre Ajustes)")

# Usuarios
for key, login in USERS.items():
    report["users"][key] = audit_user(key, login)

it = report["users"].get("it", {})
if it.get("found") and not it.get("sees_contabilidad"):
    issue("it@justech.do no ve Contabilidad")
if it.get("found") and not it.get("justech_menus_visible"):
    issue("it@justech.do no ve menús Justech")

normal = report["users"].get("normal", {})
if normal.get("found") and normal.get("sees_contabilidad"):
    issue("usuario normal ve Contabilidad sin permisos")

print("PHASE15_AUDIT:" + json.dumps(report, ensure_ascii=False, indent=2))
