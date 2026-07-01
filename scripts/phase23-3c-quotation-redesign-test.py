# -*- coding: utf-8 -*-
"""Fase 23.3C — Validacion cotizacion rediseñada (portal + HTML + PDF texto)."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/evidence/phase23-3c-quotation-redesign"
if not os.path.isdir("/evidence"):
    OUT_DIR = "/tmp/phase23-3c-quotation-redesign"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23.3c-quotation-redesign",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "root_cause": (
        "wkhtmltopdf 0.12.6 sin --encoding utf-8: acentos y NBSP monetarios "
        "se renderizan como mojibake (CotizaciÃ³n, $Â) aunque el HTML sea UTF-8 correcto"
    ),
    "fix": (
        "ir.actions.report._build_wkhtmltopdf_args fuerza --encoding utf-8; "
        "template table-based #3E4827 con acentos UTF-8 y logo max 90px inline"
    ),
    "module_version": None,
    "visual_checks": {},
    "http_checks": {},
    "pdfs": {},
    "ok": True,
    "pass": False,
    "ready_for_prod": False,
}

MOJIBAKE = ("Ã³", "Ã©", "Ã­", "Ã¡", "Ãº", "Ã±", "RepÃ", "CotizaciÃ", "$Â", "Â ")
REQUIRED_PDF = ("COTIZACIÓN", "República", "CONDICIONES")
FORBIDDEN = ("display: flex", "var(--", "object-fit", "☎", "🌐", "✉", "<svg")


def check(key, ok, detail=""):
    report["visual_checks"][key] = {
        "status": "PASS" if ok else "FAIL",
        "detail": str(detail)[:500],
    }
    if not ok:
        report["ok"] = False


def check_http(key, ok, code=None, detail=""):
    report["http_checks"][key] = {
        "status": "PASS" if ok else "FAIL",
        "http_status": code,
        "detail": str(detail)[:500],
    }
    if not ok:
        report["ok"] = False


def extract_pdf_text(pdf_path):
    """Extract text from PDF for mojibake detection."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception:
        pass
    try:
        out = subprocess.check_output(
            ["pdftotext", "-enc", "UTF-8", pdf_path, "-"],
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        return out.decode("utf-8", errors="replace")
    except Exception:
        return ""


def validate_html(html, label):
    for bad in MOJIBAKE:
        check(f"{label}_html_no_mojibake_{bad[:6]}", bad not in html, bad)
    for bad in FORBIDDEN:
        safe = bad[:10].replace(" ", "_").replace("<", "")
        check(f"{label}_html_no_{safe}", bad not in html, bad)
    check(f"{label}_html_has_cotizacion", "COTIZACI" in html.upper())
    check(f"{label}_html_has_tables", "<table" in html and "hellenia-quote-items" in html)
    check(f"{label}_html_logo_max_90", "max-height: 90px" in html)
    check(f"{label}_html_brand_color", "#3E4827" in html.upper() or "#3e4827" in html.lower())
    check(f"{label}_html_no_bootstrap_row", 'class="row hellenia' not in html)


def validate_pdf_text(text, label):
    for bad in MOJIBAKE:
        check(f"{label}_pdf_no_mojibake_{bad[:6]}", bad not in text, bad)
    for req in REQUIRED_PDF:
        safe = req.replace(" ", "_")[:12]
        check(f"{label}_pdf_has_{safe}", req in text, f"missing {req}")
    check(f"{label}_pdf_text_len", len(text.strip()) > 200, len(text.strip()))


def render_screenshot(pdf_path, out_base):
    for tool, args in (
        ("pdftoppm", ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf_path, out_base]),
        ("mutool", ["mutool", "draw", "-o", f"{out_base}.png", "-F", "png", "-r", "150", pdf_path, "1"]),
    ):
        try:
            subprocess.run(args, check=True, timeout=60)
            return f"{os.path.basename(out_base)}.png"
        except Exception:
            continue
    try:
        import fitz

        doc = fitz.open(pdf_path)
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
        shot = f"{out_base}.png"
        pix.save(shot)
        doc.close()
        return os.path.basename(shot)
    except Exception as exc:
        report["screenshot_error"] = str(exc)[:200]
        return None


mod = env["ir.module.module"].search([("name", "=", "hellenia_reports")], limit=1)
mod.button_immediate_upgrade()
env.cr.commit()
report["module_version"] = mod.latest_version

Report = env["ir.actions.report"]
SaleOrder = env["sale.order"]
action = env.ref("sale.action_report_saleorder")

orders = {}
for ref_suffix, key in (("1P", "quote_1"), ("5P", "quote_5"), ("15P", "quote_15")):
    so = SaleOrder.search([("client_order_ref", "=", f"P23-3-QUOTE-{ref_suffix}")], limit=1)
    if so:
        orders[key] = so

for key, so in orders.items():
    pdf_bytes, _ = Report._render_qweb_pdf(action.report_name, so.ids)
    html = Report._render_qweb_html(action.report_name, so.ids)[0].decode("utf-8", errors="replace")
    line_count = len(so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment))
    fname = f"quotation_{line_count}_product{'s' if line_count != 1 else ''}.pdf"
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    pdf_text = extract_pdf_text(path)
    report["pdfs"][key] = {
        "status": "OK",
        "order": so.name,
        "file": fname,
        "size_bytes": len(pdf_bytes),
        "text_sample": pdf_text[:300],
    }
    validate_html(html, key)
    validate_pdf_text(pdf_text, key)
    check(f"{key}_pdf_magic", pdf_bytes[:4] == b"%PDF")
    check(f"{key}_pdf_size", len(pdf_bytes) > 15000, len(pdf_bytes))

portal_so = SaleOrder.browse(135)
if not portal_so.exists() and orders:
    portal_so = list(orders.values())[0]

if portal_so and portal_so.access_token:
    base = env["ir.config_parameter"].sudo().get_param("web.base.url", "https://test.hellenia.cloud")
    url = f"{base}/es/my/orders/{portal_so.id}?access_token={portal_so.access_token}&report_type=pdf"
    portal_path = os.path.join(OUT_DIR, "portal_order_135.pdf")
    try:
        with urllib.request.urlopen(url, timeout=90) as resp:
            body = resp.read()
            code = resp.status
        with open(portal_path, "wb") as f:
            f.write(body)
        check_http("portal_pdf", code == 200 and body[:4] == b"%PDF", code, len(body))
        html = Report._render_qweb_html(action.report_name, portal_so.ids)[0].decode("utf-8", errors="replace")
        validate_html(html, "portal")
        portal_text = extract_pdf_text(portal_path)
        validate_pdf_text(portal_text, "portal")
        report["pdfs"]["portal"] = {
            "status": "OK",
            "order": portal_so.name,
            "file": "portal_order_135.pdf",
            "size_bytes": len(body),
            "text_sample": portal_text[:300],
        }
        shot = render_screenshot(portal_path, os.path.join(OUT_DIR, "screenshot_portal_page1"))
        if shot:
            report["screenshot"] = shot
    except urllib.error.HTTPError as exc:
        check_http("portal_pdf", False, exc.code, str(exc)[:300])
    except Exception as exc:
        check_http("portal_pdf", False, detail=str(exc)[:300])

failed = [k for k, v in report["visual_checks"].items() if v.get("status") == "FAIL"]
report["failed_checks"] = failed
report["pass"] = (
    report["ok"]
    and not failed
    and report["http_checks"].get("portal_pdf", {}).get("status") == "PASS"
)

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE23_3C:" + json.dumps(report, indent=2, ensure_ascii=False))
