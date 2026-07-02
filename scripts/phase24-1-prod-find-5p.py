# -*- coding: utf-8 -*-
import os
OUT = "/tmp/phase24-1-prod-parallel"
Report = env["ir.actions.report"]
SO = env["sale.order"]
REPORT_JT = "justech_report_design.report_hellenia_quotation_document"
found = False
for so in SO.search([], order="id desc", limit=100):
    n = len(so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment))
    if n >= 5:
        pdf, _ = Report._render_qweb_pdf(REPORT_JT, so.ids)
        with open(os.path.join(OUT, "prod_quotation_real_5p.pdf"), "wb") as f:
            f.write(pdf)
        print(f"FOUND {so.name} state={so.state} lines={n} size={len(pdf)}")
        found = True
        break
if not found:
    best_n = 0
    best = None
    for so in SO.search([], limit=200):
        n = len(so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment))
        if n > best_n:
            best_n = n
            best = so
    if best and best_n > 0:
        pdf, _ = Report._render_qweb_pdf(REPORT_JT, best.ids)
        with open(os.path.join(OUT, f"prod_quotation_max_lines_{best_n}p.pdf"), "wb") as f:
            f.write(pdf)
        print(f"MAX {best.name} state={best.state} lines={best_n} size={len(pdf)}")
    else:
        print("NO_ORDERS")
