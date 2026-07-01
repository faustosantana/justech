# -*- coding: utf-8 -*-
"""Fase 21.2 — Validación rápida correcciones framework 607."""
from __future__ import annotations

import json
from datetime import date

MARKER = "PHASE21_2:"
DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

report_data = {"checks": {}, "ok": True, "passed": 0, "total": 0, "pass": False}


def check(key, ok, detail=""):
    report_data["checks"][key] = {"ok": bool(ok), "detail": str(detail)[:300]}
    report_data["total"] += 1
    if ok:
        report_data["passed"] += 1
    else:
        report_data["ok"] = False


period_code = "202606"
date_from, date_to = env["justech.do.dgii.period"].period_bounds_from_code(period_code)
report = env["justech.do.fiscal.report"].search(
    [("report_type", "=", "607"), ("period_code", "=", period_code), ("active", "=", True)],
    order="id desc",
    limit=1,
)
if not report or not report.line_ids:
    if report:
        report.action_load_review_lines()
    else:
        report = env["justech.do.fiscal.report"].create(
            {
                "name": f"607 QA {period_code}",
                "report_type": "607",
                "period_code": period_code,
                "company_id": env.company.id,
            }
        )
        report.action_load_review_lines()

check("period_from", report.date_from_display == date_from.strftime("%d/%m/%Y"), report.date_from_display)
check("period_to", report.date_to_display == date_to.strftime("%d/%m/%Y"), report.date_to_display)

counts = report._get_fiscal_counts()
check("counts_match_valid", counts["valid"] == report.review_valid_count, f"{counts['valid']}/{report.review_valid_count}")
exportable = report._get_exportable_lines()
check("exportable_count", len(exportable) == counts["valid"], f"{len(exportable)}/{counts['valid']}")

valid_ids = set(report.line_ids_valid.ids)
expected_valid = set(
    report.line_ids.filtered(
        lambda l: l.fiscal_state == "valid" and l.include_in_report
    ).ids
)
check("filter_valid", valid_ids == expected_valid, f"{len(valid_ids)}/{len(expected_valid)}")

inc_ids = set(report.line_ids_incomplete.ids)
expected_inc = set(report.line_ids.filtered(lambda l: l.fiscal_state == "incomplete").ids)
check("filter_incomplete", inc_ids == expected_inc, f"{len(inc_ids)}/{len(expected_inc)}")

if not report.validated_at:
    check("needs_validation_btn", report._needs_period_validation(), True)
    report.action_validate_period()
else:
    check("needs_validation_btn", True, "already validated")
check("validated_at_set", bool(report.validated_at), report.validated_at)
if counts["valid"]:
    check("validation_state_ok", report.validation_state in ("ok", "warning"), report.validation_state)
else:
    check("validation_state_ok", report.validation_state == "error", report.validation_state)

diag = report._get_export_diagnostics()
check("export_diag_valid", diag["valid_count"] == counts["valid"], f"{diag['valid_count']}/{counts['valid']}")
check("export_not_no_valid", not diag["no_valid"] or counts["valid"] == 0, diag["no_valid"])

report_data["pass"] = report_data["ok"]
print(MARKER + json.dumps(report_data, ensure_ascii=False))
