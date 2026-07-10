#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba funcional wizard Justech — erp.justech.do (datos etiquetados, limpiables)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

TAG = "FISCAL-PAY-UNIFY-TEST"


def run(env):
    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "database": env.cr.dbname,
        "tag": TAG,
        "passed": False,
        "steps": [],
        "created_ids": {},
        "errors": [],
    }

    def step(name, ok, detail=""):
        report["steps"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:500]})
        if not ok:
            report["errors"].append(f"{name}: {detail}")

    company = env["res.company"].search([("name", "=", "JUSTECH S.R.L.")], limit=1)
    env = env(context=dict(env.context, allowed_company_ids=[company.id], company_id=company.id))

    partner = env["res.partner"].search([("customer_rank", ">", 0)], limit=1)
    invoice = env["account.move"].search(
        [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
            ("partner_id", "=", partner.id),
            ("company_id", "=", company.id),
        ],
        limit=1,
    )
    step("sample_invoice", bool(invoice), invoice.name if invoice else "none")
    if not invoice:
        report["passed"] = False
        return report

    Wizard = env["justech.payment.partner.wizard"]
    journal = env["account.journal"].search(
        [("type", "in", ("bank", "cash")), ("company_id", "=", company.id)], limit=1
    )
    method = journal.inbound_payment_method_line_ids[:1]
    step("journal_method", bool(journal and method), f"{journal.name if journal else None}")

    # Pago abierto
    wiz_open = Wizard.create(
        {
            "partner_type": "customer",
            "partner_id": partner.id,
            "currency_id": company.currency_id.id,
            "payment_date": fields.Date.today(),
            "communication": TAG,
            "journal_id": journal.id,
            "payment_method_line_id": method.id,
            "treasury_operation_type": "open",
            "treasury_amount_received": 100.0,
        }
    )
    try:
        res = wiz_open.action_register_payments()
        open_pay = env["account.payment"].browse(res.get("res_id"))
        step("open_payment_created", open_pay.exists() and open_pay.treasury_is_open, open_pay.name)
        report["created_ids"]["open_payment"] = open_pay.id
    except Exception as exc:
        step("open_payment_created", False, str(exc))

    # Pago aplicado con retención opcional
    residual = abs(invoice.amount_residual)
    apply_amount = min(residual, 100.0) if residual else 0
    wiz = Wizard.create(
        {
            "partner_type": "customer",
            "partner_id": partner.id,
            "currency_id": invoice.currency_id.id,
            "payment_date": fields.Date.today(),
            "communication": TAG,
            "journal_id": journal.id,
            "payment_method_line_id": method.id,
            "treasury_operation_type": "apply",
        }
    )
    wiz._load_pending_invoices()
    line = wiz.line_ids.filtered(lambda l: l.move_id == invoice)[:1]
    if not line:
        step("wizard_line", False, "line missing")
    else:
        line.apply = True
        line.amount_to_pay = apply_amount
        catalog = env["justech.do.withholding.catalog"].search(
            [("company_id", "=", company.id), ("active", "=", True), ("account_id", "!=", False)], limit=1
        )
        if catalog:
            line.withholding_catalog_ids = [(6, 0, [catalog.id])]
        try:
            before_residual = abs(invoice.amount_residual)
            result = wiz.action_register_payments()
            invoice.invalidate_recordset(["amount_residual", "payment_state"])
            after_residual = abs(invoice.amount_residual)
            step("apply_payment", after_residual < before_residual, f"{before_residual}->{after_residual}")
            if result.get("domain"):
                pay_ids = [d[2] for d in result["domain"] if d[0] == "id" and d[1] == "in"]
                if pay_ids and pay_ids[0]:
                    report["created_ids"]["apply_payments"] = pay_ids[0]
                    pay = env["account.payment"].browse(pay_ids[0][0] if isinstance(pay_ids[0], list) else pay_ids[0])
                    wh = env["justech.payment.withholding.line"].search([("payment_id", "=", pay.id)])
                    step("withholding_lines", True if not catalog else bool(wh), wh.ids)
        except Exception as exc:
            step("apply_payment", False, str(exc))

    # GL
    cr = env.cr
    cr.execute(
        "SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM account_move_line aml "
        "JOIN account_move am ON am.id=aml.move_id WHERE am.state='posted'"
    )
    d, c = cr.fetchone()
    step("gl_balanced", abs(float(d) - float(c)) < 0.01, f"{d} vs {c}")

    report["passed"] = not report["errors"]
    return report


def cleanup(env):
    report = {"deleted": [], "errors": []}
    pays = env["account.payment"].search([("memo", "ilike", TAG)])
    for pay in pays.sudo():
        try:
            wh = env["justech.payment.withholding.line"].search([("payment_id", "=", pay.id)])
            wh.unlink()
            if pay.state not in ("draft", "cancel", "canceled"):
                if hasattr(pay, "action_cancel"):
                    pay.action_cancel()
                if pay.state not in ("draft", "cancel", "canceled") and hasattr(pay, "action_draft"):
                    pay.action_draft()
            pid = pay.id
            pay.unlink()
            report["deleted"].append(pid)
        except Exception as exc:
            report["errors"].append(str(exc))
    env.cr.commit()
    return report


if "env" in dir():
    from odoo import fields

    out = run(env)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    if out.get("created_ids"):
        clean = cleanup(env)
        print(json.dumps({"cleanup": clean}, indent=2, ensure_ascii=False))
    if not out.get("passed"):
        raise SystemExit(1)
