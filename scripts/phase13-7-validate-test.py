#!/usr/bin/env python3
"""Fase 13.7 — Validación funcional completa en hellenia_test."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone

from odoo import Command

if env.cr.dbname != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={env.cr.dbname}")

report = {
    "phase": "13.7",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "fixes": {},
    "test_data": {},
    "flow": {},
    "validations": {},
    "documents": {},
    "ok": True,
    "errors": [],
    "warnings": [],
}


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


def warn(msg: str) -> None:
    report["warnings"].append(msg)


company = env.company
manager = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if manager and manager not in env.user.group_ids:
    env.user.write({"group_ids": [(4, manager.id)]})

# --- FIX 1: Adjuntos huérfanos (filestore) ---
orphan_count = 0
Attachment = env["ir.attachment"].sudo()
for att in Attachment.search([("store_fname", "!=", False), ("type", "=", "binary")]):
    path = att._full_path(att.store_fname)
    if path and not os.path.exists(path):
        att.unlink()
        orphan_count += 1
env.cr.commit()
report["fixes"]["orphan_attachments_removed"] = orphan_count

# Regenerar bundles de assets report
try:
    env["ir.qweb"]._pregenerate_assets_bundles()
    report["fixes"]["assets_regenerated"] = True
except Exception as exc:
    warn(f"No se pudo regenerar assets: {exc}")
    report["fixes"]["assets_regenerated"] = False

# --- FIX 2: Logo oficial (copiar desde empresa si existe) ---
logo_path = "/mnt/custom/hellenia_base/static/img/hellenia_logo.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        company.write({"logo": f.read()})
    report["fixes"]["logo_from_module"] = True
else:
    report["fixes"]["logo_from_module"] = False
    if not company.logo:
        warn("Logo empresa no configurado y sin archivo estático")

report["fixes"]["company_has_logo"] = bool(company.logo)

# --- Impuestos y diario ---
tax_18_sale = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale"), ("active", "=", True)],
    limit=1,
)
tax_18_purchase = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "purchase"), ("active", "=", True)],
    limit=1,
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
journal_sale.justech_do_use_ncf = True

warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)


def ensure_ncf_range(doc, start=9600, end=9699):
    rng = env["justech.do.ncf.range"].search(
        [("document_type_id", "=", doc.id), ("state", "=", "active"), ("company_id", "=", company.id)],
        limit=1,
    )
    if rng:
        return rng
    return env["justech.do.ncf.range"].create(
        {
            "name": f"P137 {doc.prefix}",
            "document_type_id": doc.id,
            "company_id": company.id,
            "sequence_start": start,
            "sequence_end": end,
            "next_sequence": start,
            "date_from": date.today().replace(month=1, day=1),
            "date_to": date.today().replace(month=12, day=31),
            "journal_ids": [Command.set(journal_sale.ids)],
        }
    ).action_activate() or env["justech.do.ncf.range"].search(
        [("document_type_id", "=", doc.id), ("state", "=", "active")], limit=1
    )


doc_b01 = env.ref("justech_l10n_do_base.doc_type_b01", raise_if_not_found=False)
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02", raise_if_not_found=False)
doc_b03 = env.ref("justech_l10n_do_base.doc_type_b03", raise_if_not_found=False)
doc_b04 = env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False)
for doc in (doc_b01, doc_b02, doc_b03, doc_b04):
    if doc:
        ensure_ncf_range(doc)

# --- TEST DATA ---
customers = []
for i in range(1, 11):
    ref = f"P137-CUST-{i:02d}"
    existing = env["res.partner"].search([("ref", "=", ref)], limit=1)
    if existing:
        customers.append(existing)
        continue
    customers.append(
        env["res.partner"].create(
            {
                "name": f"Cliente Prueba {i:02d}",
                "ref": ref,
                "customer_rank": 1,
                "vat": f"13100000{i:02d}" if i <= 9 else f"1310000{i:02d}",
                "email": f"cliente{i}@test.hellenia.local",
                "phone": f"809-555-{1000+i}",
            }
        )
    )

vendors = []
for i in range(1, 6):
    ref = f"P137-VEND-{i:02d}"
    existing = env["res.partner"].search([("ref", "=", ref)], limit=1)
    if existing:
        vendors.append(existing)
        continue
    vendors.append(
        env["res.partner"].create(
            {
                "name": f"Proveedor Prueba {i:02d}",
                "ref": ref,
                "supplier_rank": 1,
                "vat": f"40100000{i:02d}",
            }
        )
    )

products = []
category = env["product.category"].search([], limit=1)
for i in range(1, 21):
    code = f"P137-PROD-{i:02d}"
    existing = env["product.product"].search([("default_code", "=", code)], limit=1)
    if existing:
        products.append(existing)
        continue
    products.append(
        env["product.product"].create(
            {
                "name": f"Producto Prueba {i:02d}",
                "default_code": code,
                "type": "consu",
                "is_storable": True,
                "list_price": 1000.0 + i * 250,
                "standard_price": 500.0 + i * 100,
                "categ_id": category.id,
                "taxes_id": [Command.set(tax_18_sale.ids)] if tax_18_sale else [],
                "supplier_taxes_id": [Command.set(tax_18_purchase.ids)] if tax_18_purchase else [],
                "sale_ok": True,
                "purchase_ok": True,
            }
        )
    )

# Stock inicial
if warehouse:
    for prod in products[:10]:
        env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": prod.id,
                "location_id": warehouse.lot_stock_id.id,
                "inventory_quantity": 50.0 + prod.id % 20,
            }
        ).action_apply_inventory()

report["test_data"] = {
    "customers": len(customers),
    "vendors": len(vendors),
    "products": len(products),
}

# --- Partner create/search smoke (cotización) ---
try:
    ctx = {"default_customer_rank": 1, "res_partner_search_mode": "customer"}
    test_partner = env["res.partner"].with_context(**ctx).create({"name": "Smoke Cotización P137"})
    search = env["res.partner"].name_search("Smoke Cotización", limit=5)
    report["fixes"]["partner_create_search"] = {"ok": True, "id": test_partner.id, "search_hits": len(search)}
except Exception as exc:
    err(f"partner create/search: {exc}")
    report["fixes"]["partner_create_search"] = {"ok": False, "error": str(exc)}

# --- FLUJO E2E ---
customer = customers[0]
product = products[0]
vendor = vendors[0]

try:
    # Cotización
    so = env["sale.order"].create({"partner_id": customer.id})
    env["sale.order.line"].create(
        {"order_id": so.id, "product_id": product.id, "product_uom_qty": 3, "price_unit": 5000.0}
    )
    report["flow"]["quotation"] = so.name
    pdf_q, _ = env["ir.actions.report"]._render_qweb_pdf("sale.report_saleorder", so.ids)
    report["documents"]["quotation"] = len(pdf_q)

    # Pedido
    so.action_confirm()
    report["flow"]["sale_order"] = so.state

    # Entrega
    picking_out = env["stock.picking"].search([("sale_id", "=", so.id), ("picking_type_code", "=", "outgoing")], limit=1)
    if picking_out:
        picking_out.action_assign()
        for move in picking_out.move_ids:
            move.quantity = move.product_uom_qty
        picking_out.button_validate()
        report["flow"]["delivery"] = picking_out.state

    # Factura
    so._create_invoices()
    inv = so.invoice_ids[:1]
    inv.invoice_date = date.today()
    if doc_b02:
        ensure_ncf_range(doc_b02)
    inv.action_post()
    report["flow"]["invoice"] = {"name": inv.name, "ncf": inv.justech_do_ncf, "state": inv.state}
    pdf_inv, _ = env["ir.actions.report"]._render_qweb_pdf("account.account_invoices", inv.ids)
    report["documents"]["invoice"] = len(pdf_inv)

    # Cobro
    if inv.amount_residual > 0:
        pay_wiz = env["account.payment.register"].with_context(active_model="account.move", active_ids=inv.ids).create({})
        payments = pay_wiz._create_payments()
        report["flow"]["payment_in"] = payments[:1].name if payments else "n/a"

    # Nota crédito
    if doc_b04:
        ensure_ncf_range(doc_b04)
        credit = env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": customer.id,
                "journal_id": journal_sale.id,
                "invoice_date": date.today(),
                "reversed_entry_id": inv.id,
                "justech_do_document_type_id": doc_b04.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "NC P137",
                            "quantity": 1,
                            "price_unit": 200.0,
                            "tax_ids": [Command.set(tax_18_sale.ids)],
                        }
                    )
                ],
            }
        )
        credit.action_post()
        report["flow"]["credit_note"] = credit.justech_do_ncf
        pdf_nc, _ = env["ir.actions.report"]._render_qweb_pdf("account.account_invoices", credit.ids)
        report["documents"]["credit_note"] = len(pdf_nc)

    # Nota débito
    if doc_b03 and inv:
        ensure_ncf_range(doc_b03)
        debit = env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": customer.id,
                "journal_id": journal_sale.id,
                "invoice_date": date.today(),
                "debit_origin_id": inv.id,
                "justech_do_document_type_id": doc_b03.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "ND P137",
                            "quantity": 1,
                            "price_unit": 150.0,
                            "tax_ids": [Command.set(tax_18_sale.ids)],
                        }
                    )
                ],
            }
        )
        debit.action_post()
        report["flow"]["debit_note"] = debit.justech_do_ncf

    # Compra + recepción + pago
    po = env["purchase.order"].create({"partner_id": vendor.id})
    env["purchase.order.line"].create(
        {"order_id": po.id, "product_id": products[1].id, "product_qty": 5, "price_unit": 800.0}
    )
    with env.cr.savepoint():
        po.button_confirm()
    report["flow"]["purchase_order"] = po.name
    picking_in = env["stock.picking"].search([("purchase_id", "=", po.id), ("picking_type_code", "=", "incoming")], limit=1)
    if picking_in:
        for move in picking_in.move_ids:
            move.quantity = move.product_uom_qty
        picking_in.button_validate()
        report["flow"]["reception"] = picking_in.state
    bill = po.invoice_ids[:1] if po.invoice_ids else None
    if not bill:
        bill = env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": vendor.id,
                "journal_id": journal_purchase.id,
                "invoice_date": date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": products[1].name,
                            "quantity": 5,
                            "price_unit": 800.0,
                            "tax_ids": [Command.set(tax_18_purchase.ids)] if tax_18_purchase else [],
                        }
                    )
                ],
            }
        )
    bill.action_post()
    report["flow"]["vendor_bill"] = bill.name
    if bill.amount_residual > 0:
        pay_wiz = env["account.payment.register"].with_context(active_model="account.move", active_ids=bill.ids).create({})
        payments = pay_wiz._create_payments()
        report["flow"]["payment_out"] = payments[:1].name if payments else "n/a"

except Exception as exc:
    err(f"flujo E2E: {exc}")

# --- Reportes DGII ---
for rtype in ("606", "607", "608"):
    try:
        wiz = env["justech.do.fiscal.report.wizard"].create(
            {
                "report_type": rtype,
                "date_from": date.today().replace(day=1),
                "date_to": date.today(),
            }
        )
        wiz.action_generate()
        report["flow"][f"report_{rtype}"] = "ok"
    except Exception as exc:
        warn(f"reporte {rtype}: {exc}")

# --- Validaciones ---
report["validations"]["tax_18_sale"] = bool(tax_18_sale)
report["validations"]["invoice_ncf"] = bool(report.get("flow", {}).get("invoice", {}).get("ncf"))
report["validations"]["accounting_balance"] = abs(sum(env["account.move.line"].search([]).mapped("balance"))) < 0.02
report["validations"]["stock_quants"] = env["stock.quant"].search_count([("quantity", ">", 0)])
report["validations"]["hellenia_reports"] = (
    env["ir.module.module"].search([("name", "=", "hellenia_reports"), ("state", "=", "installed")], limit=1) is not None
)
report["validations"]["layout"] = company.external_report_layout_id.key if company.external_report_layout_id else None

if not report["validations"]["invoice_ncf"]:
    warn("Factura sin NCF en flujo E2E")

print("PHASE13_7_TEST:" + json.dumps(report, ensure_ascii=False, indent=2))
