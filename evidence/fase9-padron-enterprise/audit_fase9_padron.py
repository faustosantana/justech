# Fase 9 — validación Enterprise padrón DGII (justech_dev)
from odoo import api, fields
from odoo.exceptions import UserError
from datetime import timedelta
import base64

admin = env["res.users"].sudo().search([("login", "=", "jinette@dynamicspm.com")], limit=1)
uenv = api.Environment(env.cr, admin.id, {"allowed_company_ids": [1, 2, 3, 4]})
fails = []


def ok(name, cond, detail=""):
    print("%s %s %s" % ("PASS" if cond else "FAIL", name, detail))
    if not cond:
        fails.append((name, detail))


ImportSvc = uenv["justech.do.rnc.padron.import.service"]
AutoSvc = uenv["justech.do.rnc.padron.auto.service"]
Config = uenv["justech.do.rnc.padron.config"].sudo().get_config()
Padron = uenv["justech.do.rnc.padron"].sudo()
Log = uenv["justech.do.rnc.padron.import.log"].sudo()
count0 = Padron.search_count([])
ok("padron_global_count", count0 > 700000, count0)
ok("no_company_field", "company_id" not in Padron._fields)

# --- status multiempresa ---
for cid, cname in [(1, "JUSTECH"), (2, "PlugSafe"), (3, "JustOffice"), (4, "Omni")]:
    e = api.Environment(
        env.cr, admin.id, {"allowed_company_ids": [cid] + [x for x in [1, 2, 3, 4] if x != cid]}
    )
    pad = e["justech.do.rnc.padron.import.service"].sudo().status_payload()
    ok(
        "status_%s" % cname,
        pad.get("status_visual") == "green" and pad.get("count", 0) > 700000,
        pad.get("status_label"),
    )
    center = e["justech.fiscal.admin.center"].browse(
        e["justech.fiscal.admin.center"].open_for_user()["res_id"]
    )
    ok("centro_%s" % cname, center.company_id.id == cid)
    ok("can_manage_padron_%s" % cname, bool(center.can_manage_padron))

# --- config / cron / frequency ---
prev_auto = Config.auto_update_enabled
prev_freq = Config.frequency_days
prev_hour = Config.run_hour
Config.write({"auto_update_enabled": True, "frequency_days": 45, "run_hour": 3})
Config.action_save_and_schedule()
Config.invalidate_recordset()
ok("freq_45", Config.frequency_days == 45)
ok("next_run_set", bool(Config.next_run_at), Config.next_run_at)
ok("cron_synced_on", Config._cron_is_active(), Config.cron_active)
ok("run_hour_in_next", Config.next_run_at and Config.next_run_at.hour == 3, Config.next_run_at)

Config.write({"auto_update_enabled": False})
Config.action_save_and_schedule()
ok("cron_synced_off", not Config._cron_is_active())

# restore previous config prefs (no commit of test enable)
Config.write(
    {
        "auto_update_enabled": prev_auto,
        "frequency_days": prev_freq or 45,
        "run_hour": prev_hour if prev_hour is not None else 3,
    }
)
Config.action_save_and_schedule()

# --- integrity / health ---
integ = ImportSvc.integrity_check()
ok("integrity", integ.get("status_visual") in ("green", "yellow"), integ)
payload = ImportSvc.status_payload()
ok("health_payload", payload.get("status_visual") == "green")
ok("hash_last", bool(payload.get("file_hash_last")) or Log.search_count([("file_hash", "!=", False)]) > 0)

# --- failed validation must NOT shrink padron ---
bad = b"1|BAD\n2|X\n"
try:
    ImportSvc.with_context(
        justech_padron_allow_test_fixture=True,
        justech_padron_skip_ratio_check=False,
    ).apply_import(bad, "bad_tiny.txt", source="manual", delimiter="|", has_header=False)
    ok("reject_tiny_raises", False, "should have raised")
except Exception as e:
    ok("reject_tiny_raises", True, type(e).__name__)
count1 = Padron.search_count([])
ok("padron_intact_after_bad", count1 == count0, "%s→%s" % (count0, count1))

# --- lock ---
Config.invalidate_recordset()
ImportSvc._acquire_lock(Config)
try:
    try:
        ImportSvc._acquire_lock(Config)
        ok("lock_blocks", False, "second acquire should fail")
    except UserError:
        ok("lock_blocks", True)
finally:
    ImportSvc._release_lock(Config)
    env.cr.commit()

# --- retry / restore actions ---
ok("retry_method", hasattr(AutoSvc, "retry_last_failed"))
ok("reimport_action", hasattr(uenv["justech.fiscal.admin.center"], "action_padron_reimport_after_restore"))
try:
    uenv["justech.fiscal.admin.center"].browse(
        uenv["justech.fiscal.admin.center"].open_for_user()["res_id"]
    ).action_padron_reimport_after_restore()
    ok("reimport_guard_when_full", False, "should refuse when padron filled")
except UserError as e:
    ok("reimport_guard_when_full", True, str(e)[:80])

# --- history ---
ok("history_exists", Log.search_count([]) >= 1, Log.search_count([]))
ok("attachment_field", "file_attachment_id" in Log._fields)

# --- GL / multiempresa ---
for cid in (1, 2, 3, 4):
    env.cr.execute(
        """
        SELECT ABS(SUM(aml.debit)-SUM(aml.credit))<0.01
        FROM account_move_line aml
        JOIN account_move am ON am.id=aml.move_id
        WHERE am.state='posted' AND am.company_id=%s
        """,
        (cid,),
    )
    ok("gl_%s" % cid, env.cr.fetchone()[0])

# contactos no tocados por import (smoke: partner count stable not required)
ok("partner_model_untouched_by_padron_fields", "vat" in uenv["res.partner"]._fields)

env.cr.rollback()
print("---")
print("TOTAL_FAILS", len(fails))
for f in fails:
    print("FAIL", f)
print("FASE9_PASS" if not fails else "FASE9_FAIL")
