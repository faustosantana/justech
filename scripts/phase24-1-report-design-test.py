# -*- coding: utf-8 -*-
"""Fase 24.1 — Validación justech_report_design cotización QWeb+SCSS (solo TEST)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase24-1-report-design"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_NAME = "justech_report_design.report_hellenia_quotation_document"
DISC_REF = "P24-1E-QUOTE-5P-DISC"

report = {
    "phase": "24.1F-signatures-discount-totals-terms",
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


def render_case(key, so, fname, Report):
    pdf_bytes, _ = Report._render_qweb_pdf(REPORT_NAME, so.ids)
    html = Report._render_qweb_html(REPORT_NAME, so.ids)[0].decode("utf-8", errors="replace")
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    lc = len(so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment))
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
    check(f"{key}_no_totals_outer", "jt-hq-totals-outer" not in html)
    check(f"{key}_no_totals_gap", "jt-hq-totals-gap" not in html)
    check(f"{key}_totals_wrap", "jt-hq-totals-wrap" in html)
    check(f"{key}_totals_width_280", 'class="jt-hq-totals"' in html and 'width="280"' in html)
    check(
        f"{key}_no_sigs_table",
        'class="jt-hq-sigs"' in html
        and "<table" not in html.split('class="jt-hq-sigs"')[1].split("jt-hq-footer")[0]
        if 'class="jt-hq-sigs"' in html
        else False,
    )
    check(f"{key}_sig_push", "jt-hq-sig-push" in html)
    check(f"{key}_lower_zone", "jt-hq-lower" in html)
    check(f"{key}_anchor_sigs", ("jt-hq-lower-anchor" in html) == so.get_jt_quotation_anchor_signatures())

    has_disc = so.get_jt_quotation_has_discount()
    thead = html.split("<thead>")[1].split("</thead>")[0] if "<thead>" in html else ""
    check(f"{key}_discount_col", ("c-disc" in thead) == has_disc, f"has_disc={has_disc}")

    totals = html.split("jt-hq-totals")[1].split("</table>")[0] if "jt-hq-totals" in html else ""
    show_disc_totals = so.get_jt_quotation_show_discount_totals()
    check(
        f"{key}_discount_totals",
        ("Subtotal bruto" in totals) == show_disc_totals,
        f"show={show_disc_totals}",
    )
    if not show_disc_totals:
        check(f"{key}_no_discount_totals", "Descuento" not in totals)

    terms = so.get_jt_quotation_terms_display() or ""
    check(f"{key}_terms_in_pdf", terms[:40] in html if terms else False, terms[:60])
    check(
        f"{key}_terms_from_note",
        so.get_jt_quotation_terms_from_note() == bool((so.note or "").strip()),
    )

    push_px = so.get_jt_quotation_signature_push_px()
    check(f"{key}_sig_push_min", push_px >= 140 if so.get_jt_quotation_anchor_signatures() else push_px >= 0, push_px)

    shot = screenshot(path, os.path.join(OUT_DIR, f"screenshot_{key}"))
    if shot:
        report["screenshots"][key] = shot

    return html


# Instalar / actualizar módulo
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
if mod.state != "installed":
    mod.button_immediate_install()
else:
    mod.button_immediate_upgrade()
env.cr.commit()
report["module_version"] = mod.latest_version

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
SaleOrder = env["sale.order"]

cases = [
    ("1P", "quote_1", "quotation_1_product.pdf"),
    ("5P", "quote_5", "quotation_5_products.pdf"),
    ("25P", "quote_25", "quotation_25_products.pdf"),
]
orders = {}
for suffix, key, fname in cases:
    so = SaleOrder.search([("client_order_ref", "=", f"P23-3-QUOTE-{suffix}")], limit=1)
    if so:
        orders[key] = so
        render_case(key, so, fname, Report)

if "quote_1" in orders:
    pages = report["pdfs"]["quote_1"].get("pages")
    size = report["pdfs"]["quote_1"].get("size_bytes", 0)
    page_ok = pages == 1 if pages else size < 120000
    check("quote_1_single_page", page_ok, f"pages={pages} size={size}")

# Orden 5 productos con descuento (TEST)
so_disc = SaleOrder.search([("client_order_ref", "=", DISC_REF)], limit=1)
if not so_disc and orders.get("quote_5"):
    so_disc = orders["quote_5"].copy({"client_order_ref": DISC_REF})
if so_disc:
    product_lines = so_disc.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)
    if product_lines:
        if all((l.discount or 0) <= 0 for l in product_lines):
            product_lines[0].discount = 10.0
        env.cr.commit()
    render_case("quote_5_disc", so_disc, "quotation_5_products_discount.pdf", Report)
    html_disc = Report._render_qweb_html(REPORT_NAME, so_disc.ids)[0].decode("utf-8", errors="replace")
    check("quote_5_disc_has_percent", "10%" in html_disc or "10.0%" in html_disc)
    check("quote_5_disc_totals_breakdown", "Subtotal bruto" in html_disc and "Descuento" in html_disc)
else:
    check("quote_5_disc_order", False, "no base quote_5 to clone")

# Sin descuento en órdenes estándar
for key in ("quote_1", "quote_5", "quote_25"):
    if key in orders:
        html = Report._render_qweb_html(REPORT_NAME, orders[key].ids)[0].decode("utf-8", errors="replace")
        thead = html.split("<thead>")[1].split("</thead>")[0] if "<thead>" in html else ""
        check(f"{key}_no_discount_col", "c-disc" not in thead)

# Portal PDF (informativo)
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

view = env["ir.ui.view"].search([("key", "=", "sale.report_saleorder_raw")], limit=1)
children = env["ir.ui.view"].search([
    ("inherit_id", "=", view.id),
    ("key", "like", "justech_report_design.%"),
])
check("no_replace_standard", len(children) == 0, f"inherits={children.mapped('key')}")

report["pass"] = (
    len([k for k in report["failed_checks"] if k not in ("portal_pdf", "portal_pdf_info")]) == 0
    and "quote_1" in orders
    and "quote_5_disc" in report["pdfs"]
)

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE24_1:" + json.dumps(report, indent=2, ensure_ascii=False))
