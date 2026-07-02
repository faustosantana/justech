# -*- coding: utf-8 -*-
"""Fase 25A — Generación paquete revisión visual factura Justech (solo TEST)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase25-invoice-review"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_JT = "justech_report_design.report_justech_invoice_document"
GIT_COMMIT = "phase25a-visual-review"

manifest = {
    "phase": "25A-visual-review",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "report": REPORT_JT,
    "module_version": None,
    "artifacts": {},
    "scenarios": {},
    "regression": {},
}

audit = {
    "phase": "25A-visual-review",
    "timestamp_utc": manifest["timestamp_utc"],
    "database": DB,
    "constraints": {
        "prod_touched": False,
        "std_invoice_replaced": False,
        "dgii_modified": False,
        "accounting_modified": False,
        "quotation_modified": False,
    },
    "modules": {},
    "fields_used": [
        "account.move.name",
        "account.move.justech_do_ncf",
        "account.move.justech_do_document_type_id",
        "account.move.invoice_date",
        "account.move.invoice_date_due",
        "account.move.partner_id",
        "account.move.invoice_payment_term_id",
        "account.move.invoice_user_id",
        "account.move.narration",
        "account.move.amount_untaxed",
        "account.move.amount_total",
        "account.move.line.discount",
        "account.move.line.price_subtotal",
    ],
    "template_files": [
        "custom/justech_report_design/report/invoice/justech_invoice_template.xml",
        "custom/justech_report_design/static/src/scss/hellenia_invoice.scss",
        "custom/justech_report_design/static/src/scss/hellenia_quotation.scss",
    ],
}

validation = {
    "phase": "25A-visual-review",
    "timestamp_utc": manifest["timestamp_utc"],
    "database": DB,
    "status": "PENDING_USER_VISUAL_APPROVAL",
    "automated_checks": {},
    "note": "No declarar PASS FINAL hasta aprobación explícita del usuario.",
}


def pdf_pages(path):
    try:
        out = subprocess.check_output(["pdfinfo", path], stderr=subprocess.DEVNULL, timeout=15)
        for line in out.decode().splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        return None


def to_png(pdf_path, base):
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf_path, base],
            check=True,
            timeout=120,
        )
        return base + ".png"
    except Exception as e:
        return None


def render_scenario(key, move, pdf_name, meta=None):
    Report = env["ir.actions.report"]
    pdf_bytes, _ = Report._render_qweb_pdf(REPORT_JT, move.ids)
    pdf_path = os.path.join(OUT_DIR, pdf_name)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    png_base = os.path.join(OUT_DIR, pdf_name.replace(".pdf", ""))
    png_path = to_png(pdf_path, png_base)
    pages = pdf_pages(pdf_path)
    line_count = len(move._jt_invoice_product_lines())
    rec = {
        "invoice_id": move.id,
        "invoice_name": move.name,
        "move_type": move.move_type,
        "state": move.state,
        "ncf": getattr(move, "justech_do_ncf", "") or "",
        "document_type": move.get_jt_document_type_label() if hasattr(move, "get_jt_document_type_label") else "",
        "partner": move.partner_id.display_name,
        "partner_vat": move.partner_id.vat or "",
        "currency": move.currency_id.name,
        "line_count": line_count,
        "pages": pages,
        "pdf": pdf_name,
        "png": os.path.basename(png_path) if png_path else None,
        "size_bytes": len(pdf_bytes),
        "amount_untaxed": move.amount_untaxed,
        "amount_total": move.amount_total,
        "itbis_helper": move.get_jt_invoice_itbis_total(),
        "has_discount": move.get_jt_invoice_has_discount(),
        "retentions": move.get_jt_invoice_retention_lines(),
    }
    if meta:
        rec.update(meta)
    manifest["scenarios"][key] = rec
    validation["automated_checks"][f"{key}_pdf_valid"] = pdf_bytes[:4] == b"%PDF"
    validation["automated_checks"][f"{key}_png_created"] = bool(png_path and os.path.isfile(png_path))
    return rec


# Module info
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
manifest["module_version"] = mod.latest_version if mod else "unknown"
for m in ("justech_l10n_do_ncf", "hellenia_reports", "account", "sale"):
    mm = env["ir.module.module"].search([("name", "=", m)], limit=1)
    audit["modules"][m] = mm.state if mm else "missing"

Move = env["account.move"]
Product = env["product.product"].search([("sale_ok", "=", True)], limit=25)
PartnerRNC = env["res.partner"].search([("vat", "!=", False), ("customer_rank", ">", 0)], limit=1)
PartnerNoRNC = env["res.partner"].search([("vat", "=", False), ("customer_rank", ">", 0)], limit=1)
TaxITBIS = env["account.tax"].search([
    ("company_id", "=", env.company.id),
    ("type_tax_use", "=", "sale"),
    ("amount", ">", 0),
], limit=1)
TaxGov = env["account.tax"].search([
    ("company_id", "=", env.company.id),
    ("type_tax_use", "=", "sale"),
    ("amount", "<", 0),
    ("name", "ilike", "gov"),
], limit=1)
Term30 = env["account.payment.term"].search([("line_ids.nb_days", ">=", 30)], limit=1) or env["account.payment.term"].search([], limit=1)
USD = env["res.currency"].search([("name", "=", "USD")], limit=1)


def line_cmd(product, qty=1, price=100.0, discount=0.0):
    taxes = [(6, 0, TaxITBIS.ids)] if TaxITBIS else []
    return (0, 0, {
        "product_id": product.id,
        "quantity": qty,
        "price_unit": price,
        "discount": discount,
        "tax_ids": taxes,
    })


def create_inv(partner, lines, extra=None, post=False):
    vals = {
        "move_type": "out_invoice",
        "partner_id": partner.id,
        "invoice_date": datetime.now().date(),
        "invoice_payment_term_id": Term30.id if Term30 else False,
        "invoice_user_id": env.user.id,
        "invoice_line_ids": lines,
    }
    if extra:
        vals.update(extra)
    inv = Move.create(vals)
    if post:
        try:
            inv.action_post()
        except Exception as e:
            manifest.setdefault("post_warnings", {})[inv.name or str(inv.id)] = str(e)[:300]
    return inv


products = Product or env["product.product"].search([("sale_ok", "=", True)], limit=25)
if len(products) < 1:
    raise SystemExit("ABORT: no hay productos sale_ok en TEST")

p0 = products[0]

# 1. Una línea
inv1 = create_inv(PartnerRNC or PartnerNoRNC, [line_cmd(p0, qty=1, price=3500)])
render_scenario("invoice_1_line", inv1, "01_invoice_1_line.pdf")

# 2. Cinco líneas
lines5 = [line_cmd(products[i % len(products)], qty=i + 1, price=100 * (i + 1)) for i in range(5)]
inv5 = create_inv(PartnerRNC or PartnerNoRNC, lines5)
render_scenario("invoice_5_lines", inv5, "02_invoice_5_lines.pdf")

# 3. Veinte o más líneas
lines20 = [line_cmd(products[i % len(products)], qty=1, price=50 + i * 10) for i in range(22)]
inv20 = create_inv(PartnerRNC or PartnerNoRNC, lines20)
render_scenario("invoice_22_lines", inv20, "03_invoice_22_lines.pdf")

# 4. Con descuento
inv_disc = create_inv(PartnerRNC or PartnerNoRNC, [line_cmd(p0, qty=5, price=500, discount=10)])
render_scenario("invoice_with_discount", inv_disc, "04_invoice_with_discount.pdf")

# 5. Sin descuento
inv_nodisc = create_inv(PartnerRNC or PartnerNoRNC, [line_cmd(p0, qty=3, price=750, discount=0)])
render_scenario("invoice_no_discount", inv_nodisc, "05_invoice_no_discount.pdf")

# 6. Comprobante fiscal B01 (posted)
if PartnerRNC:
    inv_b01 = create_inv(PartnerRNC, [line_cmd(p0, qty=1, price=1000)], post=True)
    render_scenario("invoice_fiscal_b01", inv_b01, "06_invoice_fiscal_b01.pdf", {"expected_prefix": "B01"})

# 7. Consumo B02
if PartnerNoRNC:
    inv_b02 = create_inv(PartnerNoRNC, [line_cmd(p0, qty=2, price=450)], post=True)
    prefix = ""
    if inv_b02.justech_do_document_type_id:
        prefix = inv_b02.justech_do_document_type_id.prefix or ""
    render_scenario("invoice_consumo_b02", inv_b02, "07_invoice_consumo_b02.pdf", {"expected_prefix": "B02", "actual_prefix": prefix})
else:
    manifest["scenarios"]["invoice_consumo_b02"] = {"status": "SKIPPED", "reason": "sin partner sin RNC"}

# 8. Gubernamental (retención gobierno 5% si existe impuesto)
gov_partner = PartnerRNC or PartnerNoRNC
gov_extra = {}
if TaxGov and hasattr(Move, "hellenia_ret_isr_gov"):
    gov_extra["hellenia_ret_isr_gov"] = True
inv_gov = create_inv(gov_partner, [line_cmd(p0, qty=1, price=10000)], extra=gov_extra)
if gov_extra:
    try:
        inv_gov.action_post()
    except Exception as e:
        manifest.setdefault("post_warnings", {})[inv_gov.name or "gov"] = str(e)[:300]
render_scenario(
    "invoice_government",
    inv_gov,
    "08_invoice_government.pdf",
    {"gov_retention_toggle": bool(gov_extra), "retentions": inv_gov.get_jt_invoice_retention_lines()},
)

# 9. Nota de crédito (out_refund) — template soporta out_refund en binding
nc_created = False
base_inv = inv_b01 if PartnerRNC else Move.browse()
if PartnerRNC and base_inv:
    try:
        nc = env["account.move"].create({
            "move_type": "out_refund",
            "partner_id": PartnerRNC.id,
            "invoice_date": datetime.now().date(),
            "invoice_payment_term_id": Term30.id if Term30 else False,
            "reversed_entry_id": base_inv.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": p0.id,
                "quantity": 1,
                "price_unit": 500,
                "tax_ids": [(6, 0, TaxITBIS.ids)] if TaxITBIS else [],
            })],
        })
        nc.action_post()
        render_scenario("credit_note_b04", nc, "09_credit_note_b04.pdf", {"expected_prefix": "B04"})
        nc_created = True
    except Exception as e:
        manifest["scenarios"]["credit_note_b04"] = {"status": "ERROR", "error": str(e)[:400]}
if not nc_created:
    # fallback: buscar NC publicada existente
    existing_nc = Move.search([
        ("move_type", "=", "out_refund"),
        ("state", "=", "posted"),
        ("company_id", "=", env.company.id),
    ], limit=1)
    if existing_nc:
        render_scenario("credit_note_b04", existing_nc, "09_credit_note_b04.pdf", {"source": "existing"})

# Regresión — no tocar estándar / cotización
std = env.ref("account.account_invoices")
quot = env.ref("sale.action_report_saleorder")
validation["automated_checks"]["std_invoice_unchanged"] = std.report_name in (
    "account.report_invoice_with_payments",
    "account.report_invoice",
)
validation["automated_checks"]["quotation_unchanged"] = (
    quot.report_name == "justech_report_design.report_hellenia_quotation_document"
)
audit["regression"] = {
    "std_invoice_report": std.report_name,
    "quotation_report": quot.report_name,
    "jt_invoice_action": env.ref("justech_report_design.action_report_justech_invoice").name,
}

# Guardar JSON
with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(validation, f, indent=2, ensure_ascii=False)
with open(os.path.join(OUT_DIR, "audit.json"), "w", encoding="utf-8") as f:
    json.dump(audit, f, indent=2, ensure_ascii=False)
with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

print(json.dumps({
    "out": OUT_DIR,
    "scenarios": list(manifest["scenarios"].keys()),
    "status": validation["status"],
}))
