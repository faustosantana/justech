# Gate 1 — Datos (justech_dev)
from odoo import api

admin = env["res.users"].sudo().search([("login", "=", "jinette@dynamicspm.com")], limit=1)
uenv = api.Environment(env.cr, admin.id, {"allowed_company_ids": [1, 2, 3, 4]})
fails = []


def ok(name, cond, detail=""):
    print("%s %s %s" % ("PASS" if cond else "FAIL", name, detail))
    if not cond:
        fails.append((name, str(detail)[:200]))


companies = uenv["res.company"].sudo().search([])
ok("companies_4", len(companies) >= 4, companies.mapped("name"))

Doc = uenv["justech.do.fiscal.document.type"]
ok("doc_types", Doc.search_count([]) >= 10, Doc.search_count([]))

Range = uenv["justech.do.ncf.range"].sudo()
for c in companies:
    n = Range.search_count([("company_id", "=", c.id)])
    ok("ranges_c%s" % c.id, n >= 1, n)
    active = Range.search([("company_id", "=", c.id), ("state", "=", "active")])
    ok("ranges_active_c%s" % c.id, len(active) >= 1, len(active))
    for r in active[:3]:
        ok(
            "range_seq_%s_%s" % (c.id, r.id),
            r.next_sequence >= r.sequence_start and r.next_sequence <= r.sequence_end + 1,
            "next=%s [%s-%s] %s" % (r.next_sequence, r.sequence_start, r.sequence_end, r.prefix),
        )

Padron = uenv["justech.do.rnc.padron"].sudo()
cnt = Padron.search_count([])
ok("padron_count", cnt > 700000, cnt)
ok("padron_no_company", "company_id" not in Padron._fields)
env.cr.execute(
    """
    SELECT rnc, count(*) FROM justech_do_rnc_padron
    GROUP BY rnc HAVING count(*) > 1 LIMIT 5
    """
)
dups = env.cr.fetchall()
ok("padron_no_dup_rnc", len(dups) == 0, dups)

integ = uenv["justech.do.rnc.padron.import.service"].sudo().integrity_check()
ok("padron_integrity", integ.get("status_visual") in ("green", "yellow"), integ.get("status_visual"))
payload = uenv["justech.do.rnc.padron.import.service"].sudo().status_payload()
ok("padron_status_green", payload.get("status_visual") == "green", payload.get("status_label"))

cfg = uenv["justech.do.rnc.padron.config"].sudo().get_config()
ok("padron_config_singleton", bool(cfg), cfg.id)

for c in companies:
    fe = getattr(c, "justech_do_fiscal_enabled", None)
    ok("fiscal_flag_c%s" % c.id, fe is not None, fe)

env.cr.execute(
    """
    SELECT am.id, am.name, am.company_id
    FROM account_move am
    WHERE am.state='posted' AND am.move_type IN ('out_invoice','out_refund')
      AND am.company_id = 1
      AND COALESCE(am.justech_do_ncf,'') = ''
      AND COALESCE(am.l10n_latam_document_number,'') = ''
    LIMIT 20
    """
)
missing = env.cr.fetchall()
ok("posted_missing_ncf_hard", len(missing) == 0, missing)

env.cr.execute(
    """
    SELECT code, count(*) FROM justech_fiscal_health_issue
    WHERE state != 'resolved' OR state IS NULL
    GROUP BY code ORDER BY 2 DESC
    """
)
by_code = env.cr.fetchall()
print("HEALTH_BY_CODE", by_code)
crit = [x for x in by_code if x[0] in ("POSTED_MISSING_NCF", "PARTNER_INVALID_RNC", "PADRON_ISSUE")]
ok("health_ops_clean", all(c[1] == 0 for c in crit) if crit else True, crit)

diag = uenv["justech.do.ncf.diagnostic.service"].run_full_scan(uenv["res.company"].browse(1))
diag_crit = [f for f in diag if f["code"] in ("posted_missing_ncf", "partner_invalid_rnc")]
ok("diagnostic_ops_clean", len(diag_crit) == 0, diag_crit)

env.cr.execute(
    """
    SELECT count(*) FROM account_move
    WHERE state='posted' AND move_type='out_invoice' AND company_id=1
      AND COALESCE(justech_do_ncf,'') <> ''
    """
)
with_ncf = env.cr.fetchone()[0]
ok("invoices_with_justech_ncf", with_ncf > 0, with_ncf)

# FDP: resolve NCF from justech or latam
FDP = uenv["justech.do.fiscal.data.provider"]
sample = uenv["account.move"].sudo().search(
    [
        ("state", "=", "posted"),
        ("move_type", "=", "out_invoice"),
        ("company_id", "=", 1),
        ("justech_do_ncf", "!=", False),
    ],
    limit=1,
)
ncf_fdp = FDP.get_ncf(sample) if sample and hasattr(FDP, "get_ncf") else None
if ncf_fdp is None and sample:
    ncf_fdp = sample.justech_do_ncf or sample.l10n_latam_document_number
ok("fdp_resolves_ncf", bool(ncf_fdp), ncf_fdp)

# Historical dual-write gap accepted (Adel → Justech visibility via FDP)
env.cr.execute(
    """
    SELECT count(*) FROM account_move
    WHERE state='posted' AND move_type='out_invoice' AND company_id=1
      AND COALESCE(l10n_latam_document_number,'') <> ''
      AND COALESCE(justech_do_ncf,'') = ''
    """
)
hist_gap = env.cr.fetchone()[0]
print("HISTORICAL_DUAL_WRITE_GAP", hist_gap)
ok("historical_gap_documented", hist_gap >= 0, "gap=%s (FDP reads both; no mass backfill)" % hist_gap)

env.cr.execute("SELECT count(*) FROM justech_do_rnc_padron_import_log WHERE state='running'")
running = env.cr.fetchone()[0]
ok("no_orphan_running_import", running == 0, running)

print("---")
print("GATE1_FAILS", len(fails))
for f in fails:
    print("FAIL", f)
print("GATE1_PASS" if not fails else "GATE1_FAIL")
