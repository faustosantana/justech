# -*- coding: utf-8 -*-
"""Validación Fase 19 — campos P0 y exportador 606 en TEST."""
import base64
import json
from datetime import date

from odoo import Command

MARKER = "PHASE19:"


def _log(msg):
    print(msg)


def _result(case, ok, detail=""):
    return {"case": case, "ok": ok, "detail": detail}


results = []
company = env.company
if company.country_id.code != "DO":
    company.country_id = env.ref("base.do")
company.justech_do_fiscal_enabled = True

tax_18 = env["account.tax"].search(
    [
        ("company_id", "=", company.id),
        ("amount", "=", 18),
        ("type_tax_use", "=", "purchase"),
    ],
    limit=1,
)
journal = env["account.journal"].search(
    [("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1
)
doc_b11 = env.ref("justech_l10n_do_base.doc_type_b11")
doc_b13 = env.ref("justech_l10n_do_base.doc_type_b13")
journal.justech_do_use_ncf = True
journal.justech_do_default_document_type_id = doc_b11.id

env["hellenia.withholding.catalog"].sync_catalog_from_taxes(company)

product = env["product.product"].search([("name", "=", "PHASE19 Product")], limit=1)
if not product:
    product = env["product.product"].create(
        {
            "name": "PHASE19 Product",
            "type": "consu",
            "is_storable": True,
            "standard_price": 100.0,
            "supplier_taxes_id": [Command.set(tax_18.ids)],
        }
    )

partner_formal = env["res.partner"].search([("name", "=", "PHASE19 Proveedor B11")], limit=1)
if not partner_formal:
    partner_formal = env["res.partner"].create(
        {"name": "PHASE19 Proveedor B11", "vat": "131793916", "supplier_rank": 1}
    )
results.append(
    _result(
        "partner_id_type_b11",
        partner_formal.justech_do_partner_id_type == "1",
        partner_formal.justech_do_partner_id_type,
    )
)

partner_informal = env["res.partner"].search([("name", "=", "PHASE19 Proveedor B13")], limit=1)
if not partner_informal:
    partner_informal = env["res.partner"].create(
        {"name": "PHASE19 Proveedor B13", "vat": "00112345678", "supplier_rank": 1}
    )
results.append(
    _result(
        "partner_id_type_b13",
        partner_informal.justech_do_partner_id_type == "2",
        partner_informal.justech_do_partner_id_type,
    )
)

move = env["account.move"].search(
    [("ref", "=", "PHASE19-606-INVOICE")], limit=1
)
if not move:
    move = env["account.move"].create(
        {
            "move_type": "in_invoice",
            "partner_id": partner_formal.id,
            "journal_id": journal.id,
            "invoice_date": date.today(),
            "ref": "PHASE19-606-INVOICE",
            "justech_do_ncf": "B1100000999",
            "justech_do_document_type_id": doc_b11.id,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": 1000.0,
                    }
                )
            ],
        }
    )
    move.action_post()

results.append(_result("invoice_posted", move.state == "posted", move.state))
results.append(_result("invoice_ncf", bool(move.justech_do_ncf), move.justech_do_ncf))
results.append(
    _result(
        "dgii_line_status",
        move.justech_do_dgii_line_status == "1",
        move.justech_do_dgii_line_status,
    )
)

exporter = env["justech.do.dgii.606.exporter"]
errors = exporter.validate_moves_606(company, date.today(), date.today())
results.append(_result("validate_606", not errors, "; ".join(errors[:3])))

try:
    content, filename = exporter.export_xlsx(company, date.today(), date.today())
    ok_export = bool(content) and "606" in filename
    results.append(_result("export_606_xlsx", ok_export, filename))
except Exception as exc:
    results.append(_result("export_606_xlsx", False, str(exc)))

catalog = env["hellenia.withholding.catalog"].search(
    [("code", "=", "RET-HON-10"), ("company_id", "=", company.id)], limit=1
)
results.append(
    _result(
        "dgii_withholding_code",
        bool(catalog.dgii_withholding_code),
        catalog.dgii_withholding_code,
    )
)

passed = sum(1 for r in results if r["ok"])
payload = {
    "phase": "19",
    "passed": passed,
    "total": len(results),
    "pass": passed == len(results),
    "results": results,
}
_log(f"{MARKER}{json.dumps(payload, ensure_ascii=False)}")
