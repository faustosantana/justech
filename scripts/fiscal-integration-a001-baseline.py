#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fase A A-001 — baseline read-only erp.justech.do (justech_dev + justech_ncf_lab)."""
from __future__ import annotations

import json
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sql_count(cr, query, params=None):
    cr.execute(query, params or [])
    row = cr.fetchone()
    return row[0] if row else 0


def baseline_snapshot(env, label):
    cr = env.cr
    Move = env["account.move"]
    fields_move = Move._fields

    data = {
        "label": label,
        "database": cr.dbname,
        "ts": utc_now(),
        "posted_moves": sql_count(cr, "SELECT COUNT(*) FROM account_move WHERE state = 'posted'"),
        "partial_reconciles": sql_count(cr, "SELECT COUNT(*) FROM account_partial_reconcile"),
        "payments_active": sql_count(
            cr,
            "SELECT COUNT(*) FROM account_payment WHERE state IN ('paid', 'in_process')",
        ),
        "companies": sql_count(cr, "SELECT COUNT(*) FROM res_company"),
        "companies_fiscal_enabled": 0,
        "ncf_adel": 0,
        "ncf_justech": 0,
        "gl_balanced": False,
        "gl_debit": 0.0,
        "gl_credit": 0.0,
        "modules_fiscal": [],
    }

    cr.execute(
        """
        SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0)
        FROM account_move_line aml
        JOIN account_move am ON am.id = aml.move_id
        WHERE am.state = 'posted'
        """
    )
    deb, cred = cr.fetchone()
    data["gl_debit"] = float(deb)
    data["gl_credit"] = float(cred)
    data["gl_balanced"] = abs(float(deb) - float(cred)) < 0.01

    if "l10n_latam_document_number" in fields_move:
        data["ncf_adel"] = sql_count(
            cr,
            """
            SELECT COUNT(*) FROM account_move
            WHERE state = 'posted'
              AND l10n_latam_document_number IS NOT NULL
              AND l10n_latam_document_number != ''
            """,
        )

    if "justech_do_ncf" in fields_move:
        data["ncf_justech"] = sql_count(
            cr,
            """
            SELECT COUNT(*) FROM account_move
            WHERE state = 'posted'
              AND justech_do_ncf IS NOT NULL
              AND justech_do_ncf != ''
            """,
        )
        if "justech_do_fiscal_enabled" in env["res.company"]._fields:
            data["companies_fiscal_enabled"] = sql_count(
                cr,
                "SELECT COUNT(*) FROM res_company WHERE justech_do_fiscal_enabled = true",
            )

    cr.execute(
        """
        SELECT name, state, latest_version
        FROM ir_module_module
        WHERE name LIKE 'l10n_do%%'
           OR name LIKE 'justech_l10n%%'
           OR name LIKE 'hellenia%%'
        ORDER BY name
        """
    )
    data["modules_fiscal"] = [
        {"name": r[0], "state": r[1], "version": r[2]} for r in cr.fetchall()
    ]

    return data


if "env" in dir():
    out = {
        "iteration": "A-001",
        "snapshots": [
            baseline_snapshot(env, env.cr.dbname),
        ],
    }
    print(json.dumps(out, indent=2, default=str))
