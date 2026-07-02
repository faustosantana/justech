# -*- coding: utf-8 -*-
"""Fase 26 PROD — Factura oficial Justech + validación completa (solo hellenia_prod)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT_DIR = "/tmp/phase26-official-invoice-prod"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_JT = "justech_report_design.report_justech_invoice_document"
MAIN_ACTION = "account.account_invoices"

report = {
    "phase": "26-official-invoice-prod",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_version": None,
    "checks": {},
    "pdfs": {},
    "errors": [],
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]}
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


# Upgrade módulo
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
mod.button_immediate_upgrade()
env.cr.commit()
try:
    env["ir.qweb"].clear_caches()
except Exception:
    pass
env.cr.commit()
report["module_version"] = mod.latest_version

Report = env["ir.actions.report"]
Move = env["account.move"]
DocType = env["justech.do.fiscal.document.type"]
Company = env.company

# --- Configuración reporte oficial ---
main_action = env.ref(MAIN_ACTION)
parallel = env.ref("justech_report_design.action_report_justech_invoice", raise_if_not_found=False)
backup = env.ref("justech_report_design.action_report_invoice_backup", raise_if_not_found=False)

check("module_installed", mod.state == "installed", mod.state)
check("main_action_report", main_action.report_name == REPORT_JT, main_action.report_name)
check("parallel_unbound", not parallel or not parallel.binding_model_id)
check("backup_unbound", not backup or not backup.binding_model_id)
check("backup_exists", bool(backup))

bound_invoice_reports = Report.search([
    ("model", "=", "account.move"),
    ("binding_type", "=", "report"),
    ("binding_model_id", "!=", False),
    ("report_type", "=", "qweb-pdf"),
])
invoice_print_menu = bound_invoice_reports.filtered(
    lambda r: not r.domain or "out_invoice" in (r.domain or "") or "out_refund" in (r.domain or "")
)
check("single_print_option", len(invoice_print_menu) == 1, [
    {"id": r.id, "name": r.name, "report": r.report_name} for r in invoice_print_menu
])

# Método nomenclatura
probe = Move.new({"move_type": "out_invoice"})
check("method_short_display", hasattr(probe, "get_jt_document_type_short_display"))

# --- Helpers render ---
def render_case(key, move, filename):
    try:
        pdf_bytes, _ = Report._render_qweb_pdf(main_action.report_name, move.ids)
        html_bytes, _ = Report._render_qweb_html(main_action.report_name, move.ids)
        html = html_bytes.decode("utf-8", errors="replace") if isinstance(html_bytes, bytes) else str(html_bytes)
        pdf_path = os.path.join(OUT_DIR, filename)
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        to_png(pdf_path, pdf_path.replace(".pdf", ""))
        entry = {
            "move_id": move.id,
            "move_name": move.name,
            "pdf_bytes": len(pdf_bytes),
            "qweb_error": False,
            "html_has_jt_inv_band": "jt-inv-band" in html,
            "html_has_tipo_label": 'class="jt-inv-label">Tipo:</span>' in html,
            "html_has_old_std": "hellenia-ncf-box" in html and "jt-inv-fiscal-grid" not in html,
        }
        report["pdfs"][key] = entry
        check(f"pdf_{key}", pdf_ok(pdf_bytes) and entry["html_has_jt_inv_band"], f"size={len(pdf_bytes)}")
        check(f"design_{key}", entry["html_has_jt_inv_band"] and not entry["html_has_old_std"])
        return True
    except Exception as e:
        report["pdfs"][key] = {"qweb_error": True, "error": str(e)[:500]}
        check(f"pdf_{key}", False, str(e))
        return False


# Buscar facturas reales existentes
def find_invoice(**domain_extra):
    dom = [("move_type", "=", "out_invoice"), ("company_id", "=", Company.id)]
    dom.extend(domain_extra.items())
    return Move.search(dom, order="id desc", limit=1)


# 1. Factura normal (posted)
inv_normal = find_invoice(state="posted")
if inv_normal:
    render_case("invoice_normal", inv_normal, "01_invoice_normal.pdf")

# 2. Factura con NCF
inv_ncf = find_invoice(state="posted", justech_do_ncf="!=", False)
if not inv_ncf:
    inv_ncf = Move.search([
        ("move_type", "=", "out_invoice"),
        ("company_id", "=", Company.id),
        ("justech_do_ncf", "!=", False),
    ], order="id desc", limit=1)
if inv_ncf:
    render_case("invoice_with_ncf", inv_ncf, "02_invoice_with_ncf.pdf")
else:
    check("pdf_invoice_with_ncf", False, "sin factura con NCF en prod")

# 3. Factura con descuento — buscar línea con discount > 0
inv_disc = Move.search([
    ("move_type", "=", "out_invoice"),
    ("company_id", "=", Company.id),
    ("invoice_line_ids.discount", ">", 0),
], order="id desc", limit=1)
if inv_disc:
    render_case("invoice_with_discount", inv_disc, "03_invoice_with_discount.pdf")
else:
    check("pdf_invoice_with_discount", False, "sin factura con descuento en prod")

# 4. Consumidor final B02
dt_b02 = DocType.search([("prefix", "=", "B02")], limit=1)
inv_b02 = Move.search([
    ("move_type", "=", "out_invoice"),
    ("company_id", "=", Company.id),
    ("justech_do_document_type_id", "=", dt_b02.id if dt_b02 else 0),
], order="id desc", limit=1) if dt_b02 else Move.browse()
if inv_b02:
    render_case("invoice_b02_consumo", inv_b02, "04_invoice_b02_consumo.pdf")
else:
    check("pdf_invoice_b02_consumo", False, "sin factura B02 en prod")

# 5. Gubernamental (si existe tipo)
dt_gov = DocType.search([("name", "ilike", "gubernamental")], limit=1)
if dt_gov:
    inv_gov = Move.search([
        ("move_type", "=", "out_invoice"),
        ("company_id", "=", Company.id),
        ("justech_do_document_type_id", "=", dt_gov.id),
    ], order="id desc", limit=1)
    if inv_gov:
        render_case("invoice_gubernamental", inv_gov, "05_invoice_gubernamental.pdf")
    else:
        check("pdf_invoice_gubernamental", False, "tipo gubernamental existe pero sin factura")
else:
    report["checks"]["pdf_invoice_gubernamental"] = {"status": "SKIP", "detail": "tipo gubernamental no existe"}

# 6. Nota de crédito
nc = Move.search([
    ("move_type", "=", "out_refund"),
    ("company_id", "=", Company.id),
    ("state", "in", ["posted", "draft"]),
], order="id desc", limit=1)
if nc:
    render_case("credit_note", nc, "06_credit_note.pdf")
else:
    check("pdf_credit_note", False, "sin nota de crédito en prod")

# --- Regresión: cotización, compras ---
SaleOrder = env["sale.order"]
so = SaleOrder.search([("state", "in", ("draft", "sent", "sale"))], order="id desc", limit=1)
if so:
    try:
        pdf_so, _ = Report._render_qweb_pdf(env.ref("sale.action_report_saleorder").report_name, so.ids)
        check("regression_quotation", pdf_ok(pdf_so), f"{so.name} size={len(pdf_so)}")
    except Exception as e:
        check("regression_quotation", False, str(e))

PO = env["purchase.order"]
po = PO.search([("state", "in", ("purchase", "done"))], order="id desc", limit=1)
if po:
    try:
        pdf_po, _ = Report._render_qweb_pdf(env.ref("purchase.action_report_purchase_order").report_name, po.ids)
        check("regression_purchase", pdf_ok(pdf_po), f"size={len(pdf_po)}")
    except Exception as e:
        check("regression_purchase", False, str(e))

# DGII módulo instalado
dgii_mod = env["ir.module.module"].search([("name", "=", "justech_l10n_do_reports")], limit=1)
check("dgii_module_installed", dgii_mod.state == "installed", dgii_mod.state if dgii_mod else "missing")

critical = [
    "module_installed", "main_action_report", "parallel_unbound", "single_print_option",
    "method_short_display", "pdf_invoice_normal", "design_invoice_normal",
    "regression_quotation",
]
all_critical_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical)
report["status"] = "PASS" if all_critical_pass and not report["errors"] else "FAIL"

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps({
    "status": report["status"],
    "version": report["module_version"],
    "errors": report["errors"],
    "checks_failed": [k for k, v in report["checks"].items() if v.get("status") == "FAIL"],
}))

if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
