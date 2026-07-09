#!/usr/bin/env python3
"""HELLENIA-MENU-UAT-2 — Data UAT temporal visible (prefijo UAT-MENU-)."""
from __future__ import annotations

import json
from datetime import date

from odoo import Command, SUPERUSER_ID
from odoo.exceptions import UserError

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

env = env(user=SUPERUSER_ID)
TAG = "UAT-MENU-"
today = date.today()
R = {"tag": TAG, "database": DB, "created": [], "scenarios": {}, "errors": []}


def track(model, rec, scenario):
    R["created"].append(
        {"scenario": scenario, "model": model, "id": rec.id, "name": getattr(rec, "display_name", str(rec.id))}
    )


def master():
    company = env.company
    bank = env["account.journal"].search([("type", "=", "bank"), ("company_id", "=", company.id)], limit=1)
    return {
        "bank": bank,
        "sale": env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1),
        "purchase": env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1),
        "tax_sale": env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)], limit=1),
        "tax_purchase": env["account.tax"].search([("amount", "=", 18), ("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)], limit=1),
        "pml_in": bank._get_available_payment_method_lines("inbound")[:1],
        "pml_out": bank._get_available_payment_method_lines("outbound")[:1],
    }


def partner(name, customer=False, supplier=False):
    p = env["res.partner"].create({"name": name, "customer_rank": 1 if customer else 0, "supplier_rank": 1 if supplier else 0})
    track("res.partner", p, "partner")
    return p


def product(ref):
    p = env["product.product"].create({"name": f"{TAG}{ref}", "type": "service", "sale_ok": True, "purchase_ok": True})
    track("product.product", p, ref)
    return p


def invoice(partner, base, m, move_type="out_invoice", ref="INV"):
    journal = m["sale"] if move_type == "out_invoice" else m["purchase"]
    tax = m["tax_sale"] if move_type == "out_invoice" else m["tax_purchase"]
    inv = env["account.move"].create(
        {
            "move_type": move_type,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "invoice_date": today,
            "ref": f"{TAG}{ref}",
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product(ref).id,
                        "name": f"{TAG}{ref}",
                        "quantity": 1,
                        "price_unit": base,
                        "tax_ids": [Command.set(tax.ids)] if tax else [],
                    }
                )
            ],
        }
    )
    inv.action_post()
    track("account.move", inv, ref)
    return inv


def open_payment(partner, amount, m, partner_type="customer", ref="OPEN"):
    w = env["hellenia.payment.partner.wizard"].create(
        {
            "partner_id": partner.id,
            "partner_type": partner_type,
            "currency_id": env.company.currency_id.id,
            "journal_id": m["bank"].id,
            "payment_method_line_id": (m["pml_in"] if partner_type == "customer" else m["pml_out"]).id,
            "payment_date": today,
            "communication": f"{TAG}{ref}",
            "treasury_operation_type": "open",
            "treasury_amount_received": amount,
        }
    )
    pay = env["account.payment"].browse(w.action_register_payments()["res_id"])
    track("account.payment", pay, ref)
    return pay


def pay_invoice(partner, inv, m, partner_type, ref, amount=None, withholding=None):
    w = env["hellenia.payment.partner.wizard"].create(
        {
            "partner_id": partner.id,
            "partner_type": partner_type,
            "journal_id": m["bank"].id,
            "payment_method_line_id": (m["pml_in"] if partner_type == "customer" else m["pml_out"]).id,
            "payment_date": today,
            "communication": f"{TAG}{ref}",
            "treasury_operation_type": "apply",
        }
    )
    w._load_pending_invoices()
    line = w.line_ids.filtered(lambda l: l.move_id == inv)[:1]
    if not line:
        raise UserError(f"Factura no encontrada en wizard: {inv.ref}")
    line.apply = True
    line.amount_to_pay = amount if amount is not None else abs(inv.amount_residual)
    if withholding:
        line.withholding_catalog_ids = [Command.set(withholding.ids)]
        line._recompute_line_withholdings()
    w.action_register_payments()
    pay = env["account.payment"].search([("partner_id", "=", partner.id)], order="id desc", limit=1)
    track("account.payment", pay, ref)
    return pay


def apply_open(partner, partner_type, payment=None, move=None):
    wiz = env["treasury.open.payment.apply.wizard"].create(
        {
            "partner_id": partner.id,
            "partner_type": partner_type,
            "payment_id": payment.id if payment else False,
            "move_id": move.id if move else False,
        }
    )
    wiz.action_apply()


m = master()
cust = partner(f"{TAG}Cliente Demo", customer=True)
vend = partner(f"{TAG}Proveedor Demo", supplier=True)

try:
    inv_paid = invoice(cust, 1000, m, ref="01-FACT-PAGADA")
    pay1 = pay_invoice(cust, inv_paid, m, "customer", "01-PAGO-NORMAL")
    R["scenarios"]["01_pago_normal_aplicado"] = {"payment_id": pay1.id, "invoice_id": inv_paid.id}

    open_c = open_payment(cust, 500, m, ref="02-PAGO-ABIERTO-CLI")
    R["scenarios"]["02_pago_abierto_cliente"] = {"payment_id": open_c.id}

    open_v = open_payment(vend, 800, m, partner_type="supplier", ref="03-PAGO-ABIERTO-PROV")
    R["scenarios"]["03_pago_abierto_proveedor"] = {"payment_id": open_v.id}

    inv_partial = invoice(cust, 2000, m, ref="04-FACT-PARCIAL")
    pay_partial = pay_invoice(cust, inv_partial, m, "customer", "04-PAGO-PARCIAL", amount=inv_partial.amount_total / 2)
    R["scenarios"]["04_pago_parcial"] = {"payment_id": pay_partial.id, "residual": inv_partial.amount_residual}

    inv_total = invoice(cust, 1500, m, ref="05-FACT-TOTAL")
    pay_total = pay_invoice(cust, inv_total, m, "customer", "05-PAGO-TOTAL")
    R["scenarios"]["05_pago_total"] = {"payment_id": pay_total.id}

    cat = env["hellenia.withholding.catalog"].search([("company_id", "=", env.company.id)], limit=1)
    inv_ret = invoice(cust, 3000, m, ref="06-FACT-RET")
    if cat:
        pay_ret = pay_invoice(cust, inv_ret, m, "customer", "06-PAGO-RET", withholding=cat)
        R["scenarios"]["06_pago_con_retencion"] = {"payment_id": pay_ret.id}
    else:
        R["scenarios"]["06_pago_con_retencion"] = "skip_no_catalog"

    inv_small = invoice(cust, 1000, m, ref="07-FACT-MENOR")
    open_big = open_payment(cust, 1500, m, ref="07-PAGO-MAYOR-ABIERTO")
    R["scenarios"]["07_pago_mayor_abierto"] = {"payment_id": open_big.id, "invoice_id": inv_small.id}

    inv_ret_only = invoice(cust, 2500, m, ref="08-FACT-RET-SOLO")
    R["scenarios"]["08_factura_con_retencion"] = {"invoice_id": inv_ret_only.id}

    inv_open_apply = invoice(cust, 900, m, ref="09-FACT-APLICAR-ABIERTO")
    apply_open(cust, "customer", payment=open_c, move=inv_open_apply)
    R["scenarios"]["09_aplicar_pago_abierto"] = {"invoice_id": inv_open_apply.id}

    inv_vendor = invoice(vend, 1200, m, move_type="in_invoice", ref="10-FACT-PROV")
    pay_vendor = pay_invoice(vend, inv_vendor, m, "supplier", "10-PAGO-PROV")
    R["scenarios"]["10_factura_proveedor_pagada"] = {"payment_id": pay_vendor.id}

    if m["bank"]:
        stmt = env["account.bank.statement"].create({"name": f"{TAG}Extracto", "journal_id": m["bank"].id, "date": today})
        track("account.bank.statement", stmt, "13-bank-stmt")
        stline = env["account.bank.statement.line"].create(
            {
                "statement_id": stmt.id,
                "date": today,
                "payment_ref": f"{TAG}13-LINEA-BANCO",
                "amount": 500.0,
                "partner_id": cust.id,
            }
        )
        track("account.bank.statement.line", stline, "13-bank-line")
        R["scenarios"]["13_conciliacion_bancaria"] = {"statement_id": stmt.id, "line_id": stline.id, "note": "extracto demo; match UI en Tablero"}
    else:
        R["scenarios"]["13_conciliacion_bancaria"] = "skip_no_bank"

    env.cr.commit()
except Exception as exc:
    R["errors"].append(str(exc))
    env.cr.rollback()
    raise

print("UAT_MENU_CREATED:" + json.dumps(R, ensure_ascii=False, indent=2))
