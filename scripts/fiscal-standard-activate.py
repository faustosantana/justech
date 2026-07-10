#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Activación estándar fiscal Justech — una empresa (acumulativo)."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone

COMPANY_ID = int(os.environ.get("FISCAL_STD_COMPANY_ID", "2"))
DRY_RUN = os.environ.get("FISCAL_STD_DRY") == "1"

DOC_REFS = {
    "B01": "justech_l10n_do_base.doc_type_b01",
    "B02": "justech_l10n_do_base.doc_type_b02",
    "B03": "justech_l10n_do_base.doc_type_b03",
    "B04": "justech_l10n_do_base.doc_type_b04",
    "B11": "justech_l10n_do_base.doc_type_b11",
    "B13": "justech_l10n_do_base.doc_type_b13",
    "B14": "justech_l10n_do_base.doc_type_b14",
    "B15": "justech_l10n_do_base.doc_type_b15",
    "B17": "justech_l10n_do_base.doc_type_b17",
}

SALE_PREFIXES = ["B01", "B02", "B03", "B04", "B14", "B15"]
PURCHASE_PREFIXES = ["B11", "B13", "B17"]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def next_seq_from_max_ncf(max_ncf, default_start=1):
    if not max_ncf or len(max_ncf) < 11:
        return default_start
    try:
        return int(max_ncf[3:]) + 1
    except ValueError:
        return default_start


def activate(env):
    Company = env["res.company"]
    Range = env["justech.do.ncf.range"]
    Journal = env["account.journal"]
    cr = env.cr

    company = Company.browse(COMPANY_ID)
    if not company.exists():
        return {"ok": False, "error": f"company {COMPANY_ID} not found"}

    sale_journal = Journal.search(
        [("company_id", "=", company.id), ("type", "=", "sale")], limit=1
    )
    purchase_journal = Journal.search(
        [("company_id", "=", company.id), ("type", "=", "purchase")], limit=1
    )
    if not sale_journal:
        return {"ok": False, "error": "sale journal not found"}

    max_by_prefix = {}
    if "l10n_latam_document_number" in env["account.move"]._fields:
        cr.execute(
            """
            SELECT LEFT(l10n_latam_document_number,3), MAX(l10n_latam_document_number)
            FROM account_move
            WHERE company_id=%s AND state='posted'
              AND l10n_latam_document_number IS NOT NULL AND l10n_latam_document_number != ''
            GROUP BY 1
            """,
            (company.id,),
        )
        max_by_prefix = {r[0]: r[1] for r in cr.fetchall()}

    date_to = date.today() + timedelta(days=365)
    created_ranges = []

    def ensure_range(prefix, journal, journal_type):
        ref = DOC_REFS.get(prefix)
        if not ref:
            return
        doc = env.ref(ref, raise_if_not_found=False)
        if not doc:
            return
        start = next_seq_from_max_ncf(max_by_prefix.get(prefix), 1)
        existing = Range.search(
            [
                ("company_id", "=", company.id),
                ("document_type_id", "=", doc.id),
                ("state", "in", ("draft", "active")),
            ],
            limit=1,
        )
        if existing:
            created_ranges.append(
                {
                    "prefix": prefix,
                    "journal_type": journal_type,
                    "action": "exists",
                    "id": existing.id,
                    "next_sequence": existing.next_sequence,
                }
            )
            return
        vals = {
            "name": f"{prefix} Std {company.name}",
            "company_id": company.id,
            "document_type_id": doc.id,
            "journal_ids": [(6, 0, journal.ids)],
            "authorization_number": f"FISCAL-STD-{company.id}",
            "sequence_start": start,
            "sequence_end": start + 99,
            "next_sequence": start,
            "date_from": date.today(),
            "date_to": date_to,
            "state": "draft",
        }
        if not DRY_RUN:
            rec = Range.create(vals)
            rec.action_activate()
            created_ranges.append(
                {
                    "prefix": prefix,
                    "journal_type": journal_type,
                    "action": "created",
                    "id": rec.id,
                    "next_sequence": rec.next_sequence,
                    "start": start,
                }
            )
        else:
            created_ranges.append({"prefix": prefix, "journal_type": journal_type, "action": "dry"})

    for prefix in SALE_PREFIXES:
        ensure_range(prefix, sale_journal, "sale")
    if purchase_journal:
        for prefix in PURCHASE_PREFIXES:
            ensure_range(prefix, purchase_journal, "purchase")

    pre = {
        "fiscal_enabled": company.justech_do_fiscal_enabled,
        "sale_l10n_latam": sale_journal.l10n_latam_use_documents,
        "sale_justech_ncf": sale_journal.justech_do_use_ncf,
    }

    if not DRY_RUN:
        company.write({"justech_do_fiscal_enabled": True})
        sale_journal.write(
            {"justech_do_use_ncf": True, "l10n_latam_use_documents": False}
        )
        if purchase_journal:
            purchase_journal.write(
                {"justech_do_use_ncf": True, "l10n_latam_use_documents": False}
            )
        env.cr.commit()

    enabled = Company.search([("justech_do_fiscal_enabled", "=", True)])

    return {
        "ok": True,
        "dry_run": DRY_RUN,
        "ts": utc_now(),
        "company": {"id": company.id, "name": company.name},
        "max_ncf_adel_by_prefix": max_by_prefix,
        "ranges": created_ranges,
        "journal_before": pre,
        "purchase_journal_configured": bool(purchase_journal),
        "fiscal_enabled_now": enabled.read(["id", "name"]),
    }


out = activate(env)
print(json.dumps(out, indent=2, default=str))
if not out.get("ok"):
    raise SystemExit(1)
