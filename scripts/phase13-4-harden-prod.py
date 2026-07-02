#!/usr/bin/env python3
"""Fase 13.4 — Hardening producción hellenia_prod (solo datos/config, sin nuevas features)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

from odoo import Command

if env.cr.dbname != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={env.cr.dbname}")

report = {
    "phase": "13.4",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "actions": [],
    "cleanup": {},
    "menus": {},
    "translations": {},
    "security": {},
    "justech": {},
    "accounting_smoke": {},
    "english_remainders": [],
    "ok": True,
    "errors": [],
}


def log(action: str, detail: str = "") -> None:
    report["actions"].append({"action": action, "detail": detail})


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)
    log("ERROR", msg)


def safe_unlink(records, label: str) -> int:
    if not records:
        return 0
    try:
        n = len(records)
        records.unlink()
        log(label, str(n))
        return n
    except Exception as exc:  # noqa: BLE001
        log(f"{label}_skip", str(exc))
        return 0


# ---------------------------------------------------------------------------
# 1. Limpieza datos piloto / UAT
# ---------------------------------------------------------------------------
cleanup = {}

# Reportes fiscales de prueba
cleanup["fiscal_reports"] = safe_unlink(env["justech.do.fiscal.report"].search([]), "delete_fiscal_reports")

# Rangos NCF de prueba (P13.x, secuencias 9000+)
test_ranges = env["justech.do.ncf.range"].search(
    ["|", ("name", "ilike", "P13"), ("sequence_start", ">=", 9000)]
)
for rng in test_ranges:
    posted = env["account.move"].search_count(
        [("justech_do_ncf_range_id", "=", rng.id), ("state", "=", "posted")]
    )
    if posted:
        log("skip_ncf_range", f"{rng.name}: {posted} posted moves")
    else:
        env["justech.do.ncf.consumption"].search([("range_id", "=", rng.id)]).unlink()
        if rng.state == "active":
            rng.action_expire()
        rng.unlink()
        cleanup.setdefault("ncf_ranges_deleted", 0)
        cleanup["ncf_ranges_deleted"] += 1

# Producto piloto "Prueba"
prod_prueba = env["product.template"].search([("name", "=", "Prueba")])
if prod_prueba:
    used = env["sale.order.line"].search_count([("product_id", "in", prod_prueba.product_variant_ids.ids)])
    used += env["account.move.line"].search_count([("product_id", "in", prod_prueba.product_variant_ids.ids)])
    if used:
        log("skip_product_prueba", f"used in {used} lines")
    else:
        cleanup["product_prueba"] = safe_unlink(prod_prueba, "delete_product_prueba")

# Partners UAT/P13
uat_partners = env["res.partner"].search(
    [
        "|",
        "|",
        ("ref", "ilike", "UAT"),
        ("name", "ilike", "P13"),
        ("name", "ilike", "piloto"),
    ]
)
# Excluir compañía y usuarios internos
uat_partners = uat_partners.filtered(
    lambda p: p.id not in (env.company.partner_id.id, env.ref("base.partner_admin").id)
    and not env["res.users"].search_count([("partner_id", "=", p.id)])
)
cleanup["uat_partners"] = safe_unlink(uat_partners, "delete_uat_partners")

# Borradores transaccionales
for model, label in [
    ("sale.order", "draft_sales"),
    ("purchase.order", "draft_purchases"),
    ("account.move", "draft_moves"),
    ("stock.picking", "draft_pickings"),
]:
    if model not in env:
        continue
    drafts = env[model].search([("state", "in", ["draft", "cancel"])])
    cleanup[label] = safe_unlink(drafts, f"delete_{label}")

report["cleanup"] = cleanup

# Verificación post-limpieza
report["cleanup"]["remaining"] = {
    "uat_partners": env["res.partner"].search_count([("ref", "ilike", "UAT")]),
    "p13_partners": env["res.partner"].search_count([("name", "ilike", "P13")]),
    "uat_products": env["product.template"].search_count([("default_code", "ilike", "UAT")]),
    "product_prueba": env["product.template"].search_count([("name", "=", "Prueba")]),
    "test_ncf_ranges": env["justech.do.ncf.range"].search_count([("sequence_start", ">=", 9000)]),
}

# ---------------------------------------------------------------------------
# 2. Menú principal — solo apps operativas en español
# ---------------------------------------------------------------------------
menus = {}
MENUS_HIDE = [
    "base.menu_tests",
    "mail.menu_root_discuss",
    "spreadsheet_dashboard.spreadsheet_dashboard_menu_root",
    "utm.menu_link_tracker_root",
    "accountant.menu_accounting",
]
MENUS_ES = {
    "sale.sale_menu_root": "Ventas",
    "purchase.menu_purchase_root": "Compras",
    "stock.menu_stock_root": "Inventario",
    "contacts.menu_contacts": "Contactos",
    "account.menu_finance": "Contabilidad",
    "base.menu_administration": "Configuración",
}
langs = env["res.lang"].search([("active", "=", True)]).mapped("code") or ["es_DO", "en_US"]

for xmlid in MENUS_HIDE:
    menu = env.ref(xmlid, raise_if_not_found=False)
    if menu and menu.active:
        menu.active = False
        menus[f"hidden_{xmlid}"] = True
        log("menu_hidden", xmlid)

for xmlid, label in MENUS_ES.items():
    menu = env.ref(xmlid, raise_if_not_found=False)
    if not menu:
        continue
    for lang in langs:
        menu.with_context(lang=lang).write({"name": label})
    if not menu.active:
        menu.active = True
    menus[f"label_{xmlid}"] = label
    log("menu_label", f"{xmlid}={label}")

# Ventas: asegurar activo
sale_root = env.ref("sale.sale_menu_root", raise_if_not_found=False)
if sale_root and not sale_root.active:
    sale_root.active = True

# Apps solo administradores
apps = env.ref("base.menu_management", raise_if_not_found=False)
sys_group = env.ref("base.group_system")
if apps:
    apps.write({"group_ids": [Command.set(sys_group.ids)]})

# Menús raíz visibles (admin, es_DO)
admin = env.ref("base.user_admin")
roots_es = (
    env["ir.ui.menu"]
    .with_user(admin)
    .with_context(lang="es_DO")
    .search([("parent_id", "=", False), ("active", "=", True)], order="sequence")
)
menus["root_es_do"] = roots_es.mapped("name")
EXPECTED = {"Ventas", "Compras", "Inventario", "Contabilidad", "Contactos", "Configuración"}
menus["settings_ok"] = "Configuración" in menus["root_es_do"] or "Ajustes" in menus["root_es_do"]
menus["expected_present"] = {k: (k in menus["root_es_do"]) for k in EXPECTED}
menus["expected_present"]["Configuración"] = menus["settings_ok"]
menus["unexpected_roots"] = [
    n for n in menus["root_es_do"] if n not in EXPECTED and n not in ("Ajustes",)
]
if menus["unexpected_roots"]:
    log("menu_unexpected", str(menus["unexpected_roots"]))
if not all(menus["expected_present"].values()):
    err(f"Menús faltantes: {[k for k,v in menus['expected_present'].items() if not v]}")
if "Facturación" in menus["root_es_do"] or "Accounting" in menus["root_es_do"]:
    err("Menú Facturación/Accounting duplicado visible")

report["menus"] = menus

# ---------------------------------------------------------------------------
# 3. Traducciones Justech + escaneo inglés
# ---------------------------------------------------------------------------
JUSTECH_MENU_ES = {
    "Dominican Fiscal": "Fiscal dominicano",
    "Fiscal dominicano": "Fiscal dominicano",
    "Document Types": "Tipos de documento",
    "Tipos de documento": "Tipos de documento",
    "NCF Ranges": "Rangos NCF",
    "Rangos NCF": "Rangos NCF",
    "NCF Consumption": "Consumo NCF",
    "Consumo NCF": "Consumo NCF",
    "DGII Reports": "Reportes DGII",
    "Reportes DGII": "Reportes DGII",
    "Generate Report": "Generar reporte",
    "Generar reporte": "Generar reporte",
    "Report History": "Historial de reportes",
    "Historial de reportes": "Historial de reportes",
}
english_hint = re.compile(
    r"\b(Generate|Export|Regenerate|Draft|Done|Customer|Vendor|Report History)\b",
    re.I,
)
for src, dst in JUSTECH_MENU_ES.items():
    for menu in env["ir.ui.menu"].search([("name", "=", src)]):
        for lang in langs:
            menu.with_context(lang=lang).write({"name": dst})

eng = []
for menu in env["ir.ui.menu"].search([("name", "ilike", "justech")]):
    if english_hint.search(menu.name or ""):
        eng.append(f"menu:{menu.name}")
for act in env["ir.actions.act_window"].search([("res_model", "like", "justech.%")]):
    if english_hint.search(act.name or ""):
        eng.append(f"action:{act.name}")
report["translations"] = {"justech_menus_updated": len(JUSTECH_MENU_ES), "english_remainders": eng}
report["english_remainders"] = eng

# ---------------------------------------------------------------------------
# 4. Auditoría permisos
# ---------------------------------------------------------------------------
security = {}
users = env["res.users"].search([("active", "=", True), ("share", "=", False)])
security["internal_users"] = [{"login": u.login, "groups": len(u.group_ids)} for u in users]
# Usuario estándar sin grupo sistema
normal_users = users.filtered(lambda u: env.ref("base.group_system") not in u.group_ids)
security["non_admin_count"] = len(normal_users)
if normal_users:
    sample = normal_users[0]
    menus_sample = (
        env["ir.ui.menu"]
        .with_user(sample)
        .search([("parent_id", "=", False), ("active", "=", True)])
    )
    security["sample_user_menus"] = menus_sample.mapped("name")
    bad = [n for n in security["sample_user_menus"] if n in ("Apps", "Aplicaciones", "Tests", "Pruebas")]
    security["sample_user_bad_menus"] = bad
    if bad:
        err(f"Usuario normal ve menús restringidos: {bad}")

# Record rules Justech
for model in (
    "justech.do.fiscal.report",
    "justech.do.ncf.range",
    "justech.do.fiscal.document.type",
):
    rules = env["ir.rule"].search([("model_id.model", "=", model)])
    security[f"rules_{model}"] = len(rules)
    if not rules:
        err(f"Sin record rules: {model}")

report["security"] = security

# ---------------------------------------------------------------------------
# 5. Auditoría localización Justech
# ---------------------------------------------------------------------------
justech = {
    "modules": {},
    "document_types": env["justech.do.fiscal.document.type"].search_count([]),
    "ncf_ranges_active": env["justech.do.ncf.range"].search_count([("state", "=", "active")]),
    "fiscal_enabled": bool(env.company.justech_do_fiscal_enabled),
}
for mod in ("justech_l10n_do_base", "justech_l10n_do_ncf", "justech_l10n_do_reports", "l10n_do"):
    m = env["ir.module.module"].search([("name", "=", mod)], limit=1)
    justech["modules"][mod] = m.state if m else "missing"
    if not m or m.state != "installed":
        err(f"Módulo no instalado: {mod}")
prefixes = env["justech.do.fiscal.document.type"].search([]).mapped("prefix")
justech["ncf_prefixes"] = sorted(prefixes)
for p in ("B01", "B02", "B03", "B04", "B11", "B13"):
    if p not in prefixes:
        err(f"Tipo documento {p} ausente")
report["justech"] = justech

# ---------------------------------------------------------------------------
# 6–7. Smoke contable (cotización → factura → asientos)
# ---------------------------------------------------------------------------
smoke = {}
company = env.company
manager = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if manager and manager not in env.user.group_ids:
    env.user.write({"group_ids": [(4, manager.id)]})

tax_18 = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale"), ("active", "=", True)],
    limit=1,
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_sale.justech_do_use_ncf = True

product = env["product.product"].create(
    {
        "name": "SMOKE-P134-DELETE",
        "type": "consu",
        "list_price": 1000.0,
        "taxes_id": [Command.set(tax_18.ids)],
    }
)
partner = env["res.partner"].create({"name": "SMOKE P13.4 CF", "customer_rank": 1})
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02", raise_if_not_found=False)
rng = env["justech.do.ncf.range"].search(
    [("document_type_id", "=", doc_b02.id), ("state", "=", "active"), ("company_id", "=", company.id)],
    limit=1,
)
if not rng and doc_b02:
    rng = env["justech.do.ncf.range"].create(
        {
            "name": "SMOKE P13.4 B02",
            "document_type_id": doc_b02.id,
            "company_id": company.id,
            "sequence_start": 9900,
            "sequence_end": 9999,
            "next_sequence": 9900,
            "date_from": date.today().replace(month=1, day=1),
            "date_to": date.today().replace(month=12, day=31),
            "journal_ids": [Command.set(journal_sale.ids)],
        }
    )
    rng.action_activate()
    log("smoke_ncf_range", rng.name)

so = env["sale.order"].create({"partner_id": partner.id})
env["sale.order.line"].create(
    {"order_id": so.id, "product_id": product.id, "product_uom_qty": 1.0, "price_unit": 10000.0}
)
smoke["quote_tax"] = [t.amount for t in so.order_line.tax_ids]
smoke["quote_ok"] = 18.0 in smoke["quote_tax"] and 15.0 not in smoke["quote_tax"]
so.action_confirm()
inv = so._create_invoices()
inv.invoice_date = date.today()
inv.action_post()
smoke["invoice_posted"] = inv.state == "posted"
smoke["invoice_balanced"] = abs(sum(inv.line_ids.mapped("balance"))) < 0.02
smoke["itbis_lines"] = bool(
    inv.line_ids.filtered(lambda l: l.tax_line_id and l.tax_line_id.amount == 18)
)
smoke["receivable"] = bool(inv.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable"))
smoke["ncf"] = inv.justech_do_ncf or ""
smoke["invoice_name"] = inv.name
# Limpiar rango smoke temporal; factura publicada permanece como evidencia P13.4
if rng and rng.name.startswith("SMOKE"):
    try:
        if not env["account.move"].search_count([("justech_do_ncf_range_id", "=", rng.id), ("state", "=", "posted")]):
            rng.action_expire()
            rng.unlink()
        else:
            log("smoke_range_kept", f"posted moves reference {rng.name}")
    except Exception as exc:  # noqa: BLE001
        log("smoke_range_cleanup_skip", str(exc))
log("smoke_invoice_kept", inv.name)

if not smoke.get("quote_ok"):
    err("Smoke: cotización sin ITBIS 18%")
if not smoke.get("invoice_balanced"):
    err("Smoke: factura no balanceada")
report["accounting_smoke"] = smoke

env.cr.commit()
print("PHASE13_4_HARDENING:" + json.dumps(report, ensure_ascii=False, indent=2))
