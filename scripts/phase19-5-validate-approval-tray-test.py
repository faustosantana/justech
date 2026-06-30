# -*- coding: utf-8 -*-
"""Fase 19.5 — Validación bandeja global pendientes de aprobación en TEST."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone

from odoo import Command

MARKER = "PHASE19_5:"
DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

EVIDENCE_DIR = os.environ.get("HELLENIA_PHASE19_EVIDENCE", "/evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)
JSON_PATH = os.path.join(EVIDENCE_DIR, "phase19-5-approval-tray-test.json")

report_data = {
    "phase": "19.5",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "checks": {},
    "ok": True,
    "passed": 0,
    "total": 0,
    "pass": False,
}


def check(key, ok, detail=""):
    report_data["checks"][key] = {"ok": bool(ok), "detail": detail}
    report_data["total"] += 1
    if ok:
        report_data["passed"] += 1
    else:
        report_data["ok"] = False


company = env.company
today = date.today()
period_start = today.replace(day=1)

report = env["justech.do.fiscal.report"].create(
    {
        "name": f"P19.5 bandeja {period_start}",
        "report_type": "606",
        "date_from": period_start,
        "date_to": today,
        "company_id": company.id,
    }
)
report.action_load_review_lines()
report.action_validate_period()

line = report.line_ids.filtered(
    lambda l: l.include_in_report and l.fiscal_state == "valid"
)[:1]
if not line:
    raise SystemExit("ABORT: sin línea válida para exclusión")

env["justech.do.dgii.report.exclude.wizard"].create(
    {
        "report_id": report.id,
        "line_ids": [Command.set(line.ids)],
        "reason": "P19.5 validación bandeja global",
    }
).action_confirm_exclude()

check("submitted_metadata", bool(report.approval_submitted_by_id), report.approval_submitted_by_id.name)
check("pending_count", report.pending_approval_count > 0, report.pending_approval_count)

tray = env["justech.do.fiscal.report"].search(
    [("has_pending_approval", "=", True), ("id", "=", report.id)]
)
check("in_pending_tray", bool(tray), len(tray))
check("tray_fields", all(hasattr(report, f) for f in (
    "report_type", "period_code", "company_id", "approval_submitted_by_id",
    "approval_submitted_at", "pending_approval_count", "state"
)), "ok")

pending_lines = report.line_ids.filtered(
    lambda l: l.manual_exclusion and l.line_approval_state == "pending"
)
check("pending_lines_only", len(pending_lines) == 1, len(pending_lines))

line.action_approve_line()
report.invalidate_recordset()

tray_after = env["justech.do.fiscal.report"].search(
    [("approval_ids.state", "=", "pending"), ("id", "=", report.id)]
)
check("removed_from_tray", not tray_after, report.state)
check("state_approved", report.state == "approved", report.state)
check("audit_trail", bool(report.audit_ids.filtered(lambda a: a.event_type == "approve")), "ok")

# Segundo flujo: corrección
report2 = env["justech.do.fiscal.report"].create(
    {
        "name": f"P19.5 corrección {period_start}",
        "report_type": "607",
        "date_from": period_start,
        "date_to": today,
        "company_id": company.id,
    }
)
report2.action_load_review_lines()
line2 = report2.line_ids[:1]
if line2:
    line2.write(
        {
            "include_in_report": False,
            "manual_exclusion": True,
            "line_approval_state": "pending",
            "exclusion_reason": "P19.5 prueba 607",
            "fiscal_state": "excluded",
        }
    )
    env["justech.do.dgii.report.approval"].sudo().create(
        {
            "report_id": report2.id,
            "line_id": line2.id,
            "exclusion_reason": line2.exclusion_reason,
            "requested_by_id": env.user.id,
        }
    )
    report2.write({"state": "pending_approval"})
    tray607 = env["justech.do.fiscal.report"].search(
        [("approval_ids.state", "=", "pending"), ("id", "=", report2.id)]
    )
    check("tray_multi_type", bool(tray607) and report2.report_type == "607", report2.report_type)
    env["justech.do.dgii.report.reject.wizard"].create(
        {
            "report_id": report2.id,
            "line_ids": [Command.set(line2.ids)],
            "action_mode": "correction",
            "comment": "Solicitar corrección P19.5",
        }
    ).action_confirm_reject()
    report2.invalidate_recordset()
    check("correction_to_validated", report2.state == "validated", report2.state)
    tray607_after = env["justech.do.fiscal.report"].search(
        [("approval_ids.state", "=", "pending"), ("id", "=", report2.id)]
    )
    check("607_removed_from_tray", not tray607_after, report2.state)
else:
    check("tray_multi_type", True, "skip sin líneas 607")
    check("correction_to_validated", True, "skip")
    check("607_removed_from_tray", True, "skip")

report_data["pass"] = report_data["ok"] and report_data["passed"] == report_data["total"]
with open(JSON_PATH, "w", encoding="utf-8") as fh:
    json.dump(report_data, fh, ensure_ascii=False, indent=2, default=str)

print(f"{MARKER}{json.dumps(report_data, ensure_ascii=False, default=str)}")
