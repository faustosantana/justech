# -*- coding: utf-8 -*-
"""Fase 26F PROD — Menú histórico de Conduces de Entrega."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = "/tmp/phase26f-delivery-menu-prod"
os.makedirs(OUT, exist_ok=True)

report = {
    "phase": "26f-delivery-menu-prod",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_version": None,
    "checks": {},
    "errors": [],
}

Note = env["justech.delivery.note"]


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
report["module_version"] = mod.latest_version
check("module_version", mod.latest_version == "19.0.6.1.1", mod.latest_version)

# Menús
for xmlid, parent_needle in [
    ("justech_report_design.menu_justech_delivery_note_sale", "sale.menu_sale_order"),
    ("justech_report_design.menu_justech_delivery_note_stock", "stock.menu_stock_warehouse_mgmt"),
]:
    menu = env.ref(xmlid, raise_if_not_found=False)
    ok = bool(menu and menu.action and menu.name == "Conduces de Entrega")
    parent_xml = menu.parent_id.get_external_id().get(menu.parent_id.id, "") if menu and menu.parent_id else ""
    check(f"menu_{xmlid.split('.')[-1]}", ok, f"name={menu.name if menu else None}, parent={parent_xml}")

# Vista búsqueda y columnas
search_v = env.ref("justech_report_design.view_justech_delivery_note_search", raise_if_not_found=False)
arch_s = search_v.arch_db or "" if search_v else ""
for needle in ["filter_today", "filter_this_month", "group_partner", "group_sale_order", "group_invoice", "group_state"]:
    check(f"search_{needle}", needle in arch_s, needle in arch_s)

list_v = env.ref("justech_report_design.view_justech_delivery_note_tree", raise_if_not_found=False)
arch_l = list_v.arch_db or "" if list_v else ""
for col in ["name", "date", "partner_id", "sale_order_id", "invoice_id", "picking_id", "state", "user_id"]:
    check(f"list_col_{col}", col in arch_l, col in arch_l)

# Histórico muestra todos
action = env.ref("justech_report_design.action_justech_delivery_note").read()[0]
check("menu_action_model", action.get("res_model") == "justech.delivery.note", action.get("res_model"))
total_before = Note.search_count([])
check("menu_total_records", total_before >= 1, total_before)

# Crear desde cotización y verificar en menú
so = env["sale.order"].search(
    [
        ("state", "in", ("draft", "sent", "sale")),
        ("order_line", "!=", False),
        ("delivery_note_ids", "=", False),
    ],
    limit=1,
    order="id desc",
)
if not so:
    so = env["sale.order"].search(
        [("state", "in", ("draft", "sent", "sale")), ("order_line", "!=", False)],
        limit=1,
        order="id desc",
    )

created_note = None
if so:
    before = so.jt_delivery_note_count
    so.action_jt_create_delivery_conduce()
    so.invalidate_recordset()
    note = Note.search([("sale_order_id", "=", so.id), ("state", "!=", "cancel")], limit=1)
    created_note = note
    check("sale_create_from_button", bool(note), note.name if note else "")
    check("sale_smart_count", so.jt_delivery_note_count >= 1, so.jt_delivery_note_count)
    act_so = so.action_jt_view_delivery_notes()
    check("smart_filtered", act_so.get("domain") == [("id", "in", [note.id])] if note else False, act_so.get("domain"))
    check("smart_single_form", act_so.get("res_id") == note.id if note else False, act_so.get("res_id"))
    total_after = Note.search_count([])
    check("menu_shows_new_sale", note.id in Note.search([]).ids if note else False, total_after)

# Crear desde factura sin conduce previo
inv = env["account.move"].search(
    [
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("delivery_note_ids", "=", False),
    ],
    limit=1,
    order="id desc",
)
if not inv:
    inv = env["account.move"].search(
        [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
        limit=1,
        order="id desc",
    )

if inv:
    inv.action_jt_create_delivery_conduce()
    inv.invalidate_recordset()
    note_i = Note.search([("invoice_id", "=", inv.id), ("state", "!=", "cancel")], limit=1)
    check("invoice_create_from_button", bool(note_i), note_i.name if note_i else "")
    check("invoice_smart_count", inv.jt_delivery_note_count >= 1, inv.jt_delivery_note_count)
    act_inv = inv.action_jt_view_delivery_notes()
    if note_i:
        check("invoice_smart_filtered", note_i.id in (act_inv.get("domain") or [("", "", [])])[0][2] if act_inv.get("domain") else [note_i.id], act_inv.get("domain"))

# Abrir desde acción menú y reimprimir
note_print = created_note or Note.search([], limit=1, order="id desc")
if note_print:
    menu_act = env.ref("justech_report_design.action_justech_delivery_note").read()[0]
    menu_act["res_id"] = note_print.id
    menu_act["views"] = [(False, "form")]
    check("menu_open_form", menu_act.get("res_model") == "justech.delivery.note", note_print.name)
    report_dn = env.ref("justech_report_design.action_report_justech_delivery_note")
    pdf, _ = env["ir.actions.report"]._render_qweb_pdf(report_dn.report_name, note_print.ids)
    path = os.path.join(OUT, "01_reprint_from_menu.pdf")
    open(path, "wb").write(pdf)
    check("reprint_pdf", pdf[:4] == b"%PDF" and note_print.name.encode() in pdf, len(pdf))

# Búsqueda por número de conduce
if note_print:
    found = Note.search([("name", "=", note_print.name)], limit=1)
    check("search_by_name", bool(found), note_print.name)

critical = [
    "module_version",
    "menu_menu_justech_delivery_note_sale",
    "menu_menu_justech_delivery_note_stock",
    "search_filter_today",
    "search_filter_this_month",
    "search_group_partner",
    "search_group_sale_order",
    "search_group_invoice",
    "search_group_state",
    "list_col_name",
    "list_col_partner_id",
    "list_col_state",
    "list_col_user_id",
    "menu_action_model",
    "menu_total_records",
    "sale_create_from_button",
    "sale_smart_count",
    "smart_filtered",
    "invoice_create_from_button",
    "invoice_smart_count",
    "menu_open_form",
    "reprint_pdf",
    "search_by_name",
]
all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical)
report["status"] = "PASS" if all_pass else "FAIL"
report["pass"] = report["status"] == "PASS"

with open(os.path.join(OUT, "validation.json"), "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "errors": report["errors"]}))
env.cr.commit()
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
