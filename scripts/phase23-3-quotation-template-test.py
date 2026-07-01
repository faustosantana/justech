# -*- coding: utf-8 -*-
"""Fase 23.3 — Validación template premium cotización Hellenia (TEST)."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

REF = "P23-3-QUOTE"
OUT_DIR = "/evidence/phase23-3-quotation-template"
if not os.path.isdir("/evidence"):
    OUT_DIR = "/tmp/phase23-3-quotation-template"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23.3-quotation-template",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module_version": None,
    "quotations": {},
    "pdfs": {},
    "visual_checks": {},
    "editable_terms_test": {},
    "ok": True,
    "pass": False,
}

FORBIDDEN_EN = (
    "Quotation",
    "Customer",
    "Salesperson",
    "Payment Terms",
    "Expiration",
    "Untaxed Amount",
)
FORBIDDEN_COLORS = ("#1a365d", "#c9a227", "1a365d", "c9a227")
REQUIRED_ES = (
    "COTIZACIÓN",
    "INFORMACIÓN DEL CLIENTE",
    "INFORMACIÓN DEL VENDEDOR",
    "TÉRMINOS DE PAGO",
    "DESCRIPCIÓN",
    "CANTIDAD",
    "PRECIO UNITARIO",
    "SUBTOTAL",
    "ITBIS",
    "CONDICIONES",
    "Santo Domingo, República Dominicana",
)
REQUIRED_CLASSES = (
    "hellenia-quote-page",
    "hellenia-quote-header",
    "hellenia-quote-company",
    "hellenia-quote-title-band",
    "hellenia-card",
    "hellenia-card-title",
    "hellenia-items-table",
    "hellenia-totals",
    "hellenia-conditions",
    "hellenia-footer-contact",
)


def check(key, ok, detail=""):
    report["visual_checks"][key] = {
        "status": "PASS" if ok else "FAIL",
        "detail": str(detail)[:500],
    }
    if not ok:
        report["ok"] = False


mod = env["ir.module.module"].search([("name", "=", "hellenia_reports")], limit=1)
if not mod or mod.state != "installed":
    report["ok"] = False
    report["error"] = "hellenia_reports not installed"
    print("PHASE23_3:" + json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(1)

mod.button_immediate_upgrade()
env.cr.commit()
report["module_version"] = mod.latest_version

company = env.company
check("01_field_hellenia_quotation_terms", "hellenia_quotation_terms" in company._fields)
check(
    "02_default_terms_populated",
    bool(company.get_hellenia_quotation_terms_display()),
    (company.get_hellenia_quotation_terms_display() or "")[:80],
)

SaleOrder = env["sale.order"]
Report = env["ir.actions.report"]
Partner = env["res.partner"]
Product = env["product.product"]

customer = Partner.search([("customer_rank", ">", 0)], limit=1)
if not customer:
    customer = Partner.create({"name": f"{REF} Cliente", "ref": REF, "customer_rank": 1})

products = Product.search([("sale_ok", "=", True)], limit=20)
check("03_products_available", len(products) >= 1, len(products))
if len(products) < 1:
    print("PHASE23_3:" + json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(1)

tax_sale = env["account.tax"].search(
    [("type_tax_use", "=", "sale"), ("company_id", "=", company.id)],
    limit=1,
)
payment_term = env["account.payment.term"].search([], limit=1)
user = env.user


def build_quotation(line_count, suffix):
    name_ref = f"{REF}-{suffix}"
    existing = SaleOrder.search([("client_order_ref", "=", name_ref)], limit=1)
    if existing:
        existing.order_line.unlink()
        so = existing
    else:
        so = SaleOrder.create(
            {
                "partner_id": customer.id,
                "client_order_ref": name_ref,
                "validity_date": date.today() + timedelta(days=5),
                "payment_term_id": payment_term.id if payment_term else False,
                "user_id": user.id,
            }
        )
    lines = []
    for i in range(line_count):
        p = products[i % len(products)]
        lines.append(
            Command.create(
                {
                    "product_id": p.id,
                    "product_uom_qty": 1 + (i % 3),
                    "price_unit": 1000.0 + (i * 250),
                    "tax_id": [Command.set(tax_sale.ids)] if tax_sale else [],
                }
            )
        )
    so.write({"order_line": lines})
    return so


def validate_html(html, label):
    html_lower = html.lower()
    for word in FORBIDDEN_EN:
        check(f"{label}_no_{word.lower().replace(' ', '_')}", word not in html, word)
    for color in FORBIDDEN_COLORS:
        check(f"{label}_no_color_{color.replace('#', '')}", color not in html_lower, color)
    check(f"{label}_no_qr", "hellenia-qr" not in html_lower and "qrcode" not in html_lower)
    check(f"{label}_no_ncf", "ncf" not in html_lower)
    for text in REQUIRED_ES:
        check(f"{label}_has_{text[:20].replace(' ', '_')}", text in html, text)
    for css_class in REQUIRED_CLASSES:
        check(f"{label}_class_{css_class}", css_class in html, css_class)
    check(f"{label}_brand_color", "#3e4827" in html_lower or "3e4827" in html_lower)


def save_pdf(key, so, line_count):
    action = env.ref("sale.action_report_saleorder")
    pdf_bytes, _fmt = Report._render_qweb_pdf(action.report_name, so.ids)
    html_bytes, _ = Report._render_qweb_html(action.report_name, so.ids)
    html = html_bytes.decode("utf-8", errors="replace")

    fname = f"quotation_{line_count}_product{'s' if line_count != 1 else ''}.pdf"
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    report["quotations"][key] = {
        "name": so.name,
        "id": so.id,
        "lines": line_count,
        "client_order_ref": so.client_order_ref,
    }
    report["pdfs"][key] = {
        "status": "OK",
        "file": fname,
        "path": path,
        "size_bytes": len(pdf_bytes),
    }
    validate_html(html, key)
    return html


for count, suffix in ((1, "1P"), (5, "5P"), (15, "15P")):
    so = build_quotation(count, suffix)
    save_pdf(f"quote_{count}", so, count)

terms_so = build_quotation(1, "TERMS")
custom_note = "(TEST) Condición personalizada en nota del pedido."
terms_so.write({"note": custom_note})
html_note = save_pdf("quote_custom_note", terms_so, 1)
check("terms_order_note_used", custom_note in html_note)

terms_so.write({"note": False})
html_company = save_pdf("quote_company_terms", terms_so, 1)
check(
    "terms_company_fallback",
    "(a) Las piezas ofrecidas" in html_company,
    company.get_hellenia_quotation_terms_display()[:60],
)

original_terms = company.hellenia_quotation_terms
company.write({"hellenia_quotation_terms": "(z) Término de prueba editable desde empresa."})
env.cr.commit()
terms_so.write({"note": False})
html_edited = save_pdf("quote_edited_company_terms", terms_so, 1)
check("terms_company_editable", "(z) Término de prueba editable" in html_edited)
company.write({"hellenia_quotation_terms": original_terms})
env.cr.commit()

report["editable_terms_test"] = {
    "order_note_priority": "PASS"
    if report["visual_checks"].get("terms_order_note_used", {}).get("status") == "PASS"
    else "FAIL",
    "company_terms_fallback": "PASS"
    if report["visual_checks"].get("terms_company_fallback", {}).get("status") == "PASS"
    else "FAIL",
    "company_terms_editable": "PASS"
    if report["visual_checks"].get("terms_company_editable", {}).get("status") == "PASS"
    else "FAIL",
}

failed = [k for k, v in report["visual_checks"].items() if v.get("status") == "FAIL"]
report["failed_checks"] = failed
report["pass"] = report["ok"] and len(failed) == 0
report["ready_for_prod"] = False

validation_path = os.path.join(OUT_DIR, "validation.json")
with open(validation_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE23_3:" + json.dumps(report, indent=2, ensure_ascii=False))
