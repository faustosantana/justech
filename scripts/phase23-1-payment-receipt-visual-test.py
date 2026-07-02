# -*- coding: utf-8 -*-
"""Fase 23.1 — Certificación visual recibo de pago (TEST). Solo datos de prueba."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase23-sample-pdfs"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23.1-payment-receipt-visual",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "visual_checks": {},
    "ok": True,
    "pass": False,
}


def check(key, ok, detail=""):
    report["visual_checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]}
    if not ok:
        report["ok"] = False


company = env.company
setup = env["hellenia.account.payment.setup"]
setup.configure_banks_and_payments()
Catalog = env["hellenia.withholding.catalog"]
Catalog.sync_catalog_from_taxes(company)
env.cr.commit()

bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)
Payment = env["account.payment"]
Report = env["ir.actions.report"]

PAID_STATES = ("paid", "posted")

# Idempotencia: reutilizar pago visual ya registrado
pay = Payment.search(
    [("hellenia_payment_reference", "=", "P23-VISUAL-RECEIPT"), ("state", "in", PAID_STATES)],
    order="id desc",
    limit=1,
)
if not pay:
    pay = Payment.search(
        [("name", "=", "PBNKD/2026/00027"), ("state", "in", PAID_STATES)],
        limit=1,
    )

invoice = None
if pay:
    report["payment_reused"] = pay.name
    invoice = pay.reconciled_invoice_ids[:1]
    if not invoice and pay.hellenia_withholding_line_ids:
        invoice = pay.hellenia_withholding_line_ids[:1].move_id
    partner = pay.partner_id
else:
    invoice = env["account.move"].search(
        [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("justech_do_ncf", "!=", False),
            ("payment_state", "in", ["not_paid", "partial"]),
            ("company_id", "=", company.id),
        ],
        order="id desc",
        limit=1,
    )
    check("01_invoice_found", bool(invoice), invoice.name if invoice else "none")
    if not invoice:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        raise SystemExit(1)

    partner = invoice.partner_id
    gov_cat = Catalog.search([("code", "=", "RET-GOB-5"), ("company_id", "=", company.id)], limit=1)
    ml = bnkd.inbound_payment_method_line_ids[:1]
    wiz = env["hellenia.payment.partner.wizard"].create(
        {
            "partner_type": "customer",
            "partner_id": partner.id,
            "journal_id": bnkd.id,
            "payment_method_line_id": ml.id,
            "payment_date": date.today(),
            "hellenia_payment_reference": "P23-VISUAL-RECEIPT",
        }
    )
    wiz._load_pending_invoices()
    line = wiz.line_ids.filtered(lambda l: l.move_id == invoice)[:1]
    if not line:
        line = wiz.line_ids.filtered("move_id")[:1]
    if not line:
        check("01b_wizard_lines", False, "sin líneas en wizard")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        raise SystemExit(1)
    line.apply = True
    line.amount_to_pay = invoice.amount_residual
    if gov_cat:
        line.withholding_catalog_ids = [Command.set(gov_cat.ids)]
    wiz.action_register_payments()
    env.cr.commit()
    pay = Payment.search(
        [("hellenia_payment_reference", "=", "P23-VISUAL-RECEIPT"), ("state", "in", PAID_STATES)],
        order="id desc",
        limit=1,
    )

check("01_invoice_found", bool(invoice), invoice.name if invoice else pay.name)
if not pay:
    check("02_payment_paid", False, "no payment")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(1)

ncf = invoice.justech_do_ncf if invoice else ""
report["invoice"] = {
    "id": invoice.id if invoice else None,
    "name": invoice.name if invoice else "",
    "ncf": ncf,
    "partner": partner.name,
}
check("02_payment_paid", pay.state in PAID_STATES, f"{pay.name} state={pay.state}")

report["payment"] = {
    "id": pay.id,
    "name": pay.name,
    "state": pay.state,
    "amount": pay.amount,
    "applied": pay.hellenia_applied_amount,
    "wh_total": pay.hellenia_withholding_total,
    "net": pay.hellenia_net_transfer,
    "wh_lines": len(pay.hellenia_withholding_line_ids),
}

pdf_path = os.path.join(OUT_DIR, "09_recibo_pago.pdf")
pdf_bytes, _fmt = Report._render_qweb_pdf("account.action_report_payment_receipt", pay.ids)
with open(pdf_path, "wb") as f:
    f.write(pdf_bytes)
html_bytes, _ = Report._render_qweb_html("account.action_report_payment_receipt", pay.ids)
html = html_bytes.decode("utf-8", errors="replace")
report["pdf"] = {"path": pdf_path, "size_bytes": len(pdf_bytes)}

check("03_spanish_title", "Recibo de pago" in html, "Recibo de pago" in html)
check("04_no_payment_receipt_en", "Payment Receipt" not in html, "Payment Receipt" in html)
check("05_cliente", partner.name in html, partner.name)
if invoice:
    check("06_factura", invoice.name in html, invoice.name)
check("07_ncf_label", "Número de Comprobante Fiscal" in html, html.count("NCF"))
check("08_ncf_value", not ncf or ncf in html, ncf)
check("09_metodo_pago", not pay.payment_method_id or pay.payment_method_id.name in html, pay.payment_method_id.name)
check("10_monto_aplicado", "Monto aplicado" in html, "Monto aplicado" in html)
check("11_neto_recibido", "Neto recibido" in html, "Neto recibido" in html)
check("12_usuario_audit", pay.create_uid.name in html, pay.create_uid.name)
check("13_brand_class", "hellenia-payment-doc" in html, "hellenia-payment-doc" in html)
check("14_logo", "hellenia-logo" in html or "o_company_logo" in html, "logo present")

if pay.hellenia_withholding_line_ids:
    check("15_retenciones_section", "Detalle de retenciones" in html, len(pay.hellenia_withholding_line_ids))
    check("16_total_retenido", "Total retenido" in html, pay.hellenia_withholding_total)
    for wh in pay.hellenia_withholding_line_ids:
        check(f"17_wh_{wh.id}", wh.label in html and (not wh.ncf or wh.ncf in html), wh.amount)
else:
    report["visual_checks"]["15_retenciones_section"] = {"status": "SKIP", "detail": "sin retenciones"}

bad_en = [w for w in ("Payment Date", "Customer:", "Invoice Number", "Due Amount for") if w in html]
check("18_no_english_labels", not bad_en, bad_en)

report["pass"] = report["ok"] and all(
    v.get("status") in ("PASS", "SKIP") for v in report["visual_checks"].values()
)

evidence_path = os.path.join(OUT_DIR, "evidence.json")
if os.path.exists(evidence_path):
    with open(evidence_path) as f:
        evidence = json.load(f)
else:
    evidence = {"phase": "23-corporate-identity", "pdfs": {}}

evidence["phase23_1"] = report
evidence["pdfs"]["09_recibo_pago"] = {
    "status": "OK" if report["pass"] else "FAIL",
    "record": pay.name,
    "record_id": pay.id,
    "path": pdf_path,
    "size_bytes": len(pdf_bytes),
    "invoice": invoice.name if invoice else "",
    "ncf": ncf,
    "withholding_total": pay.hellenia_withholding_total,
    "net_transfer": pay.hellenia_net_transfer,
}
evidence["pdfs_certified"] = f"{sum(1 for p in evidence['pdfs'].values() if p.get('status') == 'OK')}/11"
evidence["ok"] = all(p.get("status") in ("OK", "SKIP") for p in evidence["pdfs"].values())
with open(evidence_path, "w") as f:
    json.dump(evidence, f, indent=2)

print(json.dumps(report, indent=2, ensure_ascii=False))
