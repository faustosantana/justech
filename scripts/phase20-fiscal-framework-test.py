# -*- coding: utf-8 -*-
"""Fase 20 — Validación correcciones framework fiscal en TEST."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from odoo import Command

MARKER = "PHASE20:"
DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

EVIDENCE_DIR = os.environ.get("HELLENIA_PHASE20_EVIDENCE", "/evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

report_data = {
    "phase": "20",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "checks": {},
    "ok": True,
    "passed": 0,
    "total": 0,
    "pass": False,
}


def check(key, ok, detail=""):
    report_data["checks"][key] = {"ok": bool(ok), "detail": str(detail)}
    report_data["total"] += 1
    if ok:
        report_data["passed"] += 1
    else:
        report_data["ok"] = False


period_util = env["justech.do.dgii.period"]
company = env.company
date_from, date_to = period_util.period_bounds_from_code("202606")

# 1. Período YYYYMM
report = env["justech.do.fiscal.report"].create(
    {
        "name": "P20 framework fiscal",
        "report_type": "606",
        "period_code": "202606",
        "company_id": company.id,
    }
)
check("period_date_from", report.date_from == date_from, report.date_from)
check("period_date_to", report.date_to == date_to, report.date_to)
check("period_display_from", report.date_from_display == "01/06/2026", report.date_from_display)
check("period_display_to", report.date_to_display == "30/06/2026", report.date_to_display)

# 2. Carga y contadores unificados
report.action_load_review_lines()
report.action_validate_period()
report._refresh_summary_counts()
check(
    "counts_match",
    report.count_all == report.review_line_count,
    f"stored={report.count_all} computed={report.review_line_count}",
)
check(
    "valid_counts_match",
    report.count_valid == report.review_valid_count,
    f"stored={report.count_valid} computed={report.review_valid_count}",
)

# 3. Bitácora / chatter en transiciones
check("audit_on_create", bool(report.audit_ids.filtered(lambda a: a.event_type == "create")), "ok")
check("audit_on_validate", bool(report.audit_ids.filtered(lambda a: a.event_type == "validate")), "ok")
check("chatter_messages", len(report.message_ids) > 0, len(report.message_ids))
check("state_validated", report.state == "validated", report.state)

# 4. Guardia de estado manual
blocked = False
try:
    report.write({"state": "approved"})
except Exception as err:
    blocked = "estado" in str(err).lower() or "state" in str(err).lower()
check("state_guard", blocked, "manual write blocked")

# 5. Bandeja pendientes
line = report.line_ids.filtered(
    lambda l: l.include_in_report and l.fiscal_state == "valid"
)[:1]
if line:
    env["justech.do.dgii.report.exclude.wizard"].create(
        {
            "report_id": report.id,
            "line_ids": [Command.set(line.ids)],
            "reason": "P20 validación bandeja",
        }
    ).action_confirm_exclude()
    report.invalidate_recordset()
    check("has_pending_flag", report.has_pending_approval, report.has_pending_approval)
    tray = env["justech.do.fiscal.report"].search(
        [("has_pending_approval", "=", True), ("id", "=", report.id)]
    )
    check("in_pending_tray", bool(tray), len(tray))
    check("submitted_by", bool(report.approval_submitted_by_id), report.approval_submitted_by_id.name)

    # Aprobar línea
    line.action_approve_line()
    report.invalidate_recordset()
    tray_after = env["justech.do.fiscal.report"].search(
        [("has_pending_approval", "=", True), ("id", "=", report.id)]
    )
    check("removed_after_approve", not tray_after, report.state)
    check("state_after_approve", report.state == "approved", report.state)
else:
    check("has_pending_flag", False, "sin línea válida")
    check("in_pending_tray", False, "sin línea válida")
    check("submitted_by", False, "sin línea válida")
    check("removed_after_approve", False, "sin línea válida")
    check("state_after_approve", False, "sin línea válida")

# 6. Asistente bloqueo Excel
report2 = env["justech.do.fiscal.report"].create(
    {
        "name": "P20 bloqueo export",
        "report_type": "606",
        "period_code": "202606",
        "company_id": company.id,
    }
)
report2.action_load_review_lines()
report2.action_validate_period()
line2 = report2.line_ids.filtered(
    lambda l: l.include_in_report and l.fiscal_state == "valid"
)[:1]
if line2:
    line2.write(
        {
            "include_in_report": False,
            "manual_exclusion": True,
            "line_approval_state": "pending",
            "exclusion_reason": "P20 bloqueo export",
            "fiscal_state": "excluded",
        }
    )
    action = report2._check_can_generate()
    check(
        "export_blocker_wizard",
        isinstance(action, dict) and action.get("res_model") == "justech.do.dgii.export.blocker.wizard",
        action.get("res_model") if isinstance(action, dict) else type(action).__name__,
    )
else:
    check("export_blocker_wizard", False, "sin línea válida")

# 7. Acción bandeja vacía (help configurado)
action_ref = env.ref("justech_l10n_do_reports.action_justech_do_fiscal_review_pending")
check("pending_action_domain", "has_pending_approval" in (action_ref.domain or ""), action_ref.domain)
check("pending_action_help", bool(action_ref.help), "help set")

# 8. Vista revisión — filtros y campos
review_form = env.ref("justech_l10n_do_reports.view_justech_do_fiscal_report_review_form")
arch = review_form.arch or ""
check("review_readonly_state", 'name="state"' in arch and "readonly" in arch, "ok")
check("review_period_display", "date_from_display" in arch, "ok")
check("review_filter_approved", "Aprobados" in arch, "ok")

report_data["pass"] = report_data["ok"] and report_data["passed"] == report_data["total"]
print(MARKER + json.dumps(report_data, ensure_ascii=False))
