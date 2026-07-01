# -*- coding: utf-8 -*-
"""Fase 23 — Genera PDF de ejemplo de cada documento corporativo Hellenia."""
from __future__ import annotations

import base64
import json
import os
from datetime import date, datetime, timezone

DB = env.cr.dbname
OUT_DIR = "/tmp/phase23-sample-pdfs"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23-corporate-identity",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module_version": None,
    "pdfs": {},
    "ok": True,
}

mod = env["ir.module.module"].search([("name", "=", "hellenia_reports")], limit=1)
if mod and mod.state == "installed":
    mod.button_immediate_upgrade()
    env.cr.commit()
    report["module_version"] = mod.latest_version
else:
    report["ok"] = False
    report["error"] = "hellenia_reports not installed"
    print(json.dumps(report, indent=2))
    raise SystemExit(1)

Report = env["ir.actions.report"]
company = env.company


def save_pdf(key, action_xmlid, record):
    if not record:
        report["pdfs"][key] = {"status": "SKIP", "detail": "no record"}
        return
    try:
        action = env.ref(action_xmlid)
        pdf_bytes, _fmt = Report._render_qweb_pdf(action.report_name, record.ids)
        fname = f"{key}.pdf"
        path = os.path.join(OUT_DIR, fname)
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        report["pdfs"][key] = {
            "status": "OK",
            "record": record.display_name,
            "record_id": record.id,
            "path": path,
            "size_bytes": len(pdf_bytes),
        }
    except Exception as exc:
        report["pdfs"][key] = {"status": "FAIL", "detail": str(exc)[:500]}
        report["ok"] = False


# Cotización
quotation = env["sale.order"].search(
    [("state", "in", ["draft", "sent"]), ("company_id", "=", company.id)],
    order="id desc",
    limit=1,
)
save_pdf("01_cotizacion", "sale.action_report_saleorder", quotation)

# Factura
invoice = env["account.move"].search(
    [
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
save_pdf("02_factura", "account.account_invoices", invoice)

# Nota de crédito
credit_note = env["account.move"].search(
    [
        ("move_type", "=", "out_refund"),
        ("state", "=", "posted"),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
save_pdf("03_nota_credito", "account.account_invoices", credit_note)

# Nota de débito (B03 o in_invoice debit)
debit_note = env["account.move"].search(
    [
        ("move_type", "in", ["out_invoice", "in_invoice"]),
        ("state", "=", "posted"),
        ("justech_do_document_type_id.prefix", "=", "B03"),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
save_pdf("04_nota_debito", "account.account_invoices", debit_note)

# Orden de compra
po = env["purchase.order"].search(
    [("state", "=", "purchase"), ("company_id", "=", company.id)],
    order="id desc",
    limit=1,
)
save_pdf("05_orden_compra", "purchase.action_report_purchase_order", po)

# RFQ
rfq = env["purchase.order"].search(
    [("state", "in", ["draft", "sent", "to approve"]), ("company_id", "=", company.id)],
    order="id desc",
    limit=1,
)
save_pdf("06_rfq", "purchase.report_purchase_quotation", rfq)

# Delivery slip
delivery = env["stock.picking"].search(
    [
        ("picking_type_id.code", "=", "outgoing"),
        ("state", "=", "done"),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
save_pdf("07_delivery_slip", "stock.action_report_delivery", delivery)

# Recepción
receipt = env["stock.picking"].search(
    [
        ("picking_type_id.code", "=", "incoming"),
        ("state", "in", ["done", "assigned"]),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
save_pdf("08_recepcion", "stock.action_report_delivery", receipt)

# Recibo de pago
payment = env["account.payment"].search(
    [
        ("state", "=", "posted"),
        ("partner_type", "=", "customer"),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
save_pdf("09_recibo_pago", "account.action_report_payment_receipt", payment)

# Estado de cuenta cliente (followup)
customer = env["res.partner"].search(
    [("customer_rank", ">", 0), ("company_id", "in", [False, company.id])],
    order="id desc",
    limit=1,
)
if customer:
    try:
        action = env.ref("account_followup.action_report_followup")
        pdf_bytes, _fmt = Report._render_qweb_pdf(action.report_name, customer.ids)
        path = os.path.join(OUT_DIR, "10_estado_cuenta_cliente.pdf")
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        report["pdfs"]["10_estado_cuenta_cliente"] = {
            "status": "OK",
            "record": customer.display_name,
            "path": path,
            "size_bytes": len(pdf_bytes),
        }
    except Exception as exc:
        report["pdfs"]["10_estado_cuenta_cliente"] = {"status": "FAIL", "detail": str(exc)[:500]}
        report["ok"] = False

# Estado de cuenta proveedor
vendor = env["res.partner"].search(
    [("supplier_rank", ">", 0)],
    order="id desc",
    limit=1,
)
if vendor:
    try:
        stmt_report = env.ref("account_reports.customer_statement_report", raise_if_not_found=False)
        if stmt_report:
            handler = env["account.customer.statement.report.handler"]
            options = handler._get_options(
                stmt_report,
                vendor.ids,
                {"partner_ids": vendor.ids, "date": {"mode": "single", "date_to": date.today().isoformat()}},
            )
            pdf_bytes = env["ir.actions.report"]._render_qweb_pdf(
                "account_reports.pdf_export_main",
                res_ids=[],
                data={"options": options, "report_id": stmt_report.id},
            )[0]
            path = os.path.join(OUT_DIR, "11_estado_cuenta_proveedor.pdf")
            with open(path, "wb") as f:
                f.write(pdf_bytes)
            report["pdfs"]["11_estado_cuenta_proveedor"] = {
                "status": "OK",
                "record": vendor.display_name,
                "path": path,
                "note": "customer_statement_report used for vendor sample",
            }
        else:
            report["pdfs"]["11_estado_cuenta_proveedor"] = {"status": "SKIP", "detail": "no report ref"}
    except Exception as exc:
        report["pdfs"]["11_estado_cuenta_proveedor"] = {"status": "FAIL", "detail": str(exc)[:500]}

evidence_path = f"/tmp/phase23-sample-pdfs/evidence.json"
with open(evidence_path, "w") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2, ensure_ascii=False))
