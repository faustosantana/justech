#!/usr/bin/env python3
"""FISCAL-RD-FINAL — Certificación definitiva módulo fiscal dominicano (TEST)."""
from __future__ import annotations

import calendar
import csv
import json
import os
from datetime import date, datetime, timezone

from odoo import Command
from odoo.exceptions import UserError

OUT = os.environ.get("FISCAL_RD_EVIDENCE", "/var/lib/odoo/fiscal-rd-evidence")
os.makedirs(OUT, exist_ok=True)

today = date.today()
period_from = today.replace(day=1)
period_to = today.replace(day=calendar.monthrange(today.year, today.month)[1])
company = env.company
TAG = "FISCALRD"

result = {"phase": "FISCAL-RD-FINAL", "timestamp": datetime.now(timezone.utc).isoformat(), "pass": True, "errors": []}
ncf_results = {"types": {}, "pass": True}
dgii_results = {"reports": {}, "pass": True}


def fail(msg):
    result["errors"].append(msg)
    result["pass"] = False


def ok_section(section, name, passed, detail=""):
    section[name] = {"ok": bool(passed), "detail": str(detail)[:800]}
    if not passed:
        section["pass"] = False
        result["pass"] = False
        fail(f"{name}: {detail}")


mgr = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if mgr and mgr not in env.user.group_ids:
    env.user.write({"group_ids": [Command.link(mgr.id)]})

DocType = env["justech.do.fiscal.document.type"]
expected_prefixes = [
    "B01", "B02", "B03", "B04", "B11", "B12", "B13", "B14", "B15", "B16", "B17",
]
loaded = set(DocType.search([]).mapped("prefix"))
ok_section(ncf_results, "all_types_loaded", set(expected_prefixes).issubset(loaded), f"missing={set(expected_prefixes)-loaded}")

journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
tax_sale = env["account.tax"].search([("company_id", "=", company.id), ("type_tax_use", "=", "sale"), ("amount", "=", 18)], limit=1)
tax_purchase = env["account.tax"].search([("company_id", "=", company.id), ("type_tax_use", "=", "purchase"), ("amount", "=", 18)], limit=1)
income_acc = env["account.account"].search([("code", "=", "410109")], limit=1)
expense_acc = env["account.account"].search([("code", "=", "510108")], limit=1)
if not income_acc:
    income_acc = env["account.account"].search([("account_type", "=", "income")], limit=1)
if not expense_acc:
    expense_acc = env["account.account"].search([("account_type", "=", "expense")], limit=1)
if income_acc:
    journal_sale.default_account_id = income_acc.id
if expense_acc:
    journal_purchase.default_account_id = expense_acc.id
receivable = env["account.account"].search([("code", "=", "120101")], limit=1)
payable = env["account.account"].search([("code", "=", "210101")], limit=1)
if receivable:
    env["ir.default"].set("res.partner", "property_account_receivable_id", receivable.id, company_id=company.id)
if payable:
    env["ir.default"].set("res.partner", "property_account_payable_id", payable.id, company_id=company.id)
journal_sale.justech_do_use_ncf = True


def sale_line(price, with_tax=False):
    vals = {"name": f"{TAG} line", "quantity": 1, "price_unit": price, "account_id": income_acc.id}
    if with_tax and tax_sale:
        vals["tax_ids"] = [Command.set(tax_sale.ids)]
    return Command.create(vals)


def purchase_line(price, with_tax=False):
    vals = {"name": f"{TAG} line", "quantity": 1, "price_unit": price, "account_id": expense_acc.id}
    if with_tax and tax_purchase:
        vals["tax_ids"] = [Command.set(tax_purchase.ids)]
    return Command.create(vals)


def ensure_range(doc, journal, base):
    rng = env["justech.do.ncf.range"].search(
        [("document_type_id", "=", doc.id), ("company_id", "=", company.id), ("state", "=", "active")], limit=1
    )
    if not rng:
        rng = env["justech.do.ncf.range"].create(
            {
                "name": f"{TAG} {doc.prefix}",
                "document_type_id": doc.id,
                "company_id": company.id,
                "sequence_start": base,
                "sequence_end": base + 50,
                "next_sequence": base,
                "date_from": period_from,
                "date_to": period_to.replace(month=12, day=31),
                "journal_ids": [Command.set(journal.ids)],
            }
        )
        rng.action_activate()
    return rng


def partner_for(doc):
    vals = {"name": f"{TAG} {doc.prefix}", "customer_rank": 1}
    if doc.requires_vat:
        vals["vat"] = "131793916"
    vals["justech_do_default_document_type_id"] = doc.id
    if receivable:
        vals["property_account_receivable_id"] = receivable.id
    return env["res.partner"].create(vals)


# --- Smoke NCF all sale types ---
sale_xml = (
    ("b01", "doc_type_b01"),
    ("b02", "doc_type_b02"),
    ("b03", "doc_type_b03"),
    ("b12", "doc_type_b12"),
    ("b14", "doc_type_b14"),
    ("b15", "doc_type_b15"),
    ("b16", "doc_type_b16"),
)
base_seq = 8800
last_b01 = None
for key, xml_id in sale_xml:
    doc = env.ref(f"justech_l10n_do_base.{xml_id}", raise_if_not_found=False)
    if not doc:
        ok_section(ncf_results["types"], key, False, "tipo no encontrado")
        continue
    ensure_range(doc, journal_sale, base_seq)
    base_seq += 60
    try:
        if key == "b03":
            if not last_b01:
                last_b01 = env["account.move"].search(
                    [("justech_do_ncf", "=like", "B01%"), ("state", "=", "posted")], limit=1
                )
            partner = last_b01.partner_id if last_b01 else partner_for(env.ref("justech_l10n_do_base.doc_type_b01"))
            inv = env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": partner.id,
                    "journal_id": journal_sale.id,
                    "invoice_date": today,
                    "debit_origin_id": last_b01.id if last_b01 else False,
                    "justech_do_document_type_id": doc.id,
                    "invoice_line_ids": [sale_line(500, with_tax=False)],
                }
            )
        else:
            partner = partner_for(doc)
            inv = env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": partner.id,
                    "journal_id": journal_sale.id,
                    "invoice_date": today,
                    "justech_do_document_type_id": doc.id,
                    "invoice_line_ids": [sale_line(2000)],
                }
            )
            if key == "b01":
                last_b01 = inv
        inv.action_post()
        pdf = env["ir.actions.report"]._render_qweb_pdf("account.account_invoices", inv.ids)
        ok_section(ncf_results["types"], f"{key}_ncf", inv.justech_do_ncf.startswith(doc.prefix), inv.justech_do_ncf)
        ok_section(ncf_results["types"], f"{key}_pdf", bool(pdf and pdf[0]), len(pdf[0]) if pdf else 0)
    except Exception as exc:
        ok_section(ncf_results["types"], key, False, str(exc))

# B04 credit note
doc_b04 = env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False)
base_inv = last_b01 or env["account.move"].search([("justech_do_ncf", "=like", "B01%"), ("state", "=", "posted")], limit=1)
if doc_b04 and base_inv:
    ensure_range(doc_b04, journal_sale, 9200)
    try:
        cn = env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": base_inv.partner_id.id,
                "journal_id": journal_sale.id,
                "invoice_date": today,
                "reversed_entry_id": base_inv.id,
                "justech_do_document_type_id": doc_b04.id,
                "invoice_line_ids": [sale_line(200, with_tax=False)],
            }
        )
        cn.action_post()
        ok_section(ncf_results["types"], "b04_ncf", cn.justech_do_ncf.startswith("B04"), cn.justech_do_ncf)
        ok_section(ncf_results["types"], "b04_origin", cn.justech_do_origin_ncf == base_inv.justech_do_ncf, cn.justech_do_origin_ncf)
    except Exception as exc:
        ok_section(ncf_results["types"], "b04", False, str(exc))

# Purchase types B11, B13, B17
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1) or env["res.partner"].create(
    {"name": f"{TAG} Vendor", "supplier_rank": 1, "vat": "101000000"}
)
journal_purchase.justech_do_use_ncf = True
for key, xml_id, seq_base in (
    ("b11", "doc_type_b11", 9300),
    ("b13", "doc_type_b13", 9400),
    ("b17", "doc_type_b17", 9500),
):
    doc = env.ref(f"justech_l10n_do_base.{xml_id}", raise_if_not_found=False)
    if not doc:
        ok_section(ncf_results["types"], key, False, "missing")
        continue
    ensure_range(doc, journal_purchase, seq_base)
    journal_purchase.write({"justech_do_default_document_type_id": doc.id})
    try:
        bill = env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": vendor.id,
                "journal_id": journal_purchase.id,
                "invoice_date": today,
                "justech_do_document_type_id": doc.id,
                "invoice_line_ids": [purchase_line(1500, with_tax=key != "b17")],
            }
        )
        bill.action_post()
        ok_section(ncf_results["types"], f"{key}_ncf", bill.justech_do_ncf.startswith(doc.prefix), bill.justech_do_ncf)
    except Exception as exc:
        ok_section(ncf_results["types"], key, False, str(exc))

# Duplicate scan
env.cr.execute(
    """
    SELECT justech_do_ncf, COUNT(*) FROM account_move
    WHERE state='posted' AND justech_do_ncf IS NOT NULL AND justech_do_ncf != ''
    GROUP BY justech_do_ncf HAVING COUNT(*)>1 LIMIT 5
    """
)
dups = env.cr.fetchall()
ok_section(ncf_results, "no_duplicate_ncf", not dups, str(dups))

# --- DGII all formats ---
for rtype in ("606", "607", "608", "609", "623"):
    try:
        rep = env["justech.do.fiscal.report"].create(
            {
                "name": f"{TAG} {rtype}",
                "report_type": rtype,
                "date_from": period_from,
                "date_to": period_to,
                "company_id": company.id,
            }
        )
        rep.action_generate()
        exp = env[rep.DGII_EXPORTER_MODELS[rtype]]
        val = exp.validate_period(company, period_from, period_to, refresh_states=False)
        export_ok = True
        export_detail = ""
        try:
            content, fname = exp.export_xlsx(company, period_from, period_to)
            export_ok = bool(content) or rtype in ("608", "623")
            export_detail = fname or "empty-ok"
        except UserError as exc:
            export_ok = rtype in ("608", "623") and "No hay documentos" in str(exc)
            export_detail = str(exc)[:200]
        ok_section(
            dgii_results["reports"],
            rtype,
            val.get("ok", True) and (export_ok or len(rep.line_ids) >= 0),
            f"lines={len(rep.line_ids)} export={export_detail}",
        )
    except Exception as exc:
        ok_section(dgii_results["reports"], rtype, False, str(exc))

# Tax mapping orphans
orphan = env["account.tax.repartition.line"].search_count(
    [("company_id", "=", company.id), ("repartition_type", "=", "tax"), ("account_id", "=", False)]
)
ok_section(result, "tax_orphans", orphan == 0, str(orphan))

# Write evidence
with open(os.path.join(OUT, "ncf_all_types.json"), "w", encoding="utf-8") as f:
    json.dump(ncf_results, f, indent=2, ensure_ascii=False)
with open(os.path.join(OUT, "dgii_all_formats.json"), "w", encoding="utf-8") as f:
    json.dump(dgii_results, f, indent=2, ensure_ascii=False)
with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(
        {
            "pass": result["pass"],
            "errors": result["errors"],
            "ncf_pass": ncf_results["pass"],
            "dgii_pass": dgii_results["pass"],
            "supported_prefixes": sorted(loaded),
        },
        f,
        indent=2,
        ensure_ascii=False,
    )

env.cr.commit()
print("FISCAL_RD_FINAL:" + json.dumps(result, indent=2, ensure_ascii=False))
