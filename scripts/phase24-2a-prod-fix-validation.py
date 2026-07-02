# -*- coding: utf-8 -*-
"""Fase 24.2A PROD — Validación corrección TEST vs PROD."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
OUT = "/tmp/phase24-2a-prod-fix"
os.makedirs(OUT, exist_ok=True)

report = {
    "phase": "24.2A-prod-fix",
    "database": DB,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "pass": False,
    "failed_checks": [],
    "checks": {},
}

def check(k, ok, detail=""):
    report["checks"][k] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:400]}
    if not ok:
        report["failed_checks"].append(k)

mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
check("module_version", mod.latest_version == "19.0.2.0.1", mod.latest_version)

SaleOrder = env["sale.order"]
Report = env["ir.actions.report"]
REPORT = "justech_report_design.report_hellenia_quotation_document"

# default_get sin note en fields_list
res = SaleOrder.default_get(["partner_id"])
check("default_get_without_note_field", not __import__("odoo.tools").tools.is_html_empty(res.get("note")))

# Nueva cotización
partner = env["res.partner"].search([], limit=1)
new = SaleOrder.create({"partner_id": partner.id})
check("new_order_note", not __import__("odoo.tools").tools.is_html_empty(new.note))
html_new = Report._render_qweb_html(REPORT, new.ids)[0].decode("utf-8", errors="replace")
check("new_pdf_has_cond", "jt-hq-cond" in html_new and "CONDICIONES" in html_new)

# Existente S00020 o primera draft
so = SaleOrder.search([("name", "=", "S00020")], limit=1) or SaleOrder.search([("state", "in", ("draft", "sent"))], limit=1)
if so:
    if __import__("odoo.tools").tools.is_html_empty(so.note):
        updated = SaleOrder.jt_backfill_empty_quotation_notes()
        so = SaleOrder.browse(so.id)
    html = Report._render_qweb_html(REPORT, so.ids)[0].decode("utf-8", errors="replace")
    hdr = html[html.find("jt-hq-hdr"):html.find("jt-hq-hdr") + 600] if "jt-hq-hdr" in html else ""
    check("existing_pdf_cond", "jt-hq-cond" in html, so.name)
    check("hdr_no_border_attr", 'border="1"' not in hdr and "border: 1px" not in hdr)
    pdf, _ = Report._render_qweb_pdf(REPORT, so.ids)
    check("existing_pdf_ok", pdf[:4] == b"%PDF", f"{so.name} {len(pdf)}")
    with open(os.path.join(OUT, f"after_{so.name}.pdf"), "wb") as f:
        f.write(pdf)

# Vista formulario
view = env.ref("justech_report_design.view_order_form_jt_quotation_terms")
check("form_view_terms", "Términos y Condiciones" in view.arch)

new.unlink()
env.cr.commit()

report["pass"] = len(report["failed_checks"]) == 0
with open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print("PHASE24_2A:" + json.dumps(report, indent=2, ensure_ascii=False))
