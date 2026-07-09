#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integridad contable extendida Sprint 2 — pagos, conciliaciones, GL (read-only)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def extended_integrity(env, label="extended"):
    cr = env.cr
    cr.execute("SELECT COUNT(*) FROM account_move WHERE state = 'posted'")
    posted_moves = cr.fetchone()[0]
    cr.execute(
        """
        SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0)
        FROM account_move_line aml
        JOIN account_move am ON am.id = aml.move_id
        WHERE am.state = 'posted'
        """
    )
    gl_debit, gl_credit = cr.fetchone()
    cr.execute("SELECT COUNT(*) FROM account_partial_reconcile")
    reconciles = cr.fetchone()[0]
    cr.execute("SELECT COUNT(*) FROM account_payment WHERE state IN ('paid','in_process')")
    payments = cr.fetchone()[0]
    cr.execute(
        """
        SELECT COUNT(*) FROM account_move
        WHERE state = 'posted' AND justech_do_ncf IS NOT NULL AND justech_do_ncf != ''
        """
    )
    ncf_posted = cr.fetchone()[0]
    return {
        "label": label,
        "ts": utc_now(),
        "posted_moves": posted_moves,
        "gl_debit": float(gl_debit),
        "gl_credit": float(gl_credit),
        "gl_balanced": abs(float(gl_debit) - float(gl_credit)) < 0.01,
        "partial_reconciles": reconciles,
        "payments_active": payments,
        "ncf_posted": ncf_posted,
    }


if "env" in dir():
    print(json.dumps(extended_integrity(env), indent=2, default=str))
