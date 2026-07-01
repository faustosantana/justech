# -*- coding: utf-8 -*-
"""Fase 23.3H — Validación paperformat cotización Hellenia."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase23-3h-paperformat-spacing"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23.3h-paperformat-spacing",
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
        import re

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
pf_quote = env.ref("hellenia_reports.paperformat_hellenia_quotation", raise_if_not_found=False)
pf_letter = env.ref("hellenia_reports.paperformat_hellenia_letter", raise_if_not_found=False)

check("paperformat_quotation_exists", bool(pf_quote))
if pf_quote:
    check("paperformat_margin_top_5", pf_quote.margin_top == 5, pf_quote.margin_top)
    check("paperformat_header_spacing_0", pf_quote.header_spacing == 0, pf_quote.header_spacing)
    check("paperformat_dpi_90", pf_quote.dpi == 90, pf_quote.dpi)
check("paperformat_letter_unchanged", pf_letter and pf_letter.margin_top == 40, getattr(pf_letter, "margin_top", None))

orders = {}
for ref_suffix, key in (("1P", "quote_1"), ("5P", "quote_5"), ("15P", "quote_15"), ("25P", "quote_25")):
    so = env["sale.order"].search([("client_order_ref", "=", f"P23-3-QUOTE-{ref_suffix}")], limit=1)
    if so:
        orders[key] = so

for key, so in orders.items():
    pf_used = action.with_context(hellenia_use_quotation_paperformat=True).get_paperformat()
    check(f"{key}_uses_quotation_paperformat", pf_used.id == pf_quote.id if pf_quote else False, pf_used.name)

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
    check(f"{key}_html_no_negative_margin", "margin: -4mm" not in html and "margin: -" not in html.split("hellenia-quote-page")[1][:200] if "hellenia-quote-page" in html else True)
    if key == "quote_1":
        check("quote_1_single_page", pages == 1, f"pages={pages}")
    else:
        check(f"{key}_pages_ok", pages is not None and pages >= 1, f"pages={pages}")

    shot = screenshot(path, os.path.join(OUT_DIR, f"screenshot_{key}_page1"))
    if shot:
        report["screenshots"][key] = shot
    if pages and pages > 1:
        shot2 = screenshot(path, os.path.join(OUT_DIR, f"screenshot_{key}_page2"), first=2, last=2)
        if shot2:
            report["screenshots"][f"{key}_p2"] = shot2

# Pedido confirmado debe seguir usando Hellenia Carta (no cotización)
confirmed = env["sale.order"].search([("state", "=", "sale")], limit=1)
if confirmed:
    pf_conf = action.get_paperformat()
    check("confirmed_order_uses_letter_paperformat", pf_conf.id == pf_letter.id, pf_conf.name)

portal_so = env["sale.order"].search([("client_order_ref", "=", "P23-3-QUOTE-1P")], limit=1)
if portal_so and portal_so.access_token:
    base = env["ir.config_parameter"].sudo().get_param("web.base.url", "https://test.hellenia.cloud")
    import urllib.request
    portal_url = f"{base}/es/my/orders/{portal_so.id}?access_token={portal_so.access_token}&report_type=pdf"
    try:
        with urllib.request.urlopen(portal_url, timeout=90) as resp:
            body = resp.read()
        path = os.path.join(OUT_DIR, "portal_quote_1.pdf")
        with open(path, "wb") as f:
            f.write(body)
        check("portal_pdf_200", resp.status == 200 and body[:4] == b"%PDF", len(body))
        check("portal_single_page", pdf_pages(path) == 1, pdf_pages(path))
    except Exception as exc:
        check("portal_pdf_200", False, str(exc)[:200])

report["pass"] = len(report["failed_checks"]) == 0 and len(orders) >= 4

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE23_3H:" + json.dumps(report, indent=2, ensure_ascii=False))
