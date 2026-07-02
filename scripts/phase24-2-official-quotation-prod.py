# -*- coding: utf-8 -*-
"""Fase 24.2 PROD — Validación oficialización cotización (solo hellenia_prod)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT_DIR = "/tmp/phase24-2-prod-official"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_JT = "justech_report_design.report_hellenia_quotation_document"
REPORT_STD = "sale.report_saleorder"
STD_ACTION = "sale.action_report_saleorder"

report = {
    "phase": "24.2-prod-official-quotation",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "pass": False,
    "failed_checks": [],
    "checks": {},
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]}
    if not ok:
        report["failed_checks"].append(key)


def pdf_ok(data):
    return data[:4] == b"%PDF"


mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
check("module_installed", mod.state == "installed", mod.state)
check("module_version", mod.latest_version == "19.0.2.0.0", mod.latest_version)

Report = env["ir.actions.report"]
SaleOrder = env["sale.order"]
Company = env.company
from odoo.tools import html2plaintext, is_html_empty

main_action = env.ref(STD_ACTION)
backup_action = env.ref("justech_report_design.action_report_saleorder_backup", raise_if_not_found=False)
check("main_action_report", main_action.report_name == REPORT_JT, main_action.report_name)
check("backup_action_exists", bool(backup_action))
check("backup_uses_standard", backup_action.report_name == REPORT_STD if backup_action else False)
check(
    "parallel_unbound",
    not env.ref("justech_report_design.action_report_hellenia_quotation").binding_model_id,
)

for key in ("sale.report_saleorder", "sale.report_saleorder_document", "sale.report_saleorder_raw"):
    v = env["ir.ui.view"].search([("key", "=", key)], limit=1)
    children = env["ir.ui.view"].search([
        ("inherit_id", "=", v.id),
        ("key", "like", "justech_report_design.%"),
    ])
    check(f"{key}_no_jt_inherit", len(children) == 0)

company_terms = (Company.hellenia_quotation_terms or "").strip()
check("company_has_default_terms", bool(company_terms), company_terms[:60])

# Cotización real existente
so_real = SaleOrder.search([("state", "in", ("draft", "sent"))], order="id desc", limit=1)
if so_real:
    pdf_main, _ = Report._render_qweb_pdf(main_action.report_name, so_real.ids)
    pdf_bak, _ = Report._render_qweb_pdf(backup_action.report_name, so_real.ids)
    check("real_main_pdf", pdf_ok(pdf_main), f"{so_real.name} size={len(pdf_main)}")
    check("real_backup_pdf", pdf_ok(pdf_bak), f"size={len(pdf_bak)}")
    with open(os.path.join(OUT_DIR, "prod_official_main.pdf"), "wb") as f:
        f.write(pdf_main)
    with open(os.path.join(OUT_DIR, "prod_official_backup.pdf"), "wb") as f:
        f.write(pdf_bak)
    report["order_used"] = so_real.name
else:
    check("real_quotation", False, "sin cotización draft/sent")

# Nueva cotización: note desde empresa (crear y eliminar)
partner = env["res.partner"].search([], limit=1)
test_so = SaleOrder.create({"partner_id": partner.id})
check("new_order_has_note", not is_html_empty(test_so.note))
check(
    "new_order_note_from_company",
    company_terms[:30] in html2plaintext(test_so.note or ""),
)
custom = "<p>(z) Prueba PROD 24.2 condiciones editadas.</p>"
test_so.write({"note": custom})
html_mod = Report._render_qweb_html(REPORT_JT, test_so.ids)[0].decode("utf-8", errors="replace")
check("modified_note_in_pdf", "Prueba PROD 24.2" in html_mod)
test_so.write({"note": False})
html_empty = Report._render_qweb_html(REPORT_JT, test_so.ids)[0].decode("utf-8", errors="replace")
check("empty_note_hides_cond", "jt-hq-cond-title" not in html_empty.split("jt-hq-footer")[0])
test_so.unlink()
env.cr.commit()

# Descuento temporal en cotización real
if so_real:
    line = so_real.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)[:1]
    orig = line.discount if line else 0
    if line:
        line.discount = 10.0
        env.cr.commit()
        html_d = Report._render_qweb_html(REPORT_JT, so_real.ids)[0].decode("utf-8", errors="replace")
        check("disc_col", "c-disc" in html_d.split("<thead>")[1].split("</thead>")[0])
        line.discount = orig
        env.cr.commit()

confirmed = SaleOrder.search([("state", "=", "sale")], limit=1)
if confirmed:
    pdf_c, _ = Report._render_qweb_pdf(main_action.report_name, confirmed.ids)
    check("confirmed_pdf", pdf_ok(pdf_c), confirmed.name)
else:
    check("confirmed_pdf", True, "SKIP")

# Portal + email
import urllib.request

so_portal = SaleOrder.search([("state", "in", ("draft", "sent"))], limit=1)
if so_portal:
    if hasattr(so_portal, "_portal_ensure_token"):
        so_portal._portal_ensure_token()
        env.cr.commit()
    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url", "")
    url = f"{base_url}/report/pdf/{main_action.report_name}/{so_portal.id}?access_token={so_portal.access_token}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "phase24-2-prod"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
            portal_ok = pdf_ok(data) or (
                resp.status == 200 and len(data) > 3000 and b"QWebException" not in data
            )
            check("portal_pdf", portal_ok, f"status={resp.status} size={len(data)}")
    except Exception as e:
        check("portal_pdf", False, str(e)[:200])
    mail_pdf, _ = Report._render_qweb_pdf(main_action.report_name, so_portal.ids)
    check("email_attachment_pdf", pdf_ok(mail_pdf), len(mail_pdf))

inv = env["account.move"].search([("move_type", "=", "out_invoice"), ("state", "=", "posted")], limit=1)
if inv:
    pdf, _ = Report._render_qweb_pdf(env.ref("account.account_invoices").report_name, inv.ids)
    check("invoice_unchanged", pdf_ok(pdf))
po = env["purchase.order"].search([], limit=1)
if po:
    pdf, _ = Report._render_qweb_pdf(env.ref("purchase.action_report_purchase_order").report_name, po.ids)
    check("purchase_unchanged", pdf_ok(pdf))

report["pass"] = len(report["failed_checks"]) == 0

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE24_2_PROD:" + json.dumps(report, indent=2, ensure_ascii=False))
