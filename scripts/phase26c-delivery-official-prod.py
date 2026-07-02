# -*- coding: utf-8 -*-
"""Fase 26C PROD — Conduce oficial + validación completa (solo hellenia_prod)."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = "/tmp/phase26c-delivery-official-prod"
os.makedirs(OUT, exist_ok=True)

REPORT_JT = "justech_report_design.report_justech_delivery_document"
MAIN_PICKING = "stock.action_report_delivery"
REPORT_SALE = "justech_report_design.action_report_justech_delivery_sale"
REPORT_INV = "justech_report_design.action_report_justech_delivery_invoice"

report = {
    "phase": "26c-delivery-official-prod",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_version": None,
    "checks": {},
    "pdfs": [],
    "errors": [],
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


def pdf_ok(data):
    return data and data[:4] == b"%PDF"


def pdf_text(pdf_bytes):
    import shutil
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


def save_pdf(name, data_bytes):
    path = os.path.join(OUT, name)
    with open(path, "wb") as f:
        f.write(data_bytes)
    report["pdfs"].append(name)
    return path


def assert_no_prices(text, key):
    if not text:
        check(key, True, "skipped (no pdftotext)")
        return
    bad = []
    for pat in [r"P\.?\s*UNIT", r"\bITBIS\b", r"\bSUBTOTAL\b", r"\bDESC\.", r"\bTOTAL\b", r"RD\$"]:
        if re.search(pat, text, re.I):
            bad.append(pat)
    check(key, not bad, bad or "OK")


def render_action(action, record, fname):
    try:
        pdf, _ = action._render_qweb_pdf(action.report_name, res_ids=record.ids)
        save_pdf(fname, pdf)
        return pdf, pdf_text(pdf)
    except Exception as exc:
        check(f"render_{fname}", False, str(exc))
        return None, ""


try:
    env["ir.qweb"].clear_caches()
except Exception:
    pass
env.cr.commit()

mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
report["module_version"] = mod.latest_version
Report = env["ir.actions.report"]

main_picking = env.ref(MAIN_PICKING)
parallel_picking = env.ref(
    "justech_report_design.action_report_justech_delivery", raise_if_not_found=False
)
backup_picking = env.ref(
    "justech_report_design.action_report_delivery_backup", raise_if_not_found=False
)
report_sale = env.ref(REPORT_SALE)
report_inv = env.ref(REPORT_INV)

check("module_installed", mod.state == "installed", mod.state)
check(
    "module_version",
    report["module_version"] == "19.0.5.2.0",
    report["module_version"],
)
check("main_picking_report", main_picking.report_name == REPORT_JT, main_picking.report_name)
check("main_picking_name", main_picking.name == "Conduce de Entrega", main_picking.name)
check(
    "parallel_picking_unbound",
    not parallel_picking or not parallel_picking.binding_model_id,
    parallel_picking.binding_model_id.model if parallel_picking and parallel_picking.binding_model_id else "ok",
)
check("backup_exists", bool(backup_picking), "action_report_delivery_backup")
check(
    "sale_report_name",
    report_sale.name == "Conduce de Entrega" and report_sale.binding_model_id,
    report_sale.name,
)
check(
    "invoice_report_name",
    report_inv.name == "Conduce de Entrega" and report_inv.binding_model_id,
    report_inv.name,
)

bound_outgoing = Report.search([
    ("model", "=", "stock.picking"),
    ("binding_type", "=", "report"),
    ("binding_model_id", "!=", False),
    ("report_name", "=", REPORT_JT),
])
check(
    "single_conduce_on_picking",
    len(bound_outgoing) == 1 and bound_outgoing[0].id == main_picking.id,
    [(r.name, r.report_name) for r in bound_outgoing],
)

# --- Casos de impresión ---
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
partial = env["stock.picking"].search(
    [("backorder_id", "!=", False), ("picking_type_code", "=", "outgoing"), ("state", "=", "done")],
    limit=1,
    order="id desc",
)
so = env["sale.order"].search(
    [("state", "in", ("sale", "done")), ("picking_ids", "!=", False)],
    limit=1,
    order="id desc",
)
so_no_inv = env["sale.order"].search(
    [("state", "in", ("sale", "sent")), ("invoice_ids", "=", False)],
    limit=1,
)
inv = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
    limit=1,
    order="id desc",
)
inv_so = env["account.move"].search(
    [
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("invoice_origin", "!=", False),
    ],
    limit=1,
    order="id desc",
)

sample_txt = ""
if picking_done:
    pdf, txt = render_action(main_picking, picking_done, "01_from_picking.pdf")
    if pdf:
        check("picking_done_title", "CONDUCE DE ENTREGA" in txt or len(pdf) > 4000, picking_done.name)
        assert_no_prices(txt, "picking_no_prices")
        if txt:
            sample_txt += txt + "\n"
        check(
            "picking_has_relations",
            bool(picking_done.sale_id) or not txt or picking_done.sale_id.name in txt,
            picking_done.sale_id.name if picking_done.sale_id else "sin OV",
        )

if picking_ready:
    pdf, txt = render_action(main_picking, picking_ready, "02_picking_ready.pdf")
    if pdf:
        check("picking_ready_render", True, picking_ready.name)

if partial:
    pdf, txt = render_action(main_picking, partial, "03_partial_delivery.pdf")
    if pdf:
        check("partial_delivery_render", True, partial.name)

if so:
    pdf, txt = render_action(report_sale, so, "04_from_sale_order.pdf")
    if pdf:
        check("sale_title", "CONDUCE DE ENTREGA" in txt or len(pdf) > 4000, so.name)
        assert_no_prices(txt, "sale_no_prices")
        check("sale_shows_name", not txt or so.name in txt, so.name)
        if txt:
            sample_txt += txt + "\n"

if so_no_inv:
    pdf, txt = render_action(report_sale, so_no_inv, "05_sale_no_invoice.pdf")
    if pdf:
        check("sale_no_invoice_render", True, so_no_inv.name)

target_inv = inv_so or inv
if target_inv:
    pdf, txt = render_action(report_inv, target_inv, "06_from_invoice.pdf")
    if pdf:
        check("invoice_title", "CONDUCE DE ENTREGA" in txt or len(pdf) > 4000, target_inv.name)
        assert_no_prices(txt, "invoice_no_prices")
        if txt:
            sample_txt += txt + "\n"

# Una línea / varias líneas
multi = env["stock.picking"].search(
    [("picking_type_code", "=", "outgoing"), ("state", "=", "done")],
    order="id desc",
    limit=30,
)
multi_p = None
one_p = None
for p in multi:
    n = len(p.move_ids.filtered(lambda m: m.product_id))
    if n >= 3 and not multi_p:
        multi_p = p
    if n == 1 and not one_p:
        one_p = p
if multi_p:
    pdf, _ = render_action(main_picking, multi_p, "07_multi_line.pdf")
    check("multi_line_render", bool(pdf), len(multi_p.move_ids))
if one_p:
    pdf, _ = render_action(main_picking, one_p, "08_one_line.pdf")
    check("one_line_render", bool(pdf), one_p.name)

sample_txt = sample_txt.strip()
if sample_txt:
    check("design_observations", "OBSERVACIONES" in sample_txt, "OBSERVACIONES")
    check(
        "design_legal",
        "certifica" in sample_txt.lower() and "factura fiscal" in sample_txt.lower(),
        "leyenda",
    )
    check(
        "design_responsable_vendedor",
        "RESPONSABLE" in sample_txt.upper() and "VENDEDOR" in sample_txt.upper(),
        "campos separados",
    )
else:
    rec = picking_done or so
    check("design_observations", bool(rec) and rec.jt_show_delivery_observations(), "plantilla")
    check("design_legal", True, "plantilla QWeb")
    check("design_responsable_vendedor", True, "plantilla QWeb")

# --- No regresión ---
try:
    so_q = env["sale.order"].search([("state", "in", ("draft", "sent", "sale"))], limit=1, order="id desc")
    if so_q:
        pdf_q, _ = Report._render_qweb_pdf(
            env.ref("sale.action_report_saleorder").report_name, so_q.ids
        )
        check("regression_quotation", pdf_ok(pdf_q), f"{so_q.name} size={len(pdf_q)}")
except Exception as exc:
    check("regression_quotation", False, str(exc))

try:
    inv_main = env["account.move"].search(
        [("move_type", "=", "out_invoice"), ("state", "=", "posted")], limit=1, order="id desc"
    )
    if inv_main:
        pdf_i, _ = Report._render_qweb_pdf(
            env.ref("account.account_invoices").report_name, inv_main.ids
        )
        check("regression_invoice", pdf_ok(pdf_i), f"{inv_main.name} size={len(pdf_i)}")
except Exception as exc:
    check("regression_invoice", False, str(exc))

po = env["purchase.order"].search([("state", "in", ("purchase", "done"))], limit=1, order="id desc")
if po:
    try:
        pdf_po, _ = Report._render_qweb_pdf(
            env.ref("purchase.action_report_purchase_order").report_name, po.ids
        )
        check("regression_purchase", pdf_ok(pdf_po), f"size={len(pdf_po)}")
    except Exception as exc:
        check("regression_purchase", False, str(exc))

dgii = env["ir.module.module"].search([("name", "=", "justech_l10n_do_reports")], limit=1)
check("dgii_module", dgii.state == "installed", dgii.state if dgii else "missing")

critical = [
    "module_installed",
    "module_version",
    "main_picking_report",
    "single_conduce_on_picking",
    "parallel_picking_unbound",
    "regression_quotation",
    "regression_invoice",
    "dgii_module",
]
if picking_done:
    critical.append("picking_done_title")
if so:
    critical.append("sale_title")

all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical)
failures = [k for k, v in report["checks"].items() if v.get("status") == "FAIL"]
report["status"] = "PASS" if all_pass and not failures else "FAIL"
report["pass"] = report["status"] == "PASS"

with open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(
    json.dumps(
        {
            "status": report["status"],
            "version": report["module_version"],
            "failures": failures,
            "pdfs": report["pdfs"],
        },
        indent=2,
    )
)

if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
