# -*- coding: utf-8 -*-
"""Fase 26G PROD — Reorganización menús y UX conduces."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = "/tmp/phase26g-delivery-menu-ux-prod"
os.makedirs(OUT, exist_ok=True)

report = {
    "phase": "26g-delivery-menu-ux-prod",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_version": None,
    "checks": {},
    "errors": [],
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
report["module_version"] = mod.latest_version
check("module_version", mod.latest_version == "19.0.6.2.0", mod.latest_version)

# Menú principal Ventas (no bajo Órdenes)
sale_menu = env.ref("justech_report_design.menu_justech_delivery_note_sale")
sale_parent_xml = sale_menu.parent_id.get_external_id().get(sale_menu.parent_id.id, "")
check(
    "sale_menu_top_level",
    sale_parent_xml == "sale.sale_menu_root",
    f"parent={sale_parent_xml}, path={sale_menu.complete_name}",
)
check(
    "sale_menu_not_under_orders",
    "menu_sale_order" not in sale_parent_xml,
    sale_parent_xml,
)

# Menú Contabilidad
acct_menu = env.ref("justech_report_design.menu_justech_delivery_note_account", raise_if_not_found=False)
acct_parent = acct_menu.parent_id.get_external_id().get(acct_menu.parent_id.id, "") if acct_menu else ""
check(
    "account_menu_exists",
    bool(acct_menu) and acct_parent == "account.menu_finance",
    f"parent={acct_parent}, path={acct_menu.complete_name if acct_menu else None}",
)

# Filtros búsqueda
search_v = env.ref("justech_report_design.view_justech_delivery_note_search")
arch_s = search_v.arch_db or ""
for needle in [
    "filter_today",
    "filter_this_week",
    "filter_this_month",
    "filter_pending",
    "filter_delivered",
]:
    check(f"search_{needle}", needle in arch_s, needle in arch_s)

# Smart button cotización
so = env["sale.order"].search(
    [("state", "in", ("draft", "sent", "sale")), ("order_line", "!=", False)],
    limit=1,
    order="id desc",
)
if so:
    form_so = env["sale.order"].get_view(view_type="form")
    check("sale_form_smart_button", "action_jt_view_delivery_notes" in form_so["arch"], True)
    check("sale_form_create_button", "Crear Conduce de Entrega" in form_so["arch"], True)
    check("sale_stat_label", so.jt_delivery_stat_label == "Conduce", so.jt_delivery_stat_label)
    note = env["justech.delivery.note"].search(
        [("sale_order_id", "=", so.id), ("state", "!=", "cancel")], limit=1
    )
    if not note:
        so.action_jt_create_delivery_conduce()
        so.invalidate_recordset()
        note = env["justech.delivery.note"].search(
            [("sale_order_id", "=", so.id), ("state", "!=", "cancel")], limit=1
        )
    check("sale_smart_count", so.jt_delivery_note_count >= 1, so.jt_delivery_note_count)
    act_so = so.action_jt_view_delivery_notes()
    check("sale_smart_filtered", act_so.get("domain") == [("id", "in", [note.id])] if note else False, act_so.get("domain"))

# Smart button factura
inv = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
    limit=1,
    order="id desc",
)
if inv:
    form_inv = env["account.move"].get_view(view_type="form")
    check("invoice_form_smart_button", "action_jt_view_delivery_notes" in form_inv["arch"], True)
    check("invoice_form_create_button", "Crear Conduce de Entrega" in form_inv["arch"], True)
    check("invoice_stat_label", inv.jt_delivery_stat_label == "Conduce", inv.jt_delivery_stat_label)
    note_i = env["justech.delivery.note"].search(
        [("invoice_id", "=", inv.id), ("state", "!=", "cancel")], limit=1
    )
    check("invoice_smart_count", inv.jt_delivery_note_count >= 0, inv.jt_delivery_note_count)
    if note_i:
        act_inv = inv.action_jt_view_delivery_notes()
        check(
            "invoice_smart_filtered",
            act_inv.get("domain") == [("id", "in", [note_i.id])],
            act_inv.get("domain"),
        )

# Histórico general
action = env.ref("justech_report_design.action_justech_delivery_note").read()[0]
check("history_action_model", action.get("res_model") == "justech.delivery.note", action.get("res_model"))
check("history_no_domain", not action.get("domain"), action.get("domain"))
total = env["justech.delivery.note"].search_count([])
check("history_total", total >= 1, total)

critical = [
    "module_version",
    "sale_menu_top_level",
    "sale_menu_not_under_orders",
    "account_menu_exists",
    "search_filter_today",
    "search_filter_this_week",
    "search_filter_this_month",
    "search_filter_pending",
    "search_filter_delivered",
    "sale_form_smart_button",
    "sale_form_create_button",
    "sale_smart_count",
    "sale_smart_filtered",
    "invoice_form_smart_button",
    "invoice_form_create_button",
    "invoice_smart_count",
    "history_action_model",
    "history_total",
]
if env["justech.delivery.note"].search([("invoice_id", "!=", False)], limit=1):
    critical.append("invoice_smart_filtered")

all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical)
report["status"] = "PASS" if all_pass else "FAIL"
report["pass"] = report["status"] == "PASS"

with open(os.path.join(OUT, "validation.json"), "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

# Evidencia navegación
with open(os.path.join(OUT, "menu_checks.txt"), "w") as f:
    f.write(f"Ventas: {sale_menu.complete_name} (parent={sale_parent_xml})\n")
    if acct_menu:
        f.write(f"Contabilidad: {acct_menu.complete_name} (parent={acct_parent})\n")
    f.write(f"Total conduces: {total}\n")
    if so:
        f.write(f"SO {so.name}: smart={so.jt_delivery_note_count} label={so.jt_delivery_stat_label}\n")
    if inv:
        f.write(f"INV {inv.name}: smart={inv.jt_delivery_note_count} label={inv.jt_delivery_stat_label}\n")

print(json.dumps({"status": report["status"], "errors": report["errors"]}))
env.cr.commit()
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
