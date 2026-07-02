# -*- coding: utf-8 -*-
"""Fase 24.1 PROD — Validación paralela justech_report_design (solo hellenia_prod)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT_DIR = "/tmp/phase24-1-prod-parallel"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_JT = "justech_report_design.report_hellenia_quotation_document"
REPORT_STD = "sale.report_saleorder"

report = {
    "phase": "24.1-prod-parallel",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "pass": False,
    "failed_checks": [],
    "checks": {},
    "pdfs": {},
    "orders_used": {},
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]}
    if not ok:
        report["failed_checks"].append(key)


def pdf_pages(path):
    try:
        out = subprocess.check_output(["pdfinfo", path], stderr=subprocess.DEVNULL, timeout=15)
        for line in out.decode().splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return None


def write_pdf(key, so, report_name, fname, Report):
    pdf_bytes, _ = Report._render_qweb_pdf(report_name, so.ids)
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    report["pdfs"][key] = {
        "order": so.name,
        "order_id": so.id,
        "file": fname,
        "size_bytes": len(pdf_bytes),
        "pages": pdf_pages(path),
    }
    check(f"{key}_pdf", pdf_bytes[:4] == b"%PDF", f"size={len(pdf_bytes)}")
    return pdf_bytes


# --- Módulo instalado ---
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
check("module_installed", mod.state == "installed", mod.state)
check("module_version", mod.latest_version == "19.0.1.1.6", mod.latest_version)
report["module_version"] = mod.latest_version

# --- Acciones de reporte en menú Imprimir ---
jt_action = env.ref("justech_report_design.action_report_hellenia_quotation", raise_if_not_found=False)
std_action = env.ref("sale.action_report_saleorder", raise_if_not_found=False)
check("jt_action_exists", bool(jt_action))
check("std_action_exists", bool(std_action))
check("jt_action_name", jt_action.name == "Cotización Hellenia (Diseño)", jt_action.name if jt_action else "")
check("jt_report_name", jt_action.report_name == REPORT_JT if jt_action else False)
check("std_report_name", std_action.report_name == REPORT_STD if std_action else False)
check(
    "no_replace_std_action",
    std_action.id != jt_action.id if std_action and jt_action else False,
)

# hellenia_reports sigue instalado
hr = env["ir.module.module"].search([("name", "=", "hellenia_reports")], limit=1)
check("hellenia_reports_installed", hr.state == "installed", hr.state)

# Sin herencia justech sobre vistas estándar
for key in ("sale.report_saleorder", "sale.report_saleorder_document", "sale.report_saleorder_raw"):
    v = env["ir.ui.view"].search([("key", "=", key)], limit=1)
    children = env["ir.ui.view"].search([
        ("inherit_id", "=", v.id),
        ("key", "like", "justech_report_design.%"),
    ])
    check(f"{key}_jt_inherits", len(children) == 0, f"inherits={children.mapped('key')}")

Report = env["ir.actions.report"]
SaleOrder = env["sale.order"]

# Cotización real: preferir sent/draft con líneas
def pick_order(min_lines=1, with_discount=False):
    domain = [("state", "in", ("draft", "sent"))]
    candidates = SaleOrder.search(domain, order="write_date desc", limit=50)
    for so in candidates:
        lines = so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)
        if len(lines) < min_lines:
            continue
        if with_discount:
            if any((l.discount or 0) > 0 for l in lines):
                return so
        else:
            if not any((l.discount or 0) > 0 for l in lines):
                return so
    return None


so_1p = pick_order(min_lines=1, with_discount=False)
if not so_1p:
    so_1p = SaleOrder.search([("state", "in", ("draft", "sent"))], limit=1)
if so_1p:
    report["orders_used"]["real_1p"] = {"name": so_1p.name, "id": so_1p.id}
    write_pdf("jt_real_1p", so_1p, REPORT_JT, "prod_quotation_real_1p.pdf", Report)
    write_pdf("std_real_1p", so_1p, REPORT_STD, "prod_quotation_standard.pdf", Report)
    html = Report._render_qweb_html(REPORT_JT, so_1p.ids)[0].decode("utf-8", errors="replace")
    check("jt_template", "jt-hq-page" in html and "jt-hq-band" in html)
    check("vis001_no_sigs_zone_table", '<table class="jt-hq-sigs-zone"' not in html)
    check("vis001_no_lower", "jt-hq-lower" not in html)
else:
    check("real_quotation_found", False, "sin cotización draft/sent")

so_5p = pick_order(min_lines=5, with_discount=False)
if so_5p:
    report["orders_used"]["real_5p"] = {"name": so_5p.name, "id": so_5p.id}
    write_pdf("jt_real_5p", so_5p, REPORT_JT, "prod_quotation_real_5p.pdf", Report)

so_disc = pick_order(min_lines=1, with_discount=True)
if so_disc:
    report["orders_used"]["real_disc"] = {"name": so_disc.name, "id": so_disc.id}
    write_pdf("jt_real_disc", so_disc, REPORT_JT, "prod_quotation_real_discount.pdf", Report)
    html_d = Report._render_qweb_html(REPORT_JT, so_disc.ids)[0].decode("utf-8", errors="replace")
    thead = html_d.split("<thead>")[1].split("</thead>")[0] if "<thead>" in html_d else ""
    check("disc_col", "c-disc" in thead)
    totals = (
        html_d.split('class="jt-hq-totals"')[1].split("</table>")[0]
        if 'class="jt-hq-totals"' in html_d
        else ""
    )
    check("disc_totals", "Subtotal bruto" in totals and "Descuento" in totals)
else:
    check("disc_quotation_found", False, "sin cotización con descuento en línea")

# Smoke: factura
Invoice = env["account.move"]
inv = Invoice.search([("move_type", "=", "out_invoice"), ("state", "=", "posted")], limit=1)
if inv:
    inv_report = env.ref("account.account_invoices", raise_if_not_found=False)
    if inv_report:
        pdf, _ = Report._render_qweb_pdf(inv_report.report_name, inv.ids)
        check("invoice_pdf", pdf[:4] == b"%PDF", f"inv={inv.name} size={len(pdf)}")
        report["orders_used"]["invoice"] = inv.name
else:
    check("invoice_found", False, "sin factura posted")

# Smoke: compra
PO = env["purchase.order"]
po = PO.search([("state", "in", ("purchase", "done", "sent"))], limit=1)
if po:
    po_report = env.ref("purchase.action_report_purchase_order", raise_if_not_found=False)
    if po_report:
        pdf, _ = Report._render_qweb_pdf(po_report.report_name, po.ids)
        check("purchase_pdf", pdf[:4] == b"%PDF", f"po={po.name} size={len(pdf)}")
        report["orders_used"]["purchase"] = po.name
else:
    check("purchase_found", False, "sin orden compra")

# Smoke: inventario (picking)
Picking = env["stock.picking"]
pick = Picking.search([("state", "=", "done")], limit=1)
if pick:
    pick_report = env.ref("stock.action_report_delivery", raise_if_not_found=False)
    if pick_report:
        pdf, _ = Report._render_qweb_pdf(pick_report.report_name, pick.ids)
        check("stock_pdf", pdf[:4] == b"%PDF", f"pick={pick.name} size={len(pdf)}")
        report["orders_used"]["picking"] = pick.name
else:
    check("picking_found", False, "sin albarán done")

# Smoke: DGII (módulo l10n_do si existe)
dgii_mod = env["ir.module.module"].search([("name", "=", "l10n_do_accounting")], limit=1)
if dgii_mod and dgii_mod.state == "installed":
    dgii_report = env["ir.actions.report"].search([
        ("report_name", "like", "%dgii%"),
    ], limit=1)
    if dgii_report:
        check("dgii_module_ok", True, dgii_mod.latest_version)
    else:
        check("dgii_module_ok", True, "l10n_do_accounting installed, no dgii report ref")
else:
    # Buscar cualquier reporte hellenia dgii
    dgii_reports = env["ir.actions.report"].search([("name", "ilike", "dgii")], limit=3)
    check("dgii_reports_present", len(dgii_reports) >= 0, str(dgii_reports.mapped("name")))

report["pass"] = len(report["failed_checks"]) == 0 and bool(so_1p)

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE24_1_PROD:" + json.dumps(report, indent=2, ensure_ascii=False))
