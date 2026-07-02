# -*- coding: utf-8 -*-
"""Fase 27 TEST — Validación Orden de Compra Hellenia (fixtures + PDFs)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from odoo import fields

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT = "/tmp/phase27-purchase-order"
os.makedirs(OUT, exist_ok=True)
FIXTURE_REF = "PHASE27-EVIDENCE"

report = {
    "phase": "27-purchase-order-test",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_version": None,
    "checks": {},
    "errors": [],
    "pdfs": [],
    "fixtures": [],
    "required_scenarios": [
        "01_one_line",
        "02_five_lines",
        "03_twenty_lines",
        "04_with_discount",
        "05_no_discount",
        "06_usd",
        "07_dop",
        "08_international_vendor",
        "09_national_vendor",
    ],
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


def render_pdf(name, po):
    report_ref = env.ref("justech_report_design.action_report_justech_purchase_order")
    pdf, _ = env["ir.actions.report"]._render_qweb_pdf(report_ref.report_name, po.ids)
    path = os.path.join(OUT, name)
    with open(path, "wb") as fh:
        fh.write(pdf)
    report["pdfs"].append(
        {"file": name, "bytes": len(pdf), "po": po.name, "partner_ref": po.partner_ref or ""}
    )
    return pdf


# --- Auditoría campos (audit.json) ---
AUDIT_FIELDS_PO = [
    "name", "state", "partner_id", "dest_address_id", "partner_ref",
    "date_order", "date_approve", "date_planned", "user_id",
    "payment_term_id", "currency_id", "incoterm_id", "incoterm_location",
    "note", "order_line", "amount_untaxed", "amount_tax", "amount_total", "company_id",
]
AUDIT_FIELDS_POL = [
    "product_id", "name", "product_qty", "product_uom_id", "price_unit",
    "discount", "tax_ids", "price_subtotal", "date_planned", "display_type",
]


def field_info(model_name, fname):
    f = env[model_name]._fields.get(fname)
    if not f:
        return None
    return {
        "type": f.type,
        "string": f.string,
        "required": bool(getattr(f, "required", False)),
        "store": bool(getattr(f, "store", True)),
    }


audit = {
    "phase": "27-purchase-order-field-audit",
    "timestamp_utc": report["timestamp_utc"],
    "database": DB,
    "models": {"purchase.order": {}, "purchase.order.line": {}},
    "field_map": {
        "order_number": "purchase.order.name",
        "state": "purchase.order.state",
        "vendor": "purchase.order.partner_id",
        "vendor_address": "partner_id (+ dest_address_id si dropship)",
        "vendor_vat": "partner_id.vat",
        "vendor_phone": "partner_id.phone",
        "vendor_email": "partner_id.email",
        "order_date": "purchase.order.date_order",
        "expected_date": "purchase.order.date_planned",
        "buyer": "purchase.order.user_id",
        "payment_terms": "purchase.order.payment_term_id",
        "currency": "purchase.order.currency_id",
        "incoterm": "purchase.order.incoterm_id + incoterm_location",
        "vendor_reference": "purchase.order.partner_ref",
        "observations": "purchase.order.note",
        "line_product": "purchase.order.line.product_id",
        "line_description": "purchase.order.line.name",
        "line_qty": "purchase.order.line.product_qty",
        "line_uom": "purchase.order.line.product_uom_id",
        "line_price": "purchase.order.line.price_unit",
        "line_discount": "purchase.order.line.discount",
        "line_taxes": "purchase.order.line.tax_ids",
        "line_subtotal": "purchase.order.line.price_subtotal",
        "subtotal": "purchase.order.amount_untaxed",
        "taxes": "purchase.order.amount_tax",
        "total": "purchase.order.amount_total",
    },
    "missing": [],
}

for fname in AUDIT_FIELDS_PO:
    info = field_info("purchase.order", fname)
    if info:
        audit["models"]["purchase.order"][fname] = info
    else:
        audit["missing"].append(f"purchase.order.{fname}")

for fname in AUDIT_FIELDS_POL:
    info = field_info("purchase.order.line", fname)
    if info:
        audit["models"]["purchase.order.line"][fname] = info
    else:
        audit["missing"].append(f"purchase.order.line.{fname}")

with open(os.path.join(OUT, "audit.json"), "w") as f:
    json.dump(audit, f, indent=2, ensure_ascii=False)

check("audit_json", not audit["missing"], audit["missing"] or "ok")

# --- Módulo y reportes ---
mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
report["module_version"] = mod.latest_version
check("module_version", mod.latest_version == "19.0.7.0.0", mod.latest_version)

jt_report = env.ref("justech_report_design.action_report_justech_purchase_order", raise_if_not_found=False)
std_report = env.ref("purchase.action_report_purchase_order", raise_if_not_found=False)
check("hellenia_report_exists", bool(jt_report), jt_report.report_name if jt_report else "")
check(
    "parallel_not_same_template",
    jt_report and std_report and jt_report.report_name != std_report.report_name,
    f"jt={jt_report.report_name if jt_report else ''} std={std_report.report_name if std_report else ''}",
)
check(
    "print_menu_bound",
    bool(jt_report and jt_report.binding_model_id and jt_report.binding_type == "report"),
    jt_report.name if jt_report else "",
)

v = env.ref("justech_report_design.view_purchase_order_form_jt_po_report", raise_if_not_found=False)
arch = v.arch_db or "" if v else ""
check("header_button", "Orden de Compra PDF" in arch and "action_jt_print_purchase_order" in arch, True)

form = env["purchase.order"].get_view(view_type="form")
form_arch = form.get("arch", "")
check("form_has_button", "action_jt_print_purchase_order" in form_arch, True)

ui_evidence = {
    "header_button_label": "Orden de Compra PDF",
    "header_button_method": "action_jt_print_purchase_order",
    "print_menu_report_name": jt_report.name if jt_report else "",
    "print_menu_binding_model": jt_report.binding_model_id.model if jt_report and jt_report.binding_model_id else "",
    "form_contains_button": "action_jt_print_purchase_order" in form_arch,
    "view_arch_snippet": arch[:500] if arch else "",
}

# --- Fixtures TEST (solo borrador, sin confirmar) ---
PO = env["purchase.order"]
Partner = env["res.partner"]
Product = env["product.product"]
Currency = env["res.currency"]

dop = Currency.search([("name", "=", "DOP")], limit=1)
usd = Currency.search([("name", "=", "USD")], limit=1)
do_country = env.ref("base.do", raise_if_not_found=False)
us_country = env.ref("base.us", raise_if_not_found=False)

products = Product.search([("purchase_ok", "=", True)], limit=25, order="id")
if len(products) < 20:
  raise SystemExit(f"ABORT: se requieren >=20 productos comprables, hay {len(products)}")

sample_po = PO.search([("order_line", "!=", False)], limit=1, order="id desc")
purchase_taxes = env["account.tax"]
if sample_po:
    for line in sample_po.order_line:
        if line.tax_ids:
            purchase_taxes = line.tax_ids
            break

national_vendor = Partner.search(
    [("supplier_rank", ">", 0), ("country_id.code", "=", "DO")], limit=1
) or Partner.search([("supplier_rank", ">", 0)], limit=1)
if not national_vendor:
    national_vendor = Partner.create(
        {
            "name": "PHASE27 Proveedor Nacional",
            "supplier_rank": 1,
            "country_id": do_country.id if do_country else False,
            "vat": "130000000",
            "email": "nacional@phase27.test",
            "phone": "809-555-0100",
            "street": "Av. Winston Churchill 123",
            "city": "Santo Domingo",
        }
    )

intl_vendor = Partner.search(
    [("supplier_rank", ">", 0), ("country_id", "!=", False), ("country_id.code", "!=", "DO")],
    limit=1,
)
if not intl_vendor:
    intl_vendor = Partner.create(
        {
            "name": "PHASE27 Vendor International Inc.",
            "supplier_rank": 1,
            "country_id": us_country.id if us_country else False,
            "email": "intl@phase27.test",
            "phone": "+1 305 555 0199",
            "street": "100 Biscayne Blvd",
            "city": "Miami",
        }
    )

planned = fields.Datetime.now() + timedelta(days=14)


def line_cmd(product, qty=1, price=100.0, discount=0.0):
    vals = {
        "product_id": product.id,
        "product_qty": qty,
        "price_unit": price,
        "date_planned": planned,
    }
    if discount:
        vals["discount"] = discount
    if purchase_taxes:
        vals["tax_ids"] = [(6, 0, purchase_taxes.ids)]
    return (0, 0, vals)


def create_fixture(key, partner, currency, line_cmds, discount_note="", extra=None):
    extra = extra or {}
    vals = {
        "partner_id": partner.id,
        "currency_id": currency.id,
        "partner_ref": f"{FIXTURE_REF}-{key}",
        "note": f"<p>Observaciones de prueba Fase 27 — escenario {key}. {discount_note}</p>",
        "date_planned": planned,
        "order_line": line_cmds,
        **extra,
    }
    po = PO.create(vals)
    report["fixtures"].append({"scenario": key, "po_id": po.id, "name": po.name, "lines": len(po.order_line)})
    return po


fixtures = {}

fixtures["01_one_line"] = create_fixture(
    "01_one_line", national_vendor, dop, [line_cmd(products[0], 3, 1500.0)]
)
fixtures["02_five_lines"] = create_fixture(
    "02_five_lines",
    national_vendor,
    dop,
    [line_cmd(products[i], i + 1, 500.0 + i * 100) for i in range(5)],
)
fixtures["03_twenty_lines"] = create_fixture(
    "03_twenty_lines",
    national_vendor,
    dop,
    [line_cmd(products[i], 1, 250.0 + i * 5) for i in range(20)],
)
fixtures["04_with_discount"] = create_fixture(
    "04_with_discount",
    national_vendor,
    dop,
    [
        line_cmd(products[0], 10, 1000.0, 5.0),
        line_cmd(products[1], 5, 800.0, 10.0),
        line_cmd(products[2], 2, 2000.0, 0.0),
    ],
    discount_note="Incluye descuentos por línea.",
)
fixtures["05_no_discount"] = create_fixture(
    "05_no_discount",
    national_vendor,
    dop,
    [line_cmd(products[3], 4, 750.0), line_cmd(products[4], 2, 1200.0)],
)
fixtures["06_usd"] = create_fixture(
    "06_usd",
    intl_vendor,
    usd,
    [line_cmd(products[5], 12, 45.50, 0.0), line_cmd(products[6], 8, 22.75, 0.0)],
)
fixtures["07_dop"] = create_fixture(
    "07_dop",
    national_vendor,
    dop,
    [line_cmd(products[7], 6, 3200.0)],
)
fixtures["08_international_vendor"] = create_fixture(
    "08_international_vendor",
    intl_vendor,
    usd,
    [line_cmd(products[8], 15, 18.90)],
)
fixtures["09_national_vendor"] = create_fixture(
    "09_national_vendor",
    national_vendor,
    dop,
    [line_cmd(products[9], 7, 890.0)],
)

scenarios = [(key, fixtures[key]) for key in report["required_scenarios"]]

for fname, po in scenarios:
    try:
        pdf = render_pdf(f"{fname}.pdf", po)
        check(f"pdf_{fname}", pdf[:4] == b"%PDF" and len(pdf) > 500, len(pdf))
    except Exception as exc:
        check(f"pdf_{fname}", False, str(exc))

# Vista previa HTML
preview_po = fixtures["04_with_discount"]
try:
    html, _ = env["ir.actions.report"]._render_qweb_html(jt_report.report_name, preview_po.ids)
    html_path = os.path.join(OUT, "00_html_preview.html")
    with open(html_path, "wb") as fh:
        fh.write(html or b"")
    ui_evidence["html_preview_bytes"] = len(html) if html else 0
    ui_evidence["html_has_title"] = b"ORDEN DE COMPRA" in (html or b"")
    ui_evidence["html_has_observations"] = b"OBSERVACIONES" in (html or b"")
    check("html_preview", bool(html) and b"ORDEN DE COMPRA" in html, len(html) if html else 0)
except Exception as exc:
    check("html_preview", False, str(exc))

with open(os.path.join(OUT, "ui_evidence.json"), "w") as f:
    json.dump(ui_evidence, f, indent=2, ensure_ascii=False)

# Reporte estándar sigue funcionando (orden real existente, no fixture)
real_po = PO.search([("partner_ref", "not ilike", FIXTURE_REF)], limit=1, order="id desc")
if std_report and real_po:
    try:
        std_pdf, _ = env["ir.actions.report"]._render_qweb_pdf(std_report.report_name, real_po.ids)
        check("standard_report_ok", std_pdf[:4] == b"%PDF", len(std_pdf))
    except Exception as exc:
        check("standard_report_ok", False, str(exc))
else:
    check("standard_report_ok", False, "no real PO")

# Botón objeto
act = fixtures["01_one_line"].action_jt_print_purchase_order()
check("button_action", act.get("type") == "ir.actions.report", act.get("report_name", act))

# Descuento columna condicional
check(
    "discount_column_hidden_no_disc",
    not fixtures["05_no_discount"].get_jt_po_has_discount(),
    fixtures["05_no_discount"].get_jt_po_has_discount(),
)
check(
    "discount_column_visible_with_disc",
    fixtures["04_with_discount"].get_jt_po_has_discount(),
    fixtures["04_with_discount"].get_jt_po_has_discount(),
)

critical = [
    "module_version",
    "hellenia_report_exists",
    "parallel_not_same_template",
    "print_menu_bound",
    "header_button",
    "form_has_button",
    "html_preview",
    "standard_report_ok",
    "button_action",
    "audit_json",
    "discount_column_hidden_no_disc",
    "discount_column_visible_with_disc",
]
critical += [f"pdf_{s}" for s in report["required_scenarios"]]

all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical if k in report["checks"])
report["status"] = "PASS" if all_pass else "FAIL"
report["pass"] = report["status"] == "PASS"
report["visual_approval_pending"] = True

with open(os.path.join(OUT, "validation.json"), "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "errors": report["errors"], "pdfs": len(report["pdfs"])}))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
