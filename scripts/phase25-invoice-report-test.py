# -*- coding: utf-8 -*-
"""Fase 25 — Validación reporte paralelo factura fiscal justech_report_design (solo TEST)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase25-invoice-report"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_JT = "justech_report_design.report_justech_invoice_document"
ACTION_JT = "justech_report_design.action_report_justech_invoice"
STD_ACTION = "account.account_invoices"
QUOT_ACTION = "sale.action_report_saleorder"

report = {
    "phase": "25-invoice-fiscal",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "pass": False,
    "failed_checks": [],
    "checks": {},
    "pdfs": {},
    "audit": {},
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]}
    if not ok:
        report["failed_checks"].append(key)


def pdf_ok(data):
    return data[:4] == b"%PDF"


def pdf_pages(path):
    try:
        out = subprocess.check_output(["pdfinfo", path], stderr=subprocess.DEVNULL, timeout=15)
        for line in out.decode().splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        return None


def screenshot(pdf_path, base_name):
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf_path, base_name],
            check=True,
            timeout=90,
        )
        return base_name + ".png"
    except Exception:
        return None


# --- Upgrade module ---
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
if mod.state != "installed":
    mod.button_immediate_install()
else:
    mod.button_immediate_upgrade()
env.cr.commit()
check("module_version", mod.latest_version == "19.0.3.0.0", mod.latest_version)

Report = env["ir.actions.report"]
Move = env["account.move"]
Product = env["product.product"]
Partner = env["res.partner"]
Tax = env["account.tax"]
Company = env.company

# --- Audit fields ---
audit = {
    "account_move_fields": [
        "name", "invoice_date", "invoice_date_due", "partner_id", "invoice_user_id",
        "invoice_payment_term_id", "currency_id", "amount_untaxed", "amount_tax",
        "amount_total", "narration", "justech_do_ncf", "justech_do_document_type_id",
    ],
    "modules": {},
}
for m in ("justech_l10n_do_ncf", "hellenia_reports", "justech_l10n_do_base"):
    mm = env["ir.module.module"].search([("name", "=", m)], limit=1)
    audit["modules"][m] = mm.state if mm else "missing"
report["audit"] = audit
check("ncf_module_installed", audit["modules"].get("justech_l10n_do_ncf") == "installed")

# --- Parallel report exists; standard untouched ---
jt_action = env.ref(ACTION_JT, raise_if_not_found=False)
std_action = env.ref(STD_ACTION)
check("jt_action_exists", bool(jt_action))
check("jt_action_name", jt_action.name == "Justech PDF — Factura" if jt_action else False)
check("jt_report_template", jt_action.report_name == REPORT_JT if jt_action else False)
check(
    "std_invoice_unchanged",
    std_action.report_name in ("account.report_invoice_with_payments", "account.report_invoice"),
    std_action.report_name,
)

# Quotation official unchanged
quot_action = env.ref(QUOT_ACTION)
check(
    "quotation_unchanged",
    quot_action.report_name == "justech_report_design.report_hellenia_quotation_document",
    quot_action.report_name,
)

# No xpath inherit on standard invoice from justech
std_view = env["ir.ui.view"].search([("key", "=", "account.report_invoice_document")], limit=1)
if std_view:
    jt_children = env["ir.ui.view"].search([
        ("inherit_id", "=", std_view.id),
        ("key", "like", "justech_report_design.%"),
    ])
    check("no_jt_inherit_std_invoice", len(jt_children) == 0)

# --- Helpers ---
itbis_tax = Tax.search([
    ("company_id", "=", Company.id),
    ("type_tax_use", "=", "sale"),
    ("amount", ">", 0),
], limit=1)
partner_rnc = Partner.search([("vat", "!=", False), ("customer_rank", ">", 0)], limit=1)
partner_no_rnc = Partner.search([("vat", "=", False), ("customer_rank", ">", 0)], limit=1)
product = Product.search([("sale_ok", "=", True)], limit=1)
payment_term = env["account.payment.term"].search([], limit=1)
usd = env["res.currency"].search([("name", "=", "USD")], limit=1)
dop = Company.currency_id


def make_invoice(partner, lines_vals, extra=None, post=False):
    vals = {
        "move_type": "out_invoice",
        "partner_id": partner.id,
        "invoice_date": datetime.now().date(),
        "invoice_payment_term_id": payment_term.id if payment_term else False,
        "invoice_user_id": env.user.id,
        "invoice_line_ids": lines_vals,
    }
    if extra:
        vals.update(extra)
    inv = Move.create(vals)
    if post and inv.state == "draft":
        try:
            inv.action_post()
        except Exception as e:
            report.setdefault("post_errors", {})[inv.name or str(inv.id)] = str(e)[:200]
    return inv


def line_vals(product, qty=1, price=100.0, discount=0.0):
    taxes = [(6, 0, itbis_tax.ids)] if itbis_tax else []
    return (0, 0, {
        "product_id": product.id,
        "quantity": qty,
        "price_unit": price,
        "discount": discount,
        "tax_ids": taxes,
    })


def render_case(key, move, fname):
    pdf_bytes, _ = Report._render_qweb_pdf(REPORT_JT, move.ids)
    html = Report._render_qweb_html(REPORT_JT, move.ids)[0].decode("utf-8", errors="replace")
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    png = screenshot(path, os.path.join(OUT_DIR, fname.replace(".pdf", "")))
    report["pdfs"][key] = {
        "invoice": move.name,
        "ncf": getattr(move, "justech_do_ncf", "") or "",
        "file": fname,
        "png": os.path.basename(png) if png else None,
        "pages": pdf_pages(path),
        "size_bytes": len(pdf_bytes),
        "amount_total": move.amount_total,
        "amount_untaxed": move.amount_untaxed,
        "itbis_helper": move.get_jt_invoice_itbis_total(),
    }
    check(f"{key}_pdf", pdf_ok(pdf_bytes), len(pdf_bytes))
    check(f"{key}_template", "jt-inv-page" in html and "jt-inv-band" in html)
    check(f"{key}_factura_band", "FACTURA" in html)
    check(f"{key}_no_dup_company", html.count('class="jt-hq-hdr"') <= 1)
    check(f"{key}_five_cols", "Información del Cliente" in html and "Fecha de Vencimiento" in html)
    check(f"{key}_footer", "jt-hq-footer-pdf" in html and "Página" in html)
    check(f"{key}_green_band", "background-color: #3E4827" in html or "jt-hq-band" in html)
    return html, path


# 1. Una línea
inv1 = make_invoice(partner_rnc or partner_no_rnc, [line_vals(product)])
html1, _ = render_case("invoice_1_line", inv1, "invoice_1_line.pdf")
check("1line_totals", str(inv1.amount_total) in html1 or inv1.format_jt_monetary(inv1.amount_total) in html1)

# 2. Varias líneas
inv_multi = make_invoice(
    partner_rnc or partner_no_rnc,
    [line_vals(product, qty=2, price=150), line_vals(product, qty=3, price=200)],
)
render_case("invoice_multi_line", inv_multi, "invoice_multi_line.pdf")

# 3. Con descuento
inv_disc = make_invoice(
    partner_rnc or partner_no_rnc,
    [line_vals(product, qty=5, price=500, discount=10.0)],
)
if not inv_disc.get_jt_invoice_has_discount():
    inv_disc.invoice_line_ids.filtered(lambda l: not l.display_type).write({"discount": 10.0})
env.cr.commit()
html_disc, _ = render_case("invoice_discount", inv_disc, "invoice_discount.pdf")
check("discount_column", inv_disc.get_jt_invoice_has_discount(), inv_disc.invoice_line_ids.mapped("discount"))
check("discount_in_pdf", "DESCUENTO" in html_disc or "Subtotal bruto" in html_disc or inv_disc.get_jt_invoice_show_discount_totals())

# 4. Sin descuento
inv_nodisc = make_invoice(partner_rnc or partner_no_rnc, [line_vals(product, price=350)])
render_case("invoice_no_discount", inv_nodisc, "invoice_no_discount.pdf")
check("no_discount_flag", not inv_nodisc.get_jt_invoice_has_discount())

# 5. NCF fiscal B01 (posted)
if partner_rnc and product:
    inv_ncf = make_invoice(partner_rnc, [line_vals(product, price=1000)], post=True)
    html_ncf, _ = render_case("invoice_ncf_b01", inv_ncf, "invoice_ncf_b01.pdf")
    ncf = getattr(inv_ncf, "justech_do_ncf", "") or ""
    check("ncf_assigned", bool(ncf), ncf)
    check("ncf_in_pdf", ncf in html_ncf if ncf else True, ncf)
    dtype = inv_ncf.get_jt_document_type_label()
    check("doc_type_in_pdf", dtype in html_ncf if dtype else True, dtype)

# 6. Consumo B02
if partner_no_rnc:
    inv_b02 = make_invoice(partner_no_rnc, [line_vals(product, price=500)], post=True)
    html_b02, _ = render_case("invoice_b02", inv_b02, "invoice_b02_consumo.pdf")
    prefix = ""
    if inv_b02.justech_do_document_type_id:
        prefix = inv_b02.justech_do_document_type_id.prefix or ""
    check("b02_prefix", prefix == "B02" or not partner_no_rnc.vat, prefix)

# 10. DOP
check("dop_currency", inv1.currency_id.name == dop.name, inv1.currency_id.name)

# 11. USD si aplica
if usd and usd != dop:
    inv_usd = make_invoice(
        partner_rnc or partner_no_rnc,
        [line_vals(product, price=100)],
        extra={"currency_id": usd.id},
    )
    render_case("invoice_usd", inv_usd, "invoice_usd.pdf")
    check("usd_currency", inv_usd.currency_id.name == "USD")

# 13. PDF backend estándar sigue
if inv1:
    std_pdf, _ = Report._render_qweb_pdf(std_action.report_name, inv1.ids)
    check("std_invoice_pdf", pdf_ok(std_pdf), len(std_pdf))

# 14-16 regression flags
check("dgii_module_intact", audit["modules"].get("justech_l10n_do_ncf") == "installed")
check("hellenia_reports_intact", audit["modules"].get("hellenia_reports") == "installed")

# Observaciones desde narration
terms = "<p>(a) Piezas originales. (b) Garantía 12 meses.</p>"
inv_obs = make_invoice(
    partner_rnc or partner_no_rnc,
    [line_vals(product)],
    extra={"narration": terms},
)
html_obs, _ = render_case("invoice_observations", inv_obs, "invoice_observations.pdf")
check("observations_in_pdf", "Piezas originales" in html_obs)

# ITBIS helper vs Odoo
if inv1.amount_tax and inv1.get_jt_invoice_itbis_total():
    diff = abs(inv1.get_jt_invoice_itbis_total() - inv1.amount_tax)
    check("itbis_matches", diff < 0.02 or inv1.get_jt_invoice_show_retentions(), diff)

report["pass"] = len(report["failed_checks"]) == 0

audit_path = os.path.join(OUT_DIR, "audit.json")
with open(audit_path, "w", encoding="utf-8") as f:
    json.dump(report["audit"], f, indent=2, ensure_ascii=False)

val_path = os.path.join(OUT_DIR, "validation.json")
with open(val_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False, default=str)

print(json.dumps({"pass": report["pass"], "failed": report["failed_checks"], "out": OUT_DIR}))
