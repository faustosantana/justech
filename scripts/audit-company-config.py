#!/usr/bin/env python3
"""Fase 7 — Verificar configuración empresa (odoo shell)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

company = env.company
partner = company.partner_id
lang = env["res.lang"].search([("code", "=", company.partner_id.lang or env.user.lang)], limit=1)
tz_users = env["res.users"].search([("active", "=", True)]).mapped("tz")
report = {
    "database": env.cr.dbname,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "company": {
        "name": company.name,
        "vat": partner.vat or "",
        "country": company.country_id.code if company.country_id else "",
        "currency": company.currency_id.name if company.currency_id else "",
        "fiscal_enabled": getattr(company, "justech_do_fiscal_enabled", None),
    },
    "user_timezones_sample": sorted(set(tz_users)),
    "checks": {
        "name_ok": company.name == "Hellenia, S.R.L.",
        "vat_ok": (partner.vat or "").replace("-", "") in ("133621282", "133-621282"),
        "country_ok": company.country_id.code == "DO",
        "currency_ok": company.currency_id.name == "DOP",
    },
}
report["ok"] = all(report["checks"].values())
print("COMPANY_AUDIT:" + json.dumps(report, indent=2, ensure_ascii=False, default=str))
