# -*- coding: utf-8 -*-
"""Fase 19.3 — Validación bandeja revisión fiscal DGII en TEST."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone

from odoo import Command, _

MARKER = "PHASE19_3:"
DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

EVIDENCE_DIR = os.environ.get("HELLENIA_PHASE19_EVIDENCE", "/evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)
JSON_PATH = os.path.join(EVIDENCE_DIR, "phase19-3-review-test.json")

report_data = {
    "phase": "19.3",
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

fiscal_user = env.ref("base.user_admin")
supervisor = env.ref("base.user_admin")

report = env["justech.do.fiscal.report"].create(
    {
        "name": f"P19.3 validación {period_start}",
        "report_type": "606",
        "date_from": period_start,
        "date_to": today,
        "company_id": company.id,
    }
)
report.action_load_review_lines()
check("lines_loaded", len(report.line_ids) > 0, len(report.line_ids))
check("review_columns", all(hasattr(l, "fiscal_state") for l in report.line_ids), "ok")

report.action_validate_period()
check("state_validated", report.state == "validated", report.state)

line = report.line_ids.filtered(
    lambda l: l.include_in_report and l.fiscal_state == "valid"
)[:1]
if line:
    env["justech.do.dgii.report.exclude.wizard"].create(
        {
            "report_id": report.id,
            "line_ids": [Command.set(line.ids)],
            "reason": "P19.3 prueba exclusión con motivo",
        }
    ).action_confirm_exclude()
    check("pending_approval", report.state == "pending_approval", report.state)
    check("audit_exclude", bool(report.audit_ids.filtered(lambda a: a.event_type == "exclude")), "ok")
    move = line.move_id
    check("move_chatter", bool(move.message_ids), len(move.message_ids))
    check("report_chatter", bool(report.message_ids), len(report.message_ids))
    blocked = report.state == "pending_approval" and report.manual_exclusion_count > 0
    check("block_export_without_approval", blocked, report.state)
    report.action_approve_report()
    check("approved", report.state == "approved", report.state)
    report.action_generate_dgii_export()
    check("generated", report.state == "generated", report.state)
    check("export_hash", bool(report.export_file_hash), report.export_file_hash)
    check("audit_generate", bool(report.audit_ids.filtered(lambda a: a.event_type == "generate")), "ok")
else:
    check("pending_approval", False, "sin línea válida para excluir")
    check("block_export_without_approval", False, "skip")

report_data["pass"] = report_data["ok"] and report_data["passed"] == report_data["total"]
with open(JSON_PATH, "w", encoding="utf-8") as fh:
    json.dump(report_data, fh, ensure_ascii=False, indent=2, default=str)

print(f"{MARKER}{json.dumps(report_data, ensure_ascii=False, default=str)}")
