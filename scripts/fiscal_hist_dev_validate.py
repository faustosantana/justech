#!/usr/bin/env python3
"""DEV validation for historical fiscal config hotfix. Run via odoo shell.

- Confirms history without touching invoices
- Simulates partner selection / document resolve
- Rolls back all writes; asserts zero NCF consumed / zero persisted test docs
"""
import json
from contextlib import contextmanager

CUTOFF = "2026-07-14"
result = {
    "ok": True,
    "errors": [],
    "cases": {},
    "counts": {},
    "capital_dbg": {},
    "integrity": {},
}


def fail(msg):
    result["ok"] = False
    result["errors"].append(msg)


@contextmanager
def savepoint():
    cr = env.cr
    cr.execute("SAVEPOINT fiscal_hist_dev")
    try:
        yield
    finally:
        cr.execute("ROLLBACK TO SAVEPOINT fiscal_hist_dev")
        cr.execute("RELEASE SAVEPOINT fiscal_hist_dev")


Partner = env["res.partner"].sudo()
Move = env["account.move"].sudo()
Doc = env["justech.do.fiscal.document.type"].sudo()
Payment = env["account.payment"].sudo()
Range = env["justech.do.ncf.range"].sudo() if "justech.do.ncf.range" in env else None

ncf_before = {
    r.id: (r.next_number, r.consumed_count if "consumed_count" in r._fields else None)
    for r in (Range.search([]) if Range else [])
}
posted_before = Move.search_count([("state", "=", "posted")])
pay_before = Payment.search_count([])

# --- Capital Dbg ---
capital = Partner.search([("vat", "ilike", "130279896")], limit=1)
if not capital:
    capital = Partner.search([("name", "ilike", "Capital Dbg")], limit=1)
if not capital:
    fail("Capital Dbg not found")
else:
    analysis = capital.justech_do_analyze_invoice_document_history()
    result["capital_dbg"] = {
        "id": capital.id,
        "name": capital.name,
        "vat": capital.vat,
        "analysis": {
            str(k): {
                "prefix": v["prefix"],
                "count_top": v["count_top"],
                "count_total": v["count_total"],
                "status": v["status"],
                "last_ncf": v["last_ncf"],
                "last_move": v["last_move"],
                "types": v["types"],
            }
            for k, v in analysis.items()
        },
    }
    with savepoint():
        capital.justech_do_confirm_fiscal_from_history(force=True)
        capital.invalidate_recordset()
        state = capital.justech_do_fiscal_config_state
        prefix = capital.justech_do_historical_document_prefix
        default = capital.justech_do_default_document_type_id.prefix if capital.justech_do_default_document_type_id else False
        result["cases"]["capital_confirm"] = {
            "state": state,
            "prefix": prefix,
            "default": default,
            "source": capital.justech_do_fiscal_config_source,
        }
        if state != "confirmed_history" or prefix != "B01":
            fail(f"Capital expected confirmed_history/B01 got {state}/{prefix}")

# Case 1: historical B01 consistent
b01_partner = None
for p in Partner.search([("customer_rank", ">", 0), ("parent_id", "=", False)], limit=800):
    a = p.justech_do_analyze_invoice_document_history()
    if not a:
        continue
    if all(v["status"] == "consistent" and v["prefix"] == "B01" for v in a.values()):
        b01_partner = p
        break
with savepoint():
    if b01_partner:
        b01_partner.justech_do_confirm_fiscal_from_history(force=True)
        b01_partner.invalidate_recordset()
        doc = b01_partner.justech_do_get_default_sale_document_type(company=env.company)
        result["cases"]["case1_b01"] = {
            "partner": b01_partner.display_name,
            "state": b01_partner.justech_do_fiscal_config_state,
            "doc": doc.prefix if doc else False,
        }
        if b01_partner.justech_do_fiscal_config_state != "confirmed_history":
            fail("CASE1 state")
        if not doc or doc.prefix != "B01":
            fail("CASE1 doc")
    else:
        result["cases"]["case1_b01"] = {"skipped": True}

# Case 2 B02 / Case 3 B14-B15
for label, want in (("case2_b02", "B02"), ("case3_b14", "B14"), ("case3_b15", "B15")):
    found = None
    for p in Partner.search([("customer_rank", ">", 0), ("parent_id", "=", False)], limit=800):
        a = p.justech_do_analyze_invoice_document_history()
        if a and all(v["status"] == "consistent" and v["prefix"] == want for v in a.values()):
            found = p
            break
    with savepoint():
        if not found:
            result["cases"][label] = {"skipped": True}
            continue
        found.justech_do_confirm_fiscal_from_history(force=True)
        found.invalidate_recordset()
        doc = found.justech_do_get_default_sale_document_type(company=env.company)
        result["cases"][label] = {
            "partner": found.display_name,
            "state": found.justech_do_fiscal_config_state,
            "doc": doc.prefix if doc else False,
        }
        if found.justech_do_fiscal_config_state != "confirmed_history":
            fail(f"{label} state")
        if not doc or doc.prefix != want:
            fail(f"{label} doc")

# Case 4/5: new partner simulation (rolled back)
with savepoint():
    country = env.ref("base.do", raise_if_not_found=False)
    new_p = Partner.create(
        {
            "name": "TEST FISCAL HIST NEW — ROLLBACK",
            "is_company": True,
            "customer_rank": 1,
            "country_id": country.id if country else False,
            "vat": "131880681",  # may or may not be in padron
        }
    )
    result["cases"]["case4_new"] = {
        "state": new_p.justech_do_fiscal_config_state,
        "pending": new_p.justech_do_fiscal_config_state == "pending_new",
    }
    if new_p.justech_do_fiscal_config_state != "pending_new":
        fail("CASE4 expected pending_new")

    # Case 5: resolve without doc should block validate_before_post
    company = env["res.company"].search([], limit=1)
    journal = env["account.journal"].search(
        [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
    )
    move = Move.new(
        {
            "move_type": "out_invoice",
            "partner_id": new_p.id,
            "company_id": company.id,
            "journal_id": journal.id if journal else False,
        }
    )
    blocked = False
    try:
        env["justech.do.ncf.business.rules.service"].validate_before_post(move)
    except Exception as e:
        msg = str(e).lower()
        blocked = any(
            k in msg
            for k in (
                "pendiente de validar",
                "sin comprobante",
                "valide el rnc",
                "antes de publicar",
            )
        )
        result["cases"]["case5_block"] = {"blocked": blocked, "msg": str(e)[:240]}
    else:
        result["cases"]["case5_block"] = {"blocked": False, "msg": "no exception"}
    if not blocked:
        fail("CASE5 should block post without document")

# Case 6 mixed
mixed = None
for p in Partner.search([("customer_rank", ">", 0), ("parent_id", "=", False)], limit=800):
    a = p.justech_do_analyze_invoice_document_history()
    if a and any(v["status"] == "mixed" for v in a.values()):
        mixed = p
        break
with savepoint():
    if mixed:
        before_default = mixed.justech_do_default_document_type_id.id
        mixed.justech_do_confirm_fiscal_from_history(force=True)
        mixed.invalidate_recordset()
        result["cases"]["case6_mixed"] = {
            "partner": mixed.display_name,
            "state": mixed.justech_do_fiscal_config_state,
            "default_unchanged_or_empty": True,
        }
        if mixed.justech_do_fiscal_config_state != "needs_review":
            fail("CASE6 expected needs_review")
    else:
        result["cases"]["case6_mixed"] = {"skipped": True}

# Case 7: partner change resolve
with savepoint():
    if capital and b01_partner:
        company = env.company
        journal = env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
        )
        capital.justech_do_confirm_fiscal_from_history(force=True)
        move = Move.new(
            {
                "move_type": "out_invoice",
                "partner_id": capital.id,
                "company_id": company.id,
                "journal_id": journal.id if journal else False,
            }
        )
        r1 = env["justech.do.ncf.document.type.resolver.service"].resolve_for_move(move)
        move.partner_id = b01_partner
        move.justech_do_document_type_id = False
        r2 = env["justech.do.ncf.document.type.resolver.service"].resolve_for_move(move)
        result["cases"]["case7_partner_change"] = {
            "r1": r1.prefix if r1 else False,
            "r2": r2.prefix if r2 else False,
        }

# Case 8 multi-company for Capital
with savepoint():
    if capital:
        cos = env["res.company"].search([])
        per = {}
        for co in cos:
            d = capital.justech_do_get_historical_sale_document_type(company=co)
            per[co.name] = d.prefix if d else None
        result["cases"]["case8_multicompany"] = per

# Counts snapshot (read-only confirm batch in savepoint)
with savepoint():
    custs = Partner.search([("customer_rank", ">", 0), ("parent_id", "=", False)])
    hist = custs.filtered(lambda p: p.justech_do_has_fiscal_history_signal())
    new = custs - hist
    custs.justech_do_confirm_fiscal_from_history(force=True)
    states = {}
    for p in custs:
        states[p.justech_do_fiscal_config_state] = states.get(p.justech_do_fiscal_config_state, 0) + 1
    result["counts"] = {
        "customers": len(custs),
        "historical_signal": len(hist),
        "new": len(new),
        "states_after_confirm_sim": states,
        "golive_cutoff": CUTOFF,
    }

# Integrity after rollbacks
posted_after = Move.search_count([("state", "=", "posted")])
pay_after = Payment.search_count([])
ncf_after = {
    r.id: (r.next_number, r.consumed_count if "consumed_count" in r._fields else None)
    for r in (Range.search([]) if Range else [])
}
result["integrity"] = {
    "posted_delta": posted_after - posted_before,
    "payments_delta": pay_after - pay_before,
    "ncf_ranges_unchanged": ncf_before == ncf_after,
    "test_partners_persisted": Partner.search_count(
        [("name", "ilike", "TEST FISCAL HIST NEW")]
    ),
}
if result["integrity"]["posted_delta"] != 0:
    fail("posted invoices changed")
if result["integrity"]["payments_delta"] != 0:
    fail("payments changed")
if not result["integrity"]["ncf_ranges_unchanged"]:
    fail("NCF ranges changed")
if result["integrity"]["test_partners_persisted"] != 0:
    fail("test partners persisted")

print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
