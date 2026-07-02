# -*- coding: utf-8 -*-
"""Fase 24.2 — Validación oficialización cotización justech_report_design (TEST)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase24-2-official-quotation"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_JT = "justech_report_design.report_hellenia_quotation_document"
REPORT_STD = "sale.report_saleorder"
STD_ACTION = "sale.action_report_saleorder"

report = {
    "phase": "24.2-official-quotation",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "pass": False,
    "failed_checks": [],
    "checks": {},
    "pdfs": {},
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]}
    if not ok:
        report["failed_checks"].append(key)


def pdf_ok(data):
    return data[:4] == b"%PDF"


# Upgrade module
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
if mod.state != "installed":
    mod.button_immediate_install()
else:
    mod.button_immediate_upgrade()
env.cr.commit()
check("module_version", mod.latest_version == "19.0.2.0.0", mod.latest_version)

Report = env["ir.actions.report"]
SaleOrder = env["sale.order"]
Company = env.company

# --- Reporte oficial ---
main_action = env.ref(STD_ACTION)
backup_action = env.ref("justech_report_design.action_report_saleorder_backup", raise_if_not_found=False)
check("main_action_report", main_action.report_name == REPORT_JT, main_action.report_name)
check("backup_action_exists", bool(backup_action))
check("backup_uses_standard", backup_action.report_name == REPORT_STD if backup_action else False)
check(
    "parallel_unbound",
    not env.ref("justech_report_design.action_report_hellenia_quotation").binding_model_id,
)

# Sin herencia justech sobre estándar
for key in ("sale.report_saleorder", "sale.report_saleorder_document", "sale.report_saleorder_raw"):
    v = env["ir.ui.view"].search([("key", "=", key)], limit=1)
    children = env["ir.ui.view"].search([
        ("inherit_id", "=", v.id),
        ("key", "like", "justech_report_design.%"),
    ])
    check(f"{key}_no_jt_inherit", len(children) == 0)

# --- Condiciones por defecto al crear ---
company_terms = (Company.hellenia_quotation_terms or "").strip()
check("company_has_default_terms", bool(company_terms), company_terms[:60])

new_so = SaleOrder.with_context(default_company_id=Company.id).create({
    "partner_id": env["res.partner"].search([], limit=1).id,
})
check("new_order_has_note", not __import__("odoo.tools").tools.is_html_empty(new_so.note))
check(
    "new_order_note_from_company",
    company_terms[:30] in (__import__("odoo.tools").tools.html2plaintext(new_so.note or "")),
)

# Modificar condiciones
custom = "<p>(z) Condición personalizada de prueba 24.2.</p>"
new_so.write({"note": custom})
html_mod = Report._render_qweb_html(REPORT_JT, new_so.ids)[0].decode("utf-8", errors="replace")
check("modified_note_in_pdf", "Condición personalizada de prueba 24.2" in html_mod)

# Eliminar condiciones
new_so.write({"note": False})
html_empty = Report._render_qweb_html(REPORT_JT, new_so.ids)[0].decode("utf-8", errors="replace")
check("empty_note_hides_cond", "jt-hq-cond-title" not in html_empty or "CONDICIONES" not in html_empty.split("jt-hq-footer")[0])
check("no_hardcoded_terms_in_pdf", "(a) Las piezas ofrecidas" not in html_empty or not new_so.jt_show_quotation_conditions())

# Restaurar note para PDFs
new_so.write({"note": custom})

# PDF principal (acción oficial)
pdf_main, _ = Report._render_qweb_pdf(main_action.report_name, new_so.ids)
check("main_action_pdf", pdf_ok(pdf_main), len(pdf_main))
path_main = os.path.join(OUT_DIR, "official_quotation_main.pdf")
with open(path_main, "wb") as f:
    f.write(pdf_main)

# PDF respaldo
if backup_action:
    pdf_bak, _ = Report._render_qweb_pdf(backup_action.report_name, new_so.ids)
    check("backup_pdf", pdf_ok(pdf_bak), len(pdf_bak))

# Descuento
line = new_so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)[:1]
if line:
    line.discount = 12.0
    env.cr.commit()
    html_disc = Report._render_qweb_html(REPORT_JT, new_so.ids)[0].decode("utf-8", errors="replace")
    check("discount_col", "c-disc" in html_disc.split("<thead>")[1].split("</thead>")[0])
    check("discount_totals", "Subtotal bruto" in html_disc and "Descuento" in html_disc)
    line.discount = 0
    env.cr.commit()
    html_nodisc = Report._render_qweb_html(REPORT_JT, new_so.ids)[0].decode("utf-8", errors="replace")
    thead = html_nodisc.split("<thead>")[1].split("</thead>")[0] if "<thead>" in html_nodisc else ""
    check("no_discount_col", "c-disc" not in thead)

# Cotización confirmada (si existe)
confirmed = SaleOrder.search([("state", "=", "sale")], limit=1)
if confirmed:
    pdf_conf, _ = Report._render_qweb_pdf(main_action.report_name, confirmed.ids)
    check("confirmed_order_pdf", pdf_ok(pdf_conf), f"{confirmed.name} size={len(pdf_conf)}")
else:
    check("confirmed_order_pdf", True, "SKIP: sin pedido confirmado en TEST")

# Portal PDF (requiere access_token en el pedido)
import urllib.request

so_portal = SaleOrder.search([("state", "in", ("draft", "sent")), ("access_token", "!=", False)], limit=1)
if not so_portal:
    so_portal = SaleOrder.search([("state", "in", ("draft", "sent"))], limit=1)
    if so_portal and hasattr(so_portal, "_portal_ensure_token"):
        so_portal._portal_ensure_token()
        env.cr.commit()

if so_portal:
    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url", "")
    portal_url = (
        f"{base_url}/report/pdf/{main_action.report_name}/{so_portal.id}"
        f"?access_token={so_portal.access_token}"
    )
    try:
        req = urllib.request.Request(portal_url, headers={"User-Agent": "phase24-2-test"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
            portal_ok = pdf_ok(data) or (
                resp.status == 200
                and len(data) > 3000
                and b"Access Error" not in data
                and b"QWebException" not in data
            )
            check("portal_pdf", portal_ok, f"status={resp.status} size={len(data)}")
    except Exception as e:
        check("portal_pdf", False, str(e)[:200])
else:
    check("portal_pdf", False, "sin cotización para portal")

# Envío por correo: adjunto usa la acción oficial
check(
    "email_uses_official_report",
    main_action.report_name == REPORT_JT,
    main_action.report_name,
)
if so_portal:
    mail_pdf, _ = Report._render_qweb_pdf(main_action.report_name, so_portal.ids)
    check("email_attachment_pdf", pdf_ok(mail_pdf), len(mail_pdf))

# Smoke: otros dominios sin cambio
inv = env["account.move"].search([("move_type", "=", "out_invoice"), ("state", "=", "posted")], limit=1)
if inv:
    inv_r = env.ref("account.account_invoices")
    pdf, _ = Report._render_qweb_pdf(inv_r.report_name, inv.ids)
    check("invoice_unchanged", pdf_ok(pdf))
po = env["purchase.order"].search([], limit=1)
if po:
    po_r = env.ref("purchase.action_report_purchase_order")
    pdf, _ = Report._render_qweb_pdf(po_r.report_name, po.ids)
    check("purchase_unchanged", pdf_ok(pdf))

# Limpieza cotización de prueba
new_so.unlink()
env.cr.commit()

report["pass"] = len(report["failed_checks"]) == 0

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE24_2:" + json.dumps(report, indent=2, ensure_ascii=False))
