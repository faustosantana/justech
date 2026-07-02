#!/usr/bin/env python3
"""Ensure shared NCF range exists for concurrency test."""
from datetime import date, timedelta

from odoo import Command

company = env["res.company"].search([], limit=1)
company.justech_do_fiscal_enabled = True
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
    [("name", "=", "Sprint0 Concurrent"), ("company_id", "=", company.id)],
    limit=1,
)
if not ncf_range:
    ncf_range = Range.create(
        {
            "name": "Sprint0 Concurrent",
            "document_type_id": doc_b02.id,
            "company_id": company.id,
            "sequence_start": 7000,
            "sequence_end": 7999,
            "next_sequence": 7000,
            "date_from": today - timedelta(days=1),
            "date_to": today + timedelta(days=30),
            "journal_ids": [Command.set(journal.ids)],
        }
    )
    ncf_range.action_activate()
else:
    max_consumed = env["justech.do.ncf.consumption"].search(
        [("range_id", "=", ncf_range.id)], order="sequence_number desc", limit=1
    )
    if max_consumed:
        ncf_range.next_sequence = max(
            max_consumed.sequence_number + 1, ncf_range.next_sequence
        )
# Isolate concurrency test: only this range may serve journal PCC for B02.
competing = Range.search(
    [
        ("company_id", "=", company.id),
        ("document_type_id", "=", doc_b02.id),
        ("state", "=", "active"),
        ("id", "!=", ncf_range.id),
    ]
)
for other in competing:
  journals = other.journal_ids
  if not journals or journal in journals:
      other.write({"state": "cancelled"})
env.cr.commit()
print("NCF_CONCURRENCY_SETUP:ok range_next=%s" % ncf_range.next_sequence)
