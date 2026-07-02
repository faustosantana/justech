# -*- coding: utf-8 -*-
"""Fase 27 TEST — Validación Orden de Compra Hellenia."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT = "/tmp/phase27-purchase-order"
os.makedirs(OUT, exist_ok=True)

report = {
    "phase": "27-purchase-order-test",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_version": None,
    "checks": {},
    "errors": [],
    "pdfs": [],
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


def render_pdf(name, po):
    report_ref = env.ref("justech_report_design.action_report_justech_purchase_order")
    pdf, _ = env["ir.actions.report"]._render_qweb_pdf(report_ref.report_name, po.ids)
    path = os.path.join(OUT, name)
    open(path, "wb").write(pdf)
    report["pdfs"].append({"file": name, "bytes": len(pdf), "po": po.name})
    return pdf


mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
report["module_version"] = mod.latest_version
check("module_version", mod.latest_version == "19.0.7.0.0", mod.latest_version)

jt_report = env.ref("justech_report_design.action_report_justech_purchase_order", raise_if_not_found=False)
std_report = env.ref("purchase.action_report_purchase_order", raise_if_not_found=False)
check("hellenia_report_exists", bool(jt_report), jt_report.report_name if jt_report else "")
check(
    "parallel_not_same_template",
    jt_report and std_report and jt_report.report_name != std_report.report_name,
    f"jt={jt_report.report_name if jt_report else ''} std={std_report.report_name if std_report else ''}",
)
check(
    "print_menu_bound",
    bool(jt_report and jt_report.binding_model_id and jt_report.binding_type == "report"),
    jt_report.name if jt_report else "",
)

v = env.ref("justech_report_design.view_purchase_order_form_jt_po_report", raise_if_not_found=False)
arch = v.arch_db or "" if v else ""
check("header_button", "Orden de Compra PDF" in arch and "action_jt_print_purchase_order" in arch, True)

form = env["purchase.order"].get_view(view_type="form")
check("form_has_button", "action_jt_print_purchase_order" in form.get("arch", ""), True)

PO = env["purchase.order"]

# Escenarios desde datos existentes
scenarios = []

one_line = PO.search([("order_line", "!=", False)], limit=1, order="id desc")
if one_line and len(one_line.order_line.filtered(lambda l: not l.display_type)) == 1:
    scenarios.append(("01_one_line", one_line))

multi = PO.search([], order="id desc")
for po in multi:
    cnt = len(po.order_line.filtered(lambda l: not l.display_type and l.product_id))
    if cnt >= 5:
        scenarios.append(("02_five_lines", po))
        break

for po in multi:
    cnt = len(po.order_line.filtered(lambda l: not l.display_type and l.product_id))
    if cnt >= 10:
        scenarios.append(("03_many_lines", po))
        break

with_disc = PO.search([], order="id desc")
for po in with_disc:
    lines = po.order_line.filtered(lambda l: not l.display_type and l.product_id)
    if any((l.discount or 0) > 0 for l in lines):
        scenarios.append(("04_with_discount", po))
        break

no_disc = PO.search([], order="id desc")
for po in no_disc:
    lines = po.order_line.filtered(lambda l: not l.display_type and l.product_id)
    if lines and not any((l.discount or 0) > 0 for l in lines):
        scenarios.append(("05_no_discount", po))
        break

usd = PO.search([("currency_id.name", "=", "USD")], limit=1, order="id desc")
if usd:
    scenarios.append(("06_usd", usd))

dop = PO.search([("currency_id.name", "=", "DOP")], limit=1, order="id desc")
if dop:
    scenarios.append(("07_dop", dop))

for po in multi:
    if po.partner_id.country_id and po.partner_id.country_id.code != "DO":
        scenarios.append(("08_international_vendor", po))
        break

for po in multi:
    if not po.partner_id.country_id or po.partner_id.country_id.code == "DO":
        scenarios.append(("09_national_vendor", po))
        break

if not scenarios and one_line:
    scenarios.append(("01_one_line", one_line))

for fname, po in scenarios:
    try:
        pdf = render_pdf(f"{fname}.pdf", po)
        check(f"pdf_{fname}", pdf[:4] == b"%PDF" and len(pdf) > 500, len(pdf))
    except Exception as e:
        check(f"pdf_{fname}", False, str(e))

# Vista previa HTML (sin error QWeb)
try:
    html, _ = env["ir.actions.report"]._render_qweb_html(
        jt_report.report_name, (scenarios[0][1].ids if scenarios else one_line.ids)
    )
    check("html_preview", bool(html) and b"ORDEN DE COMPRA" in html, len(html) if html else 0)
except Exception as e:
    check("html_preview", False, str(e))

# Reporte estándar sigue funcionando
if std_report and one_line:
    try:
        std_pdf, _ = env["ir.actions.report"]._render_qweb_pdf(std_report.report_name, one_line.ids)
        check("standard_report_ok", std_pdf[:4] == b"%PDF", len(std_pdf))
    except Exception as e:
        check("standard_report_ok", False, str(e))

# Botón objeto
if one_line:
    act = one_line.action_jt_print_purchase_order()
    check("button_action", act.get("type") == "ir.actions.report", act.get("report_name", act))

critical = [
    "module_version",
    "hellenia_report_exists",
    "parallel_not_same_template",
    "print_menu_bound",
    "header_button",
    "form_has_button",
    "html_preview",
    "standard_report_ok",
    "button_action",
]
critical += [k for k in report["checks"] if k.startswith("pdf_")]

all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical if k in report["checks"])
report["status"] = "PASS" if all_pass else "FAIL"
report["pass"] = report["status"] == "PASS"

with open(os.path.join(OUT, "validation.json"), "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "errors": report["errors"], "pdfs": len(report["pdfs"])}))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
