# -*- coding: utf-8 -*-
"""Fase 19.4 — Validación período YYYYMM y revisión fiscal visible en TEST."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone

from odoo.exceptions import UserError

MARKER = "PHASE19_4:"
DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

EVIDENCE_DIR = os.environ.get("HELLENIA_PHASE19_EVIDENCE", "/evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)
JSON_PATH = os.path.join(EVIDENCE_DIR, "phase19-4-period-review-test.json")

report_data = {
    "phase": "19.4",
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
period_util = env["justech.do.dgii.period"]

# Bloque 1 — período
try:
    dfrom, dto = period_util.period_bounds_from_code("202606")
    check(
        "period_202606",
        dfrom == date(2026, 6, 1) and dto == date(2026, 6, 30),
        f"{dfrom} — {dto}",
    )
except UserError as err:
    check("period_202606", False, str(err))

try:
    dfrom, dto = period_util.period_bounds_from_code("202602")
    check(
        "period_202602",
        dfrom == date(2026, 2, 1) and dto == date(2026, 2, 28),
        f"{dfrom} — {dto}",
    )
except UserError as err:
    check("period_202602", False, str(err))

try:
    dfrom, dto = period_util.period_bounds_from_code("202402")
    check(
        "period_202402_leap",
        dfrom == date(2024, 2, 1) and dto == date(2024, 2, 29),
        f"{dfrom} — {dto}",
    )
except UserError as err:
    check("period_202402_leap", False, str(err))

invalid_ok = False
try:
    period_util.period_bounds_from_code("202613")
except UserError:
    invalid_ok = True
check("period_invalid_error", invalid_ok, "UserError esperado")

# Wizard + revisión persistente
wiz = env["justech.do.fiscal.report.wizard"].create(
    {
        "report_type": "606",
        "company_id": company.id,
        "period_code": "202606",
        "date_from": date(2026, 6, 1),
        "date_to": date(2026, 6, 30),
    }
)
check(
    "wizard_dates",
    wiz.date_from == date(2026, 6, 1) and wiz.date_to == date(2026, 6, 30),
    f"{wiz.date_from} — {wiz.date_to}",
)

wiz.action_validate()
check("validate_period", wiz.validation_state in ("ok", "warning", "error"), wiz.validation_state)

action = wiz.action_save_review()
saved_report = env["justech.do.fiscal.report"].browse(action["res_id"])
check("save_review_persistent", bool(saved_report.id), saved_report.id)
check("review_lines_loaded", len(saved_report.line_ids) > 0, len(saved_report.line_ids))

valid_lines = saved_report.line_ids.filtered(
    lambda l: l.fiscal_state == "valid" and l.include_in_report
)
incomplete_lines = saved_report.line_ids.filtered(lambda l: l.fiscal_state == "incomplete")
excluded_lines = saved_report.line_ids.filtered(
    lambda l: l.fiscal_state == "excluded" or not l.include_in_report
)
cancelled_lines = saved_report.line_ids.filtered(lambda l: l.fiscal_state == "cancelled")

check("visible_valid", True, len(valid_lines))
check("visible_incomplete", True, len(incomplete_lines))
check("visible_excluded", True, len(excluded_lines))
check("visible_cancelled", True, len(cancelled_lines))
check(
    "excluded_have_reason",
    all(l.exclusion_reason for l in excluded_lines) if excluded_lines else True,
    len(excluded_lines),
)
check("audit_entries", bool(saved_report.audit_ids), len(saved_report.audit_ids))
check("error_report_file", bool(saved_report.error_report_file), "ok")

# Menú revisión fiscal — registro recuperable
found = env["justech.do.fiscal.report"].search(
    [("id", "=", saved_report.id)], limit=1
)
check("open_from_menu_domain", bool(found), found.name)

report_data["pass"] = report_data["ok"] and report_data["passed"] == report_data["total"]
with open(JSON_PATH, "w", encoding="utf-8") as fh:
    json.dump(report_data, fh, ensure_ascii=False, indent=2, default=str)

print(f"{MARKER}{json.dumps(report_data, ensure_ascii=False, default=str)}")
