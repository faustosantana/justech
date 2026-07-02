#!/usr/bin/env python3
"""Fase 21 — Verificación read-only post-UI de cadena 623 (sin modificar datos)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

PARTNER_REF = "P21-GOV-623-PROOF"
INVOICE_REF = "P21-GOV-INV-PROOF"
PAYMENT_REF = "P21-GOV-PAY-PROOF"
EXPECTED_GOV = 500.0

partner = env["res.partner"].search([("ref", "=", PARTNER_REF)], limit=1)
inv = env["account.move"].search(
    [("partner_id", "=", partner.id), ("ref", "=", INVOICE_REF)], limit=1
)
pay = env["account.payment"].search([("hellenia_payment_reference", "=", PAYMENT_REF)], limit=1)
if not pay and inv:
    pay = inv._get_reconciled_payments()[:1]

wh_lines = env["hellenia.payment.withholding.line"].search([("move_id", "=", inv.id)]) if inv else env["hellenia.payment.withholding.line"]

company = env.company
exporter = env["justech.do.dgii.623.exporter"]
df = date(2026, 7, 1)
dt = date(2026, 7, 31)
val = exporter.validate_period_623(company, df, dt, refresh_states=True) if inv else {}

report = {
    "phase": "21-gov-623-readonly-verify",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "partner": {"id": partner.id, "vat": partner.vat, "ref": partner.ref} if partner else None,
    "invoice": None,
    "payment": None,
    "withholding_lines": [],
    "validation_623": {
        "valid": val.get("counts", {}).get("valid", 0) if val else 0,
        "incomplete": val.get("counts", {}).get("incomplete", 0) if val else 0,
        "errors": exporter._dgii_validate_single_move(inv, df, dt) if inv else [],
    },
    "chain_ok": False,
    "conclusion": None,
}

if inv:
    report["invoice"] = {
        "name": inv.name,
        "gov_withholding": inv.justech_do_gov_withholding_amount,
        "fiscal_state": inv.justech_do_dgii_fiscal_state,
        "payment_state": inv.payment_state,
    }
if pay:
    report["payment"] = {
        "name": pay.name,
        "gov_withholding": pay.justech_do_gov_withholding_amount,
        "wh_total": pay.hellenia_withholding_total,
        "reference": pay.hellenia_payment_reference or "",
    }
for wl in wh_lines:
    report["withholding_lines"].append(
        {
            "id": wl.id,
            "code": wl.catalog_id.code,
            "amount": wl.amount,
            "move_line_id": wl.move_line_id.id,
            "gl_balance": wl.move_line_id.balance if wl.move_line_id else None,
        }
    )

gov_inv = (inv.justech_do_gov_withholding_amount or 0) if inv else 0
gov_pay = (pay.justech_do_gov_withholding_amount or 0) if pay else 0
wh_amt = sum(wh_lines.mapped("amount")) if wh_lines else 0
valid_count = report["validation_623"]["valid"]

chain = (
    partner
    and partner.vat
    and inv
    and pay
    and abs(gov_inv - EXPECTED_GOV) < 1
    and abs(gov_pay - EXPECTED_GOV) < 1
    and abs(wh_amt - EXPECTED_GOV) < 1
    and wh_lines.filtered(lambda w: w.catalog_id.code == "RET-GOB-5")
)

report["chain_ok"] = bool(chain)
if chain and valid_count > 0:
    report["conclusion"] = "CODE_CERTIFIED_MASTER_DATA_WAS_ROOT_CAUSE"
elif chain and valid_count == 0:
    report["conclusion"] = "FUNCTIONAL_BUG_623_VALIDATION_OR_EXPORT"
else:
    report["conclusion"] = "CHAIN_INCOMPLETE_CHECK_STEPS"

print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
