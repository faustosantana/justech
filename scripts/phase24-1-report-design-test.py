# -*- coding: utf-8 -*-
"""Fase 24.1 — Validación justech_report_design cotización QWeb+SCSS (solo TEST)."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase24-1-report-design"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_NAME = "justech_report_design.report_hellenia_quotation_document"

report = {
    "phase": "24.1-report-design-integration",
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


# Instalar / actualizar módulo
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
if mod.state != "installed":
    mod.button_immediate_install()
else:
    mod.button_immediate_upgrade()
env.cr.commit()
report["module_version"] = mod.latest_version

# Limpiar cache QWeb
env.registry.clear_cache()
try:
    env["ir.qweb"].clear_caches()
except Exception:
    pass

action = env.ref("justech_report_design.action_report_hellenia_quotation")
check("action_exists", bool(action))
check("report_name", action.report_name == REPORT_NAME)
check(
    "paperformat",
    action.paperformat_id.name == "Hellenia Quotation Paperformat",
    action.paperformat_id.name if action.paperformat_id else "",
)
pf = action.paperformat_id
if pf:
    check("pf_margins", pf.margin_top == 5 and pf.margin_bottom == 8 and pf.margin_left == 8 and pf.margin_right == 8)
    check("pf_dpi", pf.dpi == 90)

Report = env["ir.actions.report"]
cases = [("1P", "quote_1"), ("5P", "quote_5"), ("20P", "quote_20"), ("25P", "quote_25")]
orders = {}
for suffix, key in cases:
    so = env["sale.order"].search([("client_order_ref", "=", f"P23-3-QUOTE-{suffix}")], limit=1)
    if so:
        orders[key] = so
if "quote_20" not in orders and "quote_25" in orders:
    orders["quote_20"] = orders.pop("quote_25")

for key, so in orders.items():
    pdf_bytes, _ = Report._render_qweb_pdf(REPORT_NAME, so.ids)
    html = Report._render_qweb_html(REPORT_NAME, so.ids)[0].decode("utf-8", errors="replace")
    lc = len(so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment))
    fname = f"quotation_{lc}_product{'s' if lc != 1 else ''}.pdf"
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    pages = pdf_pages(path)
    report["pdfs"][key] = {
        "order": so.name,
        "file": fname,
        "line_count": lc,
        "pages": pages,
        "size_bytes": len(pdf_bytes),
    }

    check(f"{key}_pdf", pdf_bytes[:4] == b"%PDF")
    check(f"{key}_jt_template", "jt-hq-page" in html and "jt-hq-band" in html)
    check(f"{key}_scss_class", "jt-hq-band" in html and "jt-hq-logo" in html)
    check(f"{key}_no_inline_style_block", "<style type=\"text/css\">" not in html)
    check(f"{key}_no_external_layout", "external_layout_hellenia" not in html)
    check(f"{key}_band", "jt-hq-band-title" in html)
    check(f"{key}_no_vendor_email", "odoobot@example.com" not in html.lower())
    check(f"{key}_no_immediate", "immediate payment" not in html.lower())
    check(f"{key}_no_excel", "border: 1px solid" not in html)
    check(f"{key}_grand", "grand" in html)
    if key == "quote_1":
        page_ok = pages == 1 if pages else len(pdf_bytes) < 120000
        check("quote_1_single_page", page_ok, f"pages={pages} size={len(pdf_bytes)}")

    shot = screenshot(path, os.path.join(OUT_DIR, f"screenshot_{key}"))
    if shot:
        report["screenshots"][key] = shot

# Portal PDF (reporte paralelo — puede requerir login; informativo)
so_portal = orders.get("quote_1")
if so_portal:
    import urllib.request

    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url", "")
    pdf_url = f"{base_url}/report/pdf/{REPORT_NAME}/{so_portal.id}?access_token={so_portal.access_token}"
    try:
        req = urllib.request.Request(pdf_url, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
            is_pdf = data[:4] == b"%PDF"
            report["portal"] = {"status": resp.status, "size": len(data), "is_pdf": is_pdf}
            check("portal_pdf", is_pdf, f"status={resp.status} size={len(data)}")
    except Exception as e:
        report["portal"] = {"status": "error", "detail": str(e)[:200]}
        check("portal_pdf_info", False, str(e)[:200])

# Verificar que sale.report_saleorder no fue reemplazado
view = env["ir.ui.view"].search([("key", "=", "sale.report_saleorder_raw")], limit=1)
children = env["ir.ui.view"].search([
    ("inherit_id", "=", view.id),
    ("key", "like", "justech_report_design.%"),
])
check("no_replace_standard", len(children) == 0, f"inherits={children.mapped('key')}")

report["pass"] = len([k for k in report["failed_checks"] if k not in ("portal_pdf", "portal_pdf_info")]) == 0 and "quote_1" in orders

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE24_1:" + json.dumps(report, indent=2, ensure_ascii=False))
