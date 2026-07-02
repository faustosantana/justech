# -*- coding: utf-8 -*-
"""Fase 25B.7 — Diagnóstico + PDFs banda fiscal compacta (solo TEST)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase25b7-invoice-band"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT = "justech_report_design.report_justech_invoice_document"
ACTION_XML = "justech_report_design.action_report_justech_invoice"

result = {
    "phase": "25B.7-invoice-band",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "PENDING_USER_VISUAL_APPROVAL",
    "diagnosis": {},
    "files": {},
}


def to_png(pdf_path, base):
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf_path, base],
            check=True,
            timeout=90,
        )
        return os.path.basename(base + ".png")
    except Exception:
        return None


# --- Diagnóstico template / action / assets ---
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
action = env.ref(ACTION_XML, raise_if_not_found=False)
body_view = env["ir.ui.view"].search(
    [("key", "=", "justech_report_design.justech_invoice_body")], limit=1
)
arch = body_view.arch_db or ""

disk_paths = [
    "/mnt/custom/justech_report_design/report/invoice/justech_invoice_template.xml",
    "/opt/odoo-projects/hellenia/custom/justech_report_design/report/invoice/justech_invoice_template.xml",
]
disk_info = {}
for p in disk_paths:
    try:
        with open(p, encoding="utf-8") as f:
            content = f.read()
        disk_info[p] = {
            "exists": True,
            "jt_inv_fiscal_grid": "jt-inv-fiscal-grid" in content,
            "jt_inv_band_meta_wrap": "jt-inv-band-meta-wrap" in content,
            "jt_hq_band": "jt-hq-band" in content,
        }
    except OSError as e:
        disk_info[p] = {"exists": False, "error": str(e)}

scss_paths = [
    "/mnt/custom/justech_report_design/static/src/scss/hellenia_invoice.scss",
]
scss_info = {}
for p in scss_paths:
    try:
        with open(p, encoding="utf-8") as f:
            scss = f.read()
        scss_info[p] = {
            "exists": True,
            "has_fiscal_grid_css": ".jt-inv-fiscal-grid" in scss,
            "has_old_meta_wrap_css": ".jt-inv-band-meta-wrap" in scss,
            "background_35421f": "#35421f" in scss,
        }
    except OSError as e:
        scss_info[p] = {"exists": False, "error": str(e)}

# Upgrade + limpiar assets report
mod.button_immediate_upgrade()
env.cr.commit()

# Forzar recompilación assets report
try:
    env["ir.qweb"].clear_caches()
except Exception:
    pass
try:
    Attachment = env["ir.attachment"]
    stale = Attachment.search([
        ("url", "ilike", "/web/assets/%"),
        ("name", "ilike", "report"),
    ])
    if stale:
        stale.unlink()
except Exception:
    pass
env.cr.commit()

result["module_version"] = mod.latest_version
result["diagnosis"] = {
    "action_xml_id": ACTION_XML,
    "action_name": action.name if action else None,
    "action_report_name": action.report_name if action else None,
    "template_body_xml_id": "justech_report_design.justech_invoice_body",
    "template_body_view_id": body_view.id,
    "template_body_file": "custom/justech_report_design/report/invoice/justech_invoice_template.xml",
    "template_document_xml_id": REPORT,
    "band_classes_in_db_arch_after_upgrade": {
        "jt-hq-band": "jt-hq-band" in arch,
        "jt-inv-band": "jt-inv-band" in arch,
        "jt-inv-band-meta-wrap": "jt-inv-band-meta-wrap" in arch,
        "jt-inv-fiscal-grid": "jt-inv-fiscal-grid" in arch,
        "jt-inv-fiscal-layout": "jt-inv-fiscal-layout" in arch,
    },
    "disk_files": disk_info,
    "scss_files": scss_info,
}

# Re-read arch after upgrade
body_view.invalidate_recordset()
arch_after = env["ir.ui.view"].browse(body_view.id).arch_db or ""
result["diagnosis"]["band_classes_after_upgrade_reload"] = {
    "jt-hq-band": "jt-hq-band" in arch_after,
    "jt-inv-band": "jt-inv-band" in arch_after,
    "jt-inv-band-meta-wrap": "jt-inv-band-meta-wrap" in arch_after,
    "jt-inv-fiscal-grid": "jt-inv-fiscal-grid" in arch_after,
}
result["diagnosis"]["band_arch_snippet_after_upgrade"] = arch_after[
    max(0, arch_after.find("jt-inv-band") - 40) : arch_after.find("jt-inv-band") + 500
] if "jt-inv-band" in arch_after else arch_after[:500]

Report = env["ir.actions.report"]
Move = env["account.move"]
Product = env["product.product"].search([("sale_ok", "=", True)], limit=10)
Partner = env["res.partner"].search([("vat", "!=", False), ("customer_rank", ">", 0)], limit=1)
Tax = env["account.tax"].search([("type_tax_use", "=", "sale"), ("amount", ">", 0)], limit=1)


def line_cmd(product, qty=1, price=100.0, discount=0.0):
    return (0, 0, {
        "product_id": product.id,
        "quantity": qty,
        "price_unit": price,
        "discount": discount,
        "tax_ids": [(6, 0, Tax.ids)] if Tax else [],
    })


def render(key, move, pdf_name):
    pdf_bytes, _ = Report._render_qweb_pdf(REPORT, move.ids)
    pdf_path = os.path.join(OUT_DIR, pdf_name)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    png_path = to_png(pdf_path, os.path.join(OUT_DIR, pdf_name.replace(".pdf", "")))
    result["files"][key] = {"pdf": pdf_name, "png": png_path}
    # Verificar HTML renderizado contiene nueva estructura
    html_bytes, _ = Report._render_qweb_html(REPORT, move.ids)
    html = html_bytes.decode("utf-8", errors="replace") if isinstance(html_bytes, bytes) else str(html_bytes)
    result["files"][key]["html_has_fiscal_grid"] = "jt-inv-fiscal-grid" in html
    result["files"][key]["html_has_old_meta_wrap"] = "jt-inv-band-meta-wrap" in html


p0 = Product[0]
inv1 = Move.create({
    "move_type": "out_invoice",
    "partner_id": Partner.id,
    "invoice_date": datetime.now().date(),
    "invoice_line_ids": [line_cmd(p0, qty=1, price=3500)],
})
render("invoice_1_line", inv1, "01_invoice_1_line.pdf")

inv5 = Move.create({
    "move_type": "out_invoice",
    "partner_id": Partner.id,
    "invoice_date": datetime.now().date(),
    "invoice_line_ids": [
        line_cmd(Product[i % len(Product)], qty=i + 1, price=100 * (i + 1))
        for i in range(5)
    ],
})
render("invoice_5_lines", inv5, "02_invoice_5_lines.pdf")

inv_disc = Move.create({
    "move_type": "out_invoice",
    "partner_id": Partner.id,
    "invoice_date": datetime.now().date(),
    "invoice_line_ids": [line_cmd(p0, qty=5, price=500, discount=10)],
})
render("invoice_with_discount", inv_disc, "03_invoice_with_discount.pdf")

# Determinar si estructura nueva está en HTML
all_new = all(
    v.get("html_has_fiscal_grid") and not v.get("html_has_old_meta_wrap")
    for v in result["files"].values()
)
result["diagnosis"]["html_uses_new_structure"] = all_new
if not all_new:
    result["status"] = "FAIL_HTML_STILL_OLD_STRUCTURE"

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(json.dumps({
    "out": OUT_DIR,
    "version": result["module_version"],
    "status": result["status"],
    "html_uses_new_structure": all_new,
    "files": list(result["files"].keys()),
}))
