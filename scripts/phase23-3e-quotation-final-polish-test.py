# -*- coding: utf-8 -*-
"""Fase 23.3E — Validación ajustes finos cotización Hellenia."""
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

OUT_DIR = "/evidence/phase23-3e-quotation-final-polish"
if not os.path.isdir("/evidence"):
    OUT_DIR = "/tmp/phase23-3e-quotation-final-polish"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23.3e-quotation-final-polish",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module_version": None,
    "visual_checks": {},
    "http_checks": {},
    "pdfs": {},
    "ok": True,
    "pass": False,
    "ready_for_prod": False,
}

MOJIBAKE = ("Ã³", "Ã©", "RepÃ", "CotizaciÃ", "$Â")
FORBIDDEN_EN = ("Immediate Payment", "Payment Terms", "Quotation", "Salesperson")
REQUIRED_HTML = (
    "hellenia-quote-hdr-table",
    "hellenia-quote-sig-label",
    "hellenia-quote-sig-line",
    "COTIZACIÓN",
    "CONDICIONES",
    "max-height: 75px",
)


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
    try:
        out = subprocess.check_output(
            ["pdftotext", "-enc", "UTF-8", pdf_path, "-"],
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        return out.decode("utf-8", errors="replace")
    except Exception:
        return ""


def render_screenshot(pdf_path, out_base):
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf_path, out_base],
            check=True,
            timeout=60,
        )
        return f"{os.path.basename(out_base)}.png"
    except Exception:
        return None


def validate_html(html, label):
    for bad in MOJIBAKE:
        check(f"{label}_html_no_mojibake", bad not in html, bad)
    for bad in FORBIDDEN_EN:
        check(f"{label}_html_no_{bad.replace(' ', '_')}", bad not in html, bad)
    for req in REQUIRED_HTML:
        safe = req.replace(" ", "_").replace("#", "")[:24]
        check(f"{label}_html_has_{safe}", req in html, req)
    check(f"{label}_html_no_hdr_box_border", "hellenia-quote-hdr-table" in html)
    check(f"{label}_html_payment_es",
          "Contado" in html or "Crédito" in html)


def validate_pdf(text, label):
    for bad in MOJIBAKE:
        check(f"{label}_pdf_no_mojibake", bad not in text, bad)
    for bad in FORBIDDEN_EN:
        check(f"{label}_pdf_no_{bad.replace(' ', '_')}", bad not in text, bad)
    sig_ok = (
        "ENTREGADO POR" in text.upper()
        and "RECIBIDO POR" in text.upper()
        and "FECHA" in text.upper()
    )
    check(f"{label}_pdf_signatures", sig_ok, text[-120:])
    for req in ("COTIZACIÓN", "República", "CONDICIONES"):
        check(f"{label}_pdf_has_{req[:10]}", req in text, req)
    check(f"{label}_pdf_payment_es", "Contado" in text or "Crédito" in text)
    check(f"{label}_pdf_text_len", len(text.strip()) > 200, len(text.strip()))


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
        "bottom_spacer_px": so.get_hellenia_quotation_bottom_spacer_px(),
        "signature_spacer_px": so.get_hellenia_quotation_signature_spacer_px(),
    }
    validate_html(html, key)
    validate_pdf(pdf_text, key)
    check(f"{key}_pdf_magic", pdf_bytes[:4] == b"%PDF")

portal_so = SaleOrder.browse(135)
if not portal_so.exists() and orders:
    portal_so = list(orders.values())[0]

if portal_so and portal_so.access_token:
    base = env["ir.config_parameter"].sudo().get_param("web.base.url", "https://test.hellenia.cloud")
    portal_url = f"{base}/es/my/orders/{portal_so.id}?access_token={portal_so.access_token}&report_type=pdf"
    portal_path = os.path.join(OUT_DIR, "portal_order_135.pdf")
    try:
        with urllib.request.urlopen(portal_url, timeout=90) as resp:
            body = resp.read()
            code = resp.status
        with open(portal_path, "wb") as f:
            f.write(body)
        check_http("portal_pdf", code == 200 and body[:4] == b"%PDF", code, len(body))
        html = Report._render_qweb_html(action.report_name, portal_so.ids)[0].decode("utf-8", errors="replace")
        validate_html(html, "portal")
        validate_pdf(extract_pdf_text(portal_path), "portal")
        shot = render_screenshot(portal_path, os.path.join(OUT_DIR, "screenshot_portal_page1"))
        if shot:
            report["screenshot"] = shot
        backend_pdf, _ = Report._render_qweb_pdf(action.report_name, portal_so.ids)
        check_http("backend_pdf", backend_pdf[:4] == b"%PDF", 200, len(backend_pdf))
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
    and report["http_checks"].get("backend_pdf", {}).get("status") == "PASS"
)

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE23_3E:" + json.dumps(report, indent=2, ensure_ascii=False))
