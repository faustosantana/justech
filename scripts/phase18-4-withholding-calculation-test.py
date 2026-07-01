# -*- coding: utf-8 -*-
"""Fase 18.4 — Validación cálculo retenciones ITBIS/ISR en TEST."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

BASE = 10000.0
ITBIS = 1800.0
TOTAL = 11800.0
TOL = 0.02

report = {
    "phase": "18.4-withholding-calculation",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "invoice": {"base": BASE, "itbis": ITBIS, "total": TOTAL},
    "checks": {},
    "results": {},
    "ok": True,
    "pass": False,
}

EXPECTED = {
    "RET-ITBIS-30": 540.0,
    "RET-ITBIS-100": 1800.0,
    "RET-INF-ITBIS-75": 1350.0,
    "RET-GOB-5": 500.0,
    "RET-ISR-2": 200.0,
    "RET-HON-10": 1000.0,
    "RET-INF-ISR-10": 1000.0,
}


def check(key, ok, detail=""):
    report["checks"][key] = {"ok": bool(ok), "detail": detail}
    if not ok:
        report["ok"] = False


def near(a, b):
    return abs(a - b) <= TOL


company = env.company
Catalog = env["hellenia.withholding.catalog"]
setup = env["hellenia.account.payment.setup"]
setup.configure_withholding_reference()
Catalog.sync_catalog_from_taxes(company)
env.cr.commit()

tax_purchase = env["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)],
    limit=1,
)
tax_sale = env["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)],
    limit=1,
)
product = env["product.product"].search([("purchase_ok", "=", True)], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
customer = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
journal_purchase = env["account.journal"].search(
    [("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1
)
journal_sale = env["account.journal"].search(
    [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
)
bnkd = env["account.journal"].search([("code", "=", "BNKD"), ("company_id", "=", company.id)], limit=1)


def _cat(code):
    return Catalog.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)


def _invoice(partner, journal, tax, move_type="in_invoice"):
    move = env["account.move"].create(
        {
            "move_type": move_type,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "invoice_date": date.today(),
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": BASE,
                        "tax_ids": [Command.set(tax.ids)] if tax else [],
                    }
                )
            ],
        }
    )
    move.action_post()
    return move


def _calc(move, code):
    cat = _cat(code)
    if not cat:
        return None, f"catálogo {code} no encontrado"
    amount = cat.compute_withholding_amount(move)
    return amount, cat.rate


# --- Factura compra RD$10,000 + ITBIS ---
bill = env["account.move"].search([("ref", "=", "PHASE184-WH-CALC")], limit=1)
if not bill:
    bill = _invoice(vendor, journal_purchase, tax_purchase)
    bill.ref = "PHASE184-WH-CALC"
else:
    bill.write({"invoice_date": date.today()})

check("invoice_base", near(bill.amount_untaxed, BASE), bill.amount_untaxed)
check("invoice_itbis", near(bill.amount_tax, ITBIS), bill.amount_tax)
check("invoice_total", near(bill.amount_total, TOTAL), bill.amount_total)

for code, expected in EXPECTED.items():
    amount, rate = _calc(bill, code)
    report["results"][code] = {"expected": expected, "actual": amount, "rate": rate}
    check(f"calc_{code}", amount is not None and near(amount, expected), f"got {amount} rate {rate}")

# --- Combinaciones ---
cat30 = _cat("RET-ITBIS-30")
cat2 = _cat("RET-ISR-2")
combo1 = (cat30.compute_withholding_amount(bill) if cat30 else 0) + (
    cat2.compute_withholding_amount(bill) if cat2 else 0
)
report["results"]["combo_itbis30_isr2"] = {
    "expected_wh": 740.0,
    "expected_net": 11060.0,
    "actual_wh": combo1,
    "actual_net": TOTAL - combo1,
}
check("combo_itbis30_isr2_wh", near(combo1, 740.0), combo1)
check("combo_itbis30_isr2_net", near(TOTAL - combo1, 11060.0), TOTAL - combo1)

cat100 = _cat("RET-ITBIS-100")
cat10 = _cat("RET-HON-10")
combo2 = (cat100.compute_withholding_amount(bill) if cat100 else 0) + (
    cat10.compute_withholding_amount(bill) if cat10 else 0
)
report["results"]["combo_itbis100_isr10"] = {
    "expected_wh": 2800.0,
    "expected_net": 9000.0,
    "actual_wh": combo2,
    "actual_net": TOTAL - combo2,
}
check("combo_itbis100_isr10_wh", near(combo2, 2800.0), combo2)
check("combo_itbis100_isr10_net", near(TOTAL - combo2, 9000.0), TOTAL - combo2)

# --- Wizard + contabilidad pago proveedor ---
if bnkd and cat30 and cat2:
    wh_commands = []
    for cat in (cat30, cat2):
        amt = cat.compute_withholding_amount(bill)
        wh_commands.append(
            Command.create(
                {
                    "catalog_id": cat.id,
                    "tax_id": cat.tax_id.id,
                    "label": cat.name,
                    "base_label": cat._base_label(),
                    "base_amount": cat._base_amount(bill),
                    "rate": cat.rate,
                    "amount": amt,
                    "account_id": cat.account_id.id,
                    "currency_id": bill.currency_id.id,
                }
            )
        )
    wh_total = sum(_calc(bill, c)[0] or 0 for c in ("RET-ITBIS-30", "RET-ISR-2"))
    register = (
        env["account.payment.register"]
        .with_context(active_model="account.move", active_ids=bill.ids, dont_redirect_to_payments=True)
        .create(
            {
                "journal_id": bnkd.id,
                "payment_method_line_id": (
                    bnkd.outbound_payment_method_line_ids[:1].id
                    if bnkd.outbound_payment_method_line_ids
                    else False
                ),
                "payment_date": date.today(),
                "amount": bill.amount_residual,
                "hellenia_withholding_line_ids": wh_commands,
            }
        )
    )
    pay_vals = register._create_payment_vals_from_wizard(
        register._get_batches()[0] if hasattr(register, "_get_batches") else {}
    )
    net = pay_vals.get("amount", 0)
    writeoffs = pay_vals.get("write_off_line_vals", [])
    check("payment_net", near(net, 11060.0), net)
    check("payment_wh_lines", len(writeoffs) == 2, len(writeoffs))
    wh_sum = sum(abs(w.get("amount_currency", 0)) for w in writeoffs)
    check("payment_wh_sum", near(wh_sum, 740.0), wh_sum)
    payments = register._create_payments()
    if payments:
        move = payments.move_id
        deb = sum(move.line_ids.filtered(lambda l: l.debit > 0).mapped("debit"))
        cred = sum(move.line_ids.filtered(lambda l: l.credit > 0).mapped("credit"))
        check("entry_balanced", near(deb, cred), f"deb={deb} cred={cred}")
        report["accounting"] = {
            "payment_amount": net,
            "withholding_sum": wh_sum,
            "balanced": near(deb, cred),
        }

# --- Gobierno 5% venta ---
if customer and tax_sale and journal_sale:
    sale = _invoice(customer, journal_sale, tax_sale, "out_invoice")
    gov = _cat("RET-GOB-5")
    if gov:
        gamt = gov.compute_withholding_amount(sale)
        check("calc_RET-GOB-5_sale", near(gamt, 500.0), gamt)

report["pass"] = report["ok"]
report["cause"] = (
    "compute_withholding_amount usaba tax_id.amount (tasa efectiva l10n_do sobre base imponible) "
    "multiplicada por ITBIS facturado, en lugar de la tasa nominal del catálogo × base correcta."
)
report["formula"] = (
    "ITBIS: monto_retenido = ITBIS_facturado × (tasa_nominal / 100). "
    "ISR: monto_retenido = base_imponible × (tasa_nominal / 100)."
)

print(f"PHASE184:{json.dumps(report, ensure_ascii=False)}")
