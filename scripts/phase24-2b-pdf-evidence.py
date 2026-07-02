# -*- coding: utf-8 -*-
"""Genera PDF cotización 1p y 5p para evidencia 24.2B."""
import os

OUT = os.environ.get("OUT_DIR", "/tmp/phase24-2b-pdf")
os.makedirs(OUT, exist_ok=True)
Report = env["ir.actions.report"]
REPORT = env.ref("sale.action_report_saleorder").report_name
SO = env["sale.order"]

def pick(min_lines=1):
    for so in SO.search([("state", "in", ("draft", "sent", "sale"))], order="id desc", limit=80):
        n = len(so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment))
        if n >= min_lines:
            return so
    return SO.search([], limit=1)

so_1 = pick(1)
so_5 = pick(5) or so_1
for label, so in (("1p", so_1), ("5p", so_5)):
    if so:
        pdf, _ = Report._render_qweb_pdf(REPORT, so.ids)
        path = os.path.join(OUT, f"quotation_{label}_{so.name}.pdf")
        with open(path, "wb") as f:
            f.write(pdf)
        print(label, so.name, len(pdf), path)
