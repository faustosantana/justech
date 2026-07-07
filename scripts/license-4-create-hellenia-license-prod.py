#!/usr/bin/env python3
"""Create active Hellenia license with LICENSE-4 real catalog (5 modules only)."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = os.environ.get(
    "LICENSE4_CREATE_EVIDENCE",
    "/var/lib/odoo/license-4-hellenia-create.json",
)

LICENSE4_PRODUCT_CODES = [
    "contabilidad_rd",
    "reportes_corporativos",
    "ux_fiscal",
    "multicurrency_commercial",
    "global_audit",
]

FORBIDDEN_CODES = {"control_justech_interno", "punto_de_venta"}

report = {
    "phase": "LICENSE-4-HELLENIA",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "checks": {},
    "errors": [],
    "license_id": False,
    "product_codes": LICENSE4_PRODUCT_CODES,
}

company = env.ref("base.main_company")
LicenseSvc = env["justech.license.service"]
AccessSvc = env["justech.admin.access.service"]
internal = LicenseSvc._sudo_internal()
Product = internal["justech.commercial.product"]
License = internal["justech.license"]


def check(name, ok, detail=""):
    report["checks"][name] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:800]}
    if not ok:
        report["errors"].append(f"{name}: {detail}")


# Ensure commercial products exist
missing = []
for code in LICENSE4_PRODUCT_CODES:
    if not Product.search([("code", "=", code), ("active", "=", True)], limit=1):
        missing.append(code)
check("commercial_products_exist", not missing, missing or LICENSE4_PRODUCT_CODES)

grant = AccessSvc.issue_critical_grant(AccessSvc.CRITICAL_LICENSE_CHANGE)
license_svc = LicenseSvc.with_context(justech_critical_token=grant)

existing = LicenseSvc._get_active_license_for_company(company)
if not existing:
    existing = License.search(
        [
            ("company_line_ids.company_id", "=", company.id),
            ("state", "in", ("draft", "active")),
        ],
        limit=1,
        order="id desc",
    )

try:
    lic = license_svc.admin_upsert_license(
        company,
        tier="PRO",
        target_state="active",
        company_ids=[company.id],
        starts_at=date.today(),
        expires_at=date.today() + timedelta(days=365),
        max_companies=5,
        product_codes=LICENSE4_PRODUCT_CODES,
        name=company.name,
        license_id=existing.id if existing else None,
    )
    report["license_id"] = lic.id
    check("license_active", lic.state == "active", lic.state)
    check(
        "hellenia_company_linked",
        company.id in lic.company_line_ids.mapped("company_id").ids,
        {"company": company.name, "company_id": company.id},
    )
    feature_codes = sorted(
        lic.feature_line_ids.mapped("feature_id.code")
    )
    check("license_has_features", bool(feature_codes), feature_codes)
except Exception as exc:
    check("create_or_update_license", False, exc)
    lic = existing

lic = LicenseSvc._get_active_license_for_company(company)
check("hellenia_has_active_license", bool(lic), lic.id if lic else "none")

# Módulos del Cliente — must not show missing license
try:
    clients = LicenseSvc.get_commercial_clients()
    hellenia = next(
        (c for c in clients if c.get("primary_company_id") == company.id),
        clients[0] if clients else {},
    )
    check(
        "client_modules_has_license_id",
        bool(hellenia.get("license_id")),
        hellenia,
    )
    Control = env["justech.client.module.control"]
    panel = Control.create(
        {
            "license_id": hellenia.get("license_id") or (lic.id if lic else False),
            "company_id": company.id,
        }
    )
    panel._reload_lines()
    plan = panel.summary_plan or ""
    check(
        "client_modules_plan_not_empty",
        plan not in ("—", "", "Sin licencia", "sin licencia"),
        plan,
    )
    check(
        "client_modules_no_sin_licencia",
        "sin licencia" not in (panel.header_html or "").lower(),
        "header ok",
    )
    line_labels = panel.line_ids.mapped("license_label")
    sin_licencia_lines = [
        lbl for lbl in line_labels if lbl and "sin licencia" in lbl.lower()
    ]
    check(
        "module_lines_no_sin_licencia",
        not sin_licencia_lines,
        sin_licencia_lines or line_labels[:8],
    )
    visible_names = panel.line_ids.mapped("display_name")
    check(
        "no_control_justech_in_client_modules",
        not any("centro" in (n or "").lower() and "justech" in (n or "").lower() for n in visible_names),
        visible_names,
    )
    report["visible_modules"] = visible_names
    report["summary_plan"] = plan
except Exception as exc:
    check("client_modules_recognizes_license", False, exc)

# Verify licensed product codes on record
if lic:
    licensed_products = set()
    for feat in lic.feature_line_ids.mapped("feature_id"):
        for prod in Product.search([("active", "=", True)]):
            codes = prod.line_ids.mapped(lambda l: l.feature_code)
            if feat.code in codes:
                licensed_products.add(prod.code)
    forbidden = licensed_products & FORBIDDEN_CODES
    check("no_forbidden_modules", not forbidden, sorted(licensed_products))

report["status"] = "PASS" if not report["errors"] else "FAIL"
with open(OUT, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2, ensure_ascii=False, default=str)

print("LICENSE4_HELLENIA:" + json.dumps(report, ensure_ascii=False, default=str))
