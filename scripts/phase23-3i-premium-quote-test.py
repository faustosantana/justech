# -*- coding: utf-8 -*-
"""Fase 23.3I — Validación rediseño visual premium cotización."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase23-3i-premium-quote"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23.3i-premium-quote-visual",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "pass": False,
    "failed_checks": [],
    "checks": {},
    "pdfs": {},
    "screenshots": {},
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
        pass
    try:
        data = open(path, "rb").read()
        match = re.search(rb"/Type\s*/Pages[^>]*>>\s*.*?/Count\s+(\d+)", data, re.S)
        if match:
            return int(match.group(1))
        return len(re.findall(rb"(?<!\w)/Type\s*/Page(?!s)\b", data))
    except Exception:
        return None


def screenshot(pdf, base, first=1, last=1):
    try:
        subprocess.run(
            ["pdftoppm", "-f", str(first), "-l", str(last), "-png", "-singlefile", pdf, base],
            check=True,
            timeout=90,
        )
        return os.path.basename(base) + ".png"
    except Exception:
        return None


mod = env["ir.module.module"].search([("name", "=", "hellenia_reports")], limit=1)
mod.button_immediate_upgrade()
env.cr.commit()
report["module_version"] = mod.latest_version

Report = env["ir.actions.report"]
action = env.ref("sale.action_report_saleorder")

orders = {}
for ref_suffix, key in (("1P", "quote_1"), ("5P", "quote_5"), ("15P", "quote_15"), ("25P", "quote_25")):
    so = env["sale.order"].search([("client_order_ref", "=", f"P23-3-QUOTE-{ref_suffix}")], limit=1)
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

    pages = pdf_pages(path)
    report["pdfs"][key] = {
        "order": so.name,
        "file": fname,
        "pages": pages,
        "line_count": line_count,
        "size_bytes": len(pdf_bytes),
    }
    check(f"{key}_pdf_magic", pdf_bytes[:4] == b"%PDF")
    check(f"{key}_html_logo", "hellenia-quote-logo" in html)
    check(f"{key}_no_excel_borders", "border: 1px solid #e5e5e5" not in html)
    check(f"{key}_premium_classes", "hellenia-quote-hdr-sep" in html and "section-row" in html or line_count == 1)
    if key == "quote_1":
        check("quote_1_single_page", pages == 1, f"pages={pages}")
    else:
        check(f"{key}_pages_ok", pages is not None and pages >= 1, f"pages={pages}")

    shot = screenshot(path, os.path.join(OUT_DIR, f"screenshot_{key}_page1"))
    if shot:
        report["screenshots"][key] = shot

report["pass"] = len(report["failed_checks"]) == 0 and len(orders) >= 4

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE23_3I:" + json.dumps(report, indent=2, ensure_ascii=False))
