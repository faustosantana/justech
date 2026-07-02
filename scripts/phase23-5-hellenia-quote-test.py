# -*- coding: utf-8 -*-
"""Fase 23.5 — Validación reporte independiente cotización Hellenia."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase23-5-hellenia-quote"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23.5-independent-quote-report",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "pass": False,
    "failed_checks": [],
    "checks": {},
    "pdfs": {},
    "screenshots": {},
    "portal": {},
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


def screenshot(pdf, base):
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf, base],
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
hellenia_action = env.ref("hellenia_reports.action_report_hellenia_quotation")
std_action = env.ref("sale.action_report_saleorder")

# Verificar reporte independiente existe
check("action_exists", bool(hellenia_action))
check(
    "report_name",
    hellenia_action.report_name == "hellenia_reports.report_hellenia_quotation",
    hellenia_action.report_name,
)
check(
    "paperformat",
    hellenia_action.paperformat_id
    and hellenia_action.paperformat_id.id
    == env.ref("hellenia_reports.paperformat_hellenia_quotation").id,
)

cases = [
    ("1P", "quote_1"),
    ("5P", "quote_5"),
    ("20P", "quote_20"),
    ("25P", "quote_25"),
]
orders = {}
for ref_suffix, key in cases:
    so = env["sale.order"].search([("client_order_ref", "=", f"P23-3-QUOTE-{ref_suffix}")], limit=1)
    if so:
        orders[key] = so

# Usar 25P si no hay 20P
if "quote_20" not in orders and "quote_25" in orders:
    orders["quote_20"] = orders.pop("quote_25")

for key, so in orders.items():
    lc = len(so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment))

    # Backend: reporte independiente directo
    pdf_bytes, _ = Report._render_qweb_pdf(hellenia_action.report_name, so.ids)
    html = Report._render_qweb_html(hellenia_action.report_name, so.ids)[0].decode("utf-8", errors="replace")

    # Redirect: sale.report_saleorder para draft/sent
    pdf_std, _ = Report._render_qweb_pdf(std_action.report_name, so.ids)
    html_std = Report._render_qweb_html(std_action.report_name, so.ids)[0].decode("utf-8", errors="replace")

    fname = f"quotation_{lc}_product{'s' if lc != 1 else ''}.pdf"
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    pages = pdf_pages(path)
    report["pdfs"][key] = {
        "order": so.name,
        "file": fname,
        "pages": pages,
        "line_count": lc,
        "size_bytes": len(pdf_bytes),
    }

    check(f"{key}_pdf", pdf_bytes[:4] == b"%PDF")
    check(f"{key}_redirect_pdf", pdf_std[:4] == b"%PDF")
    check(f"{key}_uses_independent", "hellenia_quote_body" in html or "hq-doc" in html)
    check(f"{key}_no_external_layout", "external_layout" not in html)
    check(f"{key}_no_sale_document", "report_saleorder_document" not in html)
    check(f"{key}_redirect_independent", "hellenia_quote_body" in html_std or "hq-doc" in html_std)
    check(f"{key}_band_white", "hq-band-title" in html and "color: #ffffff" in html)
    check(f"{key}_no_icons", "svg" not in html.lower())
    check(f"{key}_no_vendor_email", "odoobot@example.com" not in html.lower())
    check(f"{key}_no_immediate", "immediate payment" not in html.lower())
    check(f"{key}_no_excel", "border: 1px solid" not in html)
    check(f"{key}_grand_total", "grand" in html)

    if key == "quote_1":
        check("quote_1_single_page", pages == 1, f"pages={pages}")
        check("quote_1_lines", lc == 1, f"lines={lc}")
    elif key == "quote_5":
        check("quote_5_single_page", pages == 1, f"pages={pages}")
    else:
        check(f"{key}_pages_ok", pages is not None and pages >= 1, f"pages={pages}")

    shot = screenshot(path, os.path.join(OUT_DIR, f"screenshot_{key}"))
    if shot:
        report["screenshots"][key] = shot

# Portal HTTP check
so_portal = orders.get("quote_1")
if so_portal:
    token = so_portal.access_token
    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url", "")
    portal_url = f"{base_url}/my/orders/{so_portal.id}?access_token={token}"
    pdf_url = f"{base_url}/report/pdf/sale.report_saleorder/{so_portal.id}?access_token={token}"
    try:
        import urllib.request

        req = urllib.request.Request(portal_url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            report["portal"]["order_page_status"] = resp.status
            check("portal_order_200", resp.status == 200, resp.status)
        req2 = urllib.request.Request(pdf_url, method="GET")
        with urllib.request.urlopen(req2, timeout=60) as resp2:
            report["portal"]["pdf_status"] = resp2.status
            report["portal"]["pdf_size"] = len(resp2.read())
            check("portal_pdf_200", resp2.status == 200, resp2.status)
    except Exception as e:
        check("portal_order_200", False, str(e))
        check("portal_pdf_200", False, str(e))

report["pass"] = len(report["failed_checks"]) == 0 and "quote_1" in orders

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE23_5:" + json.dumps(report, indent=2, ensure_ascii=False))
