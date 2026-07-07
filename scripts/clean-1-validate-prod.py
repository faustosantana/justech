#!/usr/bin/env python3
"""CLEAN-1 — Validación post-limpieza hellenia_prod."""
from __future__ import annotations

import calendar
import json
import os
from datetime import date, datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = os.environ.get("CLEAN1_EVIDENCE", "/var/lib/odoo/clean-1")
os.makedirs(OUT, exist_ok=True)

company = env.company
today = date.today()
period_from = today.replace(day=1)
period_to = today.replace(day=calendar.monthrange(today.year, today.month)[1])

report = {
    "phase": "CLEAN-1-VALIDATE",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "pass": True,
    "blockers": [],
    "counts": {},
    "dgii": {},
    "fiscal": {},
    "accounting_empty": {},
}

NCF_PREFIXES = ["B01", "B02", "B03", "B04", "B11", "B12", "B13", "B14", "B15", "B16", "B17"]
DGII_TYPES = ["606", "607", "608", "609", "623"]


def fail(name, detail=""):
    report["pass"] = False
    report["blockers"].append(f"{name}: {detail}")


# Conteos operativos deben ser cero
counts = {
    "posted_moves": env["account.move"].search_count([("state", "=", "posted")]),
    "all_moves": env["account.move"].search_count([]),
    "payments": env["account.payment"].search_count([]),
    "sale_orders": env["sale.order"].search_count([]) if "sale.order" in env else 0,
    "purchase_orders": env["purchase.order"].search_count([]) if "purchase.order" in env else 0,
    "bank_statements": env["account.bank.statement"].search_count([]),
    "fiscal_reports": env["justech.do.fiscal.report"].search_count([]),
    "ncf_consumptions": env["justech.do.ncf.consumption"].search_count([]),
    "pickings": env["stock.picking"].search_count([]) if "stock.picking" in env else 0,
}
report["counts"] = counts
for key, val in counts.items():
    if val != 0:
        fail(f"count_{key}", val)

# NCF types
prefixes = sorted(set(env["justech.do.fiscal.document.type"].search([]).mapped("prefix")))
missing = set(NCF_PREFIXES) - set(prefixes)
report["fiscal"]["ncf_types"] = prefixes
if missing:
    fail("ncf_types", f"missing={sorted(missing)}")

active_ranges = env["justech.do.ncf.range"].search_count(
    [("state", "=", "active"), ("company_id", "=", company.id)]
)
report["fiscal"]["active_ncf_ranges"] = active_ranges
if active_ranges < 1:
    fail("ncf_ranges", "no active ranges")

# DGII validate (periodo actual — puede estar vacío post-limpieza)
for rtype in DGII_TYPES:
    try:
        exp = env[env["justech.do.fiscal.report"].DGII_EXPORTER_MODELS[rtype]]
        val = exp.validate_period(company, period_from, period_to, refresh_states=False)
        valid = val.get("counts", {}).get("valid", 0)
        incomplete = val.get("counts", {}).get("incomplete", 0)
        passed = incomplete == 0 and (valid == 0 or rtype in ("608", "609", "623"))
        if rtype in ("606", "607") and valid > 0:
            passed = False
        report["dgii"][rtype] = {"pass": passed, "counts": val.get("counts", {})}
        if not passed:
            fail(f"dgii_{rtype}", report["dgii"][rtype])
    except Exception as exc:
        report["dgii"][rtype] = {"pass": False, "error": str(exc)[:300]}
        fail(f"dgii_{rtype}", str(exc))

# Balance / P&L / Mayor vacíos — verificar líneas con saldo en cuentas P&L/BS
MoveLine = env["account.move.line"].sudo()
lines_with_balance = MoveLine.search_count([("parent_state", "=", "posted")])
report["accounting_empty"]["posted_move_lines"] = lines_with_balance
if lines_with_balance:
    fail("general_ledger", lines_with_balance)

# Config preservada
report["preserved"] = {
    "partners": env["res.partner"].search_count([]),
    "products": env["product.product"].search_count([]),
    "accounts": env["account.account"].search_count([("company_ids", "in", company.id)]),
    "journals": env["account.journal"].search_count([("company_id", "=", company.id)]),
    "users": env["res.users"].search_count([("active", "=", True), ("share", "=", False)]),
    "audit_rules": env["justech.audit.rule"].search_count([]),
}

with open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2, ensure_ascii=False, default=str)

print("CLEAN1_VALIDATE:" + json.dumps(report, ensure_ascii=False, default=str))
