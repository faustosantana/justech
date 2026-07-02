# -*- coding: utf-8 -*-
"""Fase 27 — Validación fix Vista previa / Imprimir factura PROD."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT_DIR = "/tmp/phase27-invoice-preview-print-fix"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "27-invoice-preview-print-fix",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "checks": {},
    "invoice": {},
}

Move = env["account.move"]
Report = env["ir.actions.report"]

inv = Move.search([("name", "=", "INV/2026/00006")], limit=1)
if not inv:
    inv = Move.search(
        [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
        order="id desc",
        limit=1,
    )
if not inv:
    raise SystemExit("No posted customer invoice found")

report["invoice"] = {"id": inv.id, "name": inv.name, "state": inv.state}


def check(key, ok, detail=""):
    report["checks"][key] = {
        "status": "PASS" if ok else "FAIL",
        "detail": str(detail)[:800],
    }


layout = (
    env["base.document.layout"]
    .with_context(active_model="account.move", active_id=inv.id)
    .create({"company_id": env.company.id})
)
layout_vals = {
    "company": layout,
    "o": inv,
    "docs": inv,
    "qr_code": False,
    "account_number": "",
    "preview_css": "",
    "is_html_empty": lambda x: False,
}

# Antes fallaba: hellenia_legal_notice en external_layout_hellenia
for tpl in (
    "account.report_invoice_wizard_iframe",
    "account.report_invoice_document_preview",
    "justech_report_design.report_justech_invoice_wizard_iframe",
):
    try:
        html = env["ir.ui.view"]._render_template(tpl, layout_vals)
        text = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else str(html)
        check(
            f"preview_{tpl.split('.')[-1]}",
            "error" not in text.lower()[:200],
            f"len={len(text)} jt_band={'jt-inv-band' in text}",
        )
    except Exception as exc:
        check(f"preview_{tpl.split('.')[-1]}", False, str(exc))

# Acciones UI
for meth in ("action_invoice_download_pdf", "action_print_pdf", "preview_invoice"):
    act = getattr(inv, meth)()
    check(f"action_{meth}", act.get("type") is not None, act.get("type"))

# Render oficial
pdf, _ = Report._render_qweb_pdf(
    "justech_report_design.report_justech_invoice_document", inv.ids
)
html, _ = Report._render_qweb_html(
    "justech_report_design.report_justech_invoice_document", inv.ids
)
text = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else str(html)
check("official_pdf", pdf[:4] == b"%PDF", len(pdf))
check("official_html", "jt-inv-band" in text, len(text))

# Portal ref
ref = inv.partner_id.invoice_template_pdf_report_id.report_name or "account.account_invoices"
html_p, _ = Report._render_qweb_html(ref, inv.ids)
text_p = html_p.decode("utf-8", errors="replace") if isinstance(html_p, bytes) else str(html_p)
check("portal_html_ref", "jt-inv-band" in text_p, ref)

failures = [k for k, v in report["checks"].items() if v["status"] == "FAIL"]
report["status"] = "PASS" if not failures else "FAIL"

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "failures": failures}, ensure_ascii=False))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
