#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpieza segura de datos de prueba fiscal — solo IDs/evidencias inequívocas."""
from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone

TAG = "FISCALSTD"
EVIDENCE_DIRS = os.environ.get(
    "FISCAL_CLEANUP_EVIDENCE_DIRS",
    "/opt/odoo-dev/evidence/fiscal-standard",
).split(":")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_evidence_ids():
    move_ids: set[int] = set()
    payment_ids: set[int] = set()
    sources: list[str] = []
    for base in EVIDENCE_DIRS:
        if not base or not os.path.isdir(base):
            continue
        for path in glob.glob(os.path.join(base, "validate_*.json")):
            try:
                data = json.load(open(path, encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for mid in data.get("created_move_ids") or []:
                if isinstance(mid, int):
                    move_ids.add(mid)
            for pid in data.get("created_payment_ids") or []:
                if isinstance(pid, int):
                    payment_ids.add(pid)
            sources.append(path)
    return move_ids, payment_ids, sources


def run_cleanup(env):
    Move = env["account.move"]
    Payment = env["account.payment"]
    WhLine = env.get("justech.payment.withholding.line")
    AppLine = env.get("justech.payment.application.line")

    move_ids_evidence, payment_ids_evidence, sources = load_evidence_ids()
    move_ids = set(move_ids_evidence)
    payment_ids = set(payment_ids_evidence)

    void_moves = Move.search(
        [("justech_do_ncf_void_reason", "ilike", f"{TAG}%")]
    )
    for m in void_moves:
        move_ids.add(m.id)

    report = {
        "ts": utc_now(),
        "tag": TAG,
        "evidence_sources": sources,
        "candidate_move_ids": sorted(move_ids),
        "candidate_payment_ids": sorted(payment_ids),
        "deleted_moves": [],
        "deleted_payments": [],
        "deleted_wh_lines": [],
        "skipped": [],
        "errors": [],
    }

    def skip(label, detail):
        report["skipped"].append({"label": label, "detail": detail})

    payments = Payment.browse(sorted(payment_ids)).exists()
    for pay in payments:
        if pay.id not in payment_ids:
            skip(f"payment_{pay.id}", "not in evidence list")
            continue
        try:
            if pay.state not in ("draft", "cancel"):
                if hasattr(pay, "action_cancel"):
                    pay.action_cancel()
                elif hasattr(pay, "action_draft"):
                    pay.action_draft()
            if WhLine:
                wh = WhLine.search([("payment_id", "=", pay.id)])
                report["deleted_wh_lines"].extend(wh.ids)
                wh.unlink()
            if AppLine:
                AppLine.search([("payment_id", "=", pay.id)]).unlink()
            pid = pay.id
            pay.unlink()
            report["deleted_payments"].append(pid)
        except Exception as exc:
            report["errors"].append({"payment_id": pay.id, "error": str(exc)})

    moves = Move.browse(sorted(move_ids)).exists()
    for move in moves:
        if move.id not in move_ids:
            skip(f"move_{move.id}", "not in evidence list")
            continue
        marker_ok = (
            move.id in move_ids_evidence
            or (move.justech_do_ncf_void_reason or "").startswith(TAG)
        )
        if not marker_ok:
            skip(f"move_{move.id}", "no unequivocal marker")
            continue
        try:
            if move.state == "posted":
                rec_lines = move.line_ids.filtered(
                    lambda l: l.account_id.account_type in ("asset_receivable", "liability_payable")
                )
                for line in rec_lines:
                    line.remove_move_reconcile()
            if move.state == "posted":
                move.button_draft()
            if move.state != "draft":
                skip(f"move_{move.id}", f"state={move.state} after draft")
                continue
            mid = move.id
            move.unlink()
            report["deleted_moves"].append(mid)
        except Exception as exc:
            report["errors"].append({"move_id": move.id, "error": str(exc)})

    cr = env.cr
    cr.execute("SELECT COUNT(*) FROM account_move WHERE state='posted'")
    posted = cr.fetchone()[0]
    cr.execute("SELECT COUNT(*) FROM account_partial_reconcile")
    reconciles = cr.fetchone()[0]
    cr.execute(
        "SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) "
        "FROM account_move_line aml JOIN account_move am ON am.id=aml.move_id WHERE am.state='posted'"
    )
    d, c = cr.fetchone()
    report["post_metrics"] = {
        "posted": posted,
        "reconciles": reconciles,
        "gl_balanced": float(d) == float(c),
    }
    report["ok"] = not report["errors"]
    print(json.dumps(report, indent=2, default=str))
    return report


report = run_cleanup(env)
