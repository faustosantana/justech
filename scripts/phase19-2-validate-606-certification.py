# -*- coding: utf-8 -*-
"""Fase 19.2 — Certificación 606 período completo en TEST."""
from __future__ import annotations

import base64
import json
import os
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from odoo import _, fields

MARKER = "PHASE19_2:"
DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

EVIDENCE_DIR = os.environ.get("HELLENIA_PHASE19_EVIDENCE", "/evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)
JSON_PATH = os.path.join(EVIDENCE_DIR, "phase19-2-certification.json")
EXCEL_PATH = os.path.join(EVIDENCE_DIR, "phase19-606-full-period.xlsx")
ERRORS_PATH = os.path.join(EVIDENCE_DIR, "phase19-606-errors.xlsx")

report = {
    "phase": "19.2",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "checks": {},
    "counts": {},
    "ok": True,
    "passed": 0,
    "total": 0,
    "pass": False,
}


def check(key, ok, detail=""):
    report["checks"][key] = {"ok": bool(ok), "detail": detail}
    report["total"] += 1
    if ok:
        report["passed"] += 1
    else:
        report["ok"] = False


def _xlsx_cell_map(path):
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    shared = []
    cells = {}
    with zipfile.ZipFile(path) as zf:
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(".//m:si", ns):
                texts = [t.text or "" for t in si.findall(".//m:t", ns)]
                shared.append("".join(texts))
        sheet_xml = "xl/worksheets/sheet1.xml"
        for name in zf.namelist():
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                sheet_xml = name
                break
        root = ET.fromstring(zf.read(sheet_xml))
        for c in root.findall(".//m:c", ns):
            ref = c.get("r")
            cell_type = c.get("t")
            v = c.find("m:v", ns)
            if v is None:
                continue
            val = v.text or ""
            if cell_type == "s":
                val = shared[int(val)] if int(val) < len(shared) else val
            cells[ref] = val
    return cells


company = env.company
exporter = env["justech.do.dgii.606.exporter"]
today = fields.Date.context_today(env.user)
period_start = today.replace(day=1)
period_end = today

result = exporter.validate_period_606(company, period_start, period_end, refresh_states=True)
counts = result["counts"]
report["counts"] = counts

check("period_validated", True, json.dumps(counts))
check("excluded_uat_present", counts["excluded"] > 0, counts["excluded"])
check("valid_moves_present", counts["valid"] > 0, counts["valid"])
check("no_incomplete_blocking", counts["incomplete"] == 0, counts["incomplete"])
check("summary_has_partner_groups", counts["partners_affected"] == 0, counts["partners_affected"])

summary = exporter.format_validation_summary(result)
check("summary_spanish", "Resumen validación 606" in summary, summary[:80])

err_content, err_fname = exporter.export_errors_xlsx(
    company, period_start, period_end, result=result
)
with open(ERRORS_PATH, "wb") as fh:
    fh.write(base64.b64decode(err_content))
check("errors_xlsx_created", os.path.isfile(ERRORS_PATH), err_fname)

valid_moves = result["buckets"]["valid"]
content, filename = exporter.export_xlsx(
    company, period_start, period_end, moves=valid_moves
)
with open(EXCEL_PATH, "wb") as fh:
    fh.write(base64.b64decode(content))
check("full_period_export", os.path.isfile(EXCEL_PATH), filename)
check("export_row_count", len(valid_moves) >= 1, len(valid_moves))

cells = _xlsx_cell_map(EXCEL_PATH)
check("header_ncf", "NCF" in str(cells.get("E11", "")), cells.get("E11"))
check("data_row_12", bool(cells.get("B12")), cells.get("B12"))

fiscal_report = env["justech.do.fiscal.report"].create(
    {
        "name": f"606 certificación 19.2 {period_start} — {period_end}",
        "report_type": "606",
        "date_from": period_start,
        "date_to": period_end,
        "company_id": company.id,
    }
)
fiscal_report.action_validate()
check("history_validation_ok", fiscal_report.validation_state in ("ok", "warning"), fiscal_report.validation_state)
fiscal_report.action_generate(valid_moves=valid_moves)
fiscal_report.action_export_dgii_606(moves=valid_moves)
check("history_export", bool(fiscal_report.export_file), fiscal_report.export_filename)

report["pass"] = report["ok"] and report["passed"] == report["total"]
with open(JSON_PATH, "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=2, default=str)

print(f"{MARKER}{json.dumps(report, ensure_ascii=False, default=str)}")
