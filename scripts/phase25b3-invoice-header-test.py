# -*- coding: utf-8 -*-
"""Fase 25B.3 — Regenerar PDFs/PNG factura tras ajuste header (solo TEST)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase25b3-invoice-header"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT = "justech_report_design.report_justech_invoice_document"

result = {
    "phase": "25B.3-invoice-header",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "PENDING_USER_VISUAL_APPROVAL",
    "module_version": None,
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


mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
mod.button_immediate_upgrade()
env.cr.commit()
result["module_version"] = mod.latest_version

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
    result["files"][key] = {
        "pdf": pdf_name,
        "png": png_path,
        "emission": move.get_jt_invoice_date_display(),
        "due": move.get_jt_invoice_due_date_display(),
    }


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
    "invoice_line_ids": [line_cmd(Product[i % len(Product)], qty=i + 1, price=100 * (i + 1)) for i in range(5)],
})
render("invoice_5_lines", inv5, "02_invoice_5_lines.pdf")

inv_disc = Move.create({
    "move_type": "out_invoice",
    "partner_id": Partner.id,
    "invoice_date": datetime.now().date(),
    "invoice_line_ids": [line_cmd(p0, qty=5, price=500, discount=10)],
})
render("invoice_with_discount", inv_disc, "03_invoice_with_discount.pdf")

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(json.dumps({"out": OUT_DIR, "version": result["module_version"], "files": list(result["files"])}))
