#!/usr/bin/env python3
"""Validación Fase 3 — Golden Configuration (odoo shell stdin)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

EXPECTED = {
    "company_name": "Hellenia, S.R.L.",
    "vat": "133621282",
    "currency": "DOP",
    "country_code": "DO",
    "tz": "America/Santo_Domingo",
}

REQUIRED_CATEGORIES = [
    "Inventario",
    "Mobiliario",
    "Mesas",
    "Decoración",
    "Iluminación",
    "Lámparas",
    "Servicios",
    "Consumibles",
]

company = env["res.company"].search([], limit=1)
partner = company.partner_id
checks = {}

checks["company_name"] = {
    "ok": company.name == EXPECTED["company_name"],
    "value": company.name,
}
checks["vat"] = {"ok": partner.vat == EXPECTED["vat"], "value": partner.vat}
checks["currency"] = {
    "ok": company.currency_id.name == EXPECTED["currency"],
    "value": company.currency_id.name,
}
checks["country"] = {
    "ok": partner.country_id.code == EXPECTED["country_code"],
    "value": partner.country_id.code,
}
admin_user = env["res.users"].search([("login", "=", "admin")], limit=1)
tz = admin_user.tz
checks["timezone"] = {"ok": tz == EXPECTED["tz"], "value": tz}

taxes = env["account.tax"].search_count([("company_id", "=", company.id)])
fps = env["account.fiscal.position"].search_count([("company_id", "=", company.id)])
journals = env["account.journal"].search([("company_id", "=", company.id)])
accounts = env["account.account"].search_count([])

checks["tax_count"] = {"ok": taxes >= 14, "value": taxes}
checks["fiscal_position_count"] = {"ok": fps >= 5, "value": fps}
checks["journal_count"] = {"ok": len(journals) >= 7, "value": len(journals)}
checks["account_count"] = {"ok": accounts >= 200, "value": accounts}

cat_checks = {
    name: bool(env["product.category"].search([("name", "=", name)], limit=1))
    for name in REQUIRED_CATEGORIES
}
checks["categories"] = {"ok": all(cat_checks.values()), "value": cat_checks}

banks = env["res.partner.bank"].search([("partner_id", "=", partner.id)])
checks["bank_lines"] = {
    "ok": len(banks) >= 2,
    "value": [
        {"bank": b.bank_id.name, "currency": b.currency_id.name, "acc_number": b.acc_number}
        for b in banks
    ],
}

users = env["res.users"].search([("share", "=", False), ("active", "=", True)])
checks["internal_users"] = {
    "ok": len(users) <= 2,
    "value": [u.login for u in users],
}

payment_methods = env["account.payment.method"].search([])
checks["payment_method_count"] = {"ok": len(payment_methods) > 0, "value": len(payment_methods)}

all_ok = all(c["ok"] for c in checks.values())
result = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "ok": all_ok,
    "checks": checks,
    "journals": [{"code": j.code, "name": j.name, "type": j.type} for j in journals],
}
print("PHASE3_VALIDATION=" + json.dumps(result, ensure_ascii=False, default=str))
