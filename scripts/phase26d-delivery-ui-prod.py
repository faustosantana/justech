# -*- coding: utf-8 -*-
"""Fase 26D PROD — Botón/contador Conduce + chatter (solo hellenia_prod)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = "/tmp/phase26d-delivery-ui-prod"
os.makedirs(OUT, exist_ok=True)

report = {
    "phase": "26d-delivery-ui-prod",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_version": None,
    "checks": {},
    "pdfs": [],
    "chatter": {},
    "views": {},
    "errors": [],
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


def save_pdf(name, data):
    path = os.path.join(OUT, name)
    with open(path, "wb") as f:
        f.write(data)
    report["pdfs"].append(name)
    return path


mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
report["module_version"] = mod.latest_version
check("module_version", mod.latest_version == "19.0.5.3.0", mod.latest_version)

View = env["ir.ui.view"]
for xmlid, model in [
    ("justech_report_design.view_order_form_jt_delivery_conduce", "sale.order"),
    ("justech_report_design.view_move_form_jt_delivery_conduce", "account.move"),
]:
    view = env.ref(xmlid, raise_if_not_found=False)
    arch = view.arch_db or "" if view else ""
    ok = (
        view
        and "action_jt_print_delivery_conduce" in arch
        and "action_jt_view_delivery_pickings" in arch
        and "jt_delivery_picking_count" in arch
    )
    check(f"view_{model.replace('.', '_')}", ok, xmlid)
    report["views"][xmlid] = {
        "model": model,
        "has_print_button": "action_jt_print_delivery_conduce" in arch,
        "has_stat_button": "action_jt_view_delivery_pickings" in arch,
    }

SaleOrder = env["sale.order"]
Move = env["account.move"]

so = SaleOrder.search([("state", "in", ("draft", "sent", "sale"))], limit=1, order="id desc")
inv = Move.search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
    limit=1,
    order="id desc",
)
picking = env["stock.picking"].search(
    [("picking_type_code", "=", "outgoing"), ("state", "in", ("assigned", "done"))],
    limit=1,
    order="id desc",
)

if so:
    check("sale_has_count_field", "jt_delivery_picking_count" in so._fields, so.jt_delivery_picking_count)
    check(
        "sale_stat_label",
        so.jt_delivery_stat_label in ("Conduce", "Conduces"),
        so.jt_delivery_stat_label,
    )
    msgs_before = env["mail.message"].search_count([
        ("model", "=", "sale.order"),
        ("res_id", "=", so.id),
    ])
    try:
        action = so.action_jt_print_delivery_conduce()
        check("sale_print_action", bool(action) and action.get("type") == "ir.actions.report", action.get("type"))
        pdf, _ = env["ir.actions.report"]._render_qweb_pdf(
            action.get("report_name"),
            action.get("res_ids") or [action.get("res_id")],
        )
        save_pdf("01_from_sale_button.pdf", pdf)
        check("sale_pdf_ok", pdf[:4] == b"%PDF", len(pdf))
    except Exception as exc:
        check("sale_print_action", False, str(exc))
    msgs_after = env["mail.message"].search_count([
        ("model", "=", "sale.order"),
        ("res_id", "=", so.id),
    ])
    last = env["mail.message"].search(
        [("model", "=", "sale.order"), ("res_id", "=", so.id)],
        order="id desc",
        limit=1,
    )
    body = (last.body or "") if last else ""
    check("sale_chatter_logged", msgs_after > msgs_before, msgs_after - msgs_before)
    check(
        "sale_chatter_text",
        "Conduce de Entrega" in body,
        body[:200],
    )
    report["chatter"]["sale"] = {"id": so.id, "name": so.name, "body_snippet": body[:300]}

if inv:
    check("invoice_has_count_field", "jt_delivery_picking_count" in inv._fields, inv.jt_delivery_picking_count)
    msgs_before = env["mail.message"].search_count([
        ("model", "=", "account.move"),
        ("res_id", "=", inv.id),
    ])
    try:
        action = inv.action_jt_print_delivery_conduce()
        check("invoice_print_action", bool(action) and action.get("type") == "ir.actions.report", action.get("type"))
        pdf, _ = env["ir.actions.report"]._render_qweb_pdf(
            action.get("report_name"),
            action.get("res_ids") or [action.get("res_id")],
        )
        save_pdf("02_from_invoice_button.pdf", pdf)
        check("invoice_pdf_ok", pdf[:4] == b"%PDF", len(pdf))
    except Exception as exc:
        check("invoice_print_action", False, str(exc))
    msgs_after = env["mail.message"].search_count([
        ("model", "=", "account.move"),
        ("res_id", "=", inv.id),
    ])
    last = env["mail.message"].search(
        [("model", "=", "account.move"), ("res_id", "=", inv.id)],
        order="id desc",
        limit=1,
    )
    body = (last.body or "") if last else ""
    check("invoice_chatter_logged", msgs_after > msgs_before, msgs_after - msgs_before)
    check("invoice_chatter_text", "Conduce de Entrega" in body, body[:200])
    report["chatter"]["invoice"] = {"id": inv.id, "name": inv.name, "body_snippet": body[:300]}

if picking:
    try:
        report_action = env.ref("stock.action_report_delivery")
        pdf, _ = report_action._render_qweb_pdf(report_action.report_name, picking.ids)
        save_pdf("03_from_picking_menu.pdf", pdf)
        check("picking_menu_print", pdf[:4] == b"%PDF", picking.name)
    except Exception as exc:
        check("picking_menu_print", False, str(exc))

# Regresión mínima
try:
    if so:
        pdf_q, _ = env["ir.actions.report"]._render_qweb_pdf(
            env.ref("sale.action_report_saleorder").report_name, so.ids
        )
        check("regression_quotation", pdf_q[:4] == b"%PDF", len(pdf_q))
    if inv:
        pdf_i, _ = env["ir.actions.report"]._render_qweb_pdf(
            env.ref("account.account_invoices").report_name, inv.ids
        )
        check("regression_invoice", pdf_i[:4] == b"%PDF", len(pdf_i))
except Exception as exc:
    check("regression_quotation", False, str(exc))

critical = [
    "module_version",
    "view_sale_order",
    "view_account_move",
    "sale_print_action",
    "sale_chatter_logged",
    "sale_chatter_text",
    "invoice_print_action",
    "invoice_chatter_logged",
    "invoice_chatter_text",
    "picking_menu_print",
    "regression_quotation",
    "regression_invoice",
]
all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical)
report["status"] = "PASS" if all_pass else "FAIL"
report["pass"] = report["status"] == "PASS"

with open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "version": report["module_version"], "errors": report["errors"]}))

if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
