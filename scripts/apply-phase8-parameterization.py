#!/usr/bin/env python3
"""Fase 8 — Parametrización funcional idempotente (odoo shell stdin).

Solo configuración estándar Odoo. No modifica módulos custom ni core.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

# Reutilizar constantes Fase 3.5
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

INVENTARIO_CHILDREN = [
    "Mobiliario", "Espejos", "Lámparas", "Esculturas", "Relojería",
    "Pinturas", "Dibujos y litografías", "Tapisería", "Cristalería", "Plata", "Vajillas",
]

PAYMENT_TERM_SPECS = [
    {"name": "Pago inmediato", "days": 0},
    {"name": "15 días", "days": 15},
    {"name": "30 días", "days": 30},
    {"name": "45 días", "days": 45},
    {"name": "60 días", "days": 60},
]

actions = []


def log(action: str, detail: str = "") -> None:
    actions.append({"action": action, "detail": detail})
    print(f"[phase8] {action}: {detail}")


def ensure_lang(code: str) -> None:
    env["res.lang"]._activate_lang(code)


def get_or_create_category(name: str, parent):
    Cat = env["product.category"]
    domain = [("name", "=", name), ("parent_id", "=", parent.id if parent else False)]
    rec = Cat.search(domain, limit=1)
    if not rec:
        rec = Cat.create({"name": name, "parent_id": parent.id if parent else False})
        log("category_created", name)
    return rec


def ensure_payment_term(name: str, days: int):
    Term = env["account.payment.term"]
    term = Term.search([("name", "=", name)], limit=1)
    if term:
        return term
    term = Term.create(
        {
            "name": name,
            "line_ids": [(0, 0, {"value": "percent", "value_amount": 100.0, "nb_days": days})],
        }
    )
    log("payment_term_created", name)
    return term


def ensure_sales_team(name: str, company):
    Team = env["crm.team"]
    team = Team.search([("name", "=", name), ("company_id", "in", [company.id, False])], limit=1)
    if not team:
        team = Team.create({"name": name, "company_id": company.id})
        log("sales_team_created", name)
    return team


def ensure_pricelist(name: str, currency, company):
    PL = env["product.pricelist"]
    pl = PL.search([("name", "=", name), ("company_id", "in", [company.id, False])], limit=1)
    if not pl:
        pl = PL.create({"name": name, "currency_id": currency.id, "company_id": company.id})
        log("pricelist_created", name)
    return pl


def update_company(company) -> None:
    country = env["res.country"].search([("code", "=", COMPANY_COUNTRY_CODE)], limit=1)
    currency = env["res.currency"].search([("name", "=", COMPANY_CURRENCY)], limit=1)
    state = env["res.country.state"].search(
        [("country_id", "=", country.id), ("name", "=", COMPANY_STATE_NAME)], limit=1
    )
    partner_vals = {
        "name": COMPANY_LEGAL_NAME,
        "vat": COMPANY_VAT,
        "street": COMPANY_STREET,
        "street2": COMPANY_STREET2,
        "city": COMPANY_CITY,
        "state_id": state.id if state else False,
        "country_id": country.id,
        "phone": COMPANY_PHONE,
        "email": COMPANY_EMAIL,
        "website": COMPANY_WEBSITE,
        "lang": COMPANY_LANG,
        "comment": f"Nombre comercial: {COMPANY_TRADE_NAME}",
    }
    company.write(
        {
            "name": COMPANY_LEGAL_NAME,
            "currency_id": currency.id,
            "phone": COMPANY_PHONE,
            "email": COMPANY_EMAIL,
        }
    )
    company.partner_id.write(partner_vals)
    if hasattr(company, "justech_do_fiscal_enabled"):
        company.write({"justech_do_fiscal_enabled": True})
        log("fiscal_enabled", "justech_do_fiscal_enabled=True")
    log("company_updated", COMPANY_LEGAL_NAME)


def ensure_pilot_partner(ref: str, name: str, rank_field: str, rank_val: int):
    Partner = env["res.partner"]
    p = Partner.search([("ref", "=", ref)], limit=1)
    country = env["res.country"].search([("code", "=", "DO")], limit=1)
    vals = {
        "name": name,
        "ref": ref,
        "country_id": country.id,
        rank_field: rank_val,
        "company_type": "company",
        "comment": "Registro piloto UAT — no es dato real de negocio",
    }
    if not p:
        p = Partner.create(vals)
        log("pilot_partner_created", ref)
    else:
        p.write(vals)
        log("pilot_partner_updated", ref)
    return p


def ensure_pilot_product(code: str, name: str, categ):
    Product = env["product.product"]
    p = Product.search([("default_code", "=", code)], limit=1)
    vals = {
        "name": name,
        "default_code": code,
        "type": "consu",
        "is_storable": True,
        "categ_id": categ.id,
        "list_price": 10000.0,
        "standard_price": 5000.0,
        "description_sale": "Producto piloto UAT — reemplazar en carga catálogo",
    }
    if not p:
        p = Product.create(vals)
        log("pilot_product_created", code)
    else:
        p.write(vals)
        log("pilot_product_updated", code)
    return p


def configure_sale_journal_ncf(company) -> None:
    Journal = env["account.journal"]
    sale_j = Journal.search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
    if sale_j and hasattr(sale_j, "justech_do_use_ncf") and not sale_j.justech_do_use_ncf:
        sale_j.write({"justech_do_use_ncf": True})
        log("journal_ncf_enabled", sale_j.code)
    purchase_j = Journal.search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
    if purchase_j and hasattr(purchase_j, "justech_do_use_ncf") and not purchase_j.justech_do_use_ncf:
        purchase_j.write({"justech_do_use_ncf": True})
        log("journal_ncf_enabled", purchase_j.code)


def set_user_locale() -> None:
    for login in ("admin", "it@justech.do"):
        u = env["res.users"].search([("login", "=", login)], limit=1)
        if u:
            u.write({"tz": COMPANY_TZ, "lang": COMPANY_LANG})


# --- Ejecución ---
ensure_lang(COMPANY_LANG)
company = env["res.company"].search([], limit=1)
currency = company.currency_id

update_company(company)
set_user_locale()

inventario = get_or_create_category("Inventario", None)
for cat_name in INVENTARIO_CHILDREN:
    get_or_create_category(cat_name, inventario)

for spec in PAYMENT_TERM_SPECS:
    ensure_payment_term(spec["name"], spec["days"])

ensure_sales_team("Ventas Hellenia", company)
ensure_pricelist("Lista pública DOP", currency, company)

# Parámetro web según ambiente
import os

ICP = env["ir.config_parameter"].sudo()
web_url = os.environ.get("WEB_BASE_URL") or (
    "https://odoo.hellenia.cloud"
    if env.cr.dbname.endswith("_prod")
    else (
        "https://test.hellenia.cloud"
        if env.cr.dbname.endswith("_test")
        else "https://dev.hellenia.cloud"
    )
)
ICP.set_param("web.base.url", web_url)
log("param_set", f"web.base.url={web_url}")

skip_pilot = os.environ.get("HELLENIA_SKIP_PILOT", "").lower() in ("1", "true", "yes")
if not skip_pilot:
    espejos = env["product.category"].search(
        [("name", "=", "Espejos"), ("parent_id", "=", inventario.id)], limit=1
    )
    if not espejos:
        espejos = inventario

    ensure_pilot_partner("UAT-PILOT-VEND-001", "Proveedor Piloto UAT", "supplier_rank", 1)
    ensure_pilot_partner("UAT-PILOT-CUST-001", "Cliente Piloto UAT", "customer_rank", 1)
    ensure_pilot_product("UAT-PILOT-PROD-001", "Producto Piloto UAT — Espejo muestra", espejos)
else:
    log("pilot_data", "skipped for production")

env.cr.commit()

report = {
    "phase": "8",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "actions_count": len(actions),
    "actions": actions,
}
print("PHASE8_APPLY:" + json.dumps(report, ensure_ascii=False, default=str))
