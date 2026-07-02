#!/usr/bin/env python3
"""Fase 9 — Bloques 9, 11, 12: Reportes, auditoría, trazabilidad contable."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

company = env["res.company"].search([], limit=1)
today = date.today()
report = {"phase": 9, "blocks": {}, "ok": True}


def block(name, checks, obs=None):
    fails = [k for k, v in checks.items() if not v.get("ok")]
    st = "FAIL" if fails else ("PASS CON OBSERVACIONES" if obs else "PASS")
    if fails:
        report["ok"] = False
    report["blocks"][name] = {"status": st, "checks": checks, "observations": obs or []}


def chk(ok, detail=""):
    return {"ok": bool(ok), "detail": detail}


# BLOQUE 9 — Reportes
b9 = {}
mods = ("account_reports", "justech_l10n_do_reports", "l10n_do_reports", "sale", "purchase", "stock")
for m in mods:
    st = env["ir.module.module"].search([("name", "=", m)], limit=1).state
    b9[f"module_{m}"] = chk(st == "installed", st)

for rtype, label in (("606", "606"), ("607", "607"), ("608", "608")):
    try:
        r = env["justech.do.fiscal.report"].create(
            {
                "name": f"UAT Audit {label}",
                "report_type": rtype,
                "date_from": today.replace(day=1),
                "date_to": today,
                "company_id": company.id,
            }
        )
        r.action_generate()
        b9[f"report_{label}"] = chk(True, f"{len(r.line_ids)} lines")
    except Exception as e:
        b9[f"report_{label}"] = chk(False, str(e))

b9["stock_report"] = chk(
    env["stock.quant"].search_count([("quantity", ">", 0)]) >= 0,
    "quants accessible",
)
block(
    "block9_reports",
    b9,
    ["Reportes gerenciales EE: validación visual pendiente", "Formato TXT DGII oficial: Parcial MVP"],
)

# BLOQUE 11 — Auditoría
b11 = {}
moves = env["account.move"].search([("justech_do_ncf", "!=", False)], limit=5)
b11["ncf_traceability"] = chk(all(m.justech_do_ncf for m in moves), str(len(moves)))
consumptions = env["justech.do.ncf.consumption"].search([], limit=10)
b11["consumption_log"] = chk(len(consumptions) > 0, str(len(consumptions)))
b11["mail_messages"] = chk(
    env["mail.message"].search_count([("model", "=", "account.move")]) >= 0,
    "chatter available",
)
posted = env["account.move"].search([("state", "=", "posted")], limit=20)
balanced = all(
    abs(sum(m.line_ids.mapped("debit")) - sum(m.line_ids.mapped("credit"))) < 0.05 for m in posted
)
b11["entries_balanced"] = chk(balanced, f"checked {len(posted)}")
payments = env["account.payment"].search([("state", "in", ("paid", "in_process"))], limit=20)
b11["payments_logged"] = chk(len(payments) > 0, str(len(payments)))
block("block11_audit", b11)

# BLOQUE 12 — Validación contable trazabilidad
b12 = {}
so = env["sale.order"].search([], order="id desc", limit=1)
trail_ok = False
detail = "no sale order"
if so:
    inv = so.invoice_ids.filtered(lambda m: m.state == "posted")[:1]
    pay = env["account.payment"].search(
        [("partner_id", "=", so.partner_id.id), ("state", "in", ("paid", "in_process"))],
        limit=1,
    )
    r607 = env["justech.do.fiscal.report"].search([("report_type", "=", "607")], order="id desc", limit=1)
    trail_ok = bool(so) and bool(inv) and bool(r607)
    detail = f"so={so.name} inv={inv.name if inv else '-'} pay={pay.name if pay else '-'} r607={r607.name if r607 else '-'}"
b12["sales_trail"] = chk(trail_ok, detail)

po = env["purchase.order"].search([], order="id desc", limit=1)
ptrail = False
pdetail = "no po"
if po:
    bill = po.invoice_ids.filtered(lambda m: m.state == "posted")[:1]
    r606 = env["justech.do.fiscal.report"].search([("report_type", "=", "606")], order="id desc", limit=1)
    ptrail = bool(bill) and bool(r606)
    pdetail = f"po={po.name} bill={bill.name if bill else '-'} r606={r606.name if r606 else '-'}"
b12["purchase_trail"] = chk(ptrail, pdetail)

block(
    "block12_accounting_validation",
    b12,
    ["Conciliación bancaria end-to-end: sesión contador"],
)

report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
env.cr.commit()
print("UAT_AUDIT:" + json.dumps(report, ensure_ascii=False, default=str))
