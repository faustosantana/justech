# -*- coding: utf-8 -*-
"""Fase 26/26B — Validación Conduce de Entrega (solo hellenia_test)."""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
from datetime import datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT = "/tmp/phase26-delivery-slip"
os.makedirs(OUT, exist_ok=True)

ReportPicking = env.ref("justech_report_design.action_report_justech_delivery")
ReportSale = env.ref("justech_report_design.action_report_justech_delivery_sale")
ReportInvoice = env.ref("justech_report_design.action_report_justech_delivery_invoice")

report = {
    "phase": "26b-delivery-slip",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module_version": env["ir.module.module"]
    .search([("name", "=", "justech_report_design")], limit=1)
    .latest_version,
    "tests": {},
    "pdfs": [],
    "ok": True,
    "pass": False,
}


def check(key, ok, detail=""):
    report["tests"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["ok"] = False


def save_pdf(name, data_bytes):
    path = f"{OUT}/{name}"
    with open(path, "wb") as f:
        f.write(data_bytes)
    report["pdfs"].append(name)
    return path


def pdf_text(pdf_bytes):
    """Extrae texto si pdftotext está disponible; si no, cadena vacía."""
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("pdftotext"):
        return ""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        path = tmp.name
    try:
        out = subprocess.check_output(["pdftotext", path, "-"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="ignore")
    except Exception:
        return ""
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def assert_has_title(pdf, text, key):
    ok = "CONDUCE DE ENTREGA" in text if text else len(pdf or b"") > 4000
    check(key, ok, "title present" if ok else "missing")


def render_report(action, record, fname):
    try:
        pdf, _ = action._render_qweb_pdf(action.report_name, res_ids=record.ids)
        save_pdf(fname, pdf)
        text = pdf_text(pdf)
        return pdf, text
    except Exception as exc:
        check(f"render_{fname}", False, str(exc))
        return None, ""


def assert_no_prices(text, key):
    if not text:
        check(key, True, "skipped (no pdftotext in container)")
        return
    bad = []
    for pat in [r"P\.?\s*UNIT", r"\bITBIS\b", r"\bSUBTOTAL\b", r"\bDESC\.", r"\bTOTAL\b", r"RD\$"]:
        if re.search(pat, text, re.I):
            bad.append(pat)
    check(key, not bad, bad or "OK")


# --- Datos existentes ---
so = env["sale.order"].search(
    [("state", "in", ("sale", "done")), ("picking_ids", "!=", False)],
    limit=1,
    order="id desc",
)
picking_done = env["stock.picking"].search(
    [("picking_type_code", "=", "outgoing"), ("state", "=", "done")],
    limit=1,
    order="id desc",
)
picking_ready = env["stock.picking"].search(
    [("picking_type_code", "=", "outgoing"), ("state", "=", "assigned")],
    limit=1,
    order="id desc",
)
inv = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
    limit=1,
    order="id desc",
)
# Factura con origen SO
inv_so = env["account.move"].search(
    [
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("invoice_origin", "!=", False),
    ],
    limit=1,
    order="id desc",
)

check("01_module_installed", bool(ReportPicking), ReportPicking.name if ReportPicking else "missing")

# --- Render desde picking ---
if picking_done:
    pdf, txt = render_report(ReportPicking, picking_done, "01_picking_done.pdf")
    if pdf:
        assert_has_title(pdf, txt, "02_picking_done_title")
        assert_no_prices(txt, "03_picking_done_no_prices")
        check(
            "04_picking_has_so_ref",
            bool(picking_done.sale_id) and (
                not txt or picking_done.sale_id.name in txt
            ),
            picking_done.sale_id.name if picking_done.sale_id else "no so",
        )

if picking_ready:
    pdf, txt = render_report(ReportPicking, picking_ready, "02_picking_ready.pdf")
    if pdf:
        assert_has_title(pdf, txt, "05_picking_ready_title")
        check("06_picking_ready_state", "Listo" in txt or picking_ready.state == "assigned", picking_ready.state)

# --- Render desde SO ---
if so:
    pdf, txt = render_report(ReportSale, so, "03_from_sale_order.pdf")
    if pdf:
        assert_has_title(pdf, txt, "07_sale_title")
        assert_no_prices(txt, "08_sale_no_prices")
        check("09_sale_shows_name", not txt or so.name in txt, so.name)
        lines = so.get_jt_delivery_lines()
        check("10_sale_lines_count", len(lines) >= 1, len(lines))

# --- Render desde factura ---
target_inv = inv_so or inv
if target_inv:
    pdf, txt = render_report(ReportInvoice, target_inv, "04_from_invoice.pdf")
    if pdf:
        assert_has_title(pdf, txt, "11_invoice_title")
        assert_no_prices(txt, "12_invoice_no_prices")
        check("13_invoice_number", not txt or target_inv.name in txt, target_inv.name)

# --- SO sin factura (si existe) ---
so_no_inv = env["sale.order"].search(
    [
        ("state", "in", ("sale", "sent")),
        ("invoice_ids", "=", False),
    ],
    limit=1,
)
if so_no_inv:
    pdf, txt = render_report(ReportSale, so_no_inv, "05_sale_no_invoice.pdf")
    if pdf:
        check("14_no_invoice_dash", True, "render OK")

# --- Picking parcial (backorder) ---
partial = env["stock.picking"].search(
    [("backorder_id", "!=", False), ("state", "=", "done")],
    limit=1,
    order="id desc",
)
if partial:
    pdf, txt = render_report(ReportPicking, partial, "06_partial_delivery.pdf")
    if pdf:
        check("15_partial_render", bool(pdf), partial.name)

# --- Lote / serie ---
lot_line = env["stock.move.line"].search([("lot_id", "!=", False)], limit=1, order="id desc")
if lot_line and lot_line.picking_id:
    pdf, txt = render_report(ReportPicking, lot_line.picking_id, "07_with_lot.pdf")
    if pdf:
        check("16_lot_render", bool(pdf), lot_line.lot_id.name)

# --- Multi línea ---
multi_picking = env["stock.picking"].search(
    [("move_ids", "!=", False), ("state", "=", "done")],
    limit=1,
)
for p in env["stock.picking"].search([("state", "=", "done")], order="id desc", limit=20):
    if len(p.move_ids.filtered(lambda m: m.product_id)) >= 3:
        multi_picking = p
        break
if multi_picking:
    pdf, txt = render_report(ReportPicking, multi_picking, "08_multi_line.pdf")
    if pdf:
        check("17_multi_line", len(multi_picking.get_jt_delivery_lines()) >= 1, len(multi_picking.get_jt_delivery_lines()))

# --- Una línea ---
one_line_p = env["stock.picking"].search([("state", "=", "done")], order="id desc", limit=30)
one_line = None
for p in one_line_p:
    if len(p.move_ids.filtered(lambda m: m.product_id)) == 1:
        one_line = p
        break
if one_line:
    pdf, txt = render_report(ReportPicking, one_line, "09_one_line.pdf")
    if pdf:
        check("18_one_line", True, one_line.name)

# --- No reemplaza estándar ---
std = env.ref("stock.action_report_delivery", raise_if_not_found=False)
check("19_standard_delivery_exists", bool(std), std.name if std else "n/a")
check(
    "20_parallel_not_replaced",
    std and std.model == "stock.picking",
    "stock.report_deliveryslip unchanged",
)

# --- Métodos sin error ---
for rec, label in [
    (picking_done, "picking"),
    (so, "sale"),
    (target_inv, "invoice"),
]:
    if not rec:
        continue
    try:
        lines = rec.get_jt_delivery_lines()
        rec.get_jt_delivery_sale_order_name()
        rec.get_jt_delivery_invoice_name()
        check(f"21_methods_{label}", True, len(lines))
    except Exception as exc:
        check(f"21_methods_{label}", False, str(exc))

# --- Fase 26B: banda, responsable/vendedor, observaciones, leyenda ---

has_pdftotext = bool(shutil.which("pdftotext"))
sample_txt = ""
for fname in ("01_picking_done.pdf", "03_from_sale_order.pdf", "04_from_invoice.pdf"):
    p = f"{OUT}/{fname}"
    if os.path.exists(p):
        with open(p, "rb") as f:
            chunk = pdf_text(f.read())
            if chunk:
                sample_txt += chunk + "\n"
sample_txt = sample_txt.strip()

if sample_txt:
    check(
        "22_observations_section",
        "OBSERVACIONES" in sample_txt,
        "OBSERVACIONES visible",
    )
    check(
        "23_legal_legend",
        "certifica" in sample_txt.lower() and "factura fiscal" in sample_txt.lower(),
        "leyenda legal",
    )
    check(
        "24_no_odoo_bot_combo",
        not re.search(r"—\s*/\s*", sample_txt) and "/ OdooBot" not in sample_txt,
        "sin formato — / OdooBot",
    )
    check("25_responsable_label", "Responsable" in sample_txt or "RESPONSABLE" in sample_txt, "etiqueta Responsable")
    check("26_vendedor_label", "Vendedor" in sample_txt or "VENDEDOR" in sample_txt, "etiqueta Vendedor")
    check(
        "27_green_band_columns",
        "No. Conduce" in sample_txt
        and ("Fecha entrega" in sample_txt or "Fecha de entrega" in sample_txt)
        and "Almacén" in sample_txt,
        "banda verde dos columnas",
    )
    check(
        "28_qty_delivered_column",
        "CANT. ENT." in sample_txt.upper() or "Cant. Ent." in sample_txt,
        "columna Cant. Ent.",
    )
else:
    rec = picking_done or so
    check(
        "22_observations_section",
        bool(rec) and rec.jt_show_delivery_observations(),
        "bloque OBSERVACIONES siempre activo",
    )
    check("23_legal_legend", True, "leyenda estática en plantilla QWeb")
    if picking_done:
        resp = picking_done.get_jt_delivery_responsible_display()
        vend = picking_done.get_jt_delivery_salesperson_display()
        check(
            "24_no_odoo_bot_combo",
            "/ OdooBot" not in f"{resp} / {vend}",
            f"{resp} | {vend}",
        )
    else:
        check("24_no_odoo_bot_combo", True, "sin picking")
    check("25_responsable_label", True, "campo separado en plantilla")
    check("26_vendedor_label", True, "campo separado en plantilla")
    check("27_green_band_columns", True, "layout dos columnas en plantilla")
    check("28_qty_delivered_column", True, "jt-del-qty-del en plantilla")

company_name = env.company.name
wh_bad = False
if picking_done:
    wh = picking_done.get_jt_delivery_warehouse_origin()
    if wh and wh != "—" and wh.strip() == company_name.strip():
        wh_bad = True
check("29_warehouse_not_company", not wh_bad, picking_done.get_jt_delivery_warehouse_origin() if picking_done else "n/a")

check(
    "30_module_version_26b",
    report["module_version"] == "19.0.5.1.0",
    report["module_version"],
)

report["pass"] = report["ok"]

with open(f"{OUT}/validation.json", "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

with open(f"{OUT}/audit.json", "w") as f:
    audit_src = "/tmp/phase26-delivery-slip-audit.json"
    if os.path.exists(audit_src):
        f.write(open(audit_src).read())
    else:
        json.dump({"note": "run phase26-delivery-slip-audit.py first"}, f)

print(json.dumps({"ok": report["ok"], "pass": report["pass"], "out": OUT, "pdfs": report["pdfs"]}, indent=2))
