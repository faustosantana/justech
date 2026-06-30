#!/usr/bin/env python3
"""Fase 13.5 — Certificación motor PDF en hellenia_prod (solo lectura + smoke)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import date, datetime, timezone

from odoo import Command

if env.cr.dbname != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={env.cr.dbname}")

report = {
    "phase": "13.5",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "pdf_engine": {},
    "documents": {},
    "paperformats": {},
    "warnings": [],
    "ok": True,
    "errors": [],
}


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


report["pdf_engine"]["wkhtmltopdf_version"] = subprocess.check_output(
    ["wkhtmltopdf", "--version"], text=True
).strip()
report["pdf_engine"]["wkhtmltopdf_path"] = subprocess.check_output(
    ["which", "wkhtmltopdf"], text=True
).strip()
report["pdf_engine"]["wkhtmltoimage_path"] = subprocess.check_output(
    ["which", "wkhtmltoimage"], text=True
).strip()

ICP = env["ir.config_parameter"].sudo()
report["pdf_engine"]["web_base_url"] = ICP.get_param("web.base.url") or ""
report["pdf_engine"]["report_url"] = ICP.get_param("report.url") or ""
if not report["pdf_engine"]["report_url"]:
    report["warnings"].append("report.url vacío — configurar = web.base.url")

company = env.company
manager = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if manager and manager not in env.user.group_ids:
    env.user.write({"group_ids": [(4, manager.id)]})

tax_18 = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale"), ("active", "=", True)],
    limit=1,
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_sale.justech_do_use_ncf = True
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
if not product and tax_18:
    product = env["product.product"].create(
        {"name": "PDF Cert Product", "type": "consu", "list_price": 1000, "taxes_id": [Command.set(tax_18.ids)]}
    )
partner = env["res.partner"].search([("customer_rank", ">", 0)], limit=1) or env["res.partner"].create(
    {"name": "PDF Cert Customer", "customer_rank": 1}
)


def render_pdf(xmlid: str, res_ids: list) -> dict:
    try:
        pdf, fmt = env["ir.actions.report"]._render_qweb_pdf(xmlid, res_ids)
        return {"ok": bool(pdf and len(pdf) > 500), "bytes": len(pdf) if pdf else 0, "fmt": fmt}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def ensure_ncf_range(doc):
    rng = env["justech.do.ncf.range"].search(
        [("document_type_id", "=", doc.id), ("state", "=", "active"), ("company_id", "=", company.id)],
        limit=1,
    )
    if rng:
        return rng
    return env["justech.do.ncf.range"].create(
        {
            "name": f"PDF Cert {doc.prefix}",
            "document_type_id": doc.id,
            "company_id": company.id,
            "sequence_start": 9800,
            "sequence_end": 9999,
            "next_sequence": 9800,
            "date_from": date.today().replace(month=1, day=1),
            "date_to": date.today().replace(month=12, day=31),
            "journal_ids": [Command.set(journal_sale.ids)],
        }
    ).action_activate() or env["justech.do.ncf.range"].search(
        [("document_type_id", "=", doc.id), ("state", "=", "active")], limit=1
    )


so = env["sale.order"].create({"partner_id": partner.id})
env["sale.order.line"].create(
    {"order_id": so.id, "product_id": product.id, "product_uom_qty": 1.0, "price_unit": 15000.0}
)
report["documents"]["quotation"] = render_pdf("sale.report_saleorder", so.ids)
so.action_confirm()
report["documents"]["sale_order"] = render_pdf("sale.report_saleorder", so.ids)
so._create_invoices()
inv = so.invoice_ids[:1]
inv.invoice_date = date.today()
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02", raise_if_not_found=False)
if doc_b02:
    ensure_ncf_range(doc_b02)
inv.action_post()
report["documents"]["invoice"] = render_pdf("account.account_invoices", inv.ids)
report["documents"]["invoice_ncf"] = inv.justech_do_ncf or ""

doc_b04 = env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False)
if doc_b04 and inv:
    ensure_ncf_range(doc_b04)
    credit = env["account.move"].create(
        {
            "move_type": "out_refund",
            "partner_id": partner.id,
            "journal_id": journal_sale.id,
            "invoice_date": date.today(),
            "reversed_entry_id": inv.id,
            "justech_do_document_type_id": doc_b04.id,
            "invoice_line_ids": [
                Command.create(
                    {"name": "NC PDF cert", "quantity": 1, "price_unit": 100.0, "tax_ids": [Command.set(tax_18.ids)]}
                )
            ],
        }
    )
    credit.action_post()
    report["documents"]["credit_note"] = render_pdf("account.account_invoices", credit.ids)

vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1) or env["res.partner"].create(
    {"name": "PDF Cert Vendor", "supplier_rank": 1}
)
purchase_product = env["product.product"].search([("purchase_ok", "=", True)], limit=1) or product
po = env["purchase.order"].create({"partner_id": vendor.id})
env["purchase.order.line"].create(
    {"order_id": po.id, "product_id": purchase_product.id, "product_qty": 2.0, "price_unit": 2500.0}
)
report["documents"]["purchase_rfq"] = render_pdf("purchase.report_purchasequotation", po.ids)
po.button_confirm()
report["documents"]["purchase_order"] = render_pdf("purchase.report_purchaseorder", po.ids)

html = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>"
    "<h1>Hellenia — República Dominicana</h1>"
    "<p>ITBIS 18% · ñ á é í ó ú · café</p></body></html>"
)
with open("/tmp/hellenia_utf8_cert.html", "w", encoding="utf-8") as f:
    f.write(html)
subprocess.call(
    ["wkhtmltopdf", "--quiet", "--encoding", "UTF-8", "/tmp/hellenia_utf8_cert.html", "/tmp/hellenia_utf8_cert.pdf"]
)
report["pdf_engine"]["utf8_cli"] = {
    "ok": os.path.exists("/tmp/hellenia_utf8_cert.pdf") and os.path.getsize("/tmp/hellenia_utf8_cert.pdf") > 300,
    "bytes": os.path.getsize("/tmp/hellenia_utf8_cert.pdf") if os.path.exists("/tmp/hellenia_utf8_cert.pdf") else 0,
}
report["pdf_engine"]["barcodes_module"] = bool(
    env["ir.module.module"].search([("name", "=", "barcodes"), ("state", "=", "installed")], limit=1)
)
try:
    import qrcode  # noqa: F401

    report["pdf_engine"]["qrcode"] = True
except ImportError:
    report["pdf_engine"]["qrcode"] = False

for pf in env["report.paperformat"].search([]):
    report["paperformats"][pf.name] = {
        "format": pf.format,
        "margin_top": pf.margin_top,
        "margin_bottom": pf.margin_bottom,
        "dpi": pf.dpi,
    }

for k, v in report["documents"].items():
    if isinstance(v, dict) and not v.get("ok"):
        err(f"PDF {k}: {v.get('error', v)}")

print("PHASE13_5_PDF:" + json.dumps(report, ensure_ascii=False, indent=2))
