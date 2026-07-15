# Run inside: odoo shell -d justech_dev < thisfile
# Does not touch Production.
from datetime import date
import urllib.request

Ass = env["justech.managed.service.assessment"]
results = []


def ok(name, cond, detail=""):
    results.append((name, bool(cond), str(detail)))
    print(("PASS" if cond else "FAIL"), name, detail)


ok("db_is_justech_dev", env.cr.dbname == "justech_dev", env.cr.dbname)
mod = env["ir.module.module"].search(
    [("name", "=", "justech_managed_services"), ("state", "=", "installed")], limit=1
)
ok("module_installed", bool(mod), mod.latest_version if mod else "")
ok(
    "menu_exists",
    bool(
        env.ref(
            "justech_managed_services.menu_justech_managed_services_root",
            raise_if_not_found=False,
        )
    ),
)

partner = env["res.partner"].search([("name", "ilike", "credicefi")], limit=1)
if not partner:
    partner = env["res.partner"].create(
        {
            "name": "Credicefi (DEMO DEV)",
            "is_company": True,
            "email": "demo.credicefi@example.invalid",
        }
    )
ok("partner_credicefi", bool(partner), partner.name)

a = Ass.create(
    {
        "title": "Levantamiento inicial de soporte técnico y mesa de ayuda",
        "partner_id": partner.id,
        "email": "demo.credicefi@example.invalid",
        "form_data": {
            "support_levels": ["nivel_1", "nivel_2", "nivel_3"],
            "outsource_services": [
                "soporte_remoto",
                "soporte_presencial",
                "admin_usuarios",
                "admin_servidores",
            ],
            "coverage_schedule": "laboral",
            "service_modality": "recomendacion_justech",
        },
    }
)
ok("create_assessment", bool(a.id), a.name)
ok("sequence_format", a.name.startswith("LEV-") and str(date.today().year) in a.name, a.name)

a.action_generate_link()
ok("token_generated", bool(a.access_token) and len(a.access_token) >= 32, len(a.access_token or 0))
ok("public_url", "/servicios/levantamiento/" in (a.public_url or ""), a.public_url)
ok("state_sent", a.state == "sent", a.state)

rec, st = Ass.public_get_by_token(a.access_token)
ok("token_ok", st == "ok" and rec.id == a.id, st)
_, st_bad = Ass.public_get_by_token("invalid-token-xxx")
ok("invalid_token", st_bad == "invalid", st_bad)

deadline = a.date_deadline
a.write({"date_deadline": "2000-01-01"})
_, st_exp = Ass.public_get_by_token(a.access_token)
ok("expired_token", st_exp == "expired", st_exp)
a.write({"date_deadline": deadline})

a.write({"link_active": False})
_, st_in = Ass.public_get_by_token(a.access_token)
ok("inactive_token", st_in == "inactive", st_in)
a.write({"link_active": True})

a.public_save_partial(
    {
        "org_company_name": "Credicefi UAT",
        "employee_count_range": "51_100",
        "support_levels": ["nivel_1", "nivel_2", "nivel_3"],
    }
)
a.invalidate_recordset()
ok("partial_state", a.state == "in_progress", a.state)
ok("completion_gt0", a.completion_percent > 0, a.completion_percent)
ok("activity_dates", bool(a.date_first_activity and a.date_last_activity))
ok(
    "partner_not_auto_updated",
    "Credicefi UAT" not in (a.partner_id.name or ""),
    a.partner_id.name,
)

vals = a.get_form_display_values()
ok("continue_values", vals.get("org_company_name") == "Credicefi UAT")

a.public_submit(
    {
        "org_company_name": "Credicefi UAT",
        "employee_count_range": "51_100",
        "support_levels": ["nivel_1", "nivel_2", "nivel_3"],
        "acceptance_confirmed": True,
        "completed_by_name": "Ana Prueba",
        "completed_by_job": "Gerente TI",
    }
)
a.invalidate_recordset()
ok("submit_done", a.state == "done", a.state)
ok("date_done", bool(a.date_done))
ok("acceptance", a.acceptance_confirmed and a.completed_by_name == "Ana Prueba")
ok("link_off_after_submit", not a.link_active)
_, st_sub = Ass.public_get_by_token(a.access_token)
ok("submitted_token", st_sub == "submitted", st_sub)

blocked = False
try:
    a.public_save_partial({"org_company_name": "X"})
except Exception:
    blocked = True
ok("block_after_submit", blocked)

a.action_reopen_public()
a.invalidate_recordset()
ok("reopen", a.link_active and a.state == "in_progress", a.state)

a.action_cancel()
_, st_c = Ass.public_get_by_token(a.access_token)
ok("cancelled_token", st_c == "cancelled", st_c)

a2 = Ass.create(
    {
        "title": "UAT CRM PDF",
        "partner_id": partner.id,
        "email": "uat@example.invalid",
    }
)
a2.action_generate_link()
a2.action_create_opportunity()
ok("crm_created", bool(a2.opportunity_id), a2.opportunity_id.name if a2.opportunity_id else "")
opp_id = a2.opportunity_id.id
a2.action_create_opportunity()
ok("crm_no_dup", a2.opportunity_id.id == opp_id)

report = env.ref(
    "justech_managed_services.action_report_managed_service_assessment",
    raise_if_not_found=False,
)
ok("report_exists", bool(report))
if report:
    content, rtype = env["ir.actions.report"]._render_qweb_pdf(
        report.report_name, res_ids=a2.ids
    )
    ok("pdf_generated", bool(content) and rtype == "pdf", f"bytes={len(content)}")

partner.invalidate_recordset()
ok(
    "partner_smart_count",
    partner.justech_ms_assessment_count >= 1,
    partner.justech_ms_assessment_count,
)
lead = a2.opportunity_id
lead.invalidate_recordset()
ok(
    "lead_smart_count",
    lead.justech_ms_assessment_count >= 1,
    lead.justech_ms_assessment_count,
)

ok(
    "group_user",
    bool(env.ref("justech_managed_services.group_ms_user", raise_if_not_found=False)),
)
ok(
    "group_manager",
    bool(
        env.ref(
            "justech_managed_services.group_ms_manager", raise_if_not_found=False
        )
    ),
)
ok(
    "mail_template",
    bool(
        env.ref(
            "justech_managed_services.mail_template_assessment_invite",
            raise_if_not_found=False,
        )
    ),
)

# permissions smoke: bare user without groups
Users = env["res.users"].sudo()
bare = Users.create(
    {
        "name": "UAT MS Bare",
        "login": "uat_ms_bare_%s" % env.cr.dbname,
        "group_ids": [(6, 0, [env.ref("base.group_user").id])],
    }
)
can_read = Ass.with_user(bare).has_access("read")
ok("bare_user_no_read", not can_read)

# HTTP
token = a2.access_token
for label, url, expect in [
    (
        "http_form_200",
        f"http://172.19.0.1:8069/servicios/levantamiento/{token}",
        "Levantamiento",
    ),
    (
        "http_invalid_corporate",
        "http://172.19.0.1:8069/servicios/levantamiento/bad-token-xyz",
        "Enlace no disponible",
    ),
]:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            body = resp.read().decode("utf-8", "ignore")
            ok(label, resp.status == 200 and expect in body, resp.status)
            if label == "http_form_200":
                ok(
                    "http_no_internal",
                    "Observaciones internas" not in body
                    and "o_Chatter" not in body,
                )
    except Exception as e:
        ok(label, False, e)

ok(
    "sale_untouched_module",
    bool(
        env["ir.module.module"].search(
            [("name", "=", "sale"), ("state", "=", "installed")], limit=1
        )
    ),
)

fails = [r for r in results if not r[1]]
print("SUMMARY pass=%s fail=%s total=%s" % (len(results) - len(fails), len(fails), len(results)))
for name, _, detail in fails:
    print("FAIL_DETAIL", name, detail)
print("PUBLIC_URL", a2.public_url)
print("ASSESSMENT_ID", a2.id)
