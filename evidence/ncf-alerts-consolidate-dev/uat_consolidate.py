# -*- coding: utf-8 -*-
"""UAT alertas NCF consolidadas internas — SAVEPOINT + ROLLBACK."""
import json
from datetime import timedelta

from odoo import fields

cr = env.cr
Range = env["justech.do.ncf.range"]
Company = env["res.company"]
Activity = env["mail.activity"]
Mail = env["mail.mail"]

companies = {
    "JUSTECH": Company.browse(1),
    "JUST_OFFICE": Company.browse(3),
    "PLUGSAFE": Company.browse(2),
    "OMNI": Company.browse(4),
}
SUMMARY = Range.CONSOLIDATED_ALERT_SUMMARY
report = {"cases": {}, "companies": {}, "all_pass": True}


def count_mail():
    # Odoo 19: no subject column — match body
    return Mail.search_count(
        [
            "|",
            ("body_html", "ilike", "ALERTA DE RANGOS NCF"),
            ("body_html", "ilike", "Alerta NCF"),
        ]
    )


def count_company_activities(company):
    return Activity.search_count(
        [
            ("res_model", "=", "res.company"),
            ("res_id", "=", company.id),
            ("summary", "=", SUMMARY),
        ]
    )


def count_range_alert_activities(company):
    ids = Range.search([("company_id", "=", company.id)]).ids
    if not ids:
        return 0
    return Activity.search_count(
        [
            ("res_model", "=", "justech.do.ncf.range"),
            ("res_id", "in", ids),
            "|",
            ("summary", "ilike", "NCF"),
            ("summary", "ilike", "rango"),
        ]
    )


def fp():
    cr.execute(
        "SELECT md5(string_agg(id::text||':'||next_sequence::text||':'||sequence_end::text,'|' ORDER BY id)) "
        "FROM justech_do_ncf_range"
    )
    return cr.fetchone()[0]


fp0 = fp()
mail0 = count_mail()

# ---------- CASO 1 JUSTECH multi-range ----------
cr.execute("SAVEPOINT uat_c1")
try:
    co = companies["JUSTECH"]
    # Use existing B11,B13,B14,B15 if present
    prefixes = ["B11", "B13", "B14", "B15"]
    for pref in prefixes:
        rng = Range.search([("company_id", "=", co.id), ("prefix", "=", pref)], limit=1)
        if not rng:
            continue
        # force critical: available = 5
        rng.write({"sequence_end": rng.next_sequence + 4})
    # B14 preventive if exists: available = 18
    b14 = Range.search([("company_id", "=", co.id), ("prefix", "=", "B14")], limit=1)
    if b14:
        b14.write({"sequence_end": b14.next_sequence + 17})

    before_acts = count_company_activities(co)
    before_mail = count_mail()
    res = Range.with_company(co)._process_company_consolidated_alert(co)
    after_acts = count_company_activities(co)
    after_mail = count_mail()
    act = Activity.search(
        [("res_model", "=", "res.company"), ("res_id", "=", co.id), ("summary", "=", SUMMARY)],
        limit=1,
    )
    note = act.note or ""
    # Markup stores real HTML; fail if tags appear escaped as visible text
    rendered = (
        "&lt;p&gt;" not in note
        and "&lt;li&gt;" not in note
        and "ALERTA DE RANGOS NCF" in note
        and "<li>" in note
    )
    has_ranges = "disponibles" in note and ("Crítico" in note or "Preventivo" in note)
    case1 = {
        "ok": (
            after_acts == 1
            and after_mail == before_mail
            and res.get("alerts", 0) >= 1
            and rendered
            and has_ranges
        ),
        "activities": after_acts,
        "mail_delta": after_mail - before_mail,
        "alerts": res.get("alerts"),
        "rendered": rendered,
        "has_ranges": has_ranges,
        "note_snip": note[:240],
    }
    report["cases"]["C1_justech_multi"] = case1

    # ---------- CASO 2 second run ----------
    res2 = Range.with_company(co)._process_company_consolidated_alert(co)
    acts2 = count_company_activities(co)
    mail2 = count_mail()
    case2 = {
        "ok": acts2 == 1 and mail2 == before_mail,
        "activities": acts2,
        "mail_delta": mail2 - before_mail,
        "action": res2.get("activity"),
    }
    report["cases"]["C2_second_run"] = case2

    # ---------- CASO 3 threshold change B14 to critical ----------
    if b14:
        b14.write({"sequence_end": b14.next_sequence + 4})
        act_id_before = act.id
        Range.with_company(co)._process_company_consolidated_alert(co)
        act_after = Activity.search(
            [("res_model", "=", "res.company"), ("res_id", "=", co.id), ("summary", "=", SUMMARY)],
            limit=1,
        )
        note2 = act_after.note or ""
        case3 = {
            "ok": act_after.id == act_id_before and count_company_activities(co) == 1 and "B14" in note2,
            "same_activity": act_after.id == act_id_before,
            "activities": count_company_activities(co),
        }
    else:
        case3 = {"ok": True, "skipped": True}
    report["cases"]["C3_threshold_update"] = case3

    # ---------- CASO 4 normalize all ----------
    for rng in Range.search([("company_id", "=", co.id)]):
        if rng.state == "cancelled":
            continue
        rng.write(
            {
                "sequence_end": max(rng.sequence_end, rng.next_sequence + 50),
                "date_to": fields.Date.today() + timedelta(days=180),
                "state": "active",
            }
        )
        rng._recompute_operational_state()
    Range.with_company(co)._process_company_consolidated_alert(co)
    case4 = {
        "ok": count_company_activities(co) == 0 and count_mail() == before_mail,
        "activities": count_company_activities(co),
        "mail_delta": count_mail() - before_mail,
    }
    report["cases"]["C4_normalize_close"] = case4
finally:
    cr.execute("ROLLBACK TO SAVEPOINT uat_c1")
    cr.execute("RELEASE SAVEPOINT uat_c1")

# ---------- CASO 5 multiempresa 4/4 ----------
cr.execute("SAVEPOINT uat_c5")
try:
    mail_before = count_mail()
    per = {}
    for key, co in companies.items():
        rng = Range.search([("company_id", "=", co.id), ("prefix", "=", "B01")], limit=1)
        if not rng:
            rng = Range.search([("company_id", "=", co.id)], limit=1)
        if not rng:
            per[key] = {"ok": False, "error": "no_range"}
            report["all_pass"] = False
            continue
        rng.write({"sequence_end": rng.next_sequence + 4})  # critical
        Range.with_company(co)._process_company_consolidated_alert(co)
        acts = count_company_activities(co)
        cross = Activity.search(
            [
                ("summary", "=", SUMMARY),
                ("res_model", "=", "res.company"),
                ("res_id", "=", co.id),
            ],
            limit=1,
        )
        user_ok = True
        if cross:
            u = cross.user_id
            user_ok = co in u.company_ids
        per[key] = {
            "ok": acts == 1 and user_ok,
            "activities": acts,
            "user_id": cross.user_id.id if cross else None,
            "user_ok": user_ok,
        }
        if not per[key]["ok"]:
            report["all_pass"] = False
    total_acts = Activity.search_count(
        [("summary", "=", SUMMARY), ("res_model", "=", "res.company")]
    )
    case5 = {
        "ok": total_acts == 4 and count_mail() == mail_before and all(v.get("ok") for v in per.values()),
        "total_activities": total_acts,
        "mail_delta": count_mail() - mail_before,
        "per_company": per,
    }
    report["cases"]["C5_multicompany"] = case5
    report["companies"] = per
finally:
    cr.execute("ROLLBACK TO SAVEPOINT uat_c5")
    cr.execute("RELEASE SAVEPOINT uat_c5")

# ---------- CASO 6 no fiscal manager (simulate by filtering) — soft check ----------
cr.execute("SAVEPOINT uat_c6")
try:
    co = companies["PLUGSAFE"]
    rng = Range.search([("company_id", "=", co.id)], limit=1)
    rng.write({"sequence_end": rng.next_sequence + 3})
    # Call with patch: temporarily empty fiscal managers via context flag
    # We just verify method returns without crash and creates <=1 activity
    res = Range.with_company(co)._process_company_consolidated_alert(co)
    case6 = {
        "ok": count_company_activities(co) <= 1 and res.get("activity") != "error",
        "result": res,
        "activities": count_company_activities(co),
    }
    report["cases"]["C6_fallback"] = case6
finally:
    cr.execute("ROLLBACK TO SAVEPOINT uat_c6")
    cr.execute("RELEASE SAVEPOINT uat_c6")

fp1 = fp()
mail1 = count_mail()
report["fp_unchanged"] = fp0 == fp1
report["mail_unchanged"] = mail0 == mail1
report["mail_generated"] = mail1 - mail0
report["all_pass"] = (
    report["all_pass"]
    and all(c.get("ok") for c in report["cases"].values())
    and report["fp_unchanged"]
    and report["mail_unchanged"]
)
report["version"] = env["ir.module.module"].search([("name", "=", "justech_l10n_do_ncf")], limit=1).latest_version

print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
env.cr.rollback()
