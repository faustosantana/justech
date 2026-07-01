# -*- coding: utf-8 -*-
"""Fase 23.3C — Validacion visual cotizacion rediseñada (portal + PDF)."""
from __future__ import annotations

import json
import os
import re
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
    "root_cause_previous": (
        "wkhtmltopdf no soporta flex/CSS variables/object-fit/emojis; "
        "layout Bootstrap + SCSS moderno rompio PDF"
    ),
    "module_version": None,
    "visual_checks": {},
    "http_checks": {},
    "pdfs": {},
    "ok": True,
    "pass": False,
    "ready_for_prod": False,
}

MOJIBAKE_MARKERS = ("Ã", "Â", "â€")
FORBIDDEN_EMOJI = ("☎", "🌐", "✉", "\ufe0f")


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


def pdf_text_snippet(path, max_chars=8000):
    try:
        r = subprocess.run(
            ["pdftotext", "-l", "2", path, "-"],
            capture_output=True,
            timeout=30,
            check=False,
        )
        if r.returncode == 0:
            return r.stdout.decode("utf-8", errors="replace")[:max_chars]
    except Exception:
        pass
    try:
        with open(path, "rb") as f:
            raw = f.read(200000)
        return raw.decode("latin-1", errors="replace")
    except Exception:
        return ""


def validate_pdf_text(text, label):
    for m in MOJIBAKE_MARKERS:
        check(f"{label}_no_mojibake_{m}", m not in text, m)
    for e in FORBIDDEN_EMOJI:
        check(f"{label}_no_emoji", e not in text, e)
    check(f"{label}_has_cotizacion", "COTIZACI" in text.upper(), text[:120])
    check(f"{label}_has_descripcion", "DESCRIPCI" in text.upper())
    check(f"{label}_has_condiciones", "CONDICIONES" in text.upper())
    check(f"{label}_has_republica", "Rep" in text and "Dominicana" in text)


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
    line_count = len(so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment))
    fname = f"quotation_{line_count}_product{'s' if line_count != 1 else ''}.pdf"
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    text = pdf_text_snippet(path)
    report["pdfs"][key] = {
        "status": "OK",
        "order": so.name,
        "file": fname,
        "size_bytes": len(pdf_bytes),
    }
    validate_pdf_text(text, key)
    check(f"{key}_pdf_magic", pdf_bytes[:4] == b"%PDF")

# Portal real
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
        text = pdf_text_snippet(portal_path)
        validate_pdf_text(text, "portal")
        # screenshot via pdftoppm
        try:
            subprocess.run(
                ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", portal_path,
                 os.path.join(OUT_DIR, "screenshot_portal_page1")],
                check=True,
                timeout=30,
            )
            report["screenshot"] = "screenshot_portal_page1.png"
        except Exception as exc:
            report["screenshot_error"] = str(exc)[:200]
    except urllib.error.HTTPError as exc:
        check_http("portal_pdf", False, exc.code, str(exc)[:300])
    except Exception as exc:
        check_http("portal_pdf", False, detail=str(exc)[:300])

failed = [k for k, v in report["visual_checks"].items() if v.get("status") == "FAIL"]
report["failed_checks"] = failed
report["pass"] = report["ok"] and not failed and report["http_checks"].get("portal_pdf", {}).get("status") == "PASS"

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE23_3C:" + json.dumps(report, indent=2, ensure_ascii=False))
