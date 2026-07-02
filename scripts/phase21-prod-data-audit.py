#!/usr/bin/env python3
"""Fase 21 — Auditoría datos PROD (odoo shell): reportes DGII + cadena 623."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

company = env["res.company"].search([], limit=1)
today = date.today()
report = {
    "phase": "21-prod-data-audit",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "company": company.name,
    "fiscal": {},
    "chain_623": {},
    "accounting": {},
    "ok": True,
    "pass": False,
}


def chk(ok, detail=""):
    return {"ok": bool(ok), "detail": detail}


def fail_if(cond, key, detail=""):
    if not cond:
        report["ok"] = False


# --- Module versions ---
mod = env["ir.module.module"].search([("name", "=", "justech_l10n_do_reports")], limit=1)
report["module_version"] = mod.latest_version if mod else "missing"

# --- 623 data chain ---
inv = env["account.move"].search([("name", "=", "INV/2026/00003")], limit=1)
pay = env["account.payment"].search([("name", "=", "PBNKD/2026/00002")], limit=1)
wh_lines = env["hellenia.payment.withholding.line"].search(
    [("move_id", "=", inv.id)] if inv else [("id", "=", 0)]
)
partner = inv.partner_id if inv else env["res.partner"]

chain = {}
if inv:
    chain["invoice"] = {
        "id": inv.id,
        "name": inv.name,
        "state": inv.state,
        "gov_withholding": getattr(inv, "justech_do_gov_withholding_amount", None),
        "fiscal_state": getattr(inv, "justech_do_dgii_fiscal_state", None),
        "include_dgii": getattr(inv, "justech_do_include_in_dgii", None),
    }
if pay:
    chain["payment"] = {
        "id": pay.id,
        "name": pay.name,
        "date": str(pay.date),
        "state": pay.state,
        "ref": getattr(pay, "hellenia_payment_reference", None) or getattr(pay, "ref", None) or "",
    }
if partner:
    chain["partner"] = {
        "id": partner.id,
        "name": partner.name,
        "vat": partner.vat or "",
    }
if wh_lines:
    chain["withholding_lines"] = [
        {"id": wl.id, "amount": wl.amount, "catalog": wl.catalog_id.code if wl.catalog_id else None}
        for wl in wh_lines
    ]

# Validate 623 exporter
exporter = env["justech.do.dgii.623.exporter"]
date_from = date(2026, 7, 1)
date_to = date(2026, 7, 31)
result_623 = exporter.validate_period_623(company, date_from, date_to, refresh_states=True)
counts = result_623["counts"]
chain["validation_623_jul2026"] = {
    "valid": counts.get("valid", 0),
    "incomplete": counts.get("incomplete", 0),
    "excluded": counts.get("excluded", 0),
}
if inv and counts.get("incomplete", 0) > 0:
    errors = exporter._dgii_validate_single_move(inv, date_from, date_to)
    chain["validation_errors_inv00003"] = errors

report["chain_623"] = chain

# --- Fiscal reports programmatic (no UI) ---
for rtype in ("606", "607", "608", "623"):
    try:
        period_from = date(2026, 6, 1)
        period_to = date(2026, 6, 30)
        if rtype == "623":
            period_from = date(2026, 7, 1)
            period_to = date(2026, 7, 31)
        fr = env["justech.do.fiscal.report"].create(
            {
                "name": f"Phase21 Audit {rtype}",
                "report_type": rtype,
                "date_from": period_from,
                "date_to": period_to,
                "company_id": company.id,
            }
        )
        fr.action_generate()
        exportable = fr._get_exportable_lines() if hasattr(fr, "_get_exportable_lines") else fr.line_ids
        valid_lines = exportable.filtered(
            lambda l: l.fiscal_state == "valid" and l.include_in_report
        ) if exportable and hasattr(exportable[0] if exportable else env["justech.do.fiscal.report.line"], "fiscal_state") else exportable
        report["fiscal"][rtype] = chk(
            True,
            f"lines={len(fr.line_ids)} exportable={len(valid_lines) if valid_lines else len(fr.line_ids)} state={fr.state}",
        )
        # Test export path for 607
        if rtype == "607" and len(fr.line_ids) > 0:
            try:
                fr.action_export_dgii()
                report["fiscal"][f"{rtype}_export"] = chk(True, "action_export_dgii OK")
            except Exception as e:
                report["fiscal"][f"{rtype}_export"] = chk(False, str(e))
                report["ok"] = False
        fr.unlink()
    except Exception as e:
        report["fiscal"][rtype] = chk(False, str(e))
        report["ok"] = False

# --- Accounting sanity ---
posted = env["account.move"].search([("state", "=", "posted")], limit=50)
balanced = all(
    abs(sum(m.line_ids.mapped("debit")) - sum(m.line_ids.mapped("credit"))) < 0.05
    for m in posted
)
report["accounting"]["posted_balanced"] = chk(balanced, f"checked {len(posted)} moves")
report["accounting"]["posted_count"] = len(posted)

# Trial balance via account.move.line
aml = env["account.move.line"].search(
    [("parent_state", "=", "posted"), ("date", ">=", "2026-01-01"), ("date", "<=", "2026-12-31")]
)
total_debit = sum(aml.mapped("debit"))
total_credit = sum(aml.mapped("credit"))
report["accounting"]["ytd_debit_credit"] = chk(
    abs(total_debit - total_credit) < 0.05,
    f"debit={total_debit:.2f} credit={total_credit:.2f}",
)
if abs(total_debit - total_credit) >= 0.05:
    report["ok"] = False

report["pass"] = report["ok"] and counts.get("valid", 0) > 0
print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
