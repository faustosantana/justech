#!/usr/bin/env python3
"""PURCHASE-UX-1 — Validar PDF compras (RFQ/PO) diseño corporativo."""
from __future__ import annotations

import base64
import json
import os
import sys

OUT = os.environ.get("PURCHASE_UX1_EVIDENCE", "/var/lib/odoo/purchase-ux-1-validation.json")
PDF_DIR = os.environ.get("PURCHASE_UX1_PDF_DIR", "/var/lib/odoo/purchase-ux-1-pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

report_po = env.ref("purchase.action_report_purchase_order")
report_rfq = env.ref("purchase.report_purchase_quotation")
paper_letter = env.ref("justech_report_design.paperformat_hellenia_purchase_order")
paper_a4 = env.ref("justech_report_design.paperformat_hellenia_purchase_order_a4", raise_if_not_found=False)

report = {
    "phase": "PURCHASE-UX-1",
    "database": env.cr.dbname,
    "checks": {},
    "pdfs": [],
    "ok": True,
}


def fail(key, detail=None):
    report["ok"] = False
    report["checks"][key] = False
    if detail:
        report.setdefault("errors", []).append({key: detail})


def ok(key, value=True):
    report["checks"][key] = value


ok(
    "rfq_uses_corporate_report",
    "justech_report_design.report_justech_purchase_order_document"
    in (report_rfq.report_name or ""),
)
ok(
    "po_uses_corporate_report",
    "justech_report_design.report_justech_purchase_order_document"
    in (report_po.report_name or ""),
)

Partner = env["res.partner"]
Product = env["product.product"].create(
    {"name": "Producto PURCHASE-UX-1", "type": "consu", "purchase_ok": True}
)
partner = Partner.search([("supplier_rank", ">", 0)], limit=1) or Partner.create(
    {"name": "Proveedor PURCHASE-UX-1", "supplier_rank": 1}
)

PO = env["purchase.order"]
po = PO.create(
    {
        "partner_id": partner.id,
        "order_line": [
            (
                0,
                0,
                {
                    "name": Product.display_name,
                    "product_id": Product.id,
                    "product_qty": 2,
                    "price_unit": 150.0,
                },
            )
        ],
    }
)

states_to_test = [
    ("draft", "SOLICITUD DE COTIZACIÓN", report_rfq),
    ("sent", "SOLICITUD DE COTIZACIÓN", report_rfq),
    ("purchase", "ORDEN DE COMPRA", report_po),
]

for target_state, expected_title, report_action in states_to_test:
    if target_state == "sent" and po.state == "draft":
        po.write({"state": "sent"})
    elif target_state == "purchase" and po.state in ("draft", "sent"):
        po.button_confirm()

    title = po.get_jt_po_band_title()
    ok(f"title_{target_state}", title == expected_title)

    Report = env["ir.actions.report"].browse(report_action.id)
    for fmt_name, paper in (("letter", paper_letter), ("a4", paper_a4)):
        if not paper:
            continue
        original_pf = Report.paperformat_id
        Report.write({"paperformat_id": paper.id})
        pdf_bytes, _ = Report.with_context(force_report_rendering=True)._render_qweb_pdf(
            report_action.report_name, res_ids=po.ids
        )
        Report.write({"paperformat_id": original_pf.id})
        fname = f"po-{po.name.replace('/', '-')}-{target_state}-{fmt_name}.pdf"
        fpath = os.path.join(PDF_DIR, fname)
        with open(fpath, "wb") as fh:
            fh.write(pdf_bytes)
        report["pdfs"].append({"state": target_state, "format": fmt_name, "path": fpath, "bytes": len(pdf_bytes)})
        ok(f"pdf_{target_state}_{fmt_name}", len(pdf_bytes) > 500)

view = env.ref("justech_report_design.justech_purchase_order_body")
arch = view.arch_db or ""
ok("uses_jt_hq_band", "jt-hq-band" in arch)
ok("dynamic_title_in_template", "get_jt_po_band_title" in arch)
ok("no_purchase_order_english", "Purchase Order" not in arch)
ok("no_empty_observations_block", 't-if="doc.jt_show_po_observations()"' in arch)
ok("spanish_headers", "DESCRIPCIÓN" in arch and "SUBTOTAL" in arch)

report["status"] = "PASS" if report["ok"] else "FAIL"
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False, default=str)
print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
sys.exit(0 if report["ok"] else 1)
