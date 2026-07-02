# -*- coding: utf-8 -*-
"""Hotfix 25B.8 — Verificar método + regenerar PDFs (solo TEST)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase25b8-hotfix-doc-type"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT = "justech_report_design.report_justech_invoice_document"

result = {
    "phase": "25B.8-hotfix-doc-type",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_version": None,
    "method_exists": False,
    "method_samples": {},
    "files": {},
    "errors": [],
}


def to_png(pdf_path, base):
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf_path, base],
            check=True,
            timeout=90,
        )
        return os.path.basename(base + ".png")
    except Exception as e:
        return str(e)


# Upgrade módulo
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
mod.button_immediate_upgrade()
env.cr.commit()

try:
    env["ir.qweb"].clear_caches()
except Exception:
    pass
env.cr.commit()

result["module_version"] = mod.latest_version

Move = env["account.move"]
DocType = env["justech.do.fiscal.document.type"]

# Verificar método en account.move
probe = Move.new({"move_type": "out_invoice"})
result["method_exists"] = hasattr(probe, "get_jt_document_type_short_display")

if not result["method_exists"]:
    result["errors"].append("get_jt_document_type_short_display NO existe en account.move")
    with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    raise SystemExit("FAIL: método no cargado")

for name in [
    "Factura de Crédito Fiscal",
    "Factura de Consumo",
    "Factura Gubernamental",
    "Régimen Especial",
    "Comprobante de Exportación",
]:
    dt = DocType.search([("name", "=", name)], limit=1)
    if dt:
        m = Move.new({"move_type": "out_invoice", "justech_do_document_type_id": dt.id})
        result["method_samples"][name] = m.get_jt_document_type_short_display()

Report = env["ir.actions.report"]
Product = env["product.product"].search([("sale_ok", "=", True)], limit=10)
Partner = env["res.partner"].search([("vat", "!=", False), ("customer_rank", ">", 0)], limit=1)
Tax = env["account.tax"].search([("type_tax_use", "=", "sale"), ("amount", ">", 0)], limit=1)
dt_b01 = DocType.search([("prefix", "=", "B01")], limit=1)


def line_cmd(product, qty=1, price=100.0, discount=0.0):
    return (0, 0, {
        "product_id": product.id,
        "quantity": qty,
        "price_unit": price,
        "discount": discount,
        "tax_ids": [(6, 0, Tax.ids)] if Tax else [],
    })


def render(key, move, pdf_name):
    try:
        pdf_bytes, _ = Report._render_qweb_pdf(REPORT, move.ids)
        pdf_path = os.path.join(OUT_DIR, pdf_name)
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        html_bytes, _ = Report._render_qweb_html(REPORT, move.ids)
        html = html_bytes.decode("utf-8", errors="replace") if isinstance(html_bytes, bytes) else str(html_bytes)
        result["files"][key] = {
            "pdf": pdf_name,
            "png": to_png(pdf_path, os.path.join(OUT_DIR, pdf_name.replace(".pdf", ""))),
            "qweb_error": False,
            "html_has_tipo_label": 'class="jt-inv-label">Tipo:</span>' in html,
            "html_has_old_label": "Tipo comprobante:" in html,
            "html_has_credito_fiscal": "Crédito Fiscal" in html,
            "html_has_full_name": "Factura de Crédito Fiscal" in html,
        }
    except Exception as e:
        result["files"][key] = {"qweb_error": True, "error": str(e)}
        result["errors"].append(f"{key}: {e}")


p0 = Product[0]
inv1 = Move.create({
    "move_type": "out_invoice",
    "partner_id": Partner.id,
    "invoice_date": datetime.now().date(),
    "justech_do_document_type_id": dt_b01.id if dt_b01 else False,
    "invoice_line_ids": [line_cmd(p0, qty=1, price=3500)],
})
render("invoice_1_line", inv1, "01_invoice_1_line.pdf")

inv5 = Move.create({
    "move_type": "out_invoice",
    "partner_id": Partner.id,
    "invoice_date": datetime.now().date(),
    "justech_do_document_type_id": dt_b01.id if dt_b01 else False,
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
    "justech_do_document_type_id": dt_b01.id if dt_b01 else False,
    "invoice_line_ids": [line_cmd(p0, qty=5, price=500, discount=10)],
})
render("invoice_with_discount", inv_disc, "03_invoice_with_discount.pdf")

all_ok = (
    result["method_exists"]
    and not result["errors"]
    and all(not f.get("qweb_error") for f in result["files"].values())
    and all(f.get("html_has_tipo_label") for f in result["files"].values())
    and all(not f.get("html_has_old_label") for f in result["files"].values())
    and all(not f.get("html_has_full_name") for f in result["files"].values())
)
result["status"] = "PASS" if all_ok else "FAIL"

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(json.dumps({
    "status": result["status"],
    "method_exists": result["method_exists"],
    "version": result["module_version"],
    "samples": result["method_samples"],
    "errors": result["errors"],
}))

if not all_ok:
    raise SystemExit("VALIDATION FAILED")
