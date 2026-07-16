# -*- coding: utf-8 -*-
"""UAT completo DEV — alertas NCF consolidadas internas."""
import json
from datetime import timedelta

from odoo import fields

cr = env.cr
Range = env["justech.do.ncf.range"].sudo()
Company = env["res.company"].sudo()
Activity = env["mail.activity"].sudo()
Mail = env["mail.mail"].sudo()
Move = env["account.move"].sudo()

SUMMARY = Range.CONSOLIDATED_ALERT_SUMMARY
companies = {
    "JUSTECH": Company.browse(1),
    "JUST_OFFICE": Company.browse(3),
    "PLUGSAFE": Company.browse(2),
    "OMNI": Company.browse(4),
}
out = {"checks": {}, "all_pass": True}


def fail(key, detail):
    out["checks"][key] = {"ok": False, "detail": detail}
    out["all_pass"] = False


def ok(key, detail=None):
    out["checks"][key] = {"ok": True, "detail": detail}


def mail_ncf_count():
    return Mail.search_count(
        [
            "|",
            "|",
            ("body_html", "ilike", "ALERTA DE RANGOS NCF"),
            ("body_html", "ilike", "Alerta NCF"),
            ("body_html", "ilike", "Revisar rangos NCF"),
        ]
    )


def consol_acts(company=None):
    domain = [
        ("summary", "=", SUMMARY),
        ("res_model", "=", "res.company"),
    ]
    if company:
        domain.append(("res_id", "=", company.id))
    return Activity.search(domain)


def range_alert_acts(company=None):
    domain = [
        ("res_model", "=", "justech.do.ncf.range"),
        "|",
        ("summary", "ilike", "NCF"),
        ("summary", "ilike", "rango"),
    ]
    if company:
        ids = Range.search([("company_id", "=", company.id)]).ids
        domain.append(("res_id", "in", ids or [0]))
    return Activity.search(domain)


def snap_ranges():
    cr.execute(
        "SELECT id, company_id, next_sequence, sequence_end, state, authorization_number "
        "FROM justech_do_ncf_range ORDER BY id"
    )
    return cr.fetchall()


def snap_moves():
    return Move.search_count([])


def gl_diff():
    cr.execute("SELECT COALESCE(SUM(debit)-SUM(credit),0) FROM account_move_line")
    return float(cr.fetchone()[0])


# Baseline fingerprints
ranges0 = snap_ranges()
moves0 = snap_moves()
gl0 = gl_diff()
mail0 = mail_ncf_count()
seq0 = None
cr.execute(
    "SELECT md5(string_agg(id::text||':'||number_next::text,'|' ORDER BY id)) FROM ir_sequence"
)
seq0 = cr.fetchone()[0]

# --- Audit & consolidate legacy open range activities (no delete) ---
legacy = range_alert_acts()
legacy_ids = legacy.ids
if legacy:
    legacy.action_feedback(
        feedback="Consolidada en actividad multiempresa de rangos NCF."
    )
ok(
    "legacy_consolidated",
    {"closed": len(legacy_ids), "ids": legacy_ids},
)

# --- Functional SAVEPOINT suite ---
cr.execute("SAVEPOINT uat_full")
try:
    mail_b = mail_ncf_count()

    # CASO Justech multi-alert → 1 activity, 0 mail
    co = companies["JUSTECH"]
    for pref, avail in (("B11", 5), ("B13", 5), ("B14", 18), ("B15", 3)):
        rng = Range.search([("company_id", "=", co.id), ("prefix", "=", pref)], limit=1)
        if not rng:
            continue
        rng.write({"sequence_end": rng.next_sequence + avail - 1})
    res = Range.with_company(co)._process_company_consolidated_alert(co)
    acts = consol_acts(co)
    note = (acts[:1].note or "") if acts else ""
    escaped = "&lt;p&gt;" in note or "&lt;li&gt;" in note or "&lt;ul&gt;" in note
    # Visible raw tags as text would mean note shows literals without being HTML;
    # we require HTML structure present AND not escaped.
    html_ok = (not escaped) and ("ALERTA DE RANGOS NCF" in note) and ("<li>" in note)
    if (
        len(acts) == 1
        and mail_ncf_count() == mail_b
        and res.get("alerts", 0) >= 3
        and html_ok
        and len(range_alert_acts(co)) == 0
    ):
        ok(
            "justech_consolidated",
            {
                "activities": 1,
                "alerts": res.get("alerts"),
                "mail_delta": mail_ncf_count() - mail_b,
                "html_ok": html_ok,
                "note_snip": note[:220],
            },
        )
    else:
        fail(
            "justech_consolidated",
            {
                "acts": len(acts),
                "mail": mail_ncf_count() - mail_b,
                "res": res,
                "html_ok": html_ok,
                "range_acts": len(range_alert_acts(co)),
                "note": note[:300],
            },
        )

    act_id = acts.id if acts else False

    # Segunda ejecución
    res2 = Range.with_company(co)._process_company_consolidated_alert(co)
    acts2 = consol_acts(co)
    if len(acts2) == 1 and acts2.id == act_id and mail_ncf_count() == mail_b and res2.get("activity") == "updated":
        ok("second_run", {"activity_id": acts2.id, "action": res2.get("activity")})
    else:
        fail("second_run", {"acts": len(acts2), "res2": res2, "same": acts2.id == act_id if acts2 else False})

    # Cambio umbral B14 → crítico
    b14 = Range.search([("company_id", "=", co.id), ("prefix", "=", "B14")], limit=1)
    if b14:
        b14.write({"sequence_end": b14.next_sequence + 4})
        Range.with_company(co)._process_company_consolidated_alert(co)
        acts3 = consol_acts(co)
        note3 = acts3.note or ""
        if len(acts3) == 1 and acts3.id == act_id and "B14" in note3 and "Crítico" in note3:
            ok("threshold_update", {"same_id": True})
        else:
            fail("threshold_update", {"acts": len(acts3), "same": acts3.id == act_id if acts3 else None, "note": note3[:200]})
    else:
        ok("threshold_update", {"skipped": True})

    # Normalizar → cierra
    for rng in Range.search([("company_id", "=", co.id)]):
        if rng.state == "cancelled":
            continue
        rng.write(
            {
                "sequence_end": max(rng.sequence_end, rng.next_sequence + 80),
                "date_to": fields.Date.today() + timedelta(days=200),
            }
        )
        rng._recompute_operational_state()
    Range.with_company(co)._process_company_consolidated_alert(co)
    if len(consol_acts(co)) == 0 and mail_ncf_count() == mail_b:
        ok("normalize_close", {"activities": 0})
    else:
        fail("normalize_close", {"activities": len(consol_acts(co))})

    # Multiempresa 4/4
    per = {}
    for key, company in companies.items():
        rng = Range.search([("company_id", "=", company.id), ("prefix", "=", "B01")], limit=1)
        if not rng:
            rng = Range.search([("company_id", "=", company.id)], limit=1)
        rng.write({"sequence_end": rng.next_sequence + 4})
        Range.with_company(company)._process_company_consolidated_alert(company)
        acts_c = consol_acts(company)
        user = acts_c.user_id if acts_c else False
        cross = bool(user and company not in user.company_ids)
        per[key] = {
            "ok": len(acts_c) == 1 and not cross,
            "activities": len(acts_c),
            "user_id": user.id if user else None,
            "cross": cross,
        }
        if not per[key]["ok"]:
            out["all_pass"] = False
    total = len(consol_acts())
    if total == 4 and mail_ncf_count() == mail_b and all(v["ok"] for v in per.values()):
        ok("multicompany_4_4", {"total": total, "per": per, "mail_delta": 0})
    else:
        fail("multicompany_4_4", {"total": total, "per": per, "mail": mail_ncf_count() - mail_b})

finally:
    cr.execute("ROLLBACK TO SAVEPOINT uat_full")
    cr.execute("RELEASE SAVEPOINT uat_full")

# Post-rollback invariants
ranges1 = snap_ranges()
moves1 = snap_moves()
gl1 = gl_diff()
cr.execute(
    "SELECT md5(string_agg(id::text||':'||number_next::text,'|' ORDER BY id)) FROM ir_sequence"
)
seq1 = cr.fetchone()[0]
mail1 = mail_ncf_count()

if ranges1 == ranges0:
    ok("ranges_unchanged", True)
else:
    fail("ranges_unchanged", {"before": len(ranges0), "after": len(ranges1)})

if moves1 == moves0:
    ok("moves_unchanged", moves1)
else:
    fail("moves_unchanged", {"before": moves0, "after": moves1})

if seq1 == seq0:
    ok("sequences_unchanged", True)
else:
    fail("sequences_unchanged", False)

if abs(gl1 - gl0) < 0.0001:
    ok("gl_balanced", gl1)
else:
    fail("gl_balanced", {"before": gl0, "after": gl1})

if mail1 == mail0:
    ok("mail_ncf_unchanged", mail1)
else:
    fail("mail_ncf_unchanged", {"before": mail0, "after": mail1})

# Reports modules installed
mods = {
    m.name: m.state
    for m in env["ir.module.module"].search(
        [
            (
                "name",
                "in",
                [
                    "justech_l10n_do_reports",
                    "justech_l10n_do_ncf",
                    "justech_l10n_do_base",
                ],
            )
        ]
    )
}
ok("reports_modules", mods)

# Final open per-range alert activities should be 0 after legacy cleanup
open_range_alerts = len(range_alert_acts())
if open_range_alerts == 0:
    ok("open_range_alert_activities", 0)
else:
    fail("open_range_alert_activities", open_range_alerts)

out["version"] = env["ir.module.module"].search(
    [("name", "=", "justech_l10n_do_ncf")], limit=1
).latest_version
out["all_pass"] = out["all_pass"] and all(c.get("ok") for c in out["checks"].values())

print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
env.cr.rollback()
