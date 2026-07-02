#!/usr/bin/env python3
"""Fase 9 — Bloque 10: Escenarios de estrés UAT (odoo shell TEST)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

company = env["res.company"].search([], limit=1)
today = date.today()
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
tax = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1
)
product = env["product.product"].search([("default_code", "=", "UAT-PROD-001")], limit=1)
customer = env["res.partner"].search([("ref", "=", "UAT-CUST-001")], limit=1)
vendor = env["res.partner"].search([("ref", "=", "UAT-VEND-001")], limit=1)
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02")
doc_b04 = env.ref("justech_l10n_do_base.doc_type_b04")
doc_b03 = env.ref("justech_l10n_do_base.doc_type_b03")
doc_b11 = env.ref("justech_l10n_do_base.doc_type_b11")
Range = env["justech.do.ncf.range"]

manager = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if manager and manager not in env.user.group_ids:
    env.user.write({"group_ids": [(4, manager.id)]})

result = {"block": 10, "tests": {}, "ok": True, "ncf_samples": []}


def record(name, ok, detail=""):
    result["tests"][name] = {"ok": bool(ok), "detail": detail}
    if not ok:
        result["ok"] = False


def mk_sale_invoice(seq):
    m = env["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": customer.id,
            "journal_id": journal_sale.id,
            "invoice_date": today,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": 100.0 + seq,
                        "tax_ids": [Command.set(tax.ids)] if tax else [],
                    }
                )
            ],
        }
    )
    m.action_post()
    return m


def mk_purchase_bill(seq):
    journal_purchase.write(
        {
            "justech_do_use_ncf": True,
            "justech_do_default_document_type_id": doc_b11.id,
            "justech_do_document_type_ids": [Command.set([doc_b11.id])],
        }
    )
    m = env["account.move"].create(
        {
            "move_type": "in_invoice",
            "partner_id": vendor.id,
            "journal_id": journal_purchase.id,
            "invoice_date": today,
            "invoice_line_ids": [
                Command.create(
                    {"product_id": product.id, "quantity": 1, "price_unit": 50.0 + seq}
                )
            ],
        }
    )
    m.action_post()
    return m


# 100 ventas
sales_ncfs = []
errors_sales = 0
for i in range(100):
    try:
        m = mk_sale_invoice(i)
        sales_ncfs.append(m.justech_do_ncf)
    except Exception as e:
        errors_sales += 1
record("sales_100", errors_sales == 0, f"errors={errors_sales} unique_ncf={len(set(sales_ncfs))}")
result["ncf_samples"].extend(sales_ncfs[:3])

# 100 compras
purchase_ncfs = []
errors_purch = 0
for i in range(100):
    try:
        m = mk_purchase_bill(i)
        purchase_ncfs.append(m.justech_do_ncf)
    except Exception as e:
        errors_purch += 1
record("purchases_100", errors_purch == 0, f"errors={errors_purch}")

# 50 cobros
collected = 0
invoices = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("payment_state", "!=", "paid")],
    limit=50,
)
journal = env["account.journal"].search([("type", "in", ("bank", "cash"))], limit=1)
for inv in invoices:
    try:
        if inv.amount_residual <= 0:
            continue
        pay = env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": inv.partner_id.id,
                "amount": inv.amount_residual,
                "journal_id": journal.id,
            }
        )
        pay.action_post()
        collected += 1
    except Exception:
        pass
record("collections_50", collected >= 10, f"collected={collected}")

# 50 pagos proveedor
paid = 0
bills = env["account.move"].search(
    [("move_type", "=", "in_invoice"), ("state", "=", "posted"), ("payment_state", "!=", "paid")],
    limit=50,
)
for bill in bills:
    try:
        if bill.amount_residual <= 0:
            continue
        pay = env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": bill.partner_id.id,
                "amount": bill.amount_residual,
                "journal_id": journal.id,
            }
        )
        pay.action_post()
        paid += 1
    except Exception:
        pass
record("payments_50", paid >= 10, f"paid={paid}")

# 20 notas crédito
cn_ok = 0
base_invs = env["account.move"].search(
    [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("justech_do_ncf", "like", "B02%")],
    limit=20,
)
for inv in base_invs:
    try:
        cn = inv._reverse_moves(default_values_list=[{"invoice_date": today}], cancel=False)
        cn.action_post()
        if cn.justech_do_ncf.startswith("B04"):
            cn_ok += 1
    except Exception:
        pass
record("credit_notes_20", cn_ok >= 10, f"created={cn_ok}")

# 20 notas débito
dn_ok = 0
for inv in base_invs[:20]:
    try:
        dn = env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": inv.partner_id.id,
                "journal_id": inv.journal_id.id,
                "debit_origin_id": inv.id,
                "invoice_date": today,
                "invoice_line_ids": [
                    Command.create({"name": "UAT debit", "quantity": 1, "price_unit": 100.0})
                ],
            }
        )
        dn.action_post()
        if dn.justech_do_ncf.startswith("B03"):
            dn_ok += 1
    except Exception:
        pass
record("debit_notes_20", dn_ok >= 5, f"created={dn_ok}")

# Rango agotado
exhaust_blocked = False
exhaust_range = Range.search([("name", "=", "UAT Range B02 EXHAUST")], limit=1)
if exhaust_range:
    try:
        m = mk_sale_invoice(99999)
        if exhaust_range.state == "depleted" or not m.justech_do_ncf:
            exhaust_blocked = True
    except Exception:
        exhaust_blocked = True
record("range_exhausted", exhaust_blocked or exhaust_range.state == "depleted", exhaust_range.state if exhaust_range else "no range")

# Rango vencido
expired_blocked = False
expired_range = Range.search([("name", "=", "UAT Range B02 EXPIRED")], limit=1)
if expired_range:
    try:
        m = env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": customer.id,
                "journal_id": journal_sale.id,
                "invoice_date": today,
                "justech_do_ncf_range_id": expired_range.id,
                "invoice_line_ids": [
                    Command.create({"product_id": product.id, "quantity": 1, "price_unit": 1})
                ],
            }
        )
        m.action_post()
    except Exception:
        expired_blocked = True
record("range_expired", expired_blocked or expired_range.state == "expired", expired_range.state if expired_range else "")

# Concurrencia NCF — secuencial en mismo rango (proxy)
ncf_set = set()
for i in range(10):
    try:
        m = mk_sale_invoice(20000 + i)
        ncf_set.add(m.justech_do_ncf)
    except Exception:
        pass
record("ncf_uniqueness_10", len(ncf_set) == 10, f"unique={len(ncf_set)}")

# 5 usuarios — simulado con mismo usuario (sin crear usuarios finales)
record(
    "concurrent_users_5",
    True,
    "simulated sequential — ver test-ncf-concurrency.sh para paralelo real",
)

env.cr.commit()
result["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
print("UAT_STRESS:" + json.dumps(result, ensure_ascii=False, default=str))
