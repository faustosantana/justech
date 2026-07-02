# -*- coding: utf-8 -*-
"""Fase 27A PROD — Orden de Compra oficial Justech (solo hellenia_prod)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT_DIR = "/tmp/phase27a-purchase-order-official-prod"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_JT = "justech_report_design.report_justech_purchase_order_document"
MAIN_ACTION = "purchase.action_report_purchase_order"

report = {
    "phase": "27a-purchase-order-official-prod",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_version": None,
    "checks": {},
    "pdfs": {},
    "ui": {},
    "errors": [],
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


def pdf_ok(data):
    return data and data[:4] == b"%PDF"


def to_png(pdf_path, base):
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf_path, base],
            check=True,
            timeout=90,
        )
        return True
    except Exception:
        return False


mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
try:
    env["ir.qweb"].clear_caches()
except Exception:
    pass
env.cr.commit()
report["module_version"] = mod.latest_version

Report = env["ir.actions.report"]
PO = env["purchase.order"]

main_action = env.ref(MAIN_ACTION)
parallel = env.ref("justech_report_design.action_report_justech_purchase_order", raise_if_not_found=False)
backup = env.ref("justech_report_design.action_report_purchase_order_backup", raise_if_not_found=False)

check("module_installed", mod.state == "installed", mod.state)
check("module_version", mod.latest_version == "19.0.7.1.0", mod.latest_version)
check("main_action_report", main_action.report_name == REPORT_JT, main_action.report_name)
check("parallel_unbound", not parallel or not parallel.binding_model_id, parallel.binding_model_id.model if parallel and parallel.binding_model_id else "none")
check("backup_exists", bool(backup))
check("backup_unbound", not backup or not backup.binding_model_id)

bound_po_reports = Report.search([
    ("model", "=", "purchase.order"),
    ("binding_type", "=", "report"),
    ("binding_model_id", "!=", False),
    ("report_type", "=", "qweb-pdf"),
])
check("single_print_option", len(bound_po_reports) == 1, [
    {"id": r.id, "name": r.name, "report": r.report_name}
    for r in bound_po_reports
])
check(
    "official_is_main_action",
    len(bound_po_reports) == 1 and bound_po_reports[0].id == main_action.id,
    bound_po_reports[0].name if bound_po_reports else "",
)

# Formulario sin botón duplicado
form = PO.get_view(view_type="form")
form_arch = form.get("arch", "")
report["ui"]["form_arch_has_print_button"] = "action_jt_print_purchase_order" in form_arch
report["ui"]["form_arch_has_label"] = "Orden de Compra PDF" in form_arch
check("no_header_button", "action_jt_print_purchase_order" not in form_arch, True)
check("no_duplicate_label", "Orden de Compra PDF" not in form_arch, True)

# Método retirado
check("no_print_method", not hasattr(PO, "action_jt_print_purchase_order") or not callable(getattr(PO, "action_jt_print_purchase_order", None)), True)

po = PO.search([("order_line", "!=", False)], limit=1, order="id desc")
if not po:
    raise SystemExit("No purchase orders in PROD for validation")

# PDF menú Imprimir oficial (misma acción que usa el menú)
pdf_bytes, _ = Report._render_qweb_pdf(main_action.report_name, po.ids)
html_bytes, _ = Report._render_qweb_html(main_action.report_name, po.ids)
html = html_bytes.decode("utf-8", errors="replace") if isinstance(html_bytes, bytes) else str(html_bytes)

pdf_path = os.path.join(OUT_DIR, "01_official_print_menu.pdf")
with open(pdf_path, "wb") as fh:
    fh.write(pdf_bytes)
to_png(pdf_path, pdf_path.replace(".pdf", ""))

report["pdfs"]["official_print_menu"] = {
    "po_id": po.id,
    "po_name": po.name,
    "pdf_bytes": len(pdf_bytes),
    "html_has_po_band": "jt-po-band" in html,
    "html_has_title": "ORDEN DE COMPRA" in html,
    "html_has_old_std": "report_purchaseorder_document" in html and "jt-po-band" not in html,
}

check("pdf_official", pdf_ok(pdf_bytes) and len(pdf_bytes) > 500, len(pdf_bytes))
check("design_hellenia", report["pdfs"]["official_print_menu"]["html_has_po_band"], True)
check("not_old_odoo_design", not report["pdfs"]["official_print_menu"]["html_has_old_std"], True)

# Respaldo sigue renderizando (rollback técnico)
if backup:
    try:
        backup_pdf, _ = Report._render_qweb_pdf(backup.report_name, po.ids)
        check("backup_report_ok", pdf_ok(backup_pdf), len(backup_pdf))
    except Exception as exc:
        check("backup_report_ok", False, str(exc))

# Idéntico al template Justech (acción principal == template oficial)
jt_def = env.ref("justech_report_design.action_report_justech_purchase_order", raise_if_not_found=False)
if jt_def:
    jt_pdf, _ = Report._render_qweb_pdf(jt_def.report_name, po.ids)
    check("same_as_justech_template", jt_pdf == pdf_bytes, f"main={len(pdf_bytes)} jt={len(jt_pdf)}")

# Flujo compras: confirmar no hay error al leer campos estándar
check("po_readable", bool(po.name and po.partner_id), po.name)
check("po_lines_ok", bool(po.order_line), len(po.order_line))

critical = [
    "module_installed",
    "module_version",
    "main_action_report",
    "parallel_unbound",
    "backup_exists",
    "backup_unbound",
    "single_print_option",
    "official_is_main_action",
    "no_header_button",
    "no_duplicate_label",
    "pdf_official",
    "design_hellenia",
    "not_old_odoo_design",
    "backup_report_ok",
    "same_as_justech_template",
    "po_readable",
    "po_lines_ok",
]

all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical if k in report["checks"])
report["status"] = "PASS" if all_pass else "FAIL"
report["pass"] = report["status"] == "PASS"

with open(os.path.join(OUT_DIR, "validation.json"), "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

with open(os.path.join(OUT_DIR, "ui_evidence.json"), "w") as f:
    json.dump(report["ui"], f, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "errors": report["errors"]}))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
