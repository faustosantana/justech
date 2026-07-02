# -*- coding: utf-8 -*-
"""Diagnóstico campos account.payment — Fase 18.7."""
Payment = env["account.payment"]
wanted = [
    "hellenia_invoice_display",
    "hellenia_applied_amount",
    "hellenia_withholding_total",
    "hellenia_net_transfer",
    "hellenia_withholding_line_ids",
    "reconciled_invoice_ids",
    "reconciled_bill_ids",
]
missing = [f for f in wanted if f not in Payment._fields]
present = [f for f in wanted if f in Payment._fields]
print("PRESENT:", ",".join(present))
print("MISSING:", ",".join(missing) or "none")
mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
print(f"MODULE: {mod.state} {mod.latest_version}")
# test get_views form
try:
    env["account.payment"].get_views([(False, "form")])
    print("GET_VIEWS: OK")
except Exception as exc:
    print(f"GET_VIEWS: FAIL {exc}")
pay = env["account.payment"].search([], limit=1)
if pay:
    print(f"SAMPLE: id={pay.id} display={pay.hellenia_invoice_display!r}")
