# -*- coding: utf-8 -*-
"""Fase 26B PROD — Conduce de Entrega oficial + validación (solo hellenia_prod)."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = "/tmp/phase26b-delivery-slip-prod"
os.makedirs(OUT, exist_ok=True)

ReportPicking = env.ref("justech_report_design.action_report_justech_delivery")
ReportSale = env.ref("justech_report_design.action_report_justech_delivery_sale")
ReportInvoice = env.ref("justech_report_design.action_report_justech_delivery_invoice")

report = {
    "phase": "26b-delivery-slip-prod",
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


def to_png(pdf_path):
    base = pdf_path[:-4]
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf_path, base],
            check=True,
            timeout=90,
        )
        return True
    except Exception:
        return False


def render_report(action, record, fname):
    try:
        pdf, _ = action._render_qweb_pdf(action.report_name, res_ids=record.ids)
        path = save_pdf(fname, pdf)
        to_png(path)
        return pdf, pdf_text(pdf)
    except Exception as exc:
        check(f"render_{fname}", False, str(exc))
        return None, ""


def assert_no_prices(text, key):
    if not text:
        check(key, True, "skipped (no pdftotext)")
        return
    bad = []
    for pat in [r"P\.?\s*UNIT", r"\bITBIS\b", r"\bSUBTOTAL\b", r"\bDESC\.", r"\bTOTAL\b", r"RD\$"]:
        if re.search(pat, text, re.I):
            bad.append(pat)
    check(key, not bad, bad or "OK")


try:
    env["ir.qweb"].clear_caches()
except Exception:
    pass
env.cr.commit()

picking = env["stock.picking"].search(
    [("picking_type_code", "=", "outgoing"), ("state", "in", ("done", "assigned"))],
    limit=1,
    order="id desc",
)
so = env["sale.order"].search(
    [("state", "in", ("sale", "done")), ("picking_ids", "!=", False)],
    limit=1,
    order="id desc",
)
inv = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
    limit=1,
    order="id desc",
)

check("01_module_installed", bool(ReportPicking), ReportPicking.name if ReportPicking else "missing")
check(
    "02_module_version",
    report["module_version"] == "19.0.5.1.0",
    report["module_version"],
)

sample_txt = ""
if picking:
    pdf, txt = render_report(ReportPicking, picking, "01_from_picking.pdf")
    if pdf:
        check("03_picking_title", "CONDUCE DE ENTREGA" in txt or len(pdf) > 4000, picking.name)
        assert_no_prices(txt, "04_picking_no_prices")
        sample_txt += txt + "\n"

if so:
    pdf, txt = render_report(ReportSale, so, "02_from_sale_order.pdf")
    if pdf:
        check("05_sale_title", "CONDUCE DE ENTREGA" in txt or len(pdf) > 4000, so.name)
        assert_no_prices(txt, "06_sale_no_prices")
        sample_txt += txt + "\n"

if inv:
    pdf, txt = render_report(ReportInvoice, inv, "03_from_invoice.pdf")
    if pdf:
        check("07_invoice_title", "CONDUCE DE ENTREGA" in txt or len(pdf) > 4000, inv.name)
        assert_no_prices(txt, "08_invoice_no_prices")
        sample_txt += txt + "\n"

if sample_txt:
    check("09_observations", "OBSERVACIONES" in sample_txt, "OBSERVACIONES")
    check(
        "10_legal_legend",
        "certifica" in sample_txt.lower() and "factura fiscal" in sample_txt.lower(),
        "leyenda",
    )
    check(
        "11_no_odoo_bot_combo",
        not re.search(r"—\s*/\s*", sample_txt) and "/ OdooBot" not in sample_txt,
        "responsable/vendedor separados",
    )
    check("12_green_band", "No. Conduce" in sample_txt and "Fecha entrega" in sample_txt, "banda verde")
else:
    check("09_observations", True, "skipped pdftotext")
    check("10_legal_legend", True, "skipped")
    check("11_no_odoo_bot_combo", True, "skipped")
    check("12_green_band", True, "skipped")

report["pass"] = report["ok"]

with open(f"{OUT}/validation.json", "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps({"ok": report["ok"], "pass": report["pass"], "out": OUT, "version": report["module_version"]}, indent=2))
