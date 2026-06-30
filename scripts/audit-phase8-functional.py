#!/usr/bin/env python3
"""Fase 8 — Auditoría parametrización funcional completa (odoo shell stdin)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

company = env["res.company"].search([], limit=1)
partner = company.partner_id
now = datetime.now(timezone.utc).isoformat()

report = {
    "phase": "8",
    "database": env.cr.dbname,
    "timestamp_utc": now,
    "blocks": {},
}


def block_result(name: str, checks: dict, observations: list | None = None) -> dict:
    all_ok = all(c.get("ok") for c in checks.values())
    any_fail = any(not c.get("ok") for c in checks.values())
    if any_fail:
        status = "FAIL"
    elif observations:
        status = "PASS CON OBSERVACIONES"
    else:
        status = "PASS"
    return {"status": status, "checks": checks, "observations": observations or []}


# --- BLOQUE 1: General ---
b1 = {}
b1["company_name"] = {"ok": company.name == "Hellenia, S.R.L.", "value": company.name}
b1["vat"] = {
    "ok": (partner.vat or "").replace("-", "") == "133621282",
    "value": partner.vat,
}
b1["currency"] = {"ok": company.currency_id.name == "DOP", "value": company.currency_id.name}
b1["country"] = {
    "ok": partner.country_id.code == "DO",
    "value": partner.country_id.code,
}
langs = env["res.lang"].search([("active", "=", True)]).mapped("code")
b1["lang_es_do"] = {"ok": "es_DO" in langs, "value": langs}
users = env["res.users"].search([("active", "=", True), ("share", "=", False)])
tz_ok = all(u.tz == "America/Santo_Domingo" for u in users if u.login != "__system__")
b1["timezone"] = {
    "ok": tz_ok,
    "value": sorted({u.tz for u in users}),
}
b1["logo"] = {"ok": bool(company.logo), "value": bool(company.logo)}
params = {
    p.key: p.value
    for p in env["ir.config_parameter"].search(
        [
            (
                "key",
                "in",
                [
                    "web.base.url",
                    "mail.default.from",
                    "mail.catchall.domain",
                    "mail.bounce.alias",
                    "mail.catchall.alias",
                ],
            )
        ]
    )
}
b1["web_base_url"] = {
    "ok": params.get("web.base.url") in (
        "https://dev.hellenia.cloud",
        "https://test.hellenia.cloud",
    ),
    "value": params.get("web.base.url"),
}
banks = env["res.partner.bank"].search([("partner_id", "=", partner.id)])
b1["banks"] = {
    "ok": len(banks) >= 2,
    "value": [{"acc": b.acc_number, "cur": b.currency_id.name} for b in banks],
}
report["blocks"]["block1_general"] = block_result(
    "general",
    b1,
    [
        "Favicon: pendiente upload",
        "Pie documentos: pendiente texto oficial",
        "Firmas digitales: pendiente",
        "SMTP/alias: pendiente",
    ],
)

# --- BLOQUE 2: Comercial ---
b2 = {}
sale_installed = (
    env["ir.module.module"].search([("name", "=", "sale")], limit=1).state == "installed"
)
b2["sale_module"] = {"ok": sale_installed, "value": sale_installed}
teams = env["crm.team"].search([]) if sale_installed else env["crm.team"]
b2["sales_teams"] = {"ok": len(teams) >= 1, "value": teams.mapped("name")}
terms = env["account.payment.term"].search([])
b2["payment_terms"] = {"ok": len(terms) >= 1, "value": terms.mapped("name")}
pricelists = env["product.pricelist"].search([])
b2["pricelists"] = {"ok": len(pricelists) >= 1, "value": pricelists.mapped("name")}
customers = env["res.partner"].search([("customer_rank", ">", 0)])
b2["customers_count"] = {"ok": True, "value": len(customers)}
report["blocks"]["block2_commercial"] = block_result(
    "commercial",
    b2,
    [
        "Políticas descuento/devolución/garantía: pendiente decisión Hellenia",
        "Canales venta: pendiente",
        "Vendedores funcionales: pendiente usuarios UAT",
    ],
)

# --- BLOQUE 3: Compras ---
b3 = {}
purchase_installed = (
    env["ir.module.module"].search([("name", "=", "purchase")], limit=1).state == "installed"
)
b3["purchase_module"] = {"ok": purchase_installed, "value": purchase_installed}
vendors = env["res.partner"].search([("supplier_rank", ">", 0)])
b3["vendors_count"] = {"ok": True, "value": len(vendors)}
po_states = dict(env["purchase.order"]._fields["state"].selection)
b3["po_states"] = {"ok": "purchase" in po_states, "value": list(po_states.keys())}
report["blocks"]["block3_purchase"] = block_result(
    "purchase",
    b3,
    [
        "Aprobaciones compra: pendiente umbral monetario Hellenia",
        "Compras internacionales: pendiente validar si aplica",
        "Proveedores reales: pendiente carga post-UAT",
    ],
)

# --- BLOQUE 4: Inventario ---
b4 = {}
stock_installed = (
    env["ir.module.module"].search([("name", "=", "stock")], limit=1).state == "installed"
)
b4["stock_module"] = {"ok": stock_installed, "value": stock_installed}
wh = env["stock.warehouse"].search([("company_id", "=", company.id)])
b4["warehouses"] = {"ok": len(wh) >= 1, "value": wh.mapped("name")}
if wh:
    w = wh[0]
    b4["warehouse_code"] = {"ok": bool(w.code), "value": w.code}
    b4["locations_stock"] = {"ok": bool(w.lot_stock_id), "value": w.lot_stock_id.complete_name}
    routes = env["stock.route"].search([])
    b4["routes_count"] = {"ok": len(routes) >= 1, "value": len(routes)}
    b4["valuation"] = {
        "ok": True,
        "value": getattr(company, "anglo_saxon_accounting", None),
    }
report["blocks"]["block4_inventory"] = block_result(
    "inventory",
    b4,
    [
        "Lotes/series: pendiente política por pieza única",
        "Inventario físico: pendiente procedimiento UAT",
        "Reabastecimiento MTO/MTS: pendiente decisión",
    ],
)

# --- BLOQUE 5: Productos ---
b5 = {}
cats = env["product.category"].search([("name", "=", "Inventario"), ("parent_id", "=", False)])
children = env["product.category"].search([("parent_id", "=", cats.id)]) if cats else env["product.category"]
b5["official_categories"] = {"ok": len(children) >= 11, "value": len(children)}
products = env["product.product"].search([])
b5["products_count"] = {"ok": True, "value": len(products)}
attrs = env["product.attribute"].search([])
b5["attributes"] = {"ok": True, "value": len(attrs)}
uom = env["uom.uom"].search([])
b5["uom_count"] = {"ok": len(uom) >= 1, "value": len(uom)}
report["blocks"]["block5_products"] = block_result(
    "products",
    b5,
    [
        "Catálogo completo: NO cargado (por diseño)",
        "Marcas/fabricantes: pendiente estructura",
        "Códigos barras: pendiente catálogo",
    ],
)

# --- BLOQUE 6: Contabilidad ---
b6 = {}
journals = env["account.journal"].search([("company_id", "=", company.id)])
b6["journals"] = {"ok": len(journals) >= 8, "value": journals.mapped(lambda j: f"{j.code}:{j.type}")}
taxes = env["account.tax"].search([("company_id", "=", company.id)])
b6["taxes"] = {"ok": len(taxes) >= 14, "value": len(taxes)}
accounts = env["account.account"].search([])
b6["accounts"] = {"ok": len(accounts) >= 200, "value": len(accounts)}
fp = env["account.fiscal.position"].search([])
b6["fiscal_positions"] = {"ok": len(fp) >= 1, "value": len(fp)}
pm_lines = env["account.payment.method.line"].search([])
b6["payment_methods"] = {"ok": len(pm_lines) >= 3, "value": [l.name for l in pm_lines]}
report["blocks"]["block6_accounting"] = block_result(
    "accounting",
    b6,
    ["Validación contador oficial pendiente para cuentas automáticas producto"],
)

# --- BLOQUE 7: Localización RD ---
b7 = {}
fiscal_enabled = getattr(company, "justech_do_fiscal_enabled", False)
b7["fiscal_enabled"] = {"ok": bool(fiscal_enabled), "value": fiscal_enabled}
doc_types = env["justech.do.fiscal.document.type"].search([])
b7["fiscal_doc_types"] = {"ok": len(doc_types) >= 6, "value": len(doc_types)}
ranges = env["justech.do.ncf.range"].search([])
b7["ncf_ranges"] = {"ok": True, "value": len(ranges)}
sale_j = env["account.journal"].search(
    [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
)
ncf_journal = bool(sale_j and getattr(sale_j, "justech_do_use_ncf", False))
b7["sale_journal_ncf"] = {
    "ok": ncf_journal or len(ranges) == 0,
    "value": ncf_journal,
}
report["blocks"]["block7_dominican"] = block_result(
    "dominican",
    b7,
    [
        "Rangos NCF DGII: pendiente números autorizados Hellenia",
        "Responsable fiscal funcional: pendiente usuario Contabilidad",
    ]
    if len(ranges) == 0
    else [],
)

# --- BLOQUE 8: Reportes ---
b8 = {}
mods = {
    "account_reports": env["ir.module.module"].search([("name", "=", "account_reports")], limit=1).state,
    "justech_l10n_do_reports": env["ir.module.module"]
    .search([("name", "=", "justech_l10n_do_reports")], limit=1)
    .state,
    "l10n_do_reports": env["ir.module.module"].search([("name", "=", "l10n_do_reports")], limit=1).state,
}
b8["report_modules"] = {"ok": all(v == "installed" for v in mods.values()), "value": mods}
report["blocks"]["block8_reports"] = block_result(
    "reports",
    b8,
    ["Catálogo completo documentado en REPORT_CATALOG.md"],
)

# --- BLOQUE 9: Sistema ---
b9 = {}
smtp = env["ir.mail_server"].search([])
b9["smtp_servers"] = {"ok": True, "value": len(smtp)}
crons_active = env["ir.cron"].search_count([("active", "=", True)])
b9["crons_active"] = {"ok": True, "value": crons_active}
b9["users_active"] = {
    "ok": len(users) <= 2,
    "value": users.mapped("login"),
}
report["blocks"]["block9_system"] = block_result(
    "system",
    b9,
    [
        "SMTP: pendiente",
        "Producción odoo.hellenia.cloud: documentado, no desplegado",
    ],
)

# --- BLOQUE 10: Datos piloto ---
b10 = {}
pilot_customers = env["res.partner"].search([("ref", "ilike", "UAT-PILOT%"), ("customer_rank", ">", 0)])
pilot_vendors = env["res.partner"].search([("ref", "ilike", "UAT-PILOT%"), ("supplier_rank", ">", 0)])
pilot_products = env["product.product"].search([("default_code", "ilike", "UAT-PILOT%")])
b10["pilot_customers"] = {"ok": len(pilot_customers) >= 1, "value": len(pilot_customers)}
b10["pilot_vendors"] = {"ok": len(pilot_vendors) >= 1, "value": len(pilot_vendors)}
b10["pilot_products"] = {"ok": len(pilot_products) >= 1, "value": len(pilot_products)}
report["blocks"]["block10_pilot_data"] = block_result(
    "pilot_data",
    b10,
    ["Catálogo definitivo NO cargado"],
)

# Summary
statuses = [b["status"] for b in report["blocks"].values()]
report["summary"] = {
    "pass": statuses.count("PASS"),
    "pass_obs": statuses.count("PASS CON OBSERVACIONES"),
    "fail": statuses.count("FAIL"),
    "overall": "FAIL" if "FAIL" in statuses else "PASS CON OBSERVACIONES" if "PASS CON OBSERVACIONES" in statuses else "PASS",
}
print("PHASE8_AUDIT:" + json.dumps(report, indent=2, ensure_ascii=False, default=str))
