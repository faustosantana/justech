# -*- coding: utf-8 -*-
"""Fase 26E PROD — Conduce como registro justech.delivery.note."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = "/tmp/phase26e-delivery-note-prod"
os.makedirs(OUT, exist_ok=True)

report = {
    "phase": "26e-delivery-note-prod",
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
check("module_version", mod.latest_version == "19.0.6.0.2", mod.latest_version)

# Vistas botón
for xmlid, needle in [
    ("justech_report_design.view_order_form_jt_delivery_conduce", "Crear Conduce de Entrega"),
    ("justech_report_design.view_move_form_jt_delivery_conduce", "Crear Conduce de Entrega"),
]:
    v = env.ref(xmlid, raise_if_not_found=False)
    arch = v.arch_db or "" if v else ""
    check(f"view_{xmlid.split('.')[-1]}", needle in arch and "jt_delivery_note_count" in arch, needle in arch)

so = env["sale.order"].search([("state", "in", ("draft", "sent", "sale"))], limit=1, order="id desc")
inv = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted")], limit=1, order="id desc"
)
picking = env["stock.picking"].search(
    [("picking_type_code", "=", "outgoing"), ("state", "in", ("assigned", "done"))],
    limit=1,
    order="id desc",
)

if so:
    before = so.jt_delivery_note_count
    msgs_before = env["mail.message"].search_count([("model", "=", "sale.order"), ("res_id", "=", so.id)])
    action = so.action_jt_create_delivery_conduce()
    so.invalidate_recordset()
    check("sale_count_after_create", so.jt_delivery_note_count >= 1, so.jt_delivery_note_count)
    note = Note.search([("sale_order_id", "=", so.id), ("state", "!=", "cancel")], limit=1)
    check("sale_note_record", bool(note), note.name if note else "missing")
    check("sale_note_sequence", bool(note and note.name.startswith("COND/")), note.name if note else "")
    check("sale_note_lines", bool(note and note.line_ids), len(note.line_ids) if note else 0)
    pdf, _ = env["ir.actions.report"]._render_qweb_pdf(
        "justech_report_design.report_justech_delivery_document", note.ids
    )
    path = os.path.join(OUT, "01_from_sale_button.pdf")
    open(path, "wb").write(pdf)
    check("sale_pdf", pdf[:4] == b"%PDF", len(pdf))
    msgs_after = env["mail.message"].search_count([("model", "=", "sale.order"), ("res_id", "=", so.id)])
    check("sale_chatter", msgs_after > msgs_before, msgs_after - msgs_before)
    # sin duplicado
    count2 = so.jt_delivery_note_count
    note2, created2 = so._jt_get_or_create_delivery_note()
    check("sale_no_duplicate", not created2 and note2.id == note.id, created2)
    check("sale_count_stable", count2 == so.jt_delivery_note_count, count2)
    act_list = so.action_jt_view_delivery_notes()
    check("sale_smart_action", act_list.get("res_model") == "justech.delivery.note", act_list.get("res_model"))

if inv:
    before = inv.jt_delivery_note_count
    inv.action_jt_create_delivery_conduce()
    inv.invalidate_recordset()
    check("invoice_count_after", inv.jt_delivery_note_count >= 1, inv.jt_delivery_note_count)
    note_i = Note.search([("invoice_id", "=", inv.id), ("state", "!=", "cancel")], limit=1)
    check("invoice_note_record", bool(note_i), note_i.name if note_i else "")
    pdf, _ = env["ir.actions.report"]._render_qweb_pdf(
        "justech_report_design.report_justech_delivery_document", note_i.ids
    )
    open(os.path.join(OUT, "02_from_invoice_button.pdf"), "wb").write(pdf)
    check("invoice_pdf", pdf[:4] == b"%PDF", len(pdf))

if picking:
    note_p, _ = picking._jt_get_or_create_delivery_note()
    pdf, _ = env.ref("stock.action_report_delivery")._render_qweb_pdf(
        env.ref("stock.action_report_delivery").report_name, picking.ids
    )
    open(os.path.join(OUT, "03_from_picking.pdf"), "wb").write(pdf)
    check("picking_pdf", pdf[:4] == b"%PDF", picking.name)
    check("picking_note_linked", bool(note_p and note_p.picking_id == picking), note_p.name if note_p else "")

# Regresión
if so:
    pdf_q, _ = env["ir.actions.report"]._render_qweb_pdf(
        env.ref("sale.action_report_saleorder").report_name, so.ids
    )
    check("regression_quotation", pdf_q[:4] == b"%PDF", len(pdf_q))
if inv:
    pdf_f, _ = env["ir.actions.report"]._render_qweb_pdf(
        env.ref("account.account_invoices").report_name, inv.ids
    )
    check("regression_invoice", pdf_f[:4] == b"%PDF", len(pdf_f))

critical = [
    "module_version",
    "view_view_order_form_jt_delivery_conduce",
    "view_view_move_form_jt_delivery_conduce",
    "sale_count_after_create",
    "sale_note_record",
    "sale_note_sequence",
    "sale_pdf",
    "sale_chatter",
    "sale_no_duplicate",
    "invoice_count_after",
    "invoice_note_record",
    "invoice_pdf",
    "picking_pdf",
    "picking_note_linked",
]
all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical)
report["status"] = "PASS" if all_pass else "FAIL"
report["pass"] = report["status"] == "PASS"

with open(os.path.join(OUT, "validation.json"), "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "errors": report["errors"]}))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
