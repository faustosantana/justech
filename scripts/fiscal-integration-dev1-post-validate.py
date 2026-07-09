#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validación post-instalación erp.justech.do — solo lectura, sin modificar histórico."""
from __future__ import annotations

import json
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def validate(env, label="post_install"):
    cr = env.cr
    errors = []
    checks = {}

    def count(q, params=None):
        cr.execute(q, params or [])
        return cr.fetchone()[0]

    checks["posted_moves"] = count("SELECT COUNT(*) FROM account_move WHERE state='posted'")
    checks["partial_reconciles"] = count("SELECT COUNT(*) FROM account_partial_reconcile")
    checks["payments_active"] = count(
        "SELECT COUNT(*) FROM account_payment WHERE state IN ('paid','in_process')"
    )
    checks["companies"] = count("SELECT COUNT(*) FROM res_company")

    cr.execute(
        """
        SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0)
        FROM account_move_line aml
        JOIN account_move am ON am.id = aml.move_id
        WHERE am.state = 'posted'
        """
    )
    deb, cred = cr.fetchone()
    checks["gl_debit"] = float(deb)
    checks["gl_credit"] = float(cred)
    checks["gl_balanced"] = abs(float(deb) - float(cred)) < 0.01

    if "l10n_latam_document_number" in env["account.move"]._fields:
        checks["ncf_adel"] = count(
            """
            SELECT COUNT(*) FROM account_move
            WHERE state='posted' AND l10n_latam_document_number IS NOT NULL
              AND l10n_latam_document_number != ''
            """
        )

    if "justech_do_ncf" in env["account.move"]._fields:
        checks["ncf_justech_posted"] = count(
            """
            SELECT COUNT(*) FROM account_move
            WHERE state='posted' AND justech_do_ncf IS NOT NULL AND justech_do_ncf != ''
            """
        )
        checks["fiscal_enabled_companies"] = count(
            "SELECT COUNT(*) FROM res_company WHERE justech_do_fiscal_enabled = true"
        )
        checks["journals_justech_ncf"] = count(
            "SELECT COUNT(*) FROM account_journal WHERE justech_do_use_ncf = true"
        )

    # Apertura read-only de registros históricos (ORM browse — no write)
    Move = env["account.move"]
    Payment = env["account.payment"]
    Partner = env["res.partner"]

    sample_move = Move.search([("state", "=", "posted")], limit=1)
    if sample_move:
        _ = sample_move.name
        _ = sample_move.line_ids.mapped("balance")
        if "justech_do_ncf" in Move._fields:
            _ = sample_move.justech_do_ncf
        if "l10n_latam_document_number" in Move._fields:
            _ = sample_move.l10n_latam_document_number
    else:
        errors.append("no_posted_move_sample")

    sample_payment = Payment.search([("state", "in", ("paid", "in_process"))], limit=1)
    if sample_payment:
        _ = sample_payment.amount
        _ = sample_payment.move_id
    else:
        errors.append("no_payment_sample")

    sample_partner = Partner.search([("customer_rank", ">", 0)], limit=1)
    if sample_partner:
        _ = sample_partner.name
        _ = sample_partner.vat
    else:
        errors.append("no_partner_sample")

    credit = Move.search([("move_type", "=", "out_refund"), ("state", "=", "posted")], limit=1)
    if credit:
        _ = credit.name
    debit = Move.search([("debit_origin_id", "!=", False), ("state", "=", "posted")], limit=1)
    # debit note optional

    cr.execute(
        """
        SELECT COUNT(*) FROM account_move_line aml
        JOIN account_partial_reconcile pr ON pr.debit_move_id = aml.id OR pr.credit_move_id = aml.id
        LIMIT 1
        """
    )
    checks["reconcile_lines_exist"] = cr.fetchone()[0] > 0

    cr.execute(
        """
        SELECT name, state, latest_version FROM ir_module_module
        WHERE name IN (
          'justech_l10n_do_base','justech_l10n_do_ncf','justech_l10n_do_dashboard',
          'l10n_do_accounting','justech_l10n_do_reports'
        )
        ORDER BY name
        """
    )
    checks["modules"] = {r[0]: {"state": r[1], "version": r[2]} for r in cr.fetchall()}

    return {
        "label": label,
        "ts": utc_now(),
        "database": cr.dbname,
        "checks": checks,
        "errors": errors,
        "ok": len(errors) == 0 and checks.get("gl_balanced", False),
    }


if "env" in dir():
    print(json.dumps(validate(env), indent=2, default=str))
