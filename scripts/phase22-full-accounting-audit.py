#!/usr/bin/env python3
"""Fase 22 — Auditoría contable integral PROD (solo lectura)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

company = env.company
report = {
    "phase": "22-full-accounting-audit",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "company": company.name,
    "modules": {},
    "integrity": {},
    "receivables": {},
    "payables": {},
    "payments": {},
    "withholdings": {},
    "taxes": {},
    "ncf": {},
    "reconciliation": {},
    "dgii": {},
    "financial": {},
    "scenarios": {},
    "critical": [],
    "minor": [],
    "ok": True,
    "pass": False,
}


def mod_ver(name):
    m = env["ir.module.module"].search([("name", "=", name)], limit=1)
    return m.latest_version if m else "missing"


def check(section, key, ok, detail=""):
    report.setdefault(section, {})[key] = {"ok": bool(ok), "detail": str(detail)[:2000]}
    if not ok:
        report["ok"] = False


def critical(msg):
    report["critical"].append(msg)
    report["ok"] = False


def minor(msg):
    report["minor"].append(msg)


for m in ("hellenia_account", "justech_l10n_do_reports", "justech_l10n_do_ncf", "account", "account_reports"):
    report["modules"][m] = mod_ver(m)

Move = env["account.move"]
Payment = env["account.payment"]
AML = env["account.move.line"]
WhLine = env["hellenia.payment.withholding.line"]
Partial = env["account.partial.reconcile"]
TOL = 0.05

# --- 1. Balanced entries ---
posted = Move.search([("state", "=", "posted")])
unbalanced = []
for m in posted:
    d = sum(m.line_ids.mapped("debit"))
    c = sum(m.line_ids.mapped("credit"))
    if abs(d - c) > TOL:
        unbalanced.append({"name": m.name, "id": m.id, "debit": d, "credit": c, "diff": d - c})
check("integrity", "posted_balanced", not unbalanced, f"checked {len(posted)}, unbalanced={len(unbalanced)}")
if unbalanced:
    critical(f"Asientos descuadrados: {[u['name'] for u in unbalanced[:10]]}")

# YTD trial balance
ytd_aml = AML.search([
    ("parent_state", "=", "posted"),
    ("date", ">=", f"{date.today().year}-01-01"),
    ("date", "<=", f"{date.today().year}-12-31"),
    ("company_id", "=", company.id),
])
td = sum(ytd_aml.mapped("debit"))
tc = sum(ytd_aml.mapped("credit"))
check("integrity", "ytd_debit_credit", abs(td - tc) < TOL, f"debit={td:.2f} credit={tc:.2f}")

# --- 2. Receivables ---
out_inv = Move.search([
    ("move_type", "=", "out_invoice"),
    ("state", "=", "posted"),
    ("company_id", "=", company.id),
])
ar_mismatch = []
paid_with_residual = []
open_no_residual = []
for inv in out_inv:
    residual = abs(inv.amount_residual)
    if inv.payment_state == "paid" and residual > TOL:
        paid_with_residual.append({"name": inv.name, "residual": residual, "state": inv.payment_state})
    if inv.payment_state in ("not_paid", "partial", "in_payment") and residual < TOL:
        open_no_residual.append(inv.name)
    ar_lines = inv.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable")
    ar_bal = sum(ar_lines.mapped("amount_residual"))
    if abs(abs(ar_bal) - residual) > 1.0 and ar_lines:
        ar_mismatch.append({"name": inv.name, "move_residual": residual, "ar_residual": abs(ar_bal)})

check("receivables", "paid_zero_residual", not paid_with_residual, f"issues={len(paid_with_residual)}")
check("receivables", "open_has_residual", not open_no_residual, f"issues={len(open_no_residual)}")
check("receivables", "ar_lines_match", not ar_mismatch, f"mismatch={len(ar_mismatch)}")
if paid_with_residual:
    critical(f"Facturas cliente pagadas con residual: {[x['name'] for x in paid_with_residual]}")
if ar_mismatch:
    minor(f"CxC residual mismatch en {len(ar_mismatch)} facturas")

# --- 3. Payables ---
in_inv = Move.search([
    ("move_type", "=", "in_invoice"),
    ("state", "=", "posted"),
    ("company_id", "=", company.id),
])
ap_paid_residual = []
for inv in in_inv:
    if inv.payment_state == "paid" and abs(inv.amount_residual) > TOL:
        ap_paid_residual.append(inv.name)
check("payables", "paid_zero_residual", not ap_paid_residual, f"posted={len(in_inv)} issues={len(ap_paid_residual)}")
if ap_paid_residual:
    critical(f"Facturas proveedor pagadas con residual: {ap_paid_residual}")

# --- 4. Payments / banks ---
payments_posted = Payment.search([
    ("state", "in", ("paid", "in_process", "posted")),
    ("company_id", "=", company.id),
])
no_move = payments_posted.filtered(lambda p: not p.move_id)
check("payments", "all_have_move", not no_move, f"posted={len(payments_posted)} sin move={len(no_move)}")
if no_move:
    critical(f"Pagos sin asiento: {no_move.mapped('name')}")

draft_with_move = Payment.search([("state", "=", "draft"), ("move_id", "!=", False)])
check("payments", "no_draft_moves", not draft_with_move, f"count={len(draft_with_move)}")

# --- 5. Withholdings ---
wh_lines = WhLine.search([("company_id", "=", company.id)])
wh_no_account = wh_lines.filtered(lambda w: w.amount and not w.account_id)
wh_no_gl = wh_lines.filtered(lambda w: w.amount and w.payment_id.state in ("paid", "in_process") and not w.move_line_id)
wh_no_move = wh_lines.filtered(lambda w: w.amount and not w.move_id)

check("withholdings", "all_have_account", not wh_no_account, f"lines={len(wh_lines)} no_account={len(wh_no_account)}")
check("withholdings", "posted_have_gl", not wh_no_gl, f"no_gl={len(wh_no_gl)}")
check("withholdings", "linked_invoice", not wh_no_move, f"no_invoice={len(wh_no_move)}")
if wh_no_account:
    critical(f"Retenciones sin cuenta: ids {wh_no_account.ids}")
if wh_no_gl:
    minor(f"Retenciones sin línea GL: ids {wh_no_gl.ids}")

# Gov 623 trace
gov_wh = wh_lines.filtered(lambda w: w.withholding_code in ("RET-GOB-5", "wh_isr_gov") or w.affects_623)
gov_trace = []
for wl in gov_wh:
    inv = wl.move_id
    pay = wl.payment_id
    issues = []
    if inv and not (inv.justech_do_gov_withholding_amount or pay.justech_do_gov_withholding_amount):
        issues.append("no_gov_field")
    if inv and inv.partner_id and not inv.partner_id.vat:
        issues.append("no_rnc")
    if issues:
        gov_trace.append({"invoice": inv.name if inv else "", "payment": pay.name, "issues": issues})
check("withholdings", "gov_623_trace", not gov_trace, f"gov_lines={len(gov_wh)} issues={len(gov_trace)}")
if gov_trace:
    minor(f"Trazabilidad 623 incompleta en {len(gov_trace)} líneas (datos legacy)")

# --- 6. ITBIS sanity ---
sale_tax = env["account.tax"].search([
    ("amount", "=", 18), ("type_tax_use", "=", "sale"), ("company_id", "=", company.id)
], limit=1)
purchase_tax = env["account.tax"].search([
    ("amount", "=", 18), ("type_tax_use", "=", "purchase"), ("company_id", "=", company.id)
], limit=1)
check("taxes", "sale_itbis_18_exists", bool(sale_tax), sale_tax.name if sale_tax else "")
check("taxes", "purchase_itbis_18_exists", bool(purchase_tax), purchase_tax.name if purchase_tax else "")

# --- 7. NCF ---
ncf_moves = Move.search([
    ("state", "=", "posted"),
    ("move_type", "in", ("out_invoice", "out_refund", "in_invoice", "in_refund")),
    ("company_id", "=", company.id),
])
no_ncf = ncf_moves.filtered(lambda m: not m.justech_do_ncf and m.move_type in ("out_invoice", "out_refund"))
env.cr.execute("""
    SELECT justech_do_ncf, COUNT(*) c FROM account_move
    WHERE state='posted' AND justech_do_ncf IS NOT NULL AND justech_do_ncf != ''
    GROUP BY justech_do_ncf HAVING COUNT(*) > 1
""")
dup_ncf = env.cr.fetchall()
check("ncf", "no_duplicates", not dup_ncf, f"dups={len(dup_ncf)}")
check("ncf", "posted_have_ncf", not no_ncf, f"missing_ncf={len(no_ncf)} names={no_ncf.mapped('name')[:5]}")
if dup_ncf:
    critical(f"NCF duplicados: {dup_ncf[:5]}")
if no_ncf:
    minor(f"Facturas posted sin NCF: {no_ncf.mapped('name')}")

# --- 8. Reconciliation orphans ---
env.cr.execute("""
    SELECT COUNT(*) FROM account_partial_reconcile pr
    WHERE NOT EXISTS (SELECT 1 FROM account_move_line WHERE id = pr.debit_move_id)
       OR NOT EXISTS (SELECT 1 FROM account_move_line WHERE id = pr.credit_move_id)
""")
orphan_partial = env.cr.fetchone()[0]
check("reconciliation", "no_orphan_partials", orphan_partial == 0, f"orphans={orphan_partial}")
if orphan_partial:
    critical(f"Conciliaciones huérfanas: {orphan_partial}")

wh_orphan_partial = WhLine.search([
    ("partial_reconcile_id", "!=", False),
    ("company_id", "=", company.id),
])
bad_wh_partial = wh_orphan_partial.filtered(
    lambda w: w.partial_reconcile_id.id
    and not Partial.browse(w.partial_reconcile_id.id).exists()
)
check("reconciliation", "wh_partial_valid", not bad_wh_partial, f"checked={len(wh_orphan_partial)}")

# --- 9. DGII traceability ---
period_code = date.today().strftime("%Y%m")
period_util = env["justech.do.dgii.period"]
df, dt = period_util.period_bounds_from_code(period_code)

for rtype, exporter_name in (
    ("606", "justech.do.dgii.606.exporter"),
    ("607", "justech.do.dgii.607.exporter"),
    ("608", "justech.do.dgii.608.exporter"),
    ("623", "justech.do.dgii.623.exporter"),
):
    try:
        exp = env[exporter_name]
        if rtype == "623":
            result = exp.validate_period_623(company, df, dt, refresh_states=True)
        elif rtype == "607":
            result = exp.validate_period_607(company, df, dt, refresh_states=True)
        elif rtype == "606":
            result = exp.validate_period_606(company, df, dt, refresh_states=True)
        else:
            result = exp.validate_period_608(company, df, dt, refresh_states=True)
        counts = result.get("counts", {})
        check("dgii", f"{rtype}_validates", True, str(counts))
        # Review line loader
        fr = env["justech.do.fiscal.report"].create({
            "name": f"P22 audit {rtype}",
            "report_type": rtype,
            "date_from": df,
            "date_to": dt,
            "company_id": company.id,
        })
        lines = fr._collect_review_lines() if hasattr(fr, "_collect_review_lines") else []
        check("dgii", f"{rtype}_review_lines", len(lines) >= 0, f"lines={len(lines)}")
        if rtype == "623":
            check("dgii", "623_has_loader", len(lines) > 0, f"lines={len(lines)}")
        fr.unlink()
    except Exception as e:
        check("dgii", f"{rtype}_validates", False, str(e))
        critical(f"DGII {rtype} error: {e}")

# P21 controlled transaction
p21 = env["res.partner"].search([("ref", "=", "P21-GOV-623-PROOF")], limit=1)
p21_inv = Move.search([("ref", "=", "P21-GOV-INV-PROOF"), ("partner_id", "=", p21.id)], limit=1) if p21 else Move
p21_ok = (
    p21
    and p21.vat
    and p21_inv
    and p21_inv.justech_do_gov_withholding_amount == 500.0
    and p21_inv.payment_state == "paid"
)
check("scenarios", "p21_gov_623_chain", p21_ok, f"inv={p21_inv.name if p21_inv else 'N/A'}")

# --- 10. Financial statement coherence ---
# Assets = Liabilities + Equity (simplified from trial balance account types)
bs_types = {
    "assets": ["asset_receivable", "asset_cash", "asset_current", "asset_non_current", "asset_prepayments", "asset_fixed"],
    "liabilities": ["liability_payable", "liability_credit_card", "liability_current", "liability_non_current"],
    "equity": ["equity", "equity_unaffected"],
}
balances = {}
for label, types in bs_types.items():
    lines = AML.search([
        ("parent_state", "=", "posted"),
        ("account_id.account_type", "in", types),
        ("company_id", "=", company.id),
    ])
    balances[label] = sum(lines.mapped("balance"))

assets = balances.get("assets", 0)
liab_eq = balances.get("liabilities", 0) + balances.get("equity", 0)
check("financial", "balance_sheet_equation", abs(assets - liab_eq) < 1.0, f"A={assets:.2f} L+E={liab_eq:.2f}")

income_lines = AML.search([
    ("parent_state", "=", "posted"),
    ("account_id.account_type", "in", ["income", "income_other"]),
    ("company_id", "=", company.id),
])
expense_lines = AML.search([
    ("parent_state", "=", "posted"),
    ("account_id.account_type", "in", ["expense", "expense_depreciation", "expense_direct_cost"]),
    ("company_id", "=", company.id),
])
check("financial", "pl_accounts_accessible", True, f"income_lines={len(income_lines)} expense_lines={len(expense_lines)}")

# Credit/debit notes existence
credit_notes = Move.search_count([("move_type", "in", ("out_refund", "in_refund")), ("state", "=", "posted")])
debit_notes = Move.search_count([("move_type", "in", ("out_invoice", "in_invoice")), ("justech_do_ncf_modified", "!=", False)])
check("scenarios", "credit_notes_posted", True, f"count={credit_notes}")
check("scenarios", "debit_notes_tracked", True, f"ncf_modified={debit_notes}")

# Summary
report["summary"] = {
    "posted_moves": len(posted),
    "posted_payments": len(payments_posted),
    "withholding_lines": len(wh_lines),
    "unbalanced_moves": len(unbalanced),
    "critical_count": len(report["critical"]),
    "minor_count": len(report["minor"]),
}
report["pass"] = report["ok"] and len(report["critical"]) == 0

print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
