#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpieza inequívoca pago prueba FISCALSTD-STAB-TEST / PBNK1/2026/00001."""
from __future__ import annotations

import json
from datetime import datetime, timezone

PAYMENT_NAME = "PBNK1/2026/00001"
TAG = "FISCALSTD-STAB-TEST"


def run(env):
    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "database": env.cr.dbname,
        "payment_name": PAYMENT_NAME,
        "tag": TAG,
        "passed": False,
        "deleted_payment_id": None,
        "deleted_wh_line_ids": [],
        "invoice_preserved": None,
        "skipped": [],
        "errors": [],
    }

    pay = env["account.payment"].search([("name", "=", PAYMENT_NAME)], limit=1)
    if not pay:
        report["skipped"].append("Pago ya eliminado o inexistente")
        report["passed"] = True
        return report

    if pay.name != PAYMENT_NAME:
        report["errors"].append(f"Nombre de pago inesperado: {pay.name!r}")
        return report

    invoices = pay.reconciled_bill_ids | pay.reconciled_invoice_ids
    wh = env["justech.payment.withholding.line"].search([("payment_id", "=", pay.id)])
    app = env["justech.payment.application.line"].search([("payment_id", "=", pay.id)])

    try:
        pay = pay.sudo()
        if pay.state == "posted":
            pay.action_draft()
            pay.action_cancel()
        elif pay.state in ("in_process", "paid"):
            if hasattr(pay, "action_cancel"):
                pay.action_cancel()
            elif hasattr(pay, "button_cancel"):
                pay.button_cancel()
        if pay.state not in ("draft", "cancel", "canceled"):
            if hasattr(pay, "action_draft"):
                pay.action_draft()
        report["deleted_wh_line_ids"] = wh.ids
        wh.sudo().unlink()
        app.sudo().unlink()
        pid = pay.id
        inv_names = invoices.mapped("name")
        pay.unlink()
        env.cr.commit()
        report["deleted_payment_id"] = pid
        report["invoice_preserved"] = inv_names
        report["passed"] = True
    except Exception as exc:
        report["errors"].append(str(exc))

    return report


if "env" in dir():
    out = run(env)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    if not out.get("passed"):
        raise SystemExit(1)
