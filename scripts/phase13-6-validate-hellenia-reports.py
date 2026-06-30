#!/usr/bin/env python3
"""Fase 13.6 — Validación formatos corporativos hellenia_reports."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB not in ("hellenia_test", "hellenia_prod"):
    raise SystemExit(f"ABORT: solo hellenia_test o hellenia_prod, actual={DB}")

report = {
    "phase": "13.6",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module": {},
    "layout": {},
    "company": {},
    "documents": {},
    "checks": {},
    "ok": True,
    "errors": [],
    "warnings": [],
}


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


def warn(msg: str) -> None:
    report["warnings"].append(msg)


mod = env["ir.module.module"].search([("name", "=", "hellenia_reports")], limit=1)
report["module"]["state"] = mod.state if mod else "missing"
if not mod or mod.state != "installed":
    err("hellenia_reports no instalado")

company = env.company
layout = company.external_report_layout_id
report["layout"]["key"] = layout.key if layout else None
report["layout"]["expected"] = "hellenia_reports.external_layout_hellenia"
if layout and layout.key != "hellenia_reports.external_layout_hellenia":
    err(f"Layout incorrecto: {layout.key}")
report["company"]["name"] = company.name
report["company"]["vat"] = company.vat or ""
report["company"]["has_logo"] = bool(company.logo)
report["company"]["phone"] = company.phone or ""
report["company"]["email"] = company.email or ""
report["company"]["website"] = company.website or ""

if not company.logo:
    warn("Logo empresa no configurado en res.company")
if not company.vat:
    warn("RNC (vat) no configurado en res.company")

manager = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if manager and manager not in env.user.group_ids:
    env.user.write({"group_ids": [(4, manager.id)]})

tax_18 = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale"), ("active", "=", True)],
    limit=1,
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
if journal_sale:
    journal_sale.justech_do_use_ncf = True
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
if not product and tax_18:
    product = env["product.product"].create(
        {"name": "Hellenia Report Test", "type": "consu", "list_price": 1000, "taxes_id": [Command.set(tax_18.ids)]}
    )
partner = env["res.partner"].search([("customer_rank", ">", 0)], limit=1) or env["res.partner"].create(
    {"name": "Report UAT Customer", "customer_rank": 1}
)


def render_pdf(xmlid: str, res_ids: list) -> dict:
    try:
        pdf, fmt = env["ir.actions.report"]._render_qweb_pdf(xmlid, res_ids)
        return {
            "ok": bool(pdf and len(pdf) > 500),
            "bytes": len(pdf) if pdf else 0,
            "fmt": fmt,
        }
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
            "name": f"Report UAT {doc.prefix}",
            "document_type_id": doc.id,
            "company_id": company.id,
            "sequence_start": 9700,
            "sequence_end": 9799,
            "next_sequence": 9700,
            "date_from": date.today().replace(month=1, day=1),
            "date_to": date.today().replace(month=12, day=31),
            "journal_ids": [Command.set(journal_sale.ids)],
        }
    ).action_activate() or env["justech.do.ncf.range"].search(
        [("document_type_id", "=", doc.id), ("state", "=", "active")], limit=1
    )


# Cotización
so = env["sale.order"].create({"partner_id": partner.id})
env["sale.order.line"].create(
    {"order_id": so.id, "product_id": product.id, "product_uom_qty": 2.0, "price_unit": 8500.0}
)
report["documents"]["quotation"] = render_pdf("sale.report_saleorder", so.ids)

# Pedido
so.action_confirm()
report["documents"]["sale_order"] = render_pdf("sale.report_saleorder", so.ids)

# Factura
so._create_invoices()
inv = so.invoice_ids[:1]
inv.invoice_date = date.today()
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02", raise_if_not_found=False)
if doc_b02:
    ensure_ncf_range(doc_b02)
inv.action_post()
report["documents"]["invoice"] = render_pdf("account.account_invoices", inv.ids)
report["documents"]["invoice_ncf"] = inv.justech_do_ncf or ""
report["checks"]["invoice_has_ncf"] = bool(inv.justech_do_ncf)
report["checks"]["invoice_tax_18"] = any(
    abs(t.amount - 18) < 0.01 for t in inv.invoice_line_ids.tax_ids
)

# Nota de crédito
doc_b04 = env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False)
if doc_b04:
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
                    {"name": "NC UAT", "quantity": 1, "price_unit": 500.0, "tax_ids": [Command.set(tax_18.ids)]}
                )
            ],
        }
    )
    credit.action_post()
    report["documents"]["credit_note"] = render_pdf("account.account_invoices", credit.ids)

# Compras
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1) or env["res.partner"].create(
    {"name": "Report UAT Vendor", "supplier_rank": 1}
)
po = env["purchase.order"].create({"partner_id": vendor.id})
env["purchase.order.line"].create(
    {"order_id": po.id, "product_id": product.id, "product_qty": 3, "price_unit": 1200.0}
)
report["documents"]["purchase_rfq"] = render_pdf("purchase.report_purchasequotation", po.ids)
try:
    po.button_confirm()
    report["documents"]["purchase_order"] = render_pdf("purchase.report_purchaseorder", po.ids)
except Exception as exc:
    existing_po = env["purchase.order"].search([("state", "=", "purchase")], limit=1)
    if existing_po:
        report["documents"]["purchase_order"] = render_pdf("purchase.report_purchaseorder", existing_po.ids)
        warn(f"PO confirm falló ({exc}); usado PO existente {existing_po.name}")
    else:
        report["documents"]["purchase_order"] = {"ok": False, "error": str(exc)}

# Entrega
picking_out = env["stock.picking"].search(
    [("sale_id", "=", so.id), ("picking_type_code", "=", "outgoing")], limit=1
)
if not picking_out:
    picking_out = env["stock.picking"].search([("picking_type_code", "=", "outgoing"), ("state", "!=", "cancel")], limit=1)
if picking_out:
    report["documents"]["delivery"] = render_pdf("stock.report_deliveryslip", picking_out.ids)
else:
    warn("No hay picking de entrega para probar — omitido")

# Recepción (incoming picking si existe, sino crear PO receipt)
picking_in = env["stock.picking"].search(
    [("picking_type_code", "=", "incoming"), ("state", "!=", "cancel")], limit=1
)
if picking_in:
    report["documents"]["reception"] = render_pdf("stock.report_deliveryslip", picking_in.ids)
else:
    warn("No hay picking de recepción para probar — omitido")

pf = env.ref("hellenia_reports.paperformat_hellenia_letter", raise_if_not_found=False)
report["checks"]["paperformat"] = pf.name if pf else None

for k, v in report["documents"].items():
    if isinstance(v, dict) and not v.get("ok"):
        err(f"PDF {k}: {v.get('error', v)}")

if not report["checks"].get("invoice_has_ncf"):
    warn("Factura sin NCF en prueba")

print("PHASE13_6_REPORTS:" + json.dumps(report, ensure_ascii=False, indent=2))
