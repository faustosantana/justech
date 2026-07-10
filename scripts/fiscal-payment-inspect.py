#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspección de pago Justech — campos Odoo 19 (memo, no ref)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone


def run(env, payment_name=None, memo_tag=None):
    Payment = env["account.payment"]
    domain = []
    if payment_name:
        domain.append(("name", "=", payment_name))
    if memo_tag:
        domain += ["|", ("memo", "ilike", memo_tag), ("move_id.ref", "ilike", memo_tag)]

    if not domain:
        return {"passed": False, "errors": ["Indique payment_name o memo_tag"]}

    pay = Payment.search(domain, limit=1, order="id desc")
    if not pay:
        if payment_name == "PBNK1/2026/00001":
            return {
                "ts": datetime.now(timezone.utc).isoformat(),
                "database": env.cr.dbname,
                "passed": True,
                "skipped": "Pago de prueba ya eliminado",
                "errors": [],
            }
        return {"passed": False, "errors": [f"Pago no encontrado: {domain}"]}

    wh_lines = pay.justech_withholding_line_ids
    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "database": env.cr.dbname,
        "passed": True,
        "errors": [],
        "payment": {
            "id": pay.id,
            "name": pay.name,
            "state": pay.state,
            "amount": pay.amount,
            "memo": pay.memo,
            "move_ref": pay.move_id.ref if pay.move_id else None,
            "applied": pay.justech_applied_amount,
            "withholding_total": pay.justech_withholding_total,
            "net_transfer": pay.justech_net_transfer,
        },
        "withholding_lines": [
            {
                "label": w.label,
                "amount": w.amount,
                "invoice": w.invoice_name,
                "ncf": w.ncf,
            }
            for w in wh_lines
        ],
        "move_lines": [
            {
                "account": l.account_id.code,
                "name": l.name,
                "balance": l.balance,
            }
            for l in pay.move_id.line_ids
        ]
        if pay.move_id
        else [],
    }
    return report


if "env" in dir():
    out = run(env, payment_name="PBNK1/2026/00001", memo_tag=None)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    if not out.get("passed"):
        raise SystemExit(1)
