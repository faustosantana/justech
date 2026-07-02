#!/usr/bin/env python3
"""Fase 3 — Golden Configuration Hellenia (odoo shell stdin)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

COMPANY_LEGAL_NAME = "Hellenia, S.R.L."
COMPANY_TRADE_NAME = "Hellenia"
COMPANY_VAT = "133621282"
COMPANY_COUNTRY_CODE = "DO"
COMPANY_CURRENCY = "DOP"
COMPANY_TZ = "America/Santo_Domingo"
COMPANY_LANG = "es_DO"
COMPANY_WEBSITE = "https://hellenia.cloud"
BANK_NAME = "Banco López de Haro"

CATEGORY_TREE = {
    "Inventario": {
        "Mobiliario": ["Mesas", "Sillas", "Consolas", "Bufeteras", "Sofás", "Dormitorios"],
        "Decoración": ["Espejos", "Esculturas", "Pinturas", "Litografías", "Relojes"],
        "Iluminación": ["Lámparas", "Candelabros"],
        "Cristalería": [],
        "Plata": [],
        "Vajillas": [],
        "Tapicería": [],
    },
    "Servicios": {},
    "Consumibles": {},
}


def log(msg: str) -> None:
    print(f"[phase3] {msg}")


def ensure_lang(e, code: str) -> None:
    Lang = e["res.lang"]
    if not Lang.search_count([("code", "=", code)]):
        lang = Lang.with_context(active_test=False).search([("code", "=", code)], limit=1)
        if lang:
            lang.active = True
            log(f"activated lang {code}")
    e["res.lang"]._activate_lang(code)


def get_or_create_category(e, name: str, parent):
    Cat = e["product.category"]
    domain = [("name", "=", name)]
    domain.append(("parent_id", "=", parent.id if parent else False))
    rec = Cat.search(domain, limit=1)
    if not rec:
        rec = Cat.create({"name": name, "parent_id": parent.id if parent else False})
        log(f"created category: {name}")
    return rec


def build_categories(e, tree: dict) -> list[int]:
    created = []
    for name, children in tree.items():
        cat = get_or_create_category(e, name, None)
        created.append(cat.id)
        if isinstance(children, dict):
            for sub_name, leaves in children.items():
                sub = get_or_create_category(e, sub_name, cat)
                created.append(sub.id)
                for leaf in leaves:
                    leaf_cat = get_or_create_category(e, leaf, sub)
                    created.append(leaf_cat.id)
    return created


def prepare_banks(e, company) -> dict:
    PartnerBank = e["res.partner.bank"]
    Bank = e["res.bank"]
    partner = company.partner_id

    bank = Bank.search([("name", "=", BANK_NAME)], limit=1)
    if not bank:
        bank = Bank.create({"name": BANK_NAME})
        log(f"created bank: {BANK_NAME}")

    result = {"bank_id": bank.id, "accounts": []}
    specs = [
        {"label": "Cuenta corriente DOP", "currency": "DOP"},
        {"label": "Cuenta ahorro USD", "currency": "USD"},
    ]
    for spec in specs:
        currency = e["res.currency"].search([("name", "=", spec["currency"])], limit=1)
        existing = PartnerBank.search(
            [
                ("partner_id", "=", partner.id),
                ("bank_id", "=", bank.id),
                ("currency_id", "=", currency.id),
            ],
            limit=1,
        )
        vals = {
            "partner_id": partner.id,
            "bank_id": bank.id,
            "currency_id": currency.id,
            "acc_holder_name": COMPANY_LEGAL_NAME,
            "acc_number": f"PENDING-{spec['currency']}",
        }
        if existing:
            existing.write(vals)
            rec = existing
            log(f"updated bank line: {spec['label']}")
        else:
            rec = PartnerBank.create(vals)
            log(f"created bank line (pending number): {spec['label']}")
        result["accounts"].append(
            {
                "id": rec.id,
                "label": spec["label"],
                "currency": spec["currency"],
                "acc_number": rec.acc_number,
                "pending": True,
            }
        )
    return result


# --- ejecución odoo shell ---
company = env["res.company"].search([], limit=1)
ensure_lang(env, COMPANY_LANG)
country_do = env["res.country"].search([("code", "=", COMPANY_COUNTRY_CODE)], limit=1)
currency = env["res.currency"].search([("name", "=", COMPANY_CURRENCY)], limit=1)

partner_vals = {
    "name": COMPANY_LEGAL_NAME,
    "vat": COMPANY_VAT,
    "country_id": country_do.id,
    "lang": COMPANY_LANG,
    "website": COMPANY_WEBSITE,
    "street": False,
    "city": False,
    "zip": False,
    "phone": False,
    "email": False,
    "comment": f"Nombre comercial: {COMPANY_TRADE_NAME}",
}

company.write({"name": COMPANY_LEGAL_NAME, "currency_id": currency.id})
company.partner_id.write(partner_vals)
if "tz" in company._fields:
    company.write({"tz": COMPANY_TZ})

cat_ids = build_categories(env, CATEGORY_TREE)
bank_info = prepare_banks(env, company)
env.cr.commit()

report = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "company_id": company.id,
    "company_name": company.name,
    "vat": company.partner_id.vat,
    "currency": currency.name,
    "country": country_do.code,
    "website": company.partner_id.website,
    "category_ids": len(set(cat_ids)),
    "banks": bank_info,
}
print("PHASE3_JSON_RESULT=" + json.dumps(report, ensure_ascii=False))
