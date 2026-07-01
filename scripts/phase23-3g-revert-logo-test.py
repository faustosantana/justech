# -*- coding: utf-8 -*-
"""Fase 23.3G — Validación revert base con logo."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase23-3g-revert-logo-base"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23.3g-revert-logo-base",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "pass": False,
    "failed_checks": [],
    "checks": {},
}

def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:400]}
    if not ok:
        report["failed_checks"].append(key)


def pdf_pages(path):
    try:
        out = subprocess.check_output(["pdfinfo", path], stderr=subprocess.DEVNULL, timeout=15)
        for line in out.decode().splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        return None
    return None


def screenshot(pdf, base):
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf, base],
            check=True,
            timeout=60,
        )
        return os.path.basename(base) + ".png"
    except Exception:
        return None


mod = env["ir.module.module"].search([("name", "=", "hellenia_reports")], limit=1)
mod.button_immediate_upgrade()
env.cr.commit()

Report = env["ir.actions.report"]
action = env.ref("sale.action_report_saleorder")
so = env["sale.order"].search([("client_order_ref", "=", "P23-3-QUOTE-1P")], limit=1)
if not so:
    so = env["sale.order"].browse(135)

pdf_bytes, _ = Report._render_qweb_pdf(action.report_name, so.ids)
html = Report._render_qweb_html(action.report_name, so.ids)[0].decode("utf-8", errors="replace")

path = os.path.join(OUT_DIR, "quotation_1_product_S00134.pdf")
with open(path, "wb") as f:
    f.write(pdf_bytes)

check("pdf_magic", pdf_bytes[:4] == b"%PDF")
check("html_has_logo_img", "hellenia-quote-logo" in html)
check("html_logo_75px", "max-height: 75px" in html)
check("html_no_shell_wrapper", "hellenia-quote-shell" not in html)
check("html_no_generic_header_hide", ".header, .footer" not in html)
check("html_width_100", 'width="100%"' in html)
check("html_signatures", "hellenia-quote-sig-label" in html and "Entregado por" in html)
check("html_payment_es", "Contado" in html or "Crédito" in html)
check("html_no_immediate_payment", "Immediate Payment" not in html)

pages = pdf_pages(path)
check("single_page", pages == 1, f"pages={pages}")

shot = screenshot(path, os.path.join(OUT_DIR, "screenshot_quotation_1_product"))
if shot:
    report["screenshot"] = shot

report["order"] = so.name
report["pages"] = pages
report["size_bytes"] = len(pdf_bytes)
report["pass"] = len(report["failed_checks"]) == 0

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE23_3G:" + json.dumps(report, indent=2, ensure_ascii=False))
