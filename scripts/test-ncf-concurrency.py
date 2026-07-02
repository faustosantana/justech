#!/usr/bin/env python3
"""Sprint 0 — Prueba concurrencia NCF (dos procesos Odoo paralelos)."""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta

from odoo import Command

worker_id = int(os.environ.get("WORKER_ID", sys.argv[1] if len(sys.argv) > 1 else 0))
company = env["res.company"].search([], limit=1)
company.justech_do_fiscal_enabled = True
tax = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale")],
    limit=1,
)
product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02")
journal = env["account.journal"].search(
    [("code", "=", "PCC"), ("company_id", "=", company.id)], limit=1
)
if not journal:
    journal = env["account.journal"].create(
        {
            "name": "Phase6 Concurrent",
            "code": "PCC",
            "type": "sale",
            "company_id": company.id,
            "justech_do_use_ncf": True,
            "justech_do_document_type_ids": [Command.set([doc_b02.id])],
        }
    )
Range = env["justech.do.ncf.range"]
today = date.today()
ncf_range = Range.search(
    [
        ("name", "=", "Sprint0 Concurrent"),
        ("company_id", "=", company.id),
        ("document_type_id", "=", doc_b02.id),
    ],
    limit=1,
)
if not ncf_range:
    raise RuntimeError("Sprint0 Concurrent range missing — run setup first")
partner = env["res.partner"].create({"name": f"Concurrent Worker {worker_id}"})
move = env["account.move"].create(
    {
        "move_type": "out_invoice",
        "partner_id": partner.id,
        "journal_id": journal.id,
        "invoice_date": today,
        "invoice_line_ids": [
            Command.create(
                {
                    "product_id": product.id,
                    "quantity": 1,
                    "price_unit": 50.0,
                    "tax_ids": [Command.set(tax.ids)] if tax else [],
                }
            )
        ],
    }
)
move.action_post()
env.cr.commit()
print("NCF_CONCURRENCY_RESULT:" + json.dumps({"worker": worker_id, "ncf": move.justech_do_ncf, "move": move.name}))
