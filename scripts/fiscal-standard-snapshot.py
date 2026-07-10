#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Snapshot estándar fiscal — global + empresa + muestras históricas."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

COMPANY_ID = int(os.environ.get("FISCAL_STD_COMPANY_ID", "2"))
LABEL = os.environ.get("FISCAL_STD_SNAPSHOT_LABEL", "snapshot")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def snapshot(env):
    Company = env["res.company"]
    Move = env["account.move"]
    cr = env.cr
    company = Company.browse(COMPANY_ID)

    cr.execute(
        "SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) "
        "FROM account_move_line aml JOIN account_move am ON am.id=aml.move_id WHERE am.state='posted'"
    )
    gl = cr.fetchone()

    hist_adel_only = Move.search_count(
        [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("justech_do_ncf", "=", False),
            ("l10n_latam_document_number", "!=", False),
        ]
    )

    company_ncf_adel = 0
    company_ncf_justech = 0
    last_by_prefix = []
    if "l10n_latam_document_number" in Move._fields:
        company_ncf_adel = Move.search_count(
            [
                ("company_id", "=", company.id),
                ("l10n_latam_document_number", "!=", False),
                ("state", "=", "posted"),
            ]
        )
        cr.execute(
            """
            SELECT LEFT(l10n_latam_document_number,3), COUNT(*), MAX(l10n_latam_document_number)
            FROM account_move
            WHERE company_id=%s AND state='posted'
              AND l10n_latam_document_number IS NOT NULL AND l10n_latam_document_number != ''
            GROUP BY 1 ORDER BY 1
            """,
            (company.id,),
        )
        last_by_prefix = [
            {"prefix": r[0], "count": r[1], "max_ncf": r[2]} for r in cr.fetchall()
        ]
    if "justech_do_ncf" in Move._fields:
        company_ncf_justech = Move.search_count(
            [
                ("company_id", "=", company.id),
                ("justech_do_ncf", "!=", False),
                ("state", "=", "posted"),
            ]
        )

    ranges = []
    if "justech.do.ncf.range" in env:
        ranges = env["justech.do.ncf.range"].search(
            [("company_id", "=", company.id)]
        ).read(
            ["name", "prefix", "sequence_start", "sequence_end", "next_sequence", "state"]
        )

    sale_j = env["account.journal"].search(
        [("company_id", "=", company.id), ("type", "=", "sale")], limit=1
    )
    purchase_j = env["account.journal"].search(
        [("company_id", "=", company.id), ("type", "=", "purchase")], limit=1
    )

    # Muestras históricas para verificar integridad (solo lectura)
    hist_move = Move.search(
        [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("justech_do_ncf", "=", False),
            ("l10n_latam_document_number", "!=", False),
        ],
        order="id asc",
        limit=1,
    )
    hist_payment = env["account.payment"].search(
        [("company_id", "=", company.id), ("state", "in", ("paid", "in_process", "posted"))],
        order="id asc",
        limit=1,
    )

    historical_samples = {}
    if hist_move:
        historical_samples["move_oldest_adel"] = {
            "id": hist_move.id,
            "ncf": hist_move.l10n_latam_document_number,
            "state": hist_move.state,
        }
    if hist_payment:
        historical_samples["payment_oldest"] = {
            "id": hist_payment.id,
            "amount": hist_payment.amount,
        }

    return {
        "label": LABEL,
        "ts": utc_now(),
        "company": {
            "id": company.id,
            "name": company.name,
            "fiscal_enabled": company.justech_do_fiscal_enabled,
        },
        "global": {
            "posted_moves": Move.search_count([("state", "=", "posted")]),
            "ncf_adel_total": Move.search_count(
                [("l10n_latam_document_number", "!=", False), ("state", "=", "posted")]
            )
            if "l10n_latam_document_number" in Move._fields
            else None,
            "ncf_justech_total": Move.search_count(
                [("justech_do_ncf", "!=", False), ("state", "=", "posted")]
            )
            if "justech_do_ncf" in Move._fields
            else None,
            "reconciles": env["account.partial.reconcile"].search_count([]),
            "payments": env["account.payment"].search_count(
                [("state", "in", ("paid", "in_process", "posted"))]
            ),
            "gl_debit": float(gl[0]),
            "gl_credit": float(gl[1]),
            "gl_balanced": float(gl[0]) == float(gl[1]),
        },
        "company_metrics": {
            "posted_moves": Move.search_count(
                [("company_id", "=", company.id), ("state", "=", "posted")]
            ),
            "ncf_adel_historical": company_ncf_adel,
            "ncf_justech": company_ncf_justech,
            "historical_adel_only": hist_adel_only,
            "last_ncf_by_prefix": last_by_prefix,
        },
        "ranges": ranges,
        "sale_journal": sale_j.read(
            ["id", "name", "l10n_latam_use_documents", "justech_do_use_ncf"]
        )[0]
        if sale_j
        else None,
        "purchase_journal": purchase_j.read(
            ["id", "name", "l10n_latam_use_documents", "justech_do_use_ncf"]
        )[0]
        if purchase_j
        else None,
        "historical_samples": historical_samples,
        "fiscal_enabled_companies": [
            {"id": c.id, "name": c.name}
            for c in Company.search([("justech_do_fiscal_enabled", "=", True)])
        ],
    }


out = snapshot(env)
print(json.dumps(out, indent=2, default=str))
