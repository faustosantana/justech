#!/usr/bin/env python3
"""Fase 14 — Estabilización final TEST: fixes, demo data, validación, UX, PDF."""
from __future__ import annotations

import base64
import json
import os
import random
from datetime import date, datetime, timedelta, timezone

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

random.seed(1406)
PREFIX = "DEMO14"
today = date.today()
company = env.company
country_do = env.ref("base.do", raise_if_not_found=False)

report = {
    "phase": 14,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "fixes": {},
    "counts": {},
    "validations": {},
    "pdf": {},
    "ux": {},
    "ok": True,
    "errors": [],
    "warnings": [],
}


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


def warn(msg: str) -> None:
    report["warnings"].append(msg)


def ensure_module(name: str) -> None:
    mod = env["ir.module.module"].search([("name", "=", name)], limit=1)
    if mod and mod.state != "installed":
        mod.button_immediate_install()
        env.cr.commit()


# =============================================================================
# FASE A — CORRECCIONES
# =============================================================================
fiscal_mgr = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if fiscal_mgr and fiscal_mgr not in env.user.group_ids:
    env.user.write({"group_ids": [Command.link(fiscal_mgr.id)]})

orphan = 0
for att in env["ir.attachment"].sudo().search([("store_fname", "!=", False), ("type", "=", "binary")]):
    path = att._full_path(att.store_fname)
    if path and not os.path.exists(path):
        att.unlink()
        orphan += 1
env.cr.commit()
report["fixes"]["orphan_attachments_removed"] = orphan

try:
    env["ir.qweb"]._pregenerate_assets_bundles()
    report["fixes"]["assets_regenerated"] = True
except Exception as exc:
    warn(f"assets: {exc}")
    report["fixes"]["assets_regenerated"] = False

logo_path = "/mnt/custom/hellenia_base/static/img/hellenia_logo.jpg"
if os.path.exists(logo_path):
    company.write({"logo": base64.b64encode(open(logo_path, "rb").read())})

company.write(
    {
        "phone": company.phone or "809-555-0100",
        "email": company.email or "info@hellenia.cloud",
        "website": company.website or "https://hellenia.cloud",
        "hellenia_terms_conditions": company.hellenia_terms_conditions
        or "<p>Condiciones comerciales estándar Hellenia. Datos ficticios de demostración.</p>",
        "hellenia_legal_notice": company.hellenia_legal_notice
        or "<p>Hellenia, S.R.L. — Documento generado electrónicamente.</p>",
        "hellenia_social_whatsapp": company.hellenia_social_whatsapp or "809-555-0100",
        "hellenia_social_instagram": company.hellenia_social_instagram or "@hellenia_rd",
    }
)

for mod in ("hellenia_ui", "hellenia_reports"):
    ensure_module(mod)

try:
    env["hellenia.ui.menu.customizer"].apply_menu_labels()
    env["hellenia.ui.menu.customizer"].hide_unused_menus()
    report["fixes"]["hellenia_ui_applied"] = True
except Exception as exc:
    warn(f"hellenia_ui: {exc}")

# Idioma empresa
lang = env["res.lang"].search([("code", "=", "es_DO")], limit=1)
if lang and not lang.active:
    lang.active = True
company.partner_id.lang = "es_DO"
env.user.lang = "es_DO"

# Smoke create/search (cotización)
try:
    p = env["res.partner"].with_context(default_customer_rank=1).create(
        {"name": f"{PREFIX} Smoke Cliente", "vat": "13100099901", "country_id": country_do.id if country_do else False}
    )
    hits = env["res.partner"].name_search(f"{PREFIX} Smoke", limit=5)
    report["fixes"]["partner_create_search"] = {"ok": True, "id": p.id, "hits": len(hits)}
except Exception as exc:
    err(f"partner create/search: {exc}")

tax_sale = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale"), ("active", "=", True)],
    limit=1,
)
tax_purchase = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "purchase"), ("active", "=", True)],
    limit=1,
)
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)
if journal_sale:
    journal_sale.justech_do_use_ncf = True

doc_b01 = env.ref("justech_l10n_do_base.doc_type_b01", raise_if_not_found=False)
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02", raise_if_not_found=False)
doc_b03 = env.ref("justech_l10n_do_base.doc_type_b03", raise_if_not_found=False)
doc_b04 = env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False)


def ensure_ncf(doc, start, end, journals=None):
    if not doc:
        return False
    rng = env["justech.do.ncf.range"].search(
        [("document_type_id", "=", doc.id), ("state", "=", "active"), ("company_id", "=", company.id)],
        limit=1,
    )
    if rng and rng.next_sequence <= rng.sequence_end - 50:
        return rng
    vals = {
        "name": f"{PREFIX} {doc.prefix}",
        "document_type_id": doc.id,
        "company_id": company.id,
        "sequence_start": start,
        "sequence_end": end,
        "next_sequence": start,
        "date_from": today.replace(month=1, day=1),
        "date_to": today.replace(month=12, day=31),
    }
    if journals:
        vals["journal_ids"] = [Command.set(journals)]
    new = env["justech.do.ncf.range"].create(vals)
    new.action_activate()
    env.cr.commit()
    return env["justech.do.ncf.range"].search(
        [("document_type_id", "=", doc.id), ("state", "=", "active")], limit=1
    )


for doc, start, end in (
    (doc_b01, 10000, 10999),
    (doc_b02, 20000, 20999),
    (doc_b03, 30000, 30999),
    (doc_b04, 40000, 40999),
):
    ensure_ncf(doc, start, end, journal_sale.ids if journal_sale else None)

# =============================================================================
# FASE B — DATOS DEMO
# =============================================================================
ProductCategory = env["product.category"]
categories = []
for i in range(1, 21):
    ref = f"{PREFIX}-CAT-{i:02d}"
    cat = ProductCategory.search([("name", "=", f"Categoría Demo {i:02d}")], limit=1)
    if not cat:
        cat = ProductCategory.create({"name": f"Categoría Demo {i:02d}"})
    categories.append(cat)

brand_attr = env["product.attribute"].search([("name", "=", "Marca Hellenia")], limit=1)
if not brand_attr:
    brand_attr = env["product.attribute"].create({"name": "Marca Hellenia", "create_variant": "no_variant"})
brand_values = []
for i in range(1, 11):
    val = env["product.attribute.value"].search(
        [("attribute_id", "=", brand_attr.id), ("name", "=", f"Marca {i:02d}")], limit=1
    )
    if not val:
        val = env["product.attribute.value"].create({"attribute_id": brand_attr.id, "name": f"Marca {i:02d}"})
    brand_values.append(val)

customers_b01, customers_b02 = [], []
for i in range(1, 101):
    ref = f"{PREFIX}-CUST-{i:03d}"
    existing = env["res.partner"].search([("ref", "=", ref)], limit=1)
    if existing:
        (customers_b01 if existing.vat else customers_b02).append(existing)
        continue
    has_rnc = i <= 70
    vals = {
        "name": f"Cliente Demo {i:03d}",
        "ref": ref,
        "customer_rank": 1,
        "email": f"cliente{i:03d}@demo.hellenia.local",
        "phone": f"809-555-{i:04d}"[-8:],
        "country_id": country_do.id if country_do else False,
    }
    if has_rnc:
        vals["vat"] = f"131{i:08d}"[:11]
    partner = env["res.partner"].create(vals)
    (customers_b01 if has_rnc else customers_b02).append(partner)
    if i % 25 == 0:
        env.cr.commit()

vendors = []
for i in range(1, 41):
    ref = f"{PREFIX}-VEND-{i:03d}"
    existing = env["res.partner"].search([("ref", "=", ref)], limit=1)
    if existing:
        vendors.append(existing)
        continue
    vendors.append(
        env["res.partner"].create(
            {
                "name": f"Proveedor Demo {i:03d}",
                "ref": ref,
                "supplier_rank": 1,
                "vat": f"401{i:08d}"[:11],
                "country_id": country_do.id if country_do else False,
            }
        )
    )
    if i % 20 == 0:
        env.cr.commit()

products = []
for i in range(1, 301):
    code = f"{PREFIX}-PROD-{i:04d}"
    existing = env["product.product"].search([("default_code", "=", code)], limit=1)
    if existing:
        products.append(existing)
        continue
    cat = categories[i % len(categories)]
    brand = brand_values[i % len(brand_values)]
    tmpl = env["product.template"].create(
        {
            "name": f"Producto Demo {i:04d}",
            "default_code": code,
            "type": "consu",
            "is_storable": True,
            "list_price": 500.0 + (i % 50) * 100,
            "standard_price": 200.0 + (i % 30) * 50,
            "categ_id": cat.id,
            "sale_ok": True,
            "purchase_ok": True,
            "taxes_id": [Command.set(tax_sale.ids)] if tax_sale else [],
            "supplier_taxes_id": [Command.set(tax_purchase.ids)] if tax_purchase else [],
            "attribute_line_ids": [
                Command.create({"attribute_id": brand_attr.id, "value_ids": [Command.set([brand.id])]})
            ],
        }
    )
    products.append(tmpl.product_variant_ids[:1])
    if i % 50 == 0:
        env.cr.commit()

warehouses = list(env["stock.warehouse"].search([("company_id", "=", company.id)]))
for i in range(len(warehouses), 5):
    wh = env["stock.warehouse"].create(
        {
            "name": f"Almacén Demo {i + 1}",
            "code": f"WH{i + 1}",
            "company_id": company.id,
        }
    )
    warehouses.append(wh)
main_wh = warehouses[0]

for prod in products[:150]:
    qty = 10 + (prod.id % 40)
    q = env["stock.quant"].search(
        [("product_id", "=", prod.id), ("location_id", "=", main_wh.lot_stock_id.id)], limit=1
    )
    if not q:
        env["stock.quant"].with_context(inventory_mode=True).create(
            {"product_id": prod.id, "location_id": main_wh.lot_stock_id.id, "inventory_quantity": qty}
        ).action_apply_inventory()
env.cr.commit()

pricelists = list(env["product.pricelist"].search([("company_id", "in", [company.id, False])], limit=5))
for i in range(len(pricelists), 5):
    pricelists.append(
        env["product.pricelist"].create(
            {"name": f"Lista Precios Demo {i + 1}", "currency_id": company.currency_id.id}
        )
    )

sellers = []
sales_group = env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)
for i in range(1, 21):
    login = f"vendedor{i:02d}.demo"
    user = env["res.users"].search([("login", "=", login)], limit=1)
    if not user:
        user = env["res.users"].create(
            {
                "name": f"Vendedor Demo {i:02d}",
                "login": login,
                "email": f"{login}@demo.hellenia.local",
                "group_ids": [Command.link(sales_group.id)] if sales_group else [],
            }
        )
    sellers.append(user)

quotations, orders = [], []
target_quotes = 50
existing_quotes = env["sale.order"].search_count([("name", "like", "S%"), ("state", "in", ["draft", "sent"])])
to_create = max(0, target_quotes - existing_quotes)

customers_all = customers_b01 + customers_b02
for n in range(to_create):
    cust = random.choice(customers_b01 or customers_all)
    prod = random.choice(products)
    seller = random.choice(sellers) if sellers else env.user
    so = env["sale.order"].create(
        {
            "partner_id": cust.id,
            "user_id": seller.id,
            "pricelist_id": random.choice(pricelists).id,
        }
    )
    env["sale.order.line"].create(
        {
            "order_id": so.id,
            "product_id": prod.id,
            "product_uom_qty": 1 + n % 5,
            "price_unit": prod.list_price,
        }
    )
    quotations.append(so)
    if n < 40:
        so.action_confirm()
        orders.append(so)
    if n % 10 == 0:
        env.cr.commit()

invoices_b01, invoices_b02, credits, debits = [], [], [], []
for i in range(30):
    cust = customers_b01[i % len(customers_b01)] if customers_b01 else random.choice(customers_all)
    prod = products[i % len(products)]
    so = env["sale.order"].create({"partner_id": cust.id})
    env["sale.order.line"].create(
        {"order_id": so.id, "product_id": prod.id, "product_uom_qty": 2, "price_unit": 1500.0}
    )
    so.action_confirm()
    so._create_invoices()
    inv = so.invoice_ids[:1]
    inv.invoice_date = today - timedelta(days=i % 20)
    inv.action_post()
    invoices_b01.append(inv)

for i in range(30):
    cust = customers_b02[i % len(customers_b02)] if customers_b02 else random.choice(customers_all)
    prod = products[(i + 30) % len(products)]
    so = env["sale.order"].create({"partner_id": cust.id})
    env["sale.order.line"].create(
        {"order_id": so.id, "product_id": prod.id, "product_uom_qty": 1, "price_unit": 800.0}
    )
    so.action_confirm()
    so._create_invoices()
    inv = so.invoice_ids[:1]
    inv.invoice_date = today - timedelta(days=i % 15)
    inv.action_post()
    invoices_b02.append(inv)

posted_invs = (invoices_b01 + invoices_b02)[:30]
for i, origin in enumerate(posted_invs[:15]):
    if not doc_b04:
        break
    credit = env["account.move"].create(
        {
            "move_type": "out_refund",
            "partner_id": origin.partner_id.id,
            "journal_id": journal_sale.id,
            "invoice_date": today,
            "reversed_entry_id": origin.id,
            "justech_do_document_type_id": doc_b04.id,
            "invoice_line_ids": [
                Command.create(
                    {
                        "name": "NC demo",
                        "quantity": 1,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(tax_sale.ids)] if tax_sale else [],
                    }
                )
            ],
        }
    )
    credit.action_post()
    credits.append(credit)

for i, origin in enumerate(posted_invs[15:30]):
    if not doc_b03:
        break
    debit = env["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": origin.partner_id.id,
            "journal_id": journal_sale.id,
            "invoice_date": today,
            "debit_origin_id": origin.id,
            "justech_do_document_type_id": doc_b03.id,
            "invoice_line_ids": [
                Command.create(
                    {
                        "name": "ND demo",
                        "quantity": 1,
                        "price_unit": 75.0,
                        "tax_ids": [Command.set(tax_sale.ids)] if tax_sale else [],
                    }
                )
            ],
        }
    )
    debit.action_post()
    debits.append(debit)

payments_in, payments_out = [], []
for inv in (invoices_b01 + invoices_b02)[:30]:
    if inv.amount_residual > 0 and inv.state == "posted":
        try:
            wiz = env["account.payment.register"].with_context(active_model="account.move", active_ids=inv.ids).create({})
            pay = wiz._create_payments()
            payments_in.extend(pay)
        except Exception as exc:
            warn(f"cobro {inv.name}: {exc}")

purchases, receptions = [], []
for i in range(40):
    vendor = vendors[i % len(vendors)]
    prod = products[(i + 50) % len(products)]
    po = env["purchase.order"].create({"partner_id": vendor.id})
    env["purchase.order.line"].create(
        {"order_id": po.id, "product_id": prod.id, "product_qty": 3 + i % 5, "price_unit": prod.standard_price or 100}
    )
    with env.cr.savepoint():
        po.button_confirm()
    purchases.append(po)
    pick = env["stock.picking"].search(
        [("purchase_id", "=", po.id), ("picking_type_code", "=", "incoming")], limit=1
    )
    if pick and pick.state not in ("done", "cancel") and i < 30:
        for move in pick.move_ids:
            move.quantity = move.product_uom_qty
        pick.button_validate()
        receptions.append(pick)
    bill = po.invoice_ids[:1]
    if not bill:
        bill = env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": vendor.id,
                "journal_id": journal_purchase.id,
                "invoice_date": today,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": prod.name,
                            "quantity": 3,
                            "price_unit": prod.standard_price or 100,
                            "tax_ids": [Command.set(tax_purchase.ids)] if tax_purchase else [],
                        }
                    )
                ],
            }
        )
    if bill.state == "draft":
        bill.action_post()
    if bill.amount_residual > 0 and i < 30:
        try:
            wiz = env["account.payment.register"].with_context(active_model="account.move", active_ids=bill.ids).create({})
            payments_out.extend(wiz._create_payments())
        except Exception as exc:
            warn(f"pago {bill.name}: {exc}")
    if i % 10 == 0:
        env.cr.commit()

report["counts"] = {
    "customers": env["res.partner"].search_count([("ref", "like", f"{PREFIX}-CUST-%")]),
    "vendors": env["res.partner"].search_count([("ref", "like", f"{PREFIX}-VEND-%")]),
    "products": env["product.product"].search_count([("default_code", "like", f"{PREFIX}-PROD-%")]),
    "categories": len(categories),
    "brands": len(brand_values),
    "warehouses": len(warehouses),
    "pricelists": len(pricelists),
    "sellers": len(sellers),
    "quotations": env["sale.order"].search_count([("state", "in", ["draft", "sent"])]),
    "orders": env["sale.order"].search_count([("state", "=", "sale")]),
    "invoices_b01": len(invoices_b01),
    "invoices_b02": len(invoices_b02),
    "credit_notes": len(credits),
    "debit_notes": len(debits),
    "purchases": len(purchases),
    "receptions": len(receptions),
    "payments_in": len(payments_in),
    "payments_out": len(payments_out),
}

# =============================================================================
# FASE C — VALIDACIÓN
# =============================================================================
targets = {
    "customers": 100,
    "vendors": 40,
    "products": 300,
    "categories": 20,
    "brands": 10,
    "warehouses": 5,
    "pricelists": 5,
    "sellers": 20,
    "invoices_b01": 30,
    "invoices_b02": 30,
    "credit_notes": 15,
    "debit_notes": 15,
    "purchases": 40,
    "receptions": 30,
    "payments_in": 20,
    "payments_out": 20,
}
for key, min_val in targets.items():
    actual = report["counts"].get(key, 0)
    report["validations"][f"count_{key}"] = actual >= min_val
    if actual < min_val:
        warn(f"count {key}: {actual} < {min_val}")

report["validations"]["accounting_balance"] = abs(sum(env["account.move.line"].search([]).mapped("balance"))) < 1.0
report["validations"]["stock_quants"] = env["stock.quant"].search_count([("quantity", ">", 0)]) > 0
report["validations"]["ncf_on_invoice"] = all(
    inv.justech_do_ncf for inv in (invoices_b01[:5] + invoices_b02[:5]) if inv.state == "posted"
)

for rtype in ("606", "607", "608"):
    try:
        wiz = env["justech.do.fiscal.report.wizard"].create(
            {"report_type": rtype, "date_from": today.replace(day=1), "date_to": today}
        )
        wiz.action_generate()
        report["validations"][f"report_{rtype}"] = True
    except Exception as exc:
        report["validations"][f"report_{rtype}"] = False
        err(f"reporte {rtype}: {exc}")

# =============================================================================
# FASE D — UX
# =============================================================================
report["ux"]["company_lang"] = company.partner_id.lang
report["ux"]["user_lang"] = env.user.lang
crm_menu = env.ref("crm.crm_menu_root", raise_if_not_found=False)
report["ux"]["crm_hidden"] = not crm_menu.active if crm_menu else True
report["ux"]["account_menu"] = env.ref("account.menu_finance").name

# =============================================================================
# FASE E — PDF CORPORATIVOS
# =============================================================================
layout = company.external_report_layout_id
report["pdf"]["layout"] = layout.key if layout else None
samples = []
if quotations:
    samples.append(("quotation", "sale.report_saleorder", quotations[0].ids))
if orders:
    samples.append(("order", "sale.report_saleorder", orders[0].ids))
if invoices_b01:
    samples.append(("invoice_b01", "account.account_invoices", invoices_b01[0].ids))
if credits:
    samples.append(("credit_note", "account.account_invoices", credits[0].ids))
if purchases:
    samples.append(("purchase", "purchase.report_purchaseorder", purchases[0].ids))
if receptions:
    pick = env["stock.picking"].search([("state", "=", "done")], limit=1)
    if pick:
        samples.append(("delivery", "stock.report_deliveryslip", pick.ids))

for label, report_xmlid, ids in samples:
    try:
        pdf, _fmt = env["ir.actions.report"]._render_qweb_pdf(report_xmlid, ids)
        report["pdf"][label] = len(pdf) > 1000
        if len(pdf) < 1000:
            warn(f"PDF {label} muy pequeño")
    except Exception as exc:
        report["pdf"][label] = False
        err(f"PDF {label}: {exc}")

report["validations"]["pdf_all"] = all(v for k, v in report["pdf"].items() if k != "layout" and isinstance(v, bool))
report["ok"] = report["ok"] and report["validations"].get("accounting_balance", False)
report["ok"] = report["ok"] and report["validations"].get("ncf_on_invoice", False)
report["ok"] = report["ok"] and all(report["validations"].get(f"report_{t}", False) for t in ("606", "607", "608"))
report["ok"] = report["ok"] and report["validations"].get("pdf_all", False)
report["ok"] = report["ok"] and report["fixes"].get("partner_create_search", {}).get("ok", False)
critical_counts = ("customers", "vendors", "products", "invoices_b01", "invoices_b02", "purchases")
report["ok"] = report["ok"] and all(report["validations"].get(f"count_{k}", False) for k in critical_counts)

print("PHASE14:" + json.dumps(report, ensure_ascii=False, indent=2))
