# -*- coding: utf-8 -*-
"""Fase 23.2 — Certificación visual PDFs en PROD (solo hellenia_reports)."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT_DIR = "/tmp/phase23-2-prod-pdfs"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23.2-prod-visual-deployment",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module": None,
    "pdfs": {},
    "visual_validation": {},
    "ok": True,
    "pass": False,
}


def check(key, ok, detail=""):
    report["visual_validation"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]}
    if not ok:
        report["ok"] = False


mod = env["ir.module.module"].search([("name", "=", "hellenia_reports")], limit=1)
if not mod or mod.state != "installed":
    report["ok"] = False
    report["error"] = "hellenia_reports not installed"
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(1)

mod.button_immediate_upgrade()
env.cr.commit()
report["module"] = {"name": "hellenia_reports", "version": mod.latest_version}

Report = env["ir.actions.report"]
company = env.company
FORBIDDEN_COLORS = ("#1a365d", "#c9a227", "1a365d", "c9a227")


def save_pdf(key, action_xmlid, record, extra=None):
    if not record:
        report["pdfs"][key] = {"status": "SKIP", "detail": "no record"}
        return None
    try:
        action = env.ref(action_xmlid)
        pdf_bytes, _fmt = Report._render_qweb_pdf(action.report_name, record.ids)
        path = os.path.join(OUT_DIR, f"{key}.pdf")
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        html_bytes, _ = Report._render_qweb_html(action.report_name, record.ids)
        html = html_bytes.decode("utf-8", errors="replace")
        entry = {
            "status": "OK",
            "record": record.display_name,
            "record_id": record.id,
            "path": path,
            "size_bytes": len(pdf_bytes),
        }
        if extra:
            entry.update(extra)
        report["pdfs"][key] = entry
        return html
    except Exception as exc:
        report["pdfs"][key] = {"status": "FAIL", "detail": str(exc)[:500]}
        report["ok"] = False
        return None


# 01 Cotización
quotation = env["sale.order"].search(
    [("state", "in", ["draft", "sent"]), ("company_id", "=", company.id)],
    order="id desc",
    limit=1,
)
save_pdf("01_cotizacion", "sale.action_report_saleorder", quotation)

# 02 Factura
invoice = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("company_id", "=", company.id)],
    order="id desc",
    limit=1,
)
html_inv = save_pdf("02_factura", "account.account_invoices", invoice)

# 03 NC (borrador o posted)
credit_note = env["account.move"].search(
    [
        ("move_type", "=", "out_refund"),
        ("state", "in", ["posted", "draft"]),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
save_pdf("03_nota_credito", "account.account_invoices", credit_note)

# 04 ND
debit_note = env["account.move"].search(
    [
        ("move_type", "=", "out_invoice"),
        ("ref", "ilike", "P23-VISUAL"),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
if not debit_note:
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

# 05 OC
po = env["purchase.order"].search(
    [("state", "=", "purchase"), ("company_id", "=", company.id)],
    order="id desc",
    limit=1,
)

# 06 RFQ
rfq = env["purchase.order"].search(
    [("state", "in", ["draft", "sent", "to approve"]), ("company_id", "=", company.id)],
    order="id desc",
    limit=1,
)
save_pdf("05_orden_compra", "purchase.action_report_purchase_order", po)
save_pdf("06_rfq", "purchase.report_purchase_quotation", rfq)

# 07 Delivery
delivery = env["stock.picking"].search(
    [
        ("picking_type_id.code", "=", "outgoing"),
        ("state", "in", ["done", "assigned", "confirmed"]),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
save_pdf("07_delivery_slip", "stock.action_report_delivery", delivery)

# 08 Recepción
receipt = env["stock.picking"].search(
    [
        ("picking_type_id.code", "=", "incoming"),
        ("state", "in", ["done", "assigned", "confirmed", "waiting"]),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
save_pdf("08_recepcion", "stock.action_report_delivery", receipt)

# 09 Recibo de pago (con retenciones — P21 certificado)
payment = env["account.payment"].search(
    [
        ("state", "in", ("paid", "posted")),
        ("hellenia_withholding_line_ids", "!=", False),
        ("company_id", "=", company.id),
    ],
    order="id desc",
    limit=1,
)
if not payment:
    payment = env["account.payment"].search(
        [("state", "in", ("paid", "posted")), ("company_id", "=", company.id)],
        order="id desc",
        limit=1,
    )
html_pay = save_pdf(
    "09_recibo_pago",
    "account.action_report_payment_receipt",
    payment,
    extra={
        "withholding_total": payment.hellenia_withholding_total if payment else 0,
        "net_transfer": payment.hellenia_net_transfer if payment else 0,
    },
)

# 10 Estado cuenta cliente
customer = env["res.partner"].search([("customer_rank", ">", 0)], order="id desc", limit=1)
if customer:
    try:
        action = env.ref("account_followup.action_report_followup")
        pdf_bytes, _ = Report._render_qweb_pdf(action.report_name, customer.ids)
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

# 11 Estado cuenta proveedor
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], order="id desc", limit=1)
if vendor:
    try:
        action = env.ref("account_followup.action_report_followup")
        pdf_bytes, _ = Report._render_qweb_pdf(action.report_name, vendor.ids)
        path = os.path.join(OUT_DIR, "11_estado_cuenta_proveedor.pdf")
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        report["pdfs"]["11_estado_cuenta_proveedor"] = {
            "status": "OK",
            "record": vendor.display_name,
            "path": path,
            "size_bytes": len(pdf_bytes),
        }
    except Exception as exc:
        report["pdfs"]["11_estado_cuenta_proveedor"] = {"status": "FAIL", "detail": str(exc)[:500]}
        report["ok"] = False

# Validaciones visuales agregadas
ok_count = sum(1 for p in report["pdfs"].values() if p.get("status") == "OK")
report["pdfs_certified"] = f"{ok_count}/11"
check("pdf_count_11", ok_count == 11, ok_count)

if html_inv:
    check("invoice_ncf_label", "Número de Comprobante Fiscal" in html_inv, "NCF label")
    check("invoice_no_ncf_word", not re.search(r">\s*NCF\s*<", html_inv), "standalone NCF")
    check("invoice_no_qr", "hellenia-qr" not in html_inv, "qr")
    check("invoice_spanish", "Invoice Date" not in html_inv, "english")
    check("invoice_brand", "hellenia-invoice-doc" in html_inv or "hellenia-ncf" in html_inv, "brand class")
    for c in FORBIDDEN_COLORS:
        if c.lower() in html_inv.lower():
            check(f"invoice_no_forbidden_{c}", False, c)

if html_pay:
    check("payment_spanish_title", "Recibo de pago" in html_pay, "title")
    check("payment_withholding", "Detalle de retenciones" in html_pay or not payment.hellenia_withholding_line_ids, "wh")
    check("payment_net", "Neto recibido" in html_pay, "net")
    check("payment_brand", "hellenia-payment-doc" in html_pay, "brand")
    check("payment_ncf_label", "Número de Comprobante Fiscal" in html_pay, "ncf label")

report["pass"] = report["ok"] and ok_count == 11 and all(
    v.get("status") == "PASS" for v in report["visual_validation"].values()
)

evidence_path = os.path.join(OUT_DIR, "evidence.json")
with open(evidence_path, "w") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2, ensure_ascii=False))
