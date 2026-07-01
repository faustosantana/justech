#!/usr/bin/env python3
"""Fase 20.1 — Preparar escenario SMOKE P13.4 CF en hellenia_test (3 facturas pendientes)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

PARTNER_ID = 2361
PARTNER_REF = "SMOKE-P134-CF-2361"
BASE, TOTAL = 10000.0, 11800.0
EVIDENCE = Path("/workspace/evidence/phase20-1")
if not EVIDENCE.parent.exists():
    EVIDENCE = Path("/tmp/evidence/phase20-1")
EVIDENCE.mkdir(parents=True, exist_ok=True)

report = {
    "phase": "20.1-prepare-smoke-test-data",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "partner_id": PARTNER_ID,
    "invoices": [],
    "ok": True,
}


def fail(msg):
    report["ok"] = False
    report["error"] = msg
    raise SystemExit(msg)


partner = env["res.partner"].browse(PARTNER_ID)
if not partner.exists():
    fail(f"partner_id {PARTNER_ID} no existe")

partner.write({"ref": PARTNER_REF, "name": "SMOKE P13.4 CF"})
env.cr.commit()

mod = env["ir.module.module"].search([("name", "=", "hellenia_account")], limit=1)
if mod and mod.state == "installed":
    mod.button_immediate_upgrade()
    env.cr.commit()
    report["module_version"] = mod.latest_version

company = env.company
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
tax_sale = env["account.tax"].search(
    [("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)],
    limit=1,
)
journal_sale = env["account.journal"].search(
    [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
)

pending = env["account.move"].search(
    [
        ("partner_id", "=", PARTNER_ID),
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("payment_state", "in", ("not_paid", "partial")),
    ]
)
report["pending_before"] = pending.mapped("name")

needed = max(0, 3 - len(pending))
created = []
for i in range(needed):
    ref = f"P201-{datetime.now(timezone.utc).strftime('%H%M%S')}-{i}"
    move = env["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": PARTNER_ID,
            "journal_id": journal_sale.id,
            "invoice_date": date.today(),
            "ref": ref,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": BASE,
                        "tax_ids": [Command.set(tax_sale.ids)],
                    }
                )
            ],
        }
    )
    move.action_post()
    created.append(move.name)

env.cr.commit()

pending_after = env["account.move"].search(
    [
        ("partner_id", "=", PARTNER_ID),
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("payment_state", "in", ("not_paid", "partial")),
    ],
    order="invoice_date asc, id asc",
)
if len(pending_after) < 3:
    fail(f"se requieren 3 facturas pendientes; hay {len(pending_after)}")

for inv in pending_after[:3]:
    report["invoices"].append(
        {
            "name": inv.name,
            "amount_total": inv.amount_total,
            "amount_residual": abs(inv.amount_residual),
            "payment_state": inv.payment_state,
        }
    )

report["partner_ref"] = partner.ref
(EVIDENCE / "smoke-test-data.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps(report, indent=2, ensure_ascii=False))
