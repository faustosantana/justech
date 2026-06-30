#!/usr/bin/env python3
"""Fase 12 — Validar configuración Hellenia lista para producción."""
from __future__ import annotations

import json
from datetime import datetime, timezone

COMPANY_LANG = "es_DO"
COMPANY_TZ = "America/Santo_Domingo"
COMPANY_VAT = "133621282"
REQUIRED_MODULES = [
    "account", "account_accountant", "account_reports", "sale", "purchase",
    "stock", "contacts", "l10n_do",
    "justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports",
]

report = {
    "phase": 12,
    "block": 2,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "checks": {},
    "ok": True,
    "errors": [],
}


def chk(name: str, ok: bool, detail: str = "", obs: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    if obs and ok:
        status = "PASS CON OBSERVACIONES"
    report["checks"][name] = {"status": status, "ok": ok, "detail": detail, "observation": obs}
    if not ok:
        report["ok"] = False
        report["errors"].append(f"{name}: {detail}")


company = env.company
partner = company.partner_id

# Empresa
chk("company_name", bool(company.name), company.name or "")
chk("company_vat", partner.vat == COMPANY_VAT, partner.vat or "", "")
chk("company_country", partner.country_id.code == "DO", partner.country_id.code or "")
chk("company_street", bool(partner.street), partner.street or "")
chk("company_phone", bool(company.phone), company.phone or "")
chk("company_email", bool(company.email), company.email or "")
chk("company_website", bool(partner.website), partner.website or "")

# Regional
chk("lang_es_do", partner.lang == COMPANY_LANG, partner.lang or "")
users = env["res.users"].search([("active", "=", True), ("share", "=", False)])
chk("users_lang", all(u.lang == COMPANY_LANG for u in users), f"{len(users)} users")
chk("timezone", all(u.tz == COMPANY_TZ for u in users), COMPANY_TZ)

# Fiscal Justech
chk("fiscal_enabled", bool(company.justech_do_fiscal_enabled), str(company.justech_do_fiscal_enabled))

# Moneda
chk("currency_dop", company.currency_id.name == "DOP", company.currency_id.name)

# Diarios operativos
for jtype, label in [("sale", "journal_sale"), ("purchase", "journal_purchase"), ("bank", "journal_bank"), ("cash", "journal_cash")]:
    j = env["account.journal"].search([("type", "=", jtype), ("company_id", "=", company.id)], limit=1)
    chk(label, bool(j), j.code if j else "missing")

# Impuestos ITBIS venta
tax18 = env["account.tax"].search([
    ("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale"),
], limit=1)
chk("tax_itbis_18_sale", bool(tax18), tax18.name if tax18 else "")

# Métodos de pago
if "account.payment.method" in env:
    methods = env["account.payment.method"].search([])
    chk("payment_methods", len(methods) > 0, str(len(methods)))

# SMTP
mail_servers = env["ir.mail_server"].search([])
chk("smtp_configured", len(mail_servers) > 0, str(len(mail_servers)), "Pendiente credenciales Hellenia" if not mail_servers else "")

# Licencia EE (esperado sin código en TEST neutralizado / pre-prod)
ICP = env["ir.config_parameter"].sudo()
ee_code = ICP.get_param("database.enterprise_code")
neutralized = ICP.get_param("database.is_neutralized") == "True"
if neutralized and not ee_code:
    chk("enterprise_code", True, "neutralized", "Registrar en hellenia_prod al Go-Live")
else:
    chk("enterprise_code", bool(ee_code), "set" if ee_code else "not set", "Registrar solo en prod al Go-Live")

# Módulos
Mod = env["ir.module.module"]
for mod in REQUIRED_MODULES:
    rec = Mod.search([("name", "=", mod)], limit=1)
    chk(f"module_{mod}", rec.state == "installed" if rec else False, rec.state if rec else "N/A")

# web.base.url
base_url = ICP.get_param("web.base.url") or ""
chk("web_base_url", bool(base_url), base_url)

# Banco — cuenta bancaria configurada
bank_accounts = env["res.partner.bank"].search([("partner_id", "=", partner.id)])
chk("bank_accounts", len(bank_accounts) > 0, str(len(bank_accounts)), "Pendiente datos bancarios Hellenia" if not bank_accounts else "")

# Tipos documento fiscal
doc_types = env["justech.do.fiscal.document.type"].search([])
expected_prefixes = {"B01", "B02", "B03", "B04", "B11", "B13"}
found = set(doc_types.mapped("prefix"))
chk("fiscal_doc_types", expected_prefixes.issubset(found), ",".join(sorted(found)))

print("PHASE12_CONFIG:" + json.dumps(report, ensure_ascii=False, default=str))
