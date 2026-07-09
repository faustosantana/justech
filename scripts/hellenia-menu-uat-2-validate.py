# -*- coding: utf-8 -*-
"""HELLENIA-MENU-UAT-2 — Validación navegación contable + data UAT."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = os.environ.get("HELLENIA_MENU_UAT2_EVIDENCE", "/tmp/hellenia-menu-uat-2")
os.makedirs(OUT, exist_ok=True)
TAG = "UAT-MENU-"

report = {
    "phase": "HELLENIA-MENU-UAT-2",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "finance_children": [],
    "checks": {},
    "uat_records": {},
    "issues": [],
    "ok": True,
    "pass": False,
}


def issue(msg):
    report["ok"] = False
    report["issues"].append(msg)


def menu_xid(menu):
    d = env["ir.model.data"].search([("model", "=", "ir.ui.menu"), ("res_id", "=", menu.id)], limit=1)
    return f"{d.module}.{d.name}" if d else None


def check_menu(xid, key, must_active=True, parent_xid=None, not_at_root=False):
    m = env.ref(xid, raise_if_not_found=False)
    state = {"exists": bool(m), "active": bool(m and m.active), "name": m.name if m else None}
    if not m:
        issue(f"Menú ausente: {xid}")
        report["checks"][key] = state
        return
    if must_active and not m.active:
        issue(f"Menú inactivo: {xid}")
    if parent_xid:
        p = env.ref(parent_xid, raise_if_not_found=False)
        state["parent_ok"] = bool(p and m.parent_id == p)
        if p and m.parent_id != p:
            issue(f"Parent incorrecto {xid}: {m.parent_id.name} != {parent_xid}")
    if not_at_root:
        finance = env.ref("account.menu_finance")
        state["at_finance_root"] = m.parent_id.id == finance.id
        if m.parent_id.id == finance.id:
            issue(f"Duplicado en raíz Contabilidad: {xid}")
    if m.action:
        try:
            m.action._get_action_dict()
            state["action_ok"] = True
        except Exception as exc:
            state["action_ok"] = False
            issue(f"Acción rota {xid}: {exc}")
    report["checks"][key] = state


finance = env.ref("account.menu_finance")
for c in env["ir.ui.menu"].search([("parent_id", "=", finance.id)], order="sequence"):
    report["finance_children"].append(
        {"name": c.name, "xid": menu_xid(c), "active": c.active, "sequence": c.sequence}
    )

# Raíz esperada
expected_root = [
    "Tablero", "Clientes", "Proveedores", "Pagos", "Contabilidad",
    "Revisión", "Reportes", "Auditoría Fiscal", "Configuración",
]
root_names = [c["name"] for c in report["finance_children"] if c["active"]]
for name in expected_root:
    if name not in root_names:
        issue(f"Falta en raíz Contabilidad: {name}")

# Duplicados raíz
for xid in ("account.menu_action_move_journal_line_form", "account.menu_action_account_moves_all"):
    check_menu(xid, f"no_root_{xid.split('.')[-1]}", not_at_root=True)

check_menu("account.menu_finance_entries", "contabilidad_hub", parent_xid=None)
check_menu("account.menu_action_move_journal_line_form", "asientos", parent_xid="account.menu_finance_entries")
check_menu("account.menu_action_account_moves_all", "apuntes", parent_xid="account.menu_finance_entries")
check_menu("hellenia_ui.menu_finance_payments_root", "pagos_hub")
check_menu("hellenia_ui.menu_finance_bank_reconciliation", "bank_reconciliation")
check_menu("account_accountant.menu_account_reconcile", "reconcile_apuntes", parent_xid="account.menu_finance_entries")
check_menu("justech_l10n_do_reports.menu_justech_do_audit_root", "auditoria_fiscal")
check_menu("justech_l10n_do_treasury.menu_treasury_open_payments_customer", "open_pay_customer")
check_menu("hellenia_account.menu_hellenia_withholding_catalog", "retenciones")

# UAT data
report["uat_records"] = {
    "partners": env["res.partner"].search_count([("name", "ilike", TAG)]),
    "payments": env["account.payment"].search_count([("name", "ilike", TAG)]),
    "moves": env["account.move"].search_count([("ref", "ilike", TAG)]),
    "products": env["product.product"].search_count([("name", "ilike", TAG)]),
}
if report["uat_records"]["moves"] < 5:
    issue(f"Data UAT insuficiente: moves={report['uat_records']['moves']}")

report["pass"] = report["ok"]
with open(os.path.join(OUT, "VALIDATION.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print("HELLENIA_MENU_UAT2:" + json.dumps(report, ensure_ascii=False, indent=2))
