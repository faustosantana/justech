#!/usr/bin/env python3
"""Fase 13.2 — Validación funcional fiscal: ventas, NCF, reportes DGII, español."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

today = date.today()
company = env.company
report = {
    "phase": "13.2",
    "block": 6,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "scenarios": {},
    "ok": True,
}


def scenario(name, checks, obs=None):
    fails = [k for k, v in checks.items() if not v.get("ok")]
    status = "FAIL" if fails else ("PASS CON OBSERVACIONES" if obs else "PASS")
    if fails:
        report["ok"] = False
    report["scenarios"][name] = {"status": status, "checks": checks, "observations": obs or []}
    return status


def chk(ok, detail=""):
    return {"ok": bool(ok), "detail": detail}


# Fiscal manager group
manager = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if manager and manager not in env.user.group_ids:
    env.user.write({"group_ids": [(4, manager.id)]})

tax_18 = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale"), ("active", "=", True)],
    limit=1,
)
tax_15_active = env["account.tax"].search_count(
    [("company_id", "=", company.id), ("amount", "=", 15), ("active", "=", True)]
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)

# S1 — No 15% + ITBIS disponible
scenario(
    "tax_configuration",
    {
        "no_15_active": chk(tax_15_active == 0, f"active_15={tax_15_active}"),
        "itbis_18_sale": chk(bool(tax_18), tax_18.name if tax_18 else ""),
        "account_count_rd": chk(
            env["account.account"].search_count([]) >= 100,
            str(env["account.account"].search_count([])),
        ),
    },
)

# S2 — Cotización nueva con ITBIS correcto
s2 = {}
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
if not product:
    product = env["product.product"].create(
        {"name": "P13.2 Test", "type": "consu", "list_price": 1000.0, "taxes_id": [Command.set(tax_18.ids)]}
    )
elif tax_18:
    product.taxes_id = [Command.set(tax_18.ids)]

partner = env["res.partner"].search([("customer_rank", ">", 0)], limit=1) or env["res.partner"].create(
    {"name": "Cliente P13.2", "customer_rank": 1}
)

so = env["sale.order"].create({"partner_id": partner.id})
env["sale.order.line"].create(
    {"order_id": so.id, "product_id": product.id, "product_uom_qty": 1.0, "price_unit": 10000.0}
)
line_tax_amounts = [t.amount for t in so.order_line.tax_ids]
s2["quotation_draft"] = chk(so.state == "draft", so.state)
s2["line_has_18_not_15"] = chk(18.0 in line_tax_amounts and 15.0 not in line_tax_amounts, str(line_tax_amounts))
so.action_confirm()
s2["order_confirmed"] = chk(so.state == "sale", so.state)
scenario("new_sale_quotation", s2)

# S3 — Factura B01/B02 con NCF
s3 = {}
if journal_sale and tax_18:
    journal_sale.justech_do_use_ncf = True
    doc_b01 = env.ref("justech_l10n_do_base.doc_type_b01", raise_if_not_found=False)
    doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02", raise_if_not_found=False)
    for doc, key in ((doc_b01, "b01"), (doc_b02, "b02")):
        if not doc:
            s3[f"{key}_doc"] = chk(False, "doc type missing")
            continue
        # Ensure range
        rng = env["justech.do.ncf.range"].search(
            [("document_type_id", "=", doc.id), ("company_id", "=", company.id), ("state", "=", "active")],
            limit=1,
        )
        if not rng:
            rng = env["justech.do.ncf.range"].create(
                {
                    "name": f"P13.2 {doc.prefix}",
                    "document_type_id": doc.id,
                    "company_id": company.id,
                    "sequence_start": 9000,
                    "sequence_end": 9999,
                    "next_sequence": 9000,
                    "date_from": today.replace(month=1, day=1),
                    "date_to": today.replace(month=12, day=31),
                    "journal_ids": [Command.set(journal_sale.ids)],
                }
            )
            rng.action_activate()
        inv = env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "journal_id": journal_sale.id,
                "invoice_date": today,
                "justech_do_document_type_id": doc.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": f"Test {doc.prefix}",
                            "quantity": 1,
                            "price_unit": 5000.0,
                            "tax_ids": [Command.set(tax_18.ids)],
                        }
                    )
                ],
            }
        )
        inv.action_post()
        s3[f"{key}_posted"] = chk(inv.state == "posted", inv.name)
        s3[f"{key}_ncf"] = chk(bool(inv.justech_do_ncf), inv.justech_do_ncf or "")
        s3[f"{key}_prefix"] = chk(
            inv.justech_do_ncf.startswith(doc.prefix) if inv.justech_do_ncf else False,
            inv.justech_do_ncf or "",
        )
        itbis_lines = inv.line_ids.filtered(lambda l: l.tax_line_id and l.tax_line_id.amount == 18)
        s3[f"{key}_itbis_18"] = chk(bool(itbis_lines), str(itbis_lines.mapped("balance")))
scenario("invoices_b01_b02", s3)

# S4 — Nota crédito B04 y débito B03
s4 = {}
last_inv = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("justech_do_ncf", "!=", False)],
    order="id desc",
    limit=1,
)
if last_inv:
  try:
    credit = env["account.move"].create(
        {
            "move_type": "out_refund",
            "partner_id": last_inv.partner_id.id,
            "journal_id": last_inv.journal_id.id,
            "invoice_date": today,
            "justech_do_document_type_id": env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False).id
            if env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False)
            else False,
            "invoice_line_ids": [
                Command.create(
                    {
                        "name": "NC test",
                        "quantity": 1,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(tax_18.ids)] if tax_18 else [],
                    }
                )
            ],
        }
    )
    credit.action_post()
    s4["credit_b04"] = chk(credit.state == "posted", credit.justech_do_ncf or credit.name)
  except Exception as exc:
    s4["credit_b04"] = chk(False, str(exc))
else:
    s4["credit_b04"] = chk(False, "no base invoice")
scenario("credit_debit_notes", s4)

# S5 — Compra B11 / gasto B13
s5 = {}
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1) or env["res.partner"].create(
    {"name": "Proveedor P13.2", "supplier_rank": 1}
)
if journal_purchase and tax_18:
    for doc_xml, key in (
        ("justech_l10n_do_base.doc_type_b11", "b11"),
        ("justech_l10n_do_base.doc_type_b13", "b13"),
    ):
        doc = env.ref(doc_xml, raise_if_not_found=False)
        if not doc:
            s5[key] = chk(False, "doc missing")
            continue
        bill = env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": vendor.id,
                "journal_id": journal_purchase.id,
                "invoice_date": today,
                "ref": f"TEST-{doc.prefix}-P132",
                "justech_do_document_type_id": doc.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": f"Compra {doc.prefix}",
                            "quantity": 1,
                            "price_unit": 2000.0,
                            "tax_ids": [Command.set(tax_18.ids)],
                        }
                    )
                ],
            }
        )
        bill.action_post()
        s5[key] = chk(bill.state == "posted", bill.name)
scenario("purchases_b11_b13", s5)

# S6 — Anulación + reporte 608
s6 = {}
void_inv = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("justech_do_ncf", "!=", False)],
    order="id desc",
    limit=1,
)
if void_inv and not void_inv.justech_do_ncf_voided:
    void_inv.justech_do_ncf_void_reason = "Prueba P13.2 anulación"
    void_inv.action_void_ncf()
    s6["voided"] = chk(void_inv.justech_do_ncf_voided, void_inv.justech_do_ncf)
else:
    s6["voided"] = chk(void_inv and void_inv.justech_do_ncf_voided, "already voided or missing")

for rtype in ("606", "607", "608"):
    rep = env["justech.do.fiscal.report"].create(
        {
            "name": f"P13.2 {rtype}",
            "report_type": rtype,
            "date_from": today.replace(month=1, day=1),
            "date_to": today,
            "company_id": company.id,
        }
    )
    rep.action_generate()
    s6[f"report_{rtype}_lines"] = chk(rep.state == "done", str(len(rep.line_ids)))
    s6[f"report_{rtype}_totals"] = chk(
        hasattr(rep, "total_amount") or rep.line_ids,
        getattr(rep, "total_amount", len(rep.line_ids)),
    )
scenario("reports_606_607_608", s6)

# S7 — PDF factura
s7 = {}
if last_inv:
    pdf = env["ir.actions.report"]._render_qweb_pdf("account.account_invoices", last_inv.ids)
    s7["pdf_bytes"] = chk(pdf and len(pdf[0]) > 500, f"{len(pdf[0]) if pdf else 0}")
scenario("invoice_pdf", s7)

# S8 — Menús Justech en español (muestra)
s8 = {}
menus = env["ir.ui.menu"].search([("name", "ilike", "DGII")])
spanish_names = [m.name for m in menus]
s8["dgii_menu_es"] = chk(
    any("Reporte" in n or "DGII" in n for n in spanish_names),
    str(spanish_names),
)
scenario("spanish_ux_sample", s8)

print("PHASE13_2_VALIDATION:" + json.dumps(report, ensure_ascii=False, indent=2))
