#!/usr/bin/env python3
"""Fase 3.5 — Golden Configuration definitiva Hellenia (odoo shell stdin)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

# --- Empresa oficial (Información de la empresa para Odoo) ---
COMPANY_LEGAL_NAME = "Hellenia, S.R.L."
COMPANY_TRADE_NAME = "Hellenia"
COMPANY_VAT = "133621282"
COMPANY_STREET = "Calle Federico Geraldino No.164, Esquina David Ben Gurión"
COMPANY_STREET2 = "Plaza Stephanie, Local 3-B, Piantini"
COMPANY_CITY = "Santo Domingo"
COMPANY_STATE_NAME = "Distrito Nacional"
COMPANY_COUNTRY_CODE = "DO"
COMPANY_CURRENCY = "DOP"
COMPANY_TZ = "America/Santo_Domingo"
COMPANY_LANG = "es_DO"
COMPANY_PHONE = "+1 849-434-8694"
COMPANY_EMAIL = "info@helleniadr.com"
COMPANY_WEBSITE = "https://hellenia.cloud"

BANK_NAME = "Banco López de Haro"
BANK_ACCOUNTS = [
    {"label": "Cuenta corriente DOP", "currency": "DOP", "acc_number": "4040043811"},
    {"label": "Cuenta ahorro USD", "currency": "USD", "acc_number": "4010461048"},
]

# Categorías oficiales — hijas directas de Inventario
INVENTARIO_CHILDREN = [
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

PAYMENT_METHOD_SPECS = [
    {"journal_code": "CSH1", "journal_name": "Efectivo", "journal_type": "cash", "methods": [
        ("manual", "inbound", "Efectivo"),
        ("manual", "outbound", "Efectivo"),
    ]},
    {"journal_code": "BNK1", "journal_name": "Bank", "journal_type": "bank", "methods": [
        ("manual", "inbound", "Transferencia"),
        ("manual", "inbound", "Tarjetas"),
        ("manual", "inbound", "Link de pago"),
        ("manual", "outbound", "Transferencia"),
        ("check_printing", "outbound", "Cheques"),
    ]},
]


def log(msg: str) -> None:
    print(f"[phase35] {msg}")


def ensure_lang(e, code: str) -> None:
    e["res.lang"]._activate_lang(code)


def get_or_create_category(e, name: str, parent):
    Cat = e["product.category"]
    domain = [("name", "=", name), ("parent_id", "=", parent.id if parent else False)]
    rec = Cat.search(domain, limit=1)
    if not rec:
        rec = Cat.create({"name": name, "parent_id": parent.id if parent else False})
        log(f"category created: {name}")
    return rec


def update_company(e) -> dict:
    company = e["res.company"].search([], limit=1)
    country = e["res.country"].search([("code", "=", COMPANY_COUNTRY_CODE)], limit=1)
    currency = e["res.currency"].search([("name", "=", COMPANY_CURRENCY)], limit=1)
    state = e["res.country.state"].search(
        [("country_id", "=", country.id), ("name", "=", COMPANY_STATE_NAME)], limit=1
    )

    partner_vals = {
        "name": COMPANY_LEGAL_NAME,
        "vat": COMPANY_VAT,
        "street": COMPANY_STREET,
        "street2": COMPANY_STREET2,
        "city": COMPANY_CITY,
        "state_id": state.id if state else False,
        "zip": False,
        "country_id": country.id,
        "phone": COMPANY_PHONE,
        "email": COMPANY_EMAIL,
        "website": COMPANY_WEBSITE,
        "lang": COMPANY_LANG,
        "comment": f"Nombre comercial: {COMPANY_TRADE_NAME}",
    }
    company_vals = {
        "name": COMPANY_LEGAL_NAME,
        "currency_id": currency.id,
        "phone": COMPANY_PHONE,
        "email": COMPANY_EMAIL,
    }
    company.write(company_vals)
    company.partner_id.write(partner_vals)

    admin = e["res.users"].search([("login", "=", "admin")], limit=1)
    admin.write({"tz": COMPANY_TZ, "lang": COMPANY_LANG})

    return {
        "company_id": company.id,
        "state": state.name if state else None,
    }


def update_banks(e, company) -> list:
    Bank = e["res.bank"]
    PartnerBank = e["res.partner.bank"]
    bank = Bank.search([("name", "=", BANK_NAME)], limit=1)
    if not bank:
        bank = Bank.create({"name": BANK_NAME})

    results = []
    for spec in BANK_ACCOUNTS:
        currency = e["res.currency"].search([("name", "=", spec["currency"])], limit=1)
        existing = PartnerBank.search(
            [
                ("partner_id", "=", company.partner_id.id),
                ("bank_id", "=", bank.id),
                ("currency_id", "=", currency.id),
            ],
            limit=1,
        )
        vals = {
            "partner_id": company.partner_id.id,
            "bank_id": bank.id,
            "currency_id": currency.id,
            "acc_number": spec["acc_number"],
            "acc_holder_name": COMPANY_LEGAL_NAME,
        }
        if existing:
            existing.write(vals)
            rec = existing
        else:
            rec = PartnerBank.create(vals)
        results.append({"label": spec["label"], "acc_number": rec.acc_number, "currency": spec["currency"]})
        log(f"bank {spec['label']}: {spec['acc_number']}")
    return results


def setup_official_categories(e) -> list:
    inventario = get_or_create_category(e, "Inventario", None)
    ids = [inventario.id]
    for name in INVENTARIO_CHILDREN:
        cat = get_or_create_category(e, name, inventario)
        ids.append(cat.id)
    return ids


def ensure_journal(e, company, code: str, name: str, jtype: str):
    Journal = e["account.journal"]
    journal = Journal.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)
    if not journal and jtype == "cash":
        journal = Journal.create(
            {
                "name": name,
                "code": code,
                "type": jtype,
                "company_id": company.id,
            }
        )
        log(f"journal created: {code} ({name})")
    return journal


def setup_payment_methods(e, company) -> list:
    Journal = e["account.journal"]
    Method = e["account.payment.method"]
    Line = e["account.payment.method.line"]
    created = []

    bnk = Journal.search([("code", "=", "BNK1"), ("company_id", "=", company.id)], limit=1)
    cash = ensure_journal(e, company, "CSH1", "Efectivo", "cash")

    for spec in PAYMENT_METHOD_SPECS:
        if spec["journal_code"] == "BNK1":
            journal = bnk
        else:
            journal = cash
        if not journal:
            log(f"skip payment methods — journal missing {spec['journal_code']}")
            continue
        for pm_code, pm_type, label in spec["methods"]:
            method = Method.search(
                [("code", "=", pm_code), ("payment_type", "=", pm_type)], limit=1
            )
            if not method:
                log(f"payment method not found: {pm_code}/{pm_type}")
                continue
            line = Line.search(
                [
                    ("journal_id", "=", journal.id),
                    ("payment_method_id", "=", method.id),
                    ("name", "=", label),
                ],
                limit=1,
            )
            if not line:
                line = Line.create(
                    {
                        "journal_id": journal.id,
                        "payment_method_id": method.id,
                        "name": label,
                    }
                )
                log(f"payment line: {journal.code} — {label}")
            created.append({"journal": journal.code, "label": label, "type": pm_type})
    return created


# --- ejecución ---
ensure_lang(env, COMPANY_LANG)
company = env["res.company"].search([], limit=1)
company_info = update_company(env)
banks = update_banks(env, company)
categories = setup_official_categories(env)
payments = setup_payment_methods(env, company)
env.cr.commit()

report = {
    "phase": "3.5",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "company": company_info,
    "banks": banks,
    "categories_official": len(INVENTARIO_CHILDREN) + 1,
    "payment_lines": payments,
    "link_pago": "documented_pending_no_gateway",
}
print("PHASE35_JSON_RESULT=" + json.dumps(report, ensure_ascii=False))
