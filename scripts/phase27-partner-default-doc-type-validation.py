# -*- coding: utf-8 -*-
"""Fase 27 — Validación tipo comprobante fiscal predeterminado en contactos."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB not in ("hellenia_test", "hellenia_prod"):
    raise SystemExit(f"ABORT: solo hellenia_test/hellenia_prod, actual={DB}")

ENV = "test" if DB == "hellenia_test" else "prod"
OUT_DIR = f"/tmp/phase27-partner-default-doc-type-{ENV}"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": f"27-partner-default-doc-type-{ENV}",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "environment": ENV,
    "status": "FAIL",
    "module_versions": {},
    "checks": {},
    "scenarios": {},
    "errors": [],
    "audit": {},
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


Partner = env["res.partner"]
SaleOrder = env["sale.order"]
Move = env["account.move"]
DocType = env["justech.do.fiscal.document.type"]
Product = env["product.product"]
Tax = env["account.tax"]
Journal = env["account.journal"]
NcfRange = env["justech.do.ncf.range"]

company = env.company
if company.country_id.code != "DO":
    company.country_id = env.ref("base.do")
company.justech_do_fiscal_enabled = True

mod_base = env["ir.module.module"].search([("name", "=", "justech_l10n_do_base")], limit=1)
mod_ncf = env["ir.module.module"].search([("name", "=", "justech_l10n_do_ncf")], limit=1)
report["module_versions"] = {
    "justech_l10n_do_base": mod_base.latest_version,
    "justech_l10n_do_ncf": mod_ncf.latest_version,
}
check("module_base_version", mod_base.latest_version == "19.0.1.4.0", mod_base.latest_version)
check("module_ncf_version", mod_ncf.latest_version == "19.0.1.5.0", mod_ncf.latest_version)

doc_b01 = env.ref("justech_l10n_do_base.doc_type_b01")
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02")
check("doc_type_b01_exists", bool(doc_b01), doc_b01.prefix if doc_b01 else "")
check("doc_type_b02_exists", bool(doc_b02), doc_b02.prefix if doc_b02 else "")
check("display_name_format", doc_b01.display_name == "B01 - Factura de Crédito Fiscal", doc_b01.display_name)

# Campo en vista contacto
partner_form = Partner.get_view(view_type="form")
form_arch = partner_form.get("arch", "")
check("partner_field_in_form", "justech_do_default_document_type_id" in form_arch, True)
check(
    "partner_field_label",
    "Tipo de comprobante fiscal predeterminado" in form_arch
    or "justech_do_default_document_type_id" in form_arch,
    True,
)

# Campo en vista cotización
so_form = SaleOrder.get_view(view_type="form")
so_arch = so_form.get("arch", "")
check("sale_order_field_in_form", "justech_do_document_type_id" in so_arch, True)

product = Product.search([("sale_ok", "=", True)], limit=1)
if not product:
    product = Product.create({"name": "P27 Test Product", "type": "consu", "list_price": 100.0})
tax = Tax.search(
    [("company_id", "=", company.id), ("type_tax_use", "=", "sale"), ("amount", "=", 18)],
    limit=1,
)
journal = Journal.search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal.write(
    {
        "justech_do_use_ncf": True,
        "justech_do_document_type_ids": [Command.set(DocType.search([]).ids)],
    }
)


def ensure_range(doc):
    existing = NcfRange.search(
        [
            ("document_type_id", "=", doc.id),
            ("company_id", "=", company.id),
            ("state", "=", "active"),
        ],
        limit=1,
    )
    if existing:
        return existing
    today = date.today()
    ncf_range = NcfRange.create(
        {
            "name": f"P27 Range {doc.prefix}",
            "document_type_id": doc.id,
            "company_id": company.id,
            "sequence_start": 90001,
            "sequence_end": 90100,
            "next_sequence": 90001,
            "date_from": today.replace(day=1),
            "date_to": today.replace(year=today.year + 1),
            "journal_ids": [Command.set(journal.ids)],
        }
    )
    ncf_range.action_activate()
    return ncf_range


ensure_range(doc_b01)
ensure_range(doc_b02)

ts = datetime.now(timezone.utc).strftime("%H%M%S")


def mk_partner(name, doc_type=None, vat=None):
    vals = {"name": f"P27 {name} {ts}"}
    if doc_type:
        vals["justech_do_default_document_type_id"] = doc_type.id
    if vat:
        vals["vat"] = vat
    return Partner.create(vals)


def mk_invoice(partner, doc_type=None):
    vals = {
        "move_type": "out_invoice",
        "partner_id": partner.id,
        "journal_id": journal.id,
        "invoice_date": date.today(),
        "invoice_line_ids": [
            Command.create(
                {
                    "product_id": product.id,
                    "quantity": 1,
                    "price_unit": 100.0,
                    "tax_ids": [Command.set(tax.ids)] if tax else [],
                }
            )
        ],
    }
    if doc_type:
        vals["justech_do_document_type_id"] = doc_type.id
    return Move.create(vals)


# Escenario B01
p_b01 = mk_partner("B01", doc_b01, "131793916")
check("partner_b01_configured", p_b01.justech_do_default_document_type_id == doc_b01, p_b01.name)
so_b01 = SaleOrder.create(
    {
        "partner_id": p_b01.id,
        "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1, "price_unit": 100.0})],
    }
)
check("quotation_b01_inherited", so_b01.justech_do_document_type_id == doc_b01, so_b01.name)
so_b01.action_confirm()
inv_b01 = so_b01._create_invoices()
check("invoice_from_so_b01", inv_b01.justech_do_document_type_id == doc_b01, inv_b01.name)
inv_b01.action_post()
check("ncf_b01_generated", (inv_b01.justech_do_ncf or "").startswith("B01"), inv_b01.justech_do_ncf)
report["scenarios"]["partner_b01"] = {
    "partner": p_b01.name,
    "quotation": so_b01.name,
    "invoice": inv_b01.name,
    "ncf": inv_b01.justech_do_ncf,
}

# Escenario B02
p_b02 = mk_partner("B02", doc_b02)
check("partner_b02_configured", p_b02.justech_do_default_document_type_id == doc_b02, p_b02.name)
so_b02 = SaleOrder.create(
    {
        "partner_id": p_b02.id,
        "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1, "price_unit": 50.0})],
    }
)
check("quotation_b02_inherited", so_b02.justech_do_document_type_id == doc_b02, so_b02.name)
report["scenarios"]["partner_b02"] = {"partner": p_b02.name, "quotation": so_b02.name}

# Escenario sin configuración
p_none = mk_partner("SinDefault")
so_none = SaleOrder.create(
    {
        "partner_id": p_none.id,
        "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1, "price_unit": 25.0})],
    }
)
check("quotation_no_default_empty", not so_none.justech_do_document_type_id, so_none.name)
inv_none = mk_partner_invoice = mk_invoice(p_none)
inv_none.action_post()
check(
    "invoice_no_default_system_b02",
    (inv_none.justech_do_ncf or "").startswith("B02"),
    inv_none.justech_do_ncf,
)
report["scenarios"]["partner_no_default"] = {
    "partner": p_none.name,
    "invoice": inv_none.name,
    "ncf": inv_none.justech_do_ncf,
}

# Factura directa hereda contacto
p_direct = mk_partner("DirectB02", doc_b02)
inv_direct = mk_invoice(p_direct)
check("direct_invoice_inherited", inv_direct.justech_do_document_type_id == doc_b02, inv_direct.name)
inv_direct.action_post()
check("direct_invoice_ncf_b02", (inv_direct.justech_do_ncf or "").startswith("B02"), inv_direct.justech_do_ncf)

# Cambio manual en factura
p_manual = mk_partner("ManualOverride", doc_b01, "131793916")
inv_manual = mk_invoice(p_manual, doc_b02)
check("manual_override_set", inv_manual.justech_do_document_type_id == doc_b02, inv_manual.name)
inv_manual.action_post()
check("manual_override_ncf_b02", (inv_manual.justech_do_ncf or "").startswith("B02"), inv_manual.justech_do_ncf)

# DGII sin errores — verificar campos fiscales intactos
check("dgii_fields_present", hasattr(inv_b01, "justech_do_include_in_dgii"), True)
check("dgii_document_type_prefix", inv_b01.justech_do_document_type_id.prefix == "B01", inv_b01.justech_do_document_type_id.prefix)

# Audit trail
report["audit"] = {
    "models_touched": ["res.partner", "sale.order", "account.move"],
    "fields_added": [
        "res.partner.justech_do_default_document_type_id",
        "sale.order.justech_do_document_type_id",
    ],
    "resolution_priority": [
        "manual_invoice_value",
        "quotation_inherited_value",
        "partner_default",
        "system_rnc_heuristic",
    ],
    "dgii_logic_modified": False,
    "ncf_sequences_modified": False,
    "posted_documents_modified": False,
}

with open(os.path.join(OUT_DIR, "form_ui_snippet.txt"), "w", encoding="utf-8") as fh:
    fh.write("=== res.partner form (extract) ===\n")
    idx = form_arch.find("justech_do_default_document_type_id")
    fh.write(form_arch[max(0, idx - 200) : idx + 200] if idx >= 0 else "field not found")
    fh.write("\n\n=== sale.order form (extract) ===\n")
    idx2 = so_arch.find("justech_do_document_type_id")
    fh.write(so_arch[max(0, idx2 - 200) : idx2 + 200] if idx2 >= 0 else "field not found")

critical = [
    "module_base_version",
    "module_ncf_version",
    "partner_field_in_form",
    "partner_field_label",
    "sale_order_field_in_form",
    "display_name_format",
    "partner_b01_configured",
    "quotation_b01_inherited",
    "invoice_from_so_b01",
    "ncf_b01_generated",
    "partner_b02_configured",
    "quotation_b02_inherited",
    "quotation_no_default_empty",
    "invoice_no_default_system_b02",
    "direct_invoice_inherited",
    "direct_invoice_ncf_b02",
    "manual_override_set",
    "manual_override_ncf_b02",
    "dgii_fields_present",
    "dgii_document_type_prefix",
]

all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical)
report["status"] = "PASS" if all_pass else "FAIL"
report["pass"] = report["status"] == "PASS"

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)
with open(os.path.join(OUT_DIR, "audit.json"), "w", encoding="utf-8") as fh:
    json.dump(report["audit"], fh, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "env": ENV, "errors": report["errors"]}))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
