# -*- coding: utf-8 -*-
"""UAT multiempresa rangos NCF — SAVEPOINT + ROLLBACK. 0 NCF consumidos."""
import json
from datetime import timedelta

from odoo import fields

cr = env.cr
Range = env["justech.do.ncf.range"]
Company = env["res.company"]
companies = {
    "JUSTECH": Company.browse(1),
    "JUST_OFFICE": Company.browse(3),
    "PLUGSAFE": Company.browse(2),
    "OMNI": Company.browse(4),
}
report = {"companies": {}, "isolation": {}, "all_pass": True}


def fp_ranges():
    cr.execute(
        "SELECT md5(string_agg(t::text, '|' ORDER BY t)) "
        "FROM (SELECT id, company_id, sequence_start, sequence_end, next_sequence, state, date_to "
        "FROM justech_do_ncf_range ORDER BY id) t"
    )
    return cr.fetchone()[0]


def fp_seqs():
    cr.execute(
        "SELECT md5(string_agg(id::text || ':' || number_next::text, '|' ORDER BY id)) "
        "FROM ir_sequence"
    )
    return cr.fetchone()[0]


def move_count():
    cr.execute("SELECT count(*) FROM account_move")
    return cr.fetchone()[0]


fp0 = {"ranges": fp_ranges(), "seqs": fp_seqs(), "moves": move_count()}


def pick_range(company):
    rng = Range.search(
        [("company_id", "=", company.id), ("prefix", "=", "B01")], limit=1
    )
    if not rng:
        rng = Range.search([("company_id", "=", company.id)], limit=1)
    return rng


def run_company(key, company):
    out = {"company": company.name, "cases": {}, "ok": True}
    rng = pick_range(company)
    if not rng:
        out["ok"] = False
        out["error"] = "no_range"
        report["companies"][key] = out
        report["all_pass"] = False
        return

    out["range_id"] = rng.id
    out["prefix"] = rng.prefix
    base_start = rng.sequence_start
    base_end = rng.sequence_end
    base_next = rng.next_sequence
    base_state = rng.state
    base_date_to = rng.date_to

    cr.execute("SAVEPOINT uat_co")

    try:
        # A — force depleted without shrinking below sequence_start
        # next_sequence = end + 1 ⇒ disponibles 0 (rollback restores)
        rng.with_company(company).write(
            {"next_sequence": rng.sequence_end + 1}
        )
        rng.invalidate_recordset()
        a_ok = (
            rng.state == "depleted"
            and rng.remaining_count == 0
            and rng.pct_used >= 99.0
        )
        # block emission
        blocked = False
        try:
            rng.with_company(company)._check_usable()
        except Exception as e:
            blocked = "agotado" in str(e).lower() or "depleted" in str(e).lower() or "Agotado" in str(e)
        # alert depleted
        before_acts = env["mail.activity"].search_count(
            [("res_model", "=", "justech.do.ncf.range"), ("res_id", "=", rng.id)]
        )
        rng.with_company(company)._process_alerts()
        after_acts = env["mail.activity"].search_count(
            [("res_model", "=", "justech.do.ncf.range"), ("res_id", "=", rng.id)]
        )
        # idempotent second call
        rng.with_company(company)._process_alerts()
        after_acts2 = env["mail.activity"].search_count(
            [("res_model", "=", "justech.do.ncf.range"), ("res_id", "=", rng.id)]
        )
        recipients = rng._alert_recipient_users()
        cross = recipients.filtered(lambda u: company not in u.company_ids)
        out["cases"]["A_depleted"] = {
            "ok": a_ok and blocked,
            "state": rng.state,
            "remaining": rng.remaining_count,
            "pct": rng.pct_used,
            "blocked": blocked,
            "alert_new": after_acts > before_acts,
            "idempotent": after_acts2 == after_acts,
            "cross_recipients": len(cross),
        }

        # B — expand end (preserve next)
        expand_to = base_next + 55
        preserved_next = rng.next_sequence
        rng.with_company(company).write({"sequence_end": expand_to})
        rng.invalidate_recordset()
        auth, cons, avail, pct = rng._metrics()
        b_ok = (
            rng.state == "active"
            and rng.next_sequence == preserved_next
            and avail == expand_to - preserved_next + 1
            and abs(pct - (100.0 * cons / auth if auth else 0)) < 0.05
        )
        out["cases"]["B_expand"] = {
            "ok": b_ok,
            "state": rng.state,
            "next": rng.next_sequence,
            "preserved": preserved_next,
            "available": avail,
            "pct": pct,
            "authorized": auth,
            "consumed": cons,
        }

        # C — preventive: set available == preventive threshold
        prev_th = rng._threshold_preventive()
        # available = end - next + 1 == prev_th → end = next + prev_th - 1
        rng.with_company(company).write(
            {
                "sequence_end": rng.next_sequence + prev_th - 1,
                "alert_preventive_cycle": False,
                "alert_critical_cycle": False,
                "alert_depleted_cycle": False,
            }
        )
        rng.invalidate_recordset()
        acts0 = env["mail.activity"].search_count(
            [("res_model", "=", "justech.do.ncf.range"), ("res_id", "=", rng.id)]
        )
        rng.with_company(company)._process_alerts()
        acts1 = env["mail.activity"].search_count(
            [("res_model", "=", "justech.do.ncf.range"), ("res_id", "=", rng.id)]
        )
        rng.with_company(company)._process_alerts()
        acts2 = env["mail.activity"].search_count(
            [("res_model", "=", "justech.do.ncf.range"), ("res_id", "=", rng.id)]
        )
        out["cases"]["C_preventive"] = {
            "ok": rng.remaining_count == prev_th and acts1 >= acts0 and acts2 == acts1,
            "remaining": rng.remaining_count,
            "threshold": prev_th,
            "idempotent": acts2 == acts1,
        }

        # D — critical
        crit_th = rng._threshold_critical()
        rng.with_company(company).write(
            {
                "sequence_end": rng.next_sequence + crit_th - 1,
                "alert_critical_cycle": False,
                "alert_preventive_cycle": False,
            }
        )
        rng.invalidate_recordset()
        acts0 = env["mail.activity"].search_count(
            [("res_model", "=", "justech.do.ncf.range"), ("res_id", "=", rng.id)]
        )
        rng.with_company(company)._process_alerts()
        acts1 = env["mail.activity"].search_count(
            [("res_model", "=", "justech.do.ncf.range"), ("res_id", "=", rng.id)]
        )
        rng.with_company(company)._process_alerts()
        acts2 = env["mail.activity"].search_count(
            [("res_model", "=", "justech.do.ncf.range"), ("res_id", "=", rng.id)]
        )
        out["cases"]["D_critical"] = {
            "ok": rng.remaining_count == crit_th and acts1 >= acts0 and acts2 == acts1,
            "remaining": rng.remaining_count,
            "threshold": crit_th,
            "idempotent": acts2 == acts1,
        }

        # E — expired with stock
        rng.with_company(company).write(
            {
                "sequence_end": rng.next_sequence + 20,
                "date_to": fields.Date.today() - timedelta(days=1),
                "alert_expired_cycle": False,
            }
        )
        rng.invalidate_recordset()
        exp_blocked = False
        try:
            rng.with_company(company)._check_usable()
        except Exception as e:
            exp_blocked = "vencido" in str(e).lower() or "expired" in str(e).lower()
        # expand end should NOT revive expired
        rng.with_company(company).write({"sequence_end": rng.sequence_end + 10})
        rng.invalidate_recordset()
        still_expired = rng.state == "expired"
        out["cases"]["E_expired"] = {
            "ok": still_expired and exp_blocked and rng.remaining_count > 0,
            "state": rng.state,
            "remaining": rng.remaining_count,
            "blocked": exp_blocked,
        }

        # F — closed stays closed on expand
        rng.with_company(company).write(
            {
                "state": "cancelled",
                "date_to": base_date_to,
                "sequence_end": rng.next_sequence + 30,
            }
        )
        rng.invalidate_recordset()
        out["cases"]["F_closed"] = {
            "ok": rng.state == "cancelled",
            "state": rng.state,
        }

        out["ok"] = all(c.get("ok") for c in out["cases"].values())
        if not out["ok"]:
            report["all_pass"] = False
    except Exception as e:
        out["ok"] = False
        out["error"] = str(e)[:500]
        report["all_pass"] = False
    finally:
        cr.execute("ROLLBACK TO SAVEPOINT uat_co")
        cr.execute("RELEASE SAVEPOINT uat_co")

    report["companies"][key] = out


for key, company in companies.items():
    run_company(key, company)

# G — isolation: mutate Just Office in savepoint, check others unchanged via SQL snapshot
cr.execute("SAVEPOINT uat_iso")
try:
    others_before = {}
    for key, company in companies.items():
        if key == "JUST_OFFICE":
            continue
        cr.execute(
            "SELECT id, sequence_end, next_sequence, state FROM justech_do_ncf_range "
            "WHERE company_id=%s ORDER BY id",
            [company.id],
        )
        others_before[key] = cr.fetchall()
    jo = pick_range(companies["JUST_OFFICE"])
    jo.write({"sequence_end": jo.sequence_end + 100})
    iso_ok = True
    for key, company in companies.items():
        if key == "JUST_OFFICE":
            continue
        cr.execute(
            "SELECT id, sequence_end, next_sequence, state FROM justech_do_ncf_range "
            "WHERE company_id=%s ORDER BY id",
            [company.id],
        )
        if cr.fetchall() != others_before[key]:
            iso_ok = False
    report["isolation"]["JUST_OFFICE_mutate"] = {"ok": iso_ok}
    if not iso_ok:
        report["all_pass"] = False
finally:
    cr.execute("ROLLBACK TO SAVEPOINT uat_iso")
    cr.execute("RELEASE SAVEPOINT uat_iso")

fp1 = {"ranges": fp_ranges(), "seqs": fp_seqs(), "moves": move_count()}
report["fp_before"] = fp0
report["fp_after"] = fp1
report["unchanged"] = fp0 == fp1
report["all_pass"] = report["all_pass"] and report["unchanged"]
report["versions"] = {
    m.name: m.latest_version
    for m in env["ir.module.module"].search(
        [("name", "in", ["justech_l10n_do_base", "justech_l10n_do_ncf"])]
    )
}

print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
env.cr.rollback()
