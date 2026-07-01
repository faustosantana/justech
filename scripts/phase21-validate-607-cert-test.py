# -*- coding: utf-8 -*-
"""Fase 21 — Certificación DGII 607 en TEST."""
from __future__ import annotations

import base64
import io
import json
import os
from datetime import date, datetime, timezone

from odoo import Command

MARKER = "PHASE21_607:"
DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

EVIDENCE_DIR = os.environ.get("HELLENIA_PHASE21_EVIDENCE", "/tmp/phase21-evidence")
try:
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
except OSError:
    EVIDENCE_DIR = "/tmp"

report_data = {
    "phase": "21_607_cert",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "checks": {},
    "ok": True,
    "passed": 0,
    "total": 0,
    "pass": False,
}


def check(key, ok, detail=""):
    report_data["checks"][key] = {"ok": bool(ok), "detail": str(detail)[:500]}
    report_data["total"] += 1
    if ok:
        report_data["passed"] += 1
    else:
        report_data["ok"] = False


company = env.company
period_util = env["justech.do.dgii.period"]
period_code = date.today().strftime("%Y%m")
date_from, date_to = period_util.period_bounds_from_code(period_code)
exporter = env["justech.do.dgii.607.exporter"]

# 1. Dominio solo ventas
domain = exporter._dgii_base_period_domain(company, date_from, date_to)
check("domain_out_types", "out_invoice" in str(domain) and "out_refund" in str(domain), domain)
check("domain_no_purchases", "in_invoice" not in str(domain), domain)

result = exporter.validate_period_607(company, date_from, date_to)
move_types = result["buckets"]["all"].mapped("move_type")
check("no_purchase_in_period", "in_invoice" not in move_types, list(set(move_types)))

# 2. Resumen ventas específico
summary = exporter.format_validation_summary(result)
for phrase in (
    "Resumen validación 607",
    "Facturas exportables",
    "ITBIS facturado",
    "Ventas gravadas",
    "Documentos incompletos",
):
    check(f"summary_{phrase[:20]}", phrase in summary, phrase in summary)

# 3. Wizard período
wiz = env["justech.do.fiscal.report.wizard"].create(
    {
        "report_type": "607",
        "period_code": period_code,
        "company_id": company.id,
    }
)
check("wizard_period_from", wiz.date_from == date_from, wiz.date_from)
check("wizard_period_to", wiz.date_to == date_to, wiz.date_to)
wiz.action_validate()
check("wizard_validation_log", "607" in (wiz.validation_log or ""), bool(wiz.validation_log))

# 4. Workflow revisión + contadores
report = env["justech.do.fiscal.report"].create(
    {
        "name": f"607 Cert {period_code}",
        "report_type": "607",
        "period_code": period_code,
        "date_from": date_from,
        "date_to": date_to,
        "company_id": company.id,
    }
)
report.action_load_review_lines()
report.action_validate_period()
check("review_state", report.state == "validated", report.state)
check(
    "counts_all_match",
    report.count_all == report.review_line_count,
    f"{report.count_all}/{report.review_line_count}",
)
check(
    "counts_valid_match",
    report.count_valid == report.review_valid_count,
    f"{report.count_valid}/{report.review_valid_count}",
)
check(
    "validation_log_preserved",
    "Facturas exportables" in (report.validation_log or ""),
    (report.validation_log or "")[:120],
)
check(
    "summary_text_607",
    "Ventas gravadas" in (report.summary_text or ""),
    (report.summary_text or "")[:120],
)

# 5. Bitácora español
audit_types = set(report.audit_ids.mapped("event_type"))
check("audit_create", "create" in audit_types, audit_types)
check("audit_validate", "validate" in audit_types, audit_types)
check("chatter", len(report.message_ids) > 0, len(report.message_ids))

# 6. Historial filtrado 607
hist607 = env["justech.do.fiscal.report"].search(
    [("report_type", "=", "607"), ("active", "=", True), ("id", "=", report.id)]
)
check("history_607_filter", len(hist607) == 1, len(hist607))

# 7. Excel oficial
try:
    content, filename = exporter.export_xlsx(company, date_from, date_to)
    raw = base64.b64decode(content)
    check("excel_content", len(raw) > 500, len(raw))
    check("excel_filename", "607" in filename, filename)
    try:
        import xlsxwriter  # noqa: F401
        import zipfile

        # xlsx is zip; basic structure check
        zf = zipfile.ZipFile(io.BytesIO(raw))
        check("excel_zip", "xl/workbook.xml" in zf.namelist(), len(zf.namelist()))
    except Exception as exc:
        check("excel_zip", False, str(exc))
except Exception as exc:
    check("excel_content", False, str(exc))
    check("excel_filename", False, str(exc))

# 8. Mensajes de error específicos (si hay incompletos)
incomplete = result["buckets"]["incomplete"][:1]
if incomplete:
    errs = exporter._dgii_validate_single_move(incomplete[0], date_from, date_to)
    check(
        "specific_errors",
        bool(errs) and not all(e.strip() == "Incompleto" for e in errs),
        errs[:3],
    )
else:
    check("specific_errors", True, "sin incompletos en período")

report_data["pass"] = report_data["ok"]
print(MARKER + json.dumps(report_data, ensure_ascii=False))
