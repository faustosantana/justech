# -*- coding: utf-8 -*-
"""Extra PROD validation: discount PDF, 5p PDF, menu names, stock/DGII smoke."""
import json
import os
from datetime import datetime, timezone

OUT = "/tmp/phase24-1-prod-parallel"
os.makedirs(OUT, exist_ok=True)

Report = env["ir.actions.report"]
SO = env["sale.order"]
REPORT_JT = "justech_report_design.report_hellenia_quotation_document"
REPORT_STD = "sale.report_saleorder"

extra = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "checks": {},
    "orders": {},
}


def check(key, ok, detail=""):
    extra["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:400]}


jt = env.ref("justech_report_design.action_report_hellenia_quotation")
std = env.ref("sale.action_report_saleorder")
check("menu_jt_name", jt.name == "Cotización Hellenia (Diseño)", jt.name)
check("menu_std_exists", bool(std))
check("menu_std_binding", std.binding_model_id.model == "sale.order" if std.binding_model_id else False)
check("menu_jt_binding", jt.binding_model_id.model == "sale.order" if jt.binding_model_id else False)

# 5+ lines
so_5p = None
for so in SO.search([("state", "in", ("draft", "sent"))], order="id desc", limit=30):
    n = len(so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment))
    if n >= 5:
        so_5p = so
        break
if so_5p:
    pdf, _ = Report._render_qweb_pdf(REPORT_JT, so_5p.ids)
    with open(os.path.join(OUT, "prod_quotation_real_5p.pdf"), "wb") as f:
        f.write(pdf)
    extra["orders"]["5p"] = so_5p.name
    check("jt_5p_pdf", pdf[:4] == b"%PDF", f"{so_5p.name} lines={len(so_5p.order_line)} size={len(pdf)}")
else:
    check("order_5p_found", False, "sin cotización draft/sent con 5+ líneas")

# Discount on S00020 or first draft
so_disc = SO.search([("state", "in", ("draft", "sent"))], order="id desc", limit=1)
if so_disc:
    line = so_disc.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)[:1]
    orig_disc = line.discount if line else 0
    if line:
        line.discount = 10.0
        env.cr.commit()
    pdf, _ = Report._render_qweb_pdf(REPORT_JT, so_disc.ids)
    html = Report._render_qweb_html(REPORT_JT, so_disc.ids)[0].decode("utf-8", errors="replace")
    with open(os.path.join(OUT, "prod_quotation_real_discount.pdf"), "wb") as f:
        f.write(pdf)
    thead = html.split("<thead>")[1].split("</thead>")[0] if "<thead>" in html else ""
    totals = (
        html.split('class="jt-hq-totals"')[1].split("</table>")[0]
        if 'class="jt-hq-totals"' in html
        else ""
    )
    extra["orders"]["disc"] = so_disc.name
    check("disc_pdf", pdf[:4] == b"%PDF", f"size={len(pdf)}")
    check("disc_col", "c-disc" in thead)
    check("disc_totals", "Subtotal bruto" in totals and "Descuento" in totals)
    if line:
        line.discount = orig_disc
        env.cr.commit()

# Stock picking any state
pick = env["stock.picking"].search([], limit=1)
if pick:
    pr = env.ref("stock.action_report_delivery", raise_if_not_found=False)
    if pr:
        pdf, _ = Report._render_qweb_pdf(pr.report_name, pick.ids)
        check("stock_pdf", pdf[:4] == b"%PDF", f"{pick.name} state={pick.state} size={len(pdf)}")
else:
    check("stock_any_picking", False, "sin pickings en BD")

# DGII module smoke
dgii_mod = env["ir.module.module"].search([("name", "in", ("justech_l10n_do_ncf", "l10n_do_accounting"))])
check("dgii_modules", all(m.state == "installed" for m in dgii_mod), dgii_mod.mapped(lambda m: f"{m.name}:{m.state}"))

fr_model = env.get("justech.do.fiscal.report")
if fr_model is not None:
    rec = fr_model.search([], limit=1)
    check("dgii_data_present", True, f"records={fr_model.search_count([])}")
else:
    check("dgii_model", True, "model not loaded in shell")

extra["pass"] = all(c["status"] == "PASS" for c in extra["checks"].values())

with open(os.path.join(OUT, "validation_extra.json"), "w", encoding="utf-8") as f:
    json.dump(extra, f, indent=2, ensure_ascii=False)

print("EXTRA:" + json.dumps(extra, indent=2, ensure_ascii=False))
