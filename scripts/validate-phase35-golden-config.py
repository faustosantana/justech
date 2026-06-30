#!/usr/bin/env python3
"""Validación Fase 3.5 — Golden Configuration definitiva (odoo shell stdin)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

EXPECTED = {
    "company_name": "Hellenia, S.R.L.",
    "vat": "133621282",
    "email": "info@helleniadr.com",
    "phone": "+1 849-434-8694",
    "street_contains": "Federico Geraldino",
    "currency": "DOP",
    "country_code": "DO",
    "tz": "America/Santo_Domingo",
}

OFFICIAL_CATEGORIES = [
    "Inventario",
    "Mobiliario",
    "Espejos",
    "Lámparas",
    "Esculturas",
    "Relojería",
    "Pinturas",
    "Dibujos y litografías",
    "Tapisería",
    "Cristalería",
    "Plata",
    "Vajillas",
]

BANK_ACCOUNTS = {"4040043811", "4010461048"}

company = env["res.company"].search([], limit=1)
partner = company.partner_id
checks = {}

checks["company_name"] = {"ok": company.name == EXPECTED["company_name"], "value": company.name}
checks["vat"] = {"ok": partner.vat == EXPECTED["vat"], "value": partner.vat}
checks["email"] = {
    "ok": (partner.email == EXPECTED["email"] or company.email == EXPECTED["email"]),
    "value": partner.email or company.email,
}
checks["phone"] = {
    "ok": EXPECTED["phone"] in (partner.phone or "") or EXPECTED["phone"] in (company.phone or ""),
    "value": partner.phone or company.phone,
}
checks["address"] = {
    "ok": EXPECTED["street_contains"] in (partner.street or ""),
    "value": partner.street,
}
checks["city"] = {"ok": partner.city == "Santo Domingo", "value": partner.city}
checks["currency"] = {"ok": company.currency_id.name == EXPECTED["currency"], "value": company.currency_id.name}
checks["country"] = {"ok": partner.country_id.code == EXPECTED["country_code"], "value": partner.country_id.code}

admin = env["res.users"].search([("login", "=", "admin")], limit=1)
checks["timezone"] = {"ok": admin.tz == EXPECTED["tz"], "value": admin.tz}

banks = env["res.partner.bank"].search([("partner_id", "=", partner.id)])
acc_numbers = {b.acc_number for b in banks}
checks["banks"] = {
    "ok": BANK_ACCOUNTS.issubset(acc_numbers),
    "value": list(acc_numbers),
}

cat_checks = {
    n: bool(env["product.category"].search([("name", "=", n)], limit=1)) for n in OFFICIAL_CATEGORIES
}
inventario = env["product.category"].search([("name", "=", "Inventario"), ("parent_id", "=", False)], limit=1)
children_ok = True
if inventario:
    for n in OFFICIAL_CATEGORIES[1:]:
        if not env["product.category"].search(
            [("name", "=", n), ("parent_id", "=", inventario.id)], limit=1
        ):
            children_ok = False
            cat_checks[n] = False
checks["categories"] = {"ok": all(cat_checks.values()) and children_ok, "value": cat_checks}

lines = env["account.payment.method.line"].search([])
labels = [l.name for l in lines]
checks["payment_methods"] = {
    "ok": any("Efectivo" in (x or "") for x in labels)
    and any("Transferencia" in (x or "") for x in labels),
    "value": labels,
}

checks["tax_count"] = {
    "ok": env["account.tax"].search_count([("company_id", "=", company.id)]) >= 14,
    "value": env["account.tax"].search_count([("company_id", "=", company.id)]),
}
checks["journal_count"] = {
    "ok": env["account.journal"].search_count([("company_id", "=", company.id)]) >= 7,
    "value": env["account.journal"].search_count([("company_id", "=", company.id)]),
}
checks["account_count"] = {"ok": env["account.account"].search_count([]) >= 200, "value": env["account.account"].search_count([])}

reports_installed = env["ir.module.module"].search([("name", "=", "account_reports"), ("state", "=", "installed")])
checks["account_reports"] = {"ok": bool(reports_installed), "value": "installed" if reports_installed else "missing"}

users = env["res.users"].search([("share", "=", False), ("active", "=", True)])
checks["no_new_users"] = {"ok": len(users) <= 2, "value": [u.login for u in users]}

all_ok = all(c["ok"] for c in checks.values())
print(
    "PHASE35_VALIDATION="
    + json.dumps(
        {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "ok": all_ok, "checks": checks},
        ensure_ascii=False,
        default=str,
    )
)
