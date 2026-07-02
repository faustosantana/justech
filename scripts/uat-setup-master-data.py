#!/usr/bin/env python3
"""Fase 9 — Bloque 1: Datos maestros UAT (odoo shell TEST)."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from odoo import Command

company = env["res.company"].search([], limit=1)
country = company.partner_id.country_id
currency = company.currency_id
today = date.today()
result = {"block": 1, "created": [], "updated": [], "errors": [], "ok": True}


def uat_ref(code: str) -> str:
    return f"UAT-{code}"


def ensure_partner(ref, name, **kwargs):
    Partner = env["res.partner"]
    p = Partner.search([("ref", "=", ref)], limit=1)
    vals = {"name": name, "ref": ref, "country_id": country.id, "comment": "UAT — dato de prueba"}
    vals.update(kwargs)
    if p:
        p.write(vals)
        result["updated"].append(ref)
    else:
        p = Partner.create(vals)
        result["created"].append(ref)
    return p


def ensure_product(ref, name, storable=True, service=False, categ_name="Espejos"):
    inventario = env["product.category"].search([("name", "=", "Inventario"), ("parent_id", "=", False)], limit=1)
    categ = env["product.category"].search(
        [("name", "=", categ_name), ("parent_id", "=", inventario.id if inventario else False)], limit=1
    )
    tax = env["account.tax"].search(
        [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1
    )
    Product = env["product.product"]
    p = Product.search([("default_code", "=", ref)], limit=1)
    vals = {
        "name": name,
        "default_code": ref,
        "type": "service" if service else "consu",
        "is_storable": False if service else storable,
        "categ_id": categ.id if categ else False,
        "list_price": 15000.0 if not service else 5000.0,
        "standard_price": 7500.0 if not service else 2500.0,
        "sale_ok": True,
        "purchase_ok": not service,
        "taxes_id": [Command.set(tax.ids)] if tax else [],
    }
    if p:
        p.write(vals)
        result["updated"].append(ref)
    else:
        p = Product.create(vals)
        result["created"].append(ref)
    return p


# --- Clientes ---
ensure_partner(uat_ref("CUST-001"), "UAT Cliente Consumidor Final", customer_rank=1)
ensure_partner(
    uat_ref("CUST-002"),
    "UAT Cliente Empresa B2B",
    customer_rank=1,
    vat="101234567",
    is_company=True,
)
ensure_partner(uat_ref("CUST-003"), "UAT Cliente Interiorismo", customer_rank=1)

# --- Proveedores ---
ensure_partner(uat_ref("VEND-001"), "UAT Proveedor Mobiliario RD", supplier_rank=1)
ensure_partner(uat_ref("VEND-002"), "UAT Proveedor Espejos Import", supplier_rank=1, vat="130987654")

# --- Transportista ---
ensure_partner(uat_ref("CARRIER-001"), "UAT Transportista Local", supplier_rank=1)

# --- Productos y servicio ---
ensure_product(uat_ref("PROD-001"), "UAT Espejo Decorativo Piloto", categ_name="Espejos")
ensure_product(uat_ref("PROD-002"), "UAT Lámpara Mesa Piloto", categ_name="Lámparas")
ensure_product(uat_ref("SERV-001"), "UAT Servicio Instalación", service=True)

# --- Equipo ventas (sin usuario nuevo) ---
team = env["crm.team"].search([("name", "=", "Ventas Hellenia")], limit=1)
if not team:
    team = env["crm.team"].create({"name": "Ventas Hellenia", "company_id": company.id})
    result["created"].append("team-ventas-hellenia")

# --- Rangos NCF UAT (amplios para estrés) ---
manager = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if manager and manager not in env.user.group_ids:
    env.user.write({"group_ids": [(4, manager.id)]})

journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
for j in (journal_sale, journal_purchase):
    if j:
        j.write({"justech_do_use_ncf": True})

Range = env["justech.do.ncf.range"]
doc_types = {
    "B01": env.ref("justech_l10n_do_base.doc_type_b01"),
    "B02": env.ref("justech_l10n_do_base.doc_type_b02"),
    "B03": env.ref("justech_l10n_do_base.doc_type_b03"),
    "B04": env.ref("justech_l10n_do_base.doc_type_b04"),
    "B11": env.ref("justech_l10n_do_base.doc_type_b11"),
    "B13": env.ref("justech_l10n_do_base.doc_type_b13"),
}

for prefix, doc in doc_types.items():
    journal = journal_sale if prefix in ("B01", "B02", "B03", "B04") else journal_purchase
    if not journal:
        continue
    existing = Range.search(
        [("name", "=", f"UAT Range {prefix}"), ("company_id", "=", company.id)], limit=1
    )
    if not existing:
        r = Range.create(
            {
                "name": f"UAT Range {prefix}",
                "document_type_id": doc.id,
                "company_id": company.id,
                "sequence_start": 20000,
                "sequence_end": 29999,
                "next_sequence": 20000,
                "date_from": today - timedelta(days=30),
                "date_to": today + timedelta(days=730),
                "journal_ids": [Command.set(journal.ids)],
            }
        )
        r.action_activate()
        result["created"].append(f"ncf-range-{prefix}")
    if prefix in ("B11", "B13") and journal_purchase:
        journal_purchase.write(
            {
                "justech_do_default_document_type_id": doc.id,
                "justech_do_document_type_ids": [Command.set([doc.id])],
            }
        )

# Rangos agotado/vencido para estrés (bloque 10)
exhaust_name = "UAT Range B02 EXHAUST"
if not Range.search([("name", "=", exhaust_name)], limit=1):
    r_ex = Range.create(
        {
            "name": exhaust_name,
            "document_type_id": doc_types["B02"].id,
            "company_id": company.id,
            "sequence_start": 30000,
            "sequence_end": 30000,
            "next_sequence": 30000,
            "date_from": today - timedelta(days=30),
            "date_to": today + timedelta(days=365),
            "journal_ids": [Command.set(journal_sale.ids)],
        }
    )
    r_ex.action_activate()
    result["created"].append(exhaust_name)

expired_name = "UAT Range B02 EXPIRED"
if not Range.search([("name", "=", expired_name)], limit=1):
    r_exp = Range.create(
        {
            "name": expired_name,
            "document_type_id": doc_types["B02"].id,
            "company_id": company.id,
            "sequence_start": 30001,
            "sequence_end": 30999,
            "next_sequence": 30001,
            "date_from": today - timedelta(days=60),
            "date_to": today + timedelta(days=30),
            "journal_ids": [Command.set(journal_sale.ids)],
        }
    )
    r_exp.action_activate()
    r_exp.write({"date_to": today - timedelta(days=1), "state": "expired"})
    result["created"].append(expired_name)

company.write({"justech_do_fiscal_enabled": True})
env.cr.commit()

result["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
result["counts"] = {
    "customers": env["res.partner"].search_count([("ref", "ilike", "UAT-CUST%")]),
    "vendors": env["res.partner"].search_count([("ref", "ilike", "UAT-VEND%")]),
    "products": env["product.product"].search_count([("default_code", "ilike", "UAT-%")]),
    "ncf_ranges": env["justech.do.ncf.range"].search_count([("name", "ilike", "UAT%")]),
}
print("UAT_BLOCK1:" + json.dumps(result, ensure_ascii=False, default=str))
