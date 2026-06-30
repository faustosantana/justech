#!/usr/bin/env python3
"""Fase 6 — Validación MVP Justech l10n DO (odoo shell)."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from odoo import Command

company = env["res.company"].search([], limit=1)
result = {
    "phase": 6,
    "mvp": True,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "company": company.name,
    "modules": {},
    "tests": {},
    "ok": True,
    "errors": [],
}


def fail(test_name, msg):
    result["ok"] = False
    result["errors"].append(f"{test_name}: {msg}")
    result["tests"][test_name] = {"status": "FAIL", "message": msg}


def pass_(test_name, detail=""):
    result["tests"][test_name] = {"status": "PASS", "detail": detail}


# Module states
for mod in ("justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports"):
    rec = env["ir.module.module"].search([("name", "=", mod)], limit=1)
    result["modules"][mod] = rec.state if rec else "NOT_FOUND"
    if not rec or rec.state != "installed":
        fail(f"module_{mod}", f"state={result['modules'][mod]}")

tax_18 = env["account.tax"].search(
    [
        ("company_id", "=", company.id),
        ("amount", "=", 18),
        ("type_tax_use", "=", "sale"),
    ],
    limit=1,
)
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
if not product:
    product = env["product.product"].create(
        {
            "name": "Phase6 Lab Product",
            "type": "consu",
            "is_storable": True,
            "list_price": 100.0,
            "taxes_id": [Command.set(tax_18.ids)] if tax_18 else [],
        }
    )
journal_sale = env["account.journal"].search(
    [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
)
journal_sale.write(
    {
        "justech_do_use_ncf": True,
        "justech_do_document_type_ids": [
            Command.set(env["justech.do.fiscal.document.type"].search([]).ids)
        ],
    }
)
doc_b01 = env.ref("justech_l10n_do_base.doc_type_b01")
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02")
doc_b04 = env.ref("justech_l10n_do_base.doc_type_b04")
doc_b11 = env.ref("justech_l10n_do_base.doc_type_b11")
doc_b13 = env.ref("justech_l10n_do_base.doc_type_b13")

Range = env["justech.do.ncf.range"]
today = date.today()


def ensure_range(doc, name, journals):
    rec = Range.search(
        [
            ("document_type_id", "=", doc.id),
            ("company_id", "=", company.id),
            ("state", "=", "active"),
        ],
        limit=1,
    )
    if rec:
        return rec
    rec = Range.create(
        {
            "name": name,
            "document_type_id": doc.id,
            "company_id": company.id,
            "sequence_start": 1000,
            "sequence_end": 9999,
            "next_sequence": 1000,
            "date_from": today - timedelta(days=30),
            "date_to": today + timedelta(days=365),
            "journal_ids": [Command.set(journals.ids)],
        }
    )
    rec.action_activate()
    return rec


ensure_range(doc_b02, "Phase6 B02", journal_sale)
ensure_range(doc_b01, "Phase6 B01", journal_sale)
ensure_range(doc_b04, "Phase6 B04", journal_sale)

partner_b2b = env["res.partner"].search([("vat", "!=", False)], limit=1)
if not partner_b2b:
    partner_b2b = env["res.partner"].create({"name": "Phase6 B2B", "vat": "131793916"})
partner_cf = env["res.partner"].create({"name": f"Phase6 CF {datetime.now().timestamp()}"})


def mk_invoice(partner, move_type="out_invoice", journal=None):
    journal = journal or journal_sale
    return env["account.move"].create(
        {
            "move_type": move_type,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "invoice_date": today,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
                    }
                )
            ],
        }
    )


# B02
try:
    m_b02 = mk_invoice(partner_cf)
    m_b02.action_post()
    if not m_b02.justech_do_ncf.startswith("B02"):
        fail("invoice_b02", m_b02.justech_do_ncf)
    else:
        pass_("invoice_b02", m_b02.justech_do_ncf)
except Exception as e:
    fail("invoice_b02", str(e))

# B01
try:
    m_b01 = mk_invoice(partner_b2b)
    m_b01.action_post()
    if not m_b01.justech_do_ncf.startswith("B01"):
        fail("invoice_b01", m_b01.justech_do_ncf)
    else:
        pass_("invoice_b01", m_b01.justech_do_ncf)
except Exception as e:
    fail("invoice_b01", str(e))

# B04 credit note
try:
    cn = m_b02._reverse_moves(default_values_list=[{"invoice_date": today}])
    cn.action_post()
    if not cn.justech_do_ncf.startswith("B04"):
        fail("credit_note_b04", cn.justech_do_ncf)
    else:
        pass_("credit_note_b04", cn.justech_do_ncf)
except Exception as e:
    fail("credit_note_b04", str(e))

# Duplicate NCF
try:
    dup = mk_invoice(partner_cf)
    dup.justech_do_ncf = m_b02.justech_do_ncf
    dup.action_post()
    fail("duplicate_ncf", "should have raised")
except Exception:
    pass_("duplicate_ncf", "blocked")

# Depleted range — isolate journal so only the 1-sequence range applies
try:
    depleted_journal = env["account.journal"].create(
        {
            "name": "Phase6 Depleted Test",
            "code": "PDT",
            "type": "sale",
            "company_id": company.id,
            "justech_do_use_ncf": True,
            "justech_do_document_type_ids": [Command.set([doc_b02.id])],
        }
    )
    depleted = Range.create(
        {
            "name": "Phase6 Depleted",
            "document_type_id": doc_b02.id,
            "company_id": company.id,
            "sequence_start": 1,
            "sequence_end": 1,
            "next_sequence": 1,
            "date_from": today - timedelta(days=1),
            "date_to": today + timedelta(days=30),
            "journal_ids": [Command.set(depleted_journal.ids)],
        }
    )
    depleted.action_activate()
    dep_partner = env["res.partner"].create({"name": "Depleted CF"})
    m_dep = env["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": dep_partner.id,
            "journal_id": depleted_journal.id,
            "invoice_date": today,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
                    }
                )
            ],
        }
    )
    m_dep.action_post()
    dep_partner2 = env["res.partner"].create({"name": "Depleted CF 2"})
    m_dep2 = env["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": dep_partner2.id,
            "journal_id": depleted_journal.id,
            "invoice_date": today,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
                    }
                )
            ],
        }
    )
    m_dep2.action_post()
    fail("depleted_range", "should have raised")
except Exception:
    pass_("depleted_range", "blocked")

# Expired range
try:
    expired = Range.create(
        {
            "name": "Phase6 Expired",
            "document_type_id": doc_b02.id,
            "company_id": company.id,
            "sequence_start": 1,
            "sequence_end": 100,
            "next_sequence": 1,
            "date_from": today - timedelta(days=60),
            "date_to": today - timedelta(days=1),
            "journal_ids": [Command.set(journal_sale.ids)],
        }
    )
    expired.action_activate()
    mk_invoice(env["res.partner"].create({"name": "Expired CF"})).action_post()
    fail("expired_range", "should have raised")
except Exception:
    pass_("expired_range", "blocked")

# B11 / B13 purchase
journal_purchase = env["account.journal"].search(
    [("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1
)
for doc, label in ((doc_b11, "b11"), (doc_b13, "b13")):
    try:
        journal_purchase.write(
            {
                "justech_do_use_ncf": True,
                "justech_do_default_document_type_id": doc.id,
                "justech_do_document_type_ids": [Command.set([doc.id])],
            }
        )
        ensure_range(doc, f"Phase6 {doc.prefix}", journal_purchase)
        vendor = env["res.partner"].create({"name": f"Vendor {label}"})
        bill = env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": vendor.id,
                "journal_id": journal_purchase.id,
                "invoice_date": today,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "price_unit": 50.0,
                        }
                    )
                ],
            }
        )
        bill.action_post()
        if not bill.justech_do_ncf.startswith(doc.prefix):
            fail(f"purchase_{label}", bill.justech_do_ncf)
        else:
            pass_(f"purchase_{label}", bill.justech_do_ncf)
    except Exception as e:
        fail(f"purchase_{label}", str(e))

# Void + 608
try:
    void_move = mk_invoice(env["res.partner"].create({"name": "Void CF"}))
    void_move.action_post()
    void_move.action_void_ncf()
    r608 = env["justech.do.fiscal.report"].create(
        {
            "name": "Phase6 608",
            "report_type": "608",
            "date_from": today,
            "date_to": today,
            "company_id": company.id,
        }
    )
    r608.action_generate()
    if not r608.line_ids:
        fail("report_608", "no lines")
    else:
        pass_("report_608", str(len(r608.line_ids)))
except Exception as e:
    fail("report_608", str(e))

# 607
try:
    r607 = env["justech.do.fiscal.report"].create(
        {
            "name": "Phase6 607",
            "report_type": "607",
            "date_from": today,
            "date_to": today,
            "company_id": company.id,
        }
    )
    r607.action_generate()
    pass_("report_607", str(len(r607.line_ids)))
except Exception as e:
    fail("report_607", str(e))

# 606
try:
    r606 = env["justech.do.fiscal.report"].create(
        {
            "name": "Phase6 606",
            "report_type": "606",
            "date_from": today,
            "date_to": today,
            "company_id": company.id,
        }
    )
    r606.action_generate()
    pass_("report_606", str(len(r606.line_ids)))
except Exception as e:
    fail("report_606", str(e))

# Balanced entry + AR
try:
    debits = sum(m_b02.line_ids.mapped("debit"))
    credits = sum(m_b02.line_ids.mapped("credit"))
    if abs(debits - credits) > 0.02:
        fail("balanced_entry", f"debit={debits} credit={credits}")
    else:
        pass_("balanced_entry", f"debit={debits} credit={credits}")
    receivable = m_b02.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable")
    if not receivable:
        fail("receivable_line", "missing")
    else:
        pass_("receivable_line", str(receivable[0].balance))
except Exception as e:
    fail("balanced_entry", str(e))

# PDF render smoke test
try:
    pdf, _fmt = env["ir.actions.report"]._render_qweb_pdf(
        "account.account_invoices", m_b02.ids
    )
    if not pdf:
        fail("pdf_ncf", "empty pdf")
    else:
        pass_("pdf_ncf", f"{len(pdf)} bytes")
except Exception as e:
    fail("pdf_ncf", str(e))

print("PHASE6_MVP ok:", json.dumps(result["ok"]))
print(json.dumps(result, indent=2, default=str))
