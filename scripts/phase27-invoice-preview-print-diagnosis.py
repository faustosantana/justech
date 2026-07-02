# -*- coding: utf-8 -*-
"""Fase 27 — Diagnóstico Vista previa / Imprimir vs Descargar PDF (PROD)."""
from __future__ import annotations

import json
import os
import traceback
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT_DIR = "/tmp/phase27-invoice-preview-print"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "27-invoice-preview-print-diagnosis",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "invoice": {},
    "company": {},
    "reports": {},
    "actions": {},
    "renders": {},
    "legal_documents": {},
    "preview_templates": {},
    "status": "FAIL",
}


def safe_render_template(tpl, values):
    html = env["ir.ui.view"]._render_template(tpl, values)
    text = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else str(html)
    return {
        "html_len": len(text),
        "has_jt_band": "jt-inv-band" in text,
        "has_std_table": "o_main_table" in text,
        "has_hellenia_ncf_box": "hellenia-ncf-box" in text,
    }


Move = env["account.move"]
Report = env["ir.actions.report"]
Company = env.company

inv = Move.search([("name", "=", "INV/2026/00006")], limit=1)
if not inv:
    inv = Move.search(
        [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
        order="id desc",
        limit=1,
    )
if not inv:
    raise SystemExit("No posted customer invoice found")

report["invoice"] = {
    "id": inv.id,
    "name": inv.name,
    "state": inv.state,
    "payment_state": inv.payment_state,
    "move_type": inv.move_type,
    "ncf": getattr(inv, "justech_do_ncf", "") or "",
}
report["company"] = {
    "id": Company.id,
    "name": Company.name,
    "external_report_layout_key": Company.external_report_layout_id.key
    if Company.external_report_layout_id
    else None,
    "external_report_layout_id": Company.external_report_layout_id.id
    if Company.external_report_layout_id
    else None,
}

xml_ids = [
    "account.account_invoices",
    "account.account_invoices_without_payment",
    "justech_report_design.action_report_justech_invoice",
    "justech_report_design.action_report_invoice_backup",
]
for xid in xml_ids:
    rec = env.ref(xid, raise_if_not_found=False)
    if rec:
        report["reports"][xid] = {
            "id": rec.id,
            "name": rec.name,
            "report_name": rec.report_name,
            "binding_model": rec.binding_model_id.model if rec.binding_model_id else None,
            "domain": str(rec.domain or ""),
        }

Send = env["account.move.send"]
report["default_pdf_report"] = Send._get_default_pdf_report_id(inv).report_name

for meth in ("action_invoice_download_pdf", "action_print_pdf", "preview_invoice"):
    try:
        act = getattr(inv, meth)()
        report["actions"][meth] = {
            k: act.get(k)
            for k in ("type", "url", "target", "res_model", "report_name", "name", "view_mode")
            if act.get(k) is not None
        }
        ctx = act.get("context") or {}
        report["actions"][meth]["context_keys"] = sorted(ctx.keys())
        report["actions"][meth]["is_layout_configurator"] = act.get("res_model") == "base.document.layout"
    except Exception as exc:
        report["actions"][meth] = {"error": str(exc), "traceback": traceback.format_exc()[-1500:]}

# Admin print (may trigger layout configurator)
try:
    admin = env.ref("base.user_admin")
    act_admin = inv.with_user(admin).action_print_pdf()
    report["actions"]["action_print_pdf_as_admin"] = {
        "type": act_admin.get("type"),
        "res_model": act_admin.get("res_model"),
        "report_name": act_admin.get("report_name"),
        "is_layout_configurator": act_admin.get("res_model") == "base.document.layout",
        "context_keys": sorted((act_admin.get("context") or {}).keys()),
    }
except Exception as exc:
    report["actions"]["action_print_pdf_as_admin"] = {"error": str(exc)}

templates = [
    "justech_report_design.report_justech_invoice_document",
    "account.report_invoice_with_payments",
    "account.report_invoice",
]
for tpl in templates:
    try:
        pdf, _ = Report._render_qweb_pdf(tpl, inv.ids)
        html, _ = Report._render_qweb_html(tpl, inv.ids)
        text = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else str(html)
        report["renders"][tpl] = {
            "pdf_ok": bool(pdf and pdf[:4] == b"%PDF"),
            "pdf_bytes": len(pdf or b""),
            "has_jt_band": "jt-inv-band" in text,
            "has_std_table": "o_main_table" in text,
        }
    except Exception as exc:
        report["renders"][tpl] = {
            "error": str(exc),
            "traceback": traceback.format_exc()[-2000:],
        }

# Layout wizard preview templates (standard Odoo path)
layout_vals = {
    "company": env["base.document.layout"]
    .with_context(active_model="account.move", active_id=inv.id)
    .create({"company_id": Company.id}),
    "o": inv,
    "qr_code": bool(getattr(Company, "qr_code", False)),
    "account_number": "",
    "preview_css": "",
    "is_html_empty": lambda x: False,
}
for tpl in (
    "account.report_invoice_wizard_iframe",
    "web.report_invoice_wizard_preview",
    "account.report_invoice_document_preview",
):
    try:
        report["preview_templates"][tpl] = safe_render_template(tpl, layout_vals)
    except Exception as exc:
        report["preview_templates"][tpl] = {
            "error": str(exc),
            "traceback": traceback.format_exc()[-2000:],
        }

try:
    doc = inv._get_invoice_legal_documents("pdf")
    content = doc.get("content") or b""
    report["legal_documents"]["pdf"] = {
        "filename": doc.get("filename"),
        "size": len(content),
        "is_pdf": content[:4] == b"%PDF" if content else False,
        "errors": doc.get("errors"),
    }
except Exception as exc:
    report["legal_documents"]["pdf"] = {"error": str(exc), "traceback": traceback.format_exc()[-1500:]}

# Attachment stored PDF report id
report["invoice_pdf_report_id"] = inv.invoice_pdf_report_id.id if inv.invoice_pdf_report_id else None
if inv.invoice_pdf_report_id:
    report["stored_pdf_report"] = inv.invoice_pdf_report_id.name

preview_std_errors = [
    k for k, v in report["preview_templates"].items() if v.get("error")
]
print_errors = report["actions"].get("action_print_pdf", {}).get("is_layout_configurator")
report["diagnosis"] = {
    "download_uses": report["actions"].get("action_invoice_download_pdf", {}).get("url"),
    "print_uses_report": report["default_pdf_report"],
    "preview_uses_portal": report["actions"].get("preview_invoice", {}).get("url"),
    "preview_wizard_uses_std_template": report["preview_templates"]
    .get("account.report_invoice_document_preview", {})
    .get("has_jt_band") is False,
    "print_may_open_layout_wizard": bool(print_errors),
    "preview_template_errors": preview_std_errors,
}

report["status"] = "PASS" if not preview_std_errors else "DIAGNOSED"

out_path = os.path.join(OUT_DIR, "diagnosis.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "diagnosis": report["diagnosis"]}, ensure_ascii=False))
