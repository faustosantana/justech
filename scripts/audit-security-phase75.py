#!/usr/bin/env python3
"""Fase 7.5 — Auditoría seguridad y permisos (odoo shell)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

report = {
    "database": env.cr.dbname,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "users": {},
    "groups": {},
    "justech": {},
    "system": {},
    "cron": {},
    "risks": [],
}

# --- Users ---
Users = env["res.users"].with_context(active_test=False)
active_users = Users.search([("share", "=", False)])
report["users"]["active_internal"] = [
    {
        "id": u.id,
        "login": u.login,
        "name": u.name,
        "email": u.email or "",
        "active": u.active,
        "groups_count": len(u.group_ids),
        "tz": u.tz,
        "lang": u.lang,
    }
    for u in active_users
]
report["users"]["inactive_internal"] = Users.search_count(
    [("share", "=", False), ("active", "=", False)]
)
logins = [u.login for u in active_users]
report["users"]["duplicate_logins"] = [
    lg for lg in set(logins) if logins.count(lg) > 1
]
report["users"]["admin"] = {
    "login": env.ref("base.user_admin").login,
    "active": env.ref("base.user_admin").active,
}
report["users"]["justech_it"] = Users.search([("login", "=", "it@justech.do")], limit=1)
report["users"]["justech_it_exists"] = bool(report["users"]["justech_it"])
if report["users"]["justech_it"]:
    it = report["users"]["justech_it"]
    report["users"]["justech_it_detail"] = {
        "login": it.login,
        "active": it.active,
        "groups": sorted(it.group_ids.mapped("full_name") or it.group_ids.mapped("name")),
        "lang": it.lang,
        "tz": it.tz,
    }
    report["users"].pop("justech_it")

# --- Groups taxonomy ---
Group = env["res.groups"]
all_groups = Group.search([])
std, ent, justech_g, custom = [], [], [], []


def _group_category(g):
    if hasattr(g, "privilege_id") and g.privilege_id:
        return g.privilege_id.name or ""
    if hasattr(g, "category_id") and g.category_id:
        return g.category_id.name or ""
    return ""


def _group_xml(g):
    try:
        data = g.get_external_id()
        return data.get(g.id, "") if data else ""
    except Exception:
        return ""


for g in all_groups:
    cat = _group_category(g)
    xml = _group_xml(g)
    entry = {
        "id": g.id,
        "name": g.full_name or g.name,
        "xml_id": xml,
        "users": len(g.user_ids),
        "category": cat,
    }
    if "justech" in (xml or "").lower() or "hellenia" in (g.name or "").lower():
        justech_g.append(entry)
    elif any(
        x in (xml or "")
        for x in (
            "web_enterprise",
            "account_accountant",
            "mail_enterprise",
            "spreadsheet_edition",
            "stock_enterprise",
            "sale_enterprise",
            "digest_enterprise",
        )
    ) or "Enterprise" in cat:
        ent.append(entry)
    elif cat:
        std.append(entry)
    else:
        custom.append(entry)

report["groups"] = {
    "total": len(all_groups),
    "standard_count": len(std),
    "enterprise_count": len(ent),
    "justech_count": len(justech_g),
    "standard_sample": sorted(std, key=lambda x: x["name"])[:40],
    "enterprise": sorted(ent, key=lambda x: x["name"]),
    "justech": sorted(justech_g, key=lambda x: x["name"]),
}

# --- Justech ACL & rules ---
IrRule = env["ir.rule"]
IrAccess = env["ir.model.access"]
justech_models = env["ir.model"].search([("model", "like", "justech.%")])
report["justech"]["models"] = justech_models.mapped("model")
report["justech"]["acl"] = [
    {
        "name": a.name,
        "model": a.model_id.model,
        "group": a.group_id.full_name if a.group_id else "global",
        "perm_read": a.perm_read,
        "perm_write": a.perm_write,
        "perm_create": a.perm_create,
        "perm_unlink": a.perm_unlink,
    }
    for a in IrAccess.search([("model_id.model", "like", "justech.%")])
]
report["justech"]["rules"] = [
    {
        "name": r.name,
        "model": r.model_id.model,
        "domain": r.domain_force,
        "global_rule": getattr(r, "global", False) or getattr(r, "global_", False),
    }
    for r in IrRule.search([("model_id.model", "like", "justech.%")])
]

# Multi-company rules count
report["justech"]["multi_company_rules_total"] = IrRule.search_count(
    [("name", "ilike", "multi-company")]
)

# --- System parameters ---
ICP = env["ir.config_parameter"].sudo()
keys = [
    "web.base.url",
    "database.is_neutralized",
    "database.enterprise_code",
    "mail.catchall.domain",
    "mail.default.from",
    "mail.bounce.alias",
    "mail.catchall.alias",
]
report["system"]["parameters"] = {k: ICP.get_param(k) for k in keys}

company = env.company
report["system"]["company"] = {
    "name": company.name,
    "vat": company.partner_id.vat,
    "country": company.country_id.code,
    "currency": company.currency_id.name,
    "email": company.email or "",
    "phone": company.phone or "",
    "logo_set": bool(company.logo),
}
report["system"]["neutralized"] = ICP.get_param("database.is_neutralized") == "True"

# SMTP
mail_server = env["ir.mail_server"].search([])
report["system"]["mail_servers"] = [
    {
        "name": m.name,
        "smtp_host": m.smtp_host or "",
        "active": getattr(m, "active", True),
    }
    for m in mail_server
]

# Instance name / language
report["system"]["default_lang"] = env.ref("base.lang_es_DO", raise_if_not_found=False)
report["system"]["es_do_active"] = bool(
    env["res.lang"].search([("code", "=", "es_DO"), ("active", "=", True)], limit=1)
)

# --- Cron critical ---
critical_names = [
    "Mail",
    "Notification",
    "Payment",
    "Account",
    "Digest",
    "Snailmail",
    "SMS",
]
crons = env["ir.cron"].search([("active", "=", True)])
report["cron"]["active_count"] = len(crons)
report["cron"]["critical"] = [
    {
        "name": c.name,
        "model": c.model_id.model,
        "interval": f"{c.interval_number} {c.interval_type}",
        "nextcall": str(c.nextcall),
    }
    for c in crons
    if any(k.lower() in (c.name or "").lower() for k in critical_names)
][:25]

# Risks
if report["users"]["duplicate_logins"]:
    report["risks"].append("duplicate_active_logins")
if not report["users"].get("justech_it_exists"):
    report["risks"].append("justech_it_missing")
admin = env.ref("base.user_admin")
if not admin.active:
    report["risks"].append("admin_inactive")
if len([u for u in report["users"]["active_internal"] if u["login"] != "admin"]) == 0:
    if not report["users"].get("justech_it_exists"):
        report["risks"].append("only_admin_operational")
if not report["system"]["mail_servers"] and not report["system"]["neutralized"]:
    report["risks"].append("no_smtp_configured")

print("SECURITY_AUDIT:" + json.dumps(report, indent=2, ensure_ascii=False, default=str))
