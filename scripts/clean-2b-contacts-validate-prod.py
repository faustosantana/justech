#!/usr/bin/env python3
"""CLEAN-2B — Post-validation contacts cleanup hellenia_prod."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = os.environ.get("CLEAN2B_EVIDENCE", "/var/lib/odoo/clean-2b")
os.makedirs(OUT, exist_ok=True)

company = env.company
Partner = env["res.partner"].sudo().with_context(active_test=False)
Users = env["res.users"].sudo().with_context(active_test=False)
LicenseSvc = env["justech.license.service"]

preserve_ids = set()
for co in env["res.company"].sudo().search([]):
    if co.partner_id:
        preserve_ids.add(co.partner_id.id)
for user in Users.search([("active", "=", True)]):
    if user.partner_id:
        preserve_ids.add(user.partner_id.id)
for xmlid in ("base.partner_root", "base.public_partner", "base.partner_admin"):
    try:
        preserve_ids.add(env.ref(xmlid).id)
    except Exception:
        pass
for user in Users.search([("active", "=", False)]):
    if user.login in ("__system__", "public", "portaltemplate") and user.partner_id:
        preserve_ids.add(user.partner_id.id)

internal_user = Users.search(
    [("active", "=", True), ("share", "=", False), ("login", "!=", "admin")],
    limit=1,
) or Users.search([("login", "=", "admin")], limit=1)
visible = env["res.partner"].with_user(internal_user).search([])
visible_non_preserved = visible.filtered(lambda p: p.id not in preserve_ids)

lic = LicenseSvc._get_active_license_for_company(company)

report = {
    "phase": "CLEAN-2B-VALIDATE",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "PASS",
    "checks": {},
    "counts": {
        "partners_total": Partner.search_count([]),
        "customers": Partner.search_count([("customer_rank", ">", 0)]),
        "suppliers": Partner.search_count([("supplier_rank", ">", 0)]),
        "commercial_rank": Partner.search_count(
            ["|", ("customer_rank", ">", 0), ("supplier_rank", ">", 0)]
        ),
        "visible_for_normal_user": len(visible),
        "visible_non_preserved": len(visible_non_preserved),
        "visible_non_preserved_names": visible_non_preserved.mapped("name"),
        "preserved_partners": len(preserve_ids),
    },
    "hellenia": {
        "company_name": company.name,
        "company_id": company.id,
        "company_exists": bool(company.exists()),
    },
    "license": {
        "active": bool(lic and lic.state == "active"),
        "id": lic.id if lic else False,
        "state": lic.state if lic else False,
        "plan": lic.tier if lic else False,
    },
    "users_active_internal": Users.search_count(
        [("active", "=", True), ("share", "=", False)]
    ),
    "errors": [],
}


def check(name, ok, detail=""):
    report["checks"][name] = {"status": "PASS" if ok else "FAIL", "detail": detail}
    if not ok:
        report["status"] = "FAIL"
        report["errors"].append(f"{name}: {detail}")


check("customers_zero", report["counts"]["customers"] == 0, report["counts"]["customers"])
check("suppliers_zero", report["counts"]["suppliers"] == 0, report["counts"]["suppliers"])
check(
    "commercial_contacts_zero",
    report["counts"]["commercial_rank"] == 0,
    report["counts"]["commercial_rank"],
)
check(
    "visible_non_preserved_zero",
    report["counts"]["visible_non_preserved"] == 0,
    report["counts"]["visible_non_preserved_names"],
)
check("hellenia_company_ok", report["hellenia"]["company_exists"], company.name)
check("license_active", report["license"]["active"], report["license"])
check("users_ok", report["users_active_internal"] >= 1, report["users_active_internal"])

with open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False, default=str)

print("CLEAN2B_VALIDATE:" + json.dumps(report, ensure_ascii=False, default=str))
