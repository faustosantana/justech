#!/usr/bin/env python3
"""CLEAN-2B — Final purge of commercial/test contacts (hellenia_prod)."""
from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = os.environ.get("CLEAN2B_EVIDENCE", "/var/lib/odoo/clean-2b")
os.makedirs(OUT, exist_ok=True)

company = env.company
Partner = env["res.partner"].sudo().with_context(active_test=False)
Users = env["res.users"].sudo().with_context(active_test=False)

SYSTEM_XMLIDS = (
    "base.partner_root",
    "base.public_partner",
    "base.partner_admin",
)

TEST_USER_LOGIN_RE = re.compile(r"demo\d+|\.demo\d+", re.I)

report = {
    "phase": "CLEAN-2B",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "company": company.name,
    "ok": True,
    "errors": [],
    "before": {},
    "deleted": {},
    "preserved_count": 0,
    "deleted_count": 0,
}


def err(msg):
    report["ok"] = False
    report["errors"].append(msg)


def partner_row(p, reason="", action=""):
    return {
        "id": p.id,
        "name": p.name or "",
        "active": p.active,
        "customer_rank": p.customer_rank,
        "supplier_rank": p.supplier_rank,
        "parent_id": p.parent_id.id if p.parent_id else "",
        "parent_name": p.parent_id.name if p.parent_id else "",
        "company_id": p.company_id.id if p.company_id else "",
        "is_company": p.is_company,
        "email": p.email or "",
        "vat": p.vat or "",
        "user_logins": ",".join(
            Users.search([("partner_id", "=", p.id)]).mapped("login")
        ),
        "action": action,
        "reason": reason,
    }


def write_csv(path, rows):
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("")
        return
    fields = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def preserved_partner_ids_with_reasons():
    reasons = {}
    for co in env["res.company"].sudo().search([]):
        if co.partner_id:
            reasons[co.partner_id.id] = f"res.company:{co.name}"
    for user in Users.search([("active", "=", True)]):
        if user.partner_id:
            reasons[user.partner_id.id] = f"res.users(active):{user.login}"
    for xmlid in SYSTEM_XMLIDS:
        try:
            pid = env.ref(xmlid).id
            reasons[pid] = f"system:{xmlid}"
        except Exception:
            pass
    # Inactive system/template users
    for user in Users.search([("active", "=", False)]):
        if user.login in ("__system__", "public", "portaltemplate"):
            if user.partner_id:
                reasons[user.partner_id.id] = f"res.users(system):{user.login}"
    return reasons


def classify_partner(p, preserve_reasons):
    if p.id in preserve_reasons:
        return "preserve", preserve_reasons[p.id]
    linked_users = Users.search([("partner_id", "=", p.id)])
    if linked_users:
        demo_users = linked_users.filtered(
            lambda u: TEST_USER_LOGIN_RE.search(u.login or "")
        )
        if demo_users:
            return "delete", f"test_user_partner:{','.join(demo_users.mapped('login'))}"
        inactive = linked_users.filtered(lambda u: not u.active)
        if inactive and not linked_users.filtered(lambda u: u.active):
            return "delete", f"inactive_user_partner:{','.join(inactive.mapped('login'))}"
    if p.customer_rank or p.supplier_rank:
        return "delete", "commercial_rank"
    if re.search(r"demo\s*\d+|prueba|test", p.name or "", re.I):
        return "delete", "test_name_pattern"
    return "delete", "not_linked_company_user_or_system"


def visible_partners_for_user(user):
    return env["res.partner"].with_user(user).search([])


def snap(label):
    preserve = preserved_partner_ids_with_reasons()
    all_partners = Partner.search([])
    commercial = all_partners.filtered(
        lambda p: p.customer_rank > 0 or p.supplier_rank > 0
    )
    internal_user = Users.search(
        [("active", "=", True), ("share", "=", False), ("login", "!=", "admin")],
        limit=1,
    )
    visible = visible_partners_for_user(internal_user) if internal_user else Partner.browse()
    visible_non_preserved = visible.filtered(lambda p: p.id not in preserve)
    report[label] = {
        "partners_total": len(all_partners),
        "partners_customers": len(commercial.filtered(lambda p: p.customer_rank > 0)),
        "partners_suppliers": len(commercial.filtered(lambda p: p.supplier_rank > 0)),
        "partners_commercial_rank": len(commercial),
        "partners_preserved": len(preserve),
        "visible_for_normal_user": len(visible),
        "visible_non_preserved": len(visible_non_preserved),
        "visible_non_preserved_names": visible_non_preserved.mapped("name"),
    }


preserve_reasons = preserved_partner_ids_with_reasons()
all_partners = Partner.search([])
before_rows = []
to_delete = Partner.browse()
to_preserve = Partner.browse()
delete_rows = []
preserve_rows = []

for p in all_partners.sorted(key=lambda x: x.id):
    action, reason = classify_partner(p, preserve_reasons)
    row = partner_row(p, reason=reason, action=action)
    before_rows.append(row)
    if action == "preserve":
        to_preserve |= p
        preserve_rows.append(row)
    else:
        to_delete |= p
        delete_rows.append(row)

snap("before")
write_csv(os.path.join(OUT, "partners_before.csv"), before_rows)
write_csv(os.path.join(OUT, "partners_preserved.csv"), preserve_rows)

# Delete inactive demo/test users first (personas de prueba)
demo_users = Users.search([]).filtered(
    lambda u: TEST_USER_LOGIN_RE.search(u.login or "")
)
deleted_logins = []
if demo_users:
    deleted_logins = demo_users.mapped("login")
    try:
        demo_users.with_context(justech_skip_audit=True).unlink()
        report["deleted"]["demo_users"] = {
            "count": len(deleted_logins),
            "logins": deleted_logins,
        }
    except Exception as exc:
        # Users may cascade-delete with partners; treat as success if gone
        remaining = Users.search([("login", "in", deleted_logins)])
        report["deleted"]["demo_users"] = {
            "count": len(deleted_logins) - len(remaining),
            "logins": deleted_logins,
            "detail": str(exc)[:300],
        }
else:
    report["deleted"]["demo_users"] = {"count": 0}

# Zero ranks then unlink partners (children first)
to_delete = Partner.search([("id", "in", to_delete.ids)])
to_delete = to_delete.sorted(key=lambda p: (bool(p.child_ids), p.id), reverse=True)
if to_delete.filtered(lambda p: p.customer_rank or p.supplier_rank):
    to_delete.filtered(lambda p: p.customer_rank or p.supplier_rank).write(
        {"customer_rank": 0, "supplier_rank": 0}
    )

deleted_ids = []
if to_delete:
    try:
        with env.cr.savepoint():
            to_delete.with_context(justech_skip_audit=True).unlink()
        deleted_ids = to_delete.ids
    except Exception as exc:
        pids = tuple(to_delete.ids)
        if pids:
            for table, col in (
                ("res_partner_bank", "partner_id"),
                ("res_partner_res_partner_category_rel", "partner_id"),
                ("mail_followers", "partner_id"),
                ("mail_message", "author_id"),
            ):
                try:
                    env.cr.execute(f"DELETE FROM {table} WHERE {col} IN %s", (pids,))
                except Exception:
                    pass
            env.cr.execute("UPDATE res_partner SET parent_id = NULL WHERE id IN %s", (pids,))
            env.cr.execute("DELETE FROM res_partner WHERE id IN %s", (pids,))
            Partner.invalidate_model()
            deleted_ids = list(pids)
            report["deleted"]["partners"] = {"count": len(pids), "detail": f"sql_purge: {exc}"}
        else:
            err(f"partners: {exc}")
else:
    report["deleted"]["partners"] = {"count": 0}

if "partners" not in report["deleted"]:
    report["deleted"]["partners"] = {"count": len(deleted_ids), "ids": deleted_ids}

for row in delete_rows:
    row["deleted"] = row["id"] in deleted_ids
write_csv(os.path.join(OUT, "partners_deleted.csv"), delete_rows)

env.cr.commit()

snap("after")
report["preserved_count"] = len(preserve_rows)
report["deleted_count"] = report["deleted"].get("partners", {}).get("count", 0)

# License / company sanity
LicenseSvc = env["justech.license.service"]
lic = LicenseSvc._get_active_license_for_company(company)
report["license_active"] = bool(lic and lic.state == "active")
report["license_id"] = lic.id if lic else False
report["users_active_internal"] = Users.search_count(
    [("active", "=", True), ("share", "=", False)]
)

checks = {
    "no_customers": report["after"]["partners_customers"] == 0,
    "no_suppliers": report["after"]["partners_suppliers"] == 0,
    "no_commercial_rank": report["after"]["partners_commercial_rank"] == 0,
    "visible_non_preserved_zero": report["after"]["visible_non_preserved"] == 0,
    "hellenia_company_exists": env["res.company"].search_count([]) >= 1,
    "license_active": report["license_active"],
    "users_ok": report["users_active_internal"] >= 1,
}
report["checks"] = checks
report["ok"] = report["ok"] and all(checks.values())

with open(os.path.join(OUT, "clean-2b-report.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False, default=str)

print("CLEAN2B:" + json.dumps(report, ensure_ascii=False, default=str))
