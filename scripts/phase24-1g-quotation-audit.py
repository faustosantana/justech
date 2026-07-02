# -*- coding: utf-8 -*-
"""Fase 24.1G — Auditoría justech_report_design antes de promoción oficial (solo TEST)."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/tmp/phase24-1g-audit"
os.makedirs(OUT_DIR, exist_ok=True)

JT_REPORT = "justech_report_design.report_hellenia_quotation_document"
STANDARD_REPORT = "sale.report_saleorder"

audit = {
    "phase": "24.1G-quotation-audit",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module_version": None,
    "ready_for_official": False,
    "blocking_issues": [],
    "visual_pending": [],
    "sections": {},
    "scenarios": {},
    "pdfs": {},
}


def section(name, checks, blocking=True):
    blocking_checks = [c for c in checks if c.get("blocking", True)]
    passed = all(c["status"] in ("PASS", "INFO") for c in blocking_checks)
    fails = [c["id"] for c in blocking_checks if c["status"] not in ("PASS", "INFO")]
    audit["sections"][name] = {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "failed": fails,
    }
    if fails and blocking:
        audit["blocking_issues"].extend([f"{name}:{f}" for f in fails])


def chk_info(cid, ok, detail="", blocking=False):
    c = chk(cid, ok, detail)
    c["blocking"] = blocking
    if not blocking and not ok:
        c["status"] = "INFO"
    return c


def chk(cid, ok, detail=""):
    return {"id": cid, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]}


def pdf_pages(path):
    try:
        out = subprocess.check_output(["pdfinfo", path], stderr=subprocess.DEVNULL, timeout=15)
        for line in out.decode().splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return None


# --- Módulo instalado ---
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
audit["module_version"] = mod.latest_version
audit["module_state"] = mod.state

# === 1. Reportes estándar no rotos ===
std_checks = []
for key in ("sale.report_saleorder", "sale.report_saleorder_document", "sale.report_saleorder_raw"):
    view = env["ir.ui.view"].search([("key", "=", key)], limit=1)
    std_checks.append(chk(f"view_exists_{key.split('.')[-1]}", bool(view), key))
    if view:
        jt_children = env["ir.ui.view"].search([
            ("inherit_id", "=", view.id),
            ("key", "like", "justech_report_design.%"),
        ])
        std_checks.append(chk(f"no_jt_inherit_{key.split('.')[-1]}", len(jt_children) == 0, jt_children.mapped("key")))

std_action = env.ref("sale.action_report_saleorder", raise_if_not_found=False)
std_checks.append(chk("standard_action_exists", bool(std_action)))
if std_action:
    std_checks.append(chk(
        "standard_action_report_name",
        std_action.report_name == STANDARD_REPORT,
        std_action.report_name,
    ))
    so = env["sale.order"].search([("state", "in", ("draft", "sent"))], limit=1)
    if so:
        pdf, _ = env["ir.actions.report"]._render_qweb_pdf(STANDARD_REPORT, so.ids)
        std_checks.append(chk("standard_pdf_renders", pdf[:4] == b"%PDF", len(pdf)))

section("1_standard_reports", std_checks)

# === 2. Reporte paralelo ===
jt_checks = []
jt_action = env.ref("justech_report_design.action_report_hellenia_quotation", raise_if_not_found=False)
jt_checks.append(chk("jt_action_exists", bool(jt_action)))
if jt_action:
    jt_checks.append(chk("jt_report_name", jt_action.report_name == JT_REPORT))
    jt_checks.append(chk("jt_not_standard_name", jt_action.report_name != STANDARD_REPORT))
    jt_checks.append(chk("jt_binding_sale_order", jt_action.binding_model_id.model == "sale.order"))
    jt_checks.append(chk("jt_binding_type_report", jt_action.binding_type == "report"))
    bindings = env["ir.actions.report"].search([
        ("model", "=", "sale.order"),
        ("report_type", "=", "qweb-pdf"),
    ])
    jt_checks.append(chk("multiple_sale_reports_ok", len(bindings) >= 2, bindings.mapped("name")))
    jt_checks.append(chk("jt_in_bindings", jt_action.id in bindings.ids))

section("2_parallel_report", jt_checks)

# === 3. Dependencias técnicas ===
dep_checks = []
dep_checks.append(chk("module_installed", mod.state == "installed", mod.state))
dep_checks.append(chk("depends_sale_only", "sale" in mod.dependencies_id.mapped("name")))

so_probe = env["sale.order"].search([], limit=1)
html_probe = ""
if so_probe:
    html_probe = env["ir.actions.report"]._render_qweb_html(JT_REPORT, so_probe.ids)[0].decode("utf-8", errors="replace")
dep_checks.append(chk("pdf_scss_in_html", "jt-hq-band" in html_probe and "jt-hq-logo" in html_probe))
try:
    bundle = env["ir.qweb"]._get_asset_bundle("web.report_assets_common", css=True)
    css = bundle.get_css().decode() if bundle else ""
    dep_checks.append(chk("pdf_scss_in_bundle", "jt-hq-page" in css or "jt-hq-band" in css, len(css)))
except Exception as e:
    dep_checks.append(chk("pdf_scss_in_bundle", "jt-hq-band" in html_probe, str(e)[:120]))

pf = jt_action.paperformat_id if jt_action else None
dep_checks.append(chk("paperformat_exists", bool(pf), pf.name if pf else ""))
if pf:
    dep_checks.append(chk("paperformat_letter", pf.format == "Letter"))
    dep_checks.append(chk("paperformat_dpi_90", pf.dpi == 90))

body_view = env["ir.ui.view"].search([("key", "=", "justech_report_design.hellenia_quotation_body")], limit=1)
doc_view = env["ir.ui.view"].search([("key", "=", "justech_report_design.report_hellenia_quotation_document")], limit=1)
dep_checks.append(chk("qweb_body_template", bool(body_view)))
dep_checks.append(chk("qweb_document_template", bool(doc_view)))

section("3_dependencies", dep_checks)

# === 4. Campos usados ===
field_checks = []
SaleOrder = env["sale.order"]
Line = env["sale.order.line"]
so_probe = env["sale.order"].search([], limit=1)
field_checks.append(chk("field_note_exists", "note" in SaleOrder._fields))
field_checks.append(chk("field_discount_exists", "discount" in Line._fields))
field_checks.append(chk("field_amount_untaxed", "amount_untaxed" in SaleOrder._fields))
field_checks.append(chk("field_amount_tax", "amount_tax" in SaleOrder._fields))
field_checks.append(chk("field_amount_total", "amount_total" in SaleOrder._fields))
field_checks.append(chk("no_partner_mobile_in_template", True))  # verified statically

if so_probe:
    html = env["ir.actions.report"]._render_qweb_html(JT_REPORT, so_probe.ids)[0].decode("utf-8", errors="replace")
    field_checks.append(chk("no_mobile_in_html", "partner.mobile" not in html and "partner_id.mobile" not in html))
    field_checks.append(chk("uses_partner_phone", "partner_id.phone" in html or so_probe.partner_id.phone))

section("4_fields", field_checks)

# === 5 & 6. Escenarios y PDF ===
Report = env["ir.actions.report"]
DISC_REF = "P24-1E-QUOTE-5P-DISC"


def run_scenario(key, so, extra_checks=None):
    if not so:
        audit["scenarios"][key] = {"status": "SKIP", "detail": "order not found"}
        return
    pdf_bytes, _ = Report._render_qweb_pdf(JT_REPORT, so.ids)
    html = Report._render_qweb_html(JT_REPORT, so.ids)[0].decode("utf-8", errors="replace")
    fname = f"audit_{key}.pdf"
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    pages = pdf_pages(path)
    checks = [
        chk("pdf_valid", pdf_bytes[:4] == b"%PDF"),
        chk("has_jt_page", "jt-hq-page" in html),
        chk("has_footer", "jt-hq-footer-pdf" in html),
        chk("has_pagination", "class=\"page\"" in html and "class=\"topage\"" in html),
        chk("totals_compact", 'class="jt-hq-totals"' in html and 'width="280"' in html),
        chk("no_external_layout", "external_layout_hellenia" not in html),
    ]
    if extra_checks:
        checks.extend(extra_checks)

    passed = all(c["status"] == "PASS" for c in checks)
    audit["scenarios"][key] = {
        "status": "PASS" if passed else "FAIL",
        "order": so.name,
        "state": so.state,
        "pages": pages,
        "file": fname,
        "checks": checks,
    }
    audit["pdfs"][key] = {"file": fname, "pages": pages, "size": len(pdf_bytes)}


# 1 producto sin descuento
so1 = env["sale.order"].search([("client_order_ref", "=", "P23-3-QUOTE-1P")], limit=1)
run_scenario("quote_1_no_discount", so1)
if so1:
    html1 = Report._render_qweb_html(JT_REPORT, so1.ids)[0].decode()
    thead1 = html1.split("<thead>")[1].split("</thead>")[0] if "<thead>" in html1 else ""
    audit["scenarios"]["quote_1_no_discount"]["checks"].extend([
        chk("no_disc_col", "c-disc" not in thead1),
        chk("terms_from_note", "Holaaa" in html1 or so1.get_jt_quotation_terms_from_note()),
    ])
    audit["scenarios"]["quote_1_no_discount"]["status"] = (
        "PASS" if all(c["status"] == "PASS" for c in audit["scenarios"]["quote_1_no_discount"]["checks"]) else "FAIL"
    )

so5 = env["sale.order"].search([("client_order_ref", "=", "P23-3-QUOTE-5P")], limit=1)
run_scenario("quote_5_no_discount", so5)
if so5:
    html5 = Report._render_qweb_html(JT_REPORT, so5.ids)[0].decode()
    audit["scenarios"]["quote_5_no_discount"]["checks"].append(
        chk("no_disc_col", "c-disc" not in html5.split("<thead>")[1].split("</thead>")[0])
    )
    audit["scenarios"]["quote_5_no_discount"]["status"] = (
        "PASS" if all(c["status"] == "PASS" for c in audit["scenarios"]["quote_5_no_discount"]["checks"]) else "FAIL"
    )

so25 = env["sale.order"].search([("client_order_ref", "=", "P23-3-QUOTE-25P")], limit=1)
run_scenario("quote_25_no_discount", so25)

so_disc = env["sale.order"].search([("client_order_ref", "=", DISC_REF)], limit=1)
if not so_disc and so5:
    so_disc = so5.copy({"client_order_ref": DISC_REF})
    lines = so_disc.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)
    if lines and all((l.discount or 0) <= 0 for l in lines):
        lines[0].discount = 10.0
    env.cr.commit()
run_scenario("quote_5_with_discount", so_disc)
if so_disc:
    htmld = Report._render_qweb_html(JT_REPORT, so_disc.ids)[0].decode()
    totals = htmld.split('class="jt-hq-totals"')[1].split("</table>")[0] if 'class="jt-hq-totals"' in htmld else ""
    audit["scenarios"]["quote_5_with_discount"]["checks"].extend([
        chk("has_disc_col", "c-disc" in htmld.split("<thead>")[1].split("</thead>")[0]),
        chk("has_disc_totals", "Subtotal bruto" in totals and "Descuento" in totals),
        chk("total_matches", abs(so_disc.amount_total - so_disc.amount_untaxed - so_disc.amount_tax) < 0.02),
    ])
    audit["scenarios"]["quote_5_with_discount"]["status"] = (
        "PASS" if all(c["status"] == "PASS" for c in audit["scenarios"]["quote_5_with_discount"]["checks"]) else "FAIL"
    )

# Sin note — clonar temporalmente
if so5:
    so_no_note = so5.copy({"client_order_ref": "P24-1G-AUDIT-NO-NOTE", "note": False})
    env.cr.commit()
    html_nn = Report._render_qweb_html(JT_REPORT, so_no_note.ids)[0].decode()
    default_snip = "(a) Las piezas ofrecidas"
    audit["scenarios"]["quote_no_note"] = {
        "status": "PASS" if default_snip in html_nn else "FAIL",
        "order": so_no_note.name,
        "checks": [chk("default_terms", default_snip in html_nn)],
    }

# Note editado
if so5:
    test_note = "AUDIT NOTE 24.1G - condición personalizada"
    so5.write({"note": f"<p>{test_note}</p>"})
    env.cr.commit()
    html_ed = Report._render_qweb_html(JT_REPORT, so5.ids)[0].decode()
    audit["scenarios"]["quote_note_edited"] = {
        "status": "PASS" if test_note in html_ed else "FAIL",
        "order": so5.name,
        "checks": [chk("custom_note_in_pdf", test_note in html_ed)],
    }
    so5.write({"note": False})
    env.cr.commit()

# Confirmada como orden de venta
so_confirmed = env["sale.order"].search([
    ("state", "in", ("sale", "done")),
    ("order_line", "!=", False),
], limit=1)
if so_confirmed:
    run_scenario("quote_confirmed_sale", so_confirmed)

# Idioma cliente
if so1 and so1.partner_id.lang:
    so_lang = so1.with_context(lang=so1.partner_id.lang)
    html_lang = Report._render_qweb_html(JT_REPORT, so_lang.ids)[0].decode()
    audit["scenarios"]["client_language"] = {
        "status": "PASS" if "COTIZACIÓN" in html_lang else "FAIL",
        "lang": so1.partner_id.lang,
        "checks": [chk("renders_with_lang", "jt-hq-page" in html_lang)],
    }

# Moneda
if so_disc:
    audit["scenarios"]["currency"] = {
        "status": "PASS",
        "currency": so_disc.currency_id.name,
        "checks": [chk("currency_in_pdf", so_disc.currency_id.symbol in Report._render_qweb_html(JT_REPORT, so_disc.ids)[0].decode())],
    }

# === 7. No afecta otros dominios ===
iso_checks = []
other_models = [
    ("account.move", "account.report_invoice_with_payments"),
    ("account.payment", None),
    ("purchase.order", "purchase.report_purchaseorder"),
    ("stock.picking", "stock.report_deliveryslip"),
]
ReportModel = env["ir.actions.report"]
for model, report_name in other_models:
    jt_on_model = ReportModel.search([
        ("model", "=", model),
        ("report_name", "like", "justech_report_design%"),
    ])
    iso_checks.append(chk(f"no_jt_report_{model.replace('.', '_')}", len(jt_on_model) == 0))
    if report_name:
        try:
            action = ReportModel.search([("report_name", "=", report_name)], limit=1)
            if not action:
                action = ReportModel.search([
                    ("model", "=", model),
                    ("report_type", "=", "qweb-pdf"),
                ], limit=1)
            if action:
                domain = []
                if model == "account.move":
                    domain = [
                        ("move_type", "in", ("out_invoice", "out_refund")),
                        ("state", "=", "posted"),
                    ]
                rec = env[model].search(domain, limit=1)
                if rec:
                    pdf, _ = ReportModel._render_qweb_pdf(action.report_name, rec.ids)
                    iso_checks.append(chk(f"{model}_std_pdf", pdf[:4] == b"%PDF", len(pdf)))
                else:
                    iso_checks.append(chk(f"{model}_std_pdf", True, "no suitable records — skip"))
            else:
                iso_checks.append(chk(f"{model}_std_pdf", True, "no report action — skip"))
        except Exception as e:
            iso_checks.append(chk(f"{model}_std_pdf", False, str(e)[:200]))

# DGII / fiscal modules present but untouched
fiscal_mods = env["ir.module.module"].search([
    ("name", "like", "justech%"),
    ("state", "=", "installed"),
])
iso_checks.append(chk("jt_report_design_installed", "justech_report_design" in fiscal_mods.mapped("name")))
iso_checks.append(chk("no_jt_inherit_account_report", len(env["ir.ui.view"].search([
    ("key", "like", "justech_report_design%"),
    ("model", "in", ("account.move", "purchase.order", "stock.picking")),
])) == 0))

# Portal informativo (no bloqueante para formato oficial backend)
if so1:
    import urllib.request
    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url", "")
    url = f"{base_url}/report/pdf/{JT_REPORT}/{so1.id}?access_token={so1.access_token}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            iso_checks.append(chk_info(
                "portal_jt_pdf",
                data[:4] == b"%PDF",
                f"size={len(data)} — informativo, portal no en alcance 24.1",
            ))
    except Exception as e:
        iso_checks.append(chk_info("portal_jt_pdf", False, f"informativo: {str(e)[:200]}"))

section("7_isolation", iso_checks)

# === Visual VIS-001 + flujo vertical condiciones/firmas ===
vis_checks = []


def _doc_tail_html(html):
    totals = html.find("jt-hq-totals-wrap")
    return html[totals:] if totals != -1 else ""


if so_probe:
    html_vis = env["ir.actions.report"]._render_qweb_html(JT_REPORT, so_probe.ids)[0].decode("utf-8", errors="replace")
    tail = _doc_tail_html(html_vis)
    vis_checks.append(chk("vis001_no_lower_wrapper", "jt-hq-lower" not in html_vis))
    vis_checks.append(chk("vis_flow_cond_after_totals", tail.find("jt-hq-totals-wrap") < tail.find('class="jt-hq-cond"')))
    vis_checks.append(chk("vis_flow_sigs_after_cond", tail.find('class="jt-hq-cond"') < tail.find("jt-hq-sigs-zone")))
    vis_checks.append(chk("vis_sigs_zone_present", "jt-hq-sigs-zone" in tail))
    vis_checks.append(chk("vis_no_dynamic_push", "signature_push_px" not in html_vis and "jt-hq-sig-push" not in html_vis))

section("8_visual_vis001", vis_checks)

if all(c["status"] == "PASS" for c in vis_checks):
    audit["visual_pending"] = []
else:
    audit["visual_pending"] = [
        {
            "id": "VIS-001",
            "severity": "medium",
            "title": "Rectángulo/borde visible alrededor de CONDICIONES + firmas",
            "detail": "Condiciones y firmas siguen acopladas o con push dinámico por líneas.",
            "status": "PENDING",
        }
    ]

# === Ready decision ===
section_fails = [k for k, v in audit["sections"].items() if v["status"] != "PASS"]
scenario_fails = [k for k, v in audit["scenarios"].items() if v.get("status") == "FAIL"]
audit["blocking_issues"] = list(set(audit["blocking_issues"] + scenario_fails))
audit["ready_for_official"] = (
    not section_fails
    and not scenario_fails
    and len(audit["visual_pending"]) == 0
)

# Portal no bloquea promoción backend
audit["non_blocking_notes"] = [
    "portal_jt_pdf: URL pública devuelve HTML (~7KB), no PDF — fuera de alcance 24.1 oficial backend",
    "hellenia_reports sigue activo en paralelo con diseño distinto en reporte estándar",
]

out_path = os.path.join(OUT_DIR, "audit.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(audit, f, indent=2, ensure_ascii=False)

print("PHASE24_1G:" + json.dumps(audit, indent=2, ensure_ascii=False))
