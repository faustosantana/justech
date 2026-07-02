#!/usr/bin/env python3
"""Fase 16 — Go-Live: importación datos reales, usuarios, NCF, SMTP, limpieza y validación."""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

IMPORT_DIR = Path(os.environ.get("HELLENIA_IMPORT_DIR", "/opt/odoo-projects/hellenia/data/hellenia/import"))
LOGO_PATH = "/mnt/custom/hellenia_base/static/img/hellenia_logo.jpg"

ROLE_GROUPS = {
    "Gerencia General": (
        "sales_team.group_sale_manager",
        "purchase.group_purchase_manager",
        "stock.group_stock_manager",
        "account.group_account_readonly",
    ),
    "Contabilidad": (
        "account.group_account_manager",
        "justech_l10n_do_base.group_justech_do_fiscal_manager",
    ),
    "Caja": (
        "account.group_account_invoice",
        "justech_l10n_do_base.group_justech_do_fiscal_user",
    ),
    "Compras": (
        "purchase.group_purchase_user",
        "account.group_account_invoice",
        "justech_l10n_do_base.group_justech_do_fiscal_user",
    ),
    "Ventas": (
        "sales_team.group_sale_salesman",
        "account.group_account_invoice",
        "justech_l10n_do_base.group_justech_do_fiscal_user",
    ),
    "Inventario": ("stock.group_stock_user",),
    "Atención al cliente": ("sales_team.group_sale_salesman",),
    "Atencion al cliente": ("sales_team.group_sale_salesman",),
}

DOC_TYPE_BY_PREFIX = {
    "B01": "justech_l10n_do_base.doc_type_b01",
    "B02": "justech_l10n_do_base.doc_type_b02",
    "B03": "justech_l10n_do_base.doc_type_b03",
    "B04": "justech_l10n_do_base.doc_type_b04",
    "B11": "justech_l10n_do_base.doc_type_b11",
    "B13": "justech_l10n_do_base.doc_type_b13",
}

report = {
    "phase": "16",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "import_dir": str(IMPORT_DIR),
    "steps": {},
    "loaded": {},
    "pending_client": [],
    "ok": True,
    "errors": [],
}


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


def pending(msg: str) -> None:
    report["pending_client"].append(msg)


def read_csv(name: str) -> list[dict]:
    path = IMPORT_DIR / name
    if not path.exists():
        return []
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not row:
                continue
            first = next(iter(row.values()), "")
            if str(first).strip().startswith("#"):
                continue
            if not any(str(v).strip() for v in row.values()):
                continue
            rows.append({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return rows


def resolve_groups(role: str, groups_field: str = "") -> list:
    xmlids = []
    if groups_field:
        xmlids = [x.strip() for x in groups_field.split(";") if x.strip()]
    elif role in ROLE_GROUPS:
        xmlids = list(ROLE_GROUPS[role])
    groups = []
    for xid in xmlids:
        g = env.ref(xid, raise_if_not_found=False)
        if g:
            groups.append(g.id)
    return groups


# --- 1. Logo ---
company = env.company
logo_ok = bool(company.logo)
if not logo_ok and os.path.exists(LOGO_PATH):
    import base64

    company.write({"logo": base64.b64encode(open(LOGO_PATH, "rb").read())})
    logo_ok = True
    report["steps"]["logo"] = "loaded_from_module"
else:
    report["steps"]["logo"] = "already_present" if logo_ok else "missing_no_file"
if not logo_ok:
    pending("Logo empresa — cargar imagen oficial")

# --- 2. SMTP ---
smtp_host = os.environ.get("SMTP_HOST", "").strip()
smtp_user = os.environ.get("SMTP_USER", "").strip()
smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
smtp_from = os.environ.get("SMTP_FROM", smtp_user).strip()
smtp_port = int(os.environ.get("SMTP_PORT", "587") or "587")
smtp_ssl = os.environ.get("SMTP_SSL", "false").lower() in ("1", "true", "yes")

if smtp_host and smtp_user and smtp_pass:
    MailServer = env["ir.mail_server"]
    existing = MailServer.search([("smtp_host", "=", smtp_host), ("smtp_user", "=", smtp_user)], limit=1)
    vals = {
        "name": "Hellenia Corporativo",
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_pass": smtp_pass,
        "smtp_encryption": "ssl" if smtp_ssl else "starttls",
        "from_filter": smtp_from,
        "active": True,
    }
    if existing:
        existing.write(vals)
    else:
        MailServer.create(vals)
    env["ir.config_parameter"].sudo().set_param("mail.default.from", smtp_from)
    env["ir.config_parameter"].sudo().set_param("mail.catchall.domain", smtp_from.split("@")[-1] if "@" in smtp_from else "")
    report["steps"]["smtp"] = {"configured": True, "host": smtp_host, "user": smtp_user}
else:
    report["steps"]["smtp"] = {"configured": False}
    pending("SMTP corporativo — entregar credenciales (SMTP_HOST, SMTP_USER, SMTP_PASSWORD en .env)")

# --- 3. Usuarios reales ---
user_rows = read_csv("users.csv")
created_users = []
if not user_rows:
    pending("Usuarios reales — completar data/hellenia/import/users.csv según ROLE_MATRIX.md")
else:
    for row in user_rows:
        login = row.get("login", "")
        if not login:
            continue
        groups = resolve_groups(row.get("role_hellenia", ""), row.get("groups_odoo", ""))
        vals = {
            "name": row.get("name", login),
            "login": login,
            "email": row.get("email", login),
            "lang": row.get("lang", "es_DO"),
            "tz": row.get("tz", "America/Santo_Domingo"),
            "group_ids": [Command.set(groups)],
            "active": True,
        }
        user = env["res.users"].with_context(active_test=False).search([("login", "=", login)], limit=1)
        if user:
            user.write(vals)
            created_users.append({"login": login, "action": "updated"})
        else:
            vals["password"] = os.environ.get("DEFAULT_USER_PASSWORD", "ChangeMe-Hellenia-2026!")
            env["res.users"].create(vals)
            created_users.append({"login": login, "action": "created"})
report["loaded"]["users"] = created_users

# --- 4. Rangos NCF reales ---
ncf_rows = read_csv("ncf_rangos_dgii.csv")
ncf_created = []
journal_sale = env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
journal_purchase = env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1)

if not ncf_rows:
    pending("Rangos NCF DGII — completar data/hellenia/import/ncf_rangos_dgii.csv con autorizaciones reales")
else:
    Range = env["justech.do.ncf.range"]
    for row in ncf_rows:
        prefix = row.get("document_type_prefix", "").strip().upper()
        if not prefix or prefix.startswith("#"):
            continue
        doc_xid = DOC_TYPE_BY_PREFIX.get(prefix)
        doc = env.ref(doc_xid, raise_if_not_found=False) if doc_xid else None
        if not doc:
            err(f"NCF tipo desconocido: {prefix}")
            continue
        auth = row.get("authorization_number", "").strip()
        if not auth or "XXXX" in auth.upper() or auth.upper().startswith("AUTH-DGII"):
            err(f"NCF {prefix}: número de autorización DGII inválido o placeholder")
            continue
        start = int(row.get("sequence_start", "1"))
        end = int(row.get("sequence_end", "0"))
        if end < start:
            err(f"NCF {prefix}: secuencia inválida")
            continue
        journals = journal_sale if prefix in ("B01", "B02", "B03", "B04") else journal_purchase
        existing = Range.search(
            [("document_type_id", "=", doc.id), ("authorization_number", "=", auth), ("company_id", "=", company.id)],
            limit=1,
        )
        vals = {
            "name": row.get("name", f"DGII {prefix}"),
            "document_type_id": doc.id,
            "company_id": company.id,
            "authorization_number": auth,
            "sequence_start": start,
            "sequence_end": end,
            "next_sequence": start,
            "date_from": row.get("date_from"),
            "date_to": row.get("date_to"),
            "journal_ids": [Command.set(journals.ids)] if journals else [],
        }
        if existing:
            existing.write(vals)
            if existing.state == "draft":
                existing.action_activate()
            ncf_created.append({"prefix": prefix, "action": "updated", "auth": auth})
        else:
            rec = Range.create(vals)
            rec.action_activate()
            ncf_created.append({"prefix": prefix, "action": "created", "auth": auth})
report["loaded"]["ncf_ranges"] = ncf_created
required_ncf = {"B01", "B02", "B03", "B04", "B11", "B13"}
loaded_prefixes = {x["prefix"] for x in ncf_created}
missing_ncf = required_ncf - loaded_prefixes
if missing_ncf:
    pending(f"Rangos NCF faltantes: {sorted(missing_ncf)}")

# --- 5. Importar maestros ---
client_rows = read_csv("clientes.csv")
vendor_rows = read_csv("proveedores.csv")
product_rows = read_csv("productos.csv")
stock_rows = read_csv("existencias.csv")

partners_created = {"clients": 0, "vendors": 0}
Partner = env["res.partner"]

if not client_rows:
    pending("Clientes — completar data/hellenia/import/clientes.csv")
else:
    for row in client_rows:
        ref = row.get("ref") or row.get("vat") or row.get("name")
        domain = [("ref", "=", ref)] if row.get("ref") else [("name", "=", row.get("name"))]
        p = Partner.search(domain, limit=1)
        vals = {
            "name": row.get("name"),
            "ref": row.get("ref") or False,
            "vat": row.get("vat") or False,
            "customer_rank": int(row.get("customer_rank", "1") or "1"),
            "street": row.get("street") or False,
            "city": row.get("city") or False,
            "phone": row.get("phone") or False,
            "email": row.get("email") or False,
            "comment": row.get("comment") or False,
        }
        if p:
            p.write(vals)
        else:
            Partner.create(vals)
        partners_created["clients"] += 1

if not vendor_rows:
    pending("Proveedores — completar data/hellenia/import/proveedores.csv")
else:
    for row in vendor_rows:
        ref = row.get("ref") or row.get("vat") or row.get("name")
        domain = [("ref", "=", ref)] if row.get("ref") else [("name", "=", row.get("name"))]
        p = Partner.search(domain, limit=1)
        vals = {
            "name": row.get("name"),
            "ref": row.get("ref") or False,
            "vat": row.get("vat") or False,
            "supplier_rank": int(row.get("supplier_rank", "1") or "1"),
            "street": row.get("street") or False,
            "city": row.get("city") or False,
            "phone": row.get("phone") or False,
            "email": row.get("email") or False,
        }
        if p:
            p.write(vals)
        else:
            Partner.create(vals)
        partners_created["vendors"] += 1

products_created = 0
if not product_rows:
    pending("Productos — completar data/hellenia/import/productos.csv")
else:
    Product = env["product.template"]
    for row in product_rows:
        code = row.get("default_code") or False
        domain = [("default_code", "=", code)] if code else [("name", "=", row.get("name"))]
        prod = Product.search(domain, limit=1)
        categ_name = row.get("categ_name", "Inventario")
        categ = env["product.category"].search([("name", "=", categ_name)], limit=1)
        if not categ:
            categ = env["product.category"].create({"name": categ_name})
        ptype = row.get("type", "consu")
        vals = {
            "name": row.get("name"),
            "default_code": code,
            "categ_id": categ.id,
            "list_price": float(row.get("list_price", "0") or "0"),
            "standard_price": float(row.get("standard_price", "0") or "0"),
            "type": ptype,
            "sale_ok": True,
            "purchase_ok": True,
        }
        if ptype == "consu":
            vals["is_storable"] = True
        if prod:
            prod.write(vals)
        else:
            Product.create(vals)
        products_created += 1

report["loaded"]["partners"] = partners_created
report["loaded"]["products"] = products_created

if stock_rows and product_rows:
    warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
    loc = warehouse.lot_stock_id if warehouse else False
    stock_done = 0
    for row in stock_rows:
        code = row.get("default_code", "")
        qty = float(row.get("qty", "0") or "0")
        prod = env["product.product"].search([("default_code", "=", code)], limit=1)
        if prod and loc and qty > 0:
            env["stock.quant"]._update_available_quantity(prod, loc, qty)
            stock_done += 1
    report["loaded"]["stock_lines"] = stock_done
elif not stock_rows and product_rows:
    pending("Existencias iniciales — opcional: existencias.csv")

# --- 6. Limpieza datos prueba ---
cleanup = {}

# Usuarios demo
demo_users = env["res.users"].with_context(active_test=False).search(
    [("login", "ilike", "demo"), ("login", "!=", "it@justech.do")]
)
for u in demo_users:
    u.write({"active": False})
cleanup["demo_users_deactivated"] = demo_users.mapped("login")

# Facturas smoke P13.4
smoke_invoices = env["account.move"].search(
    [("name", "in", ["INV/2026/00001", "INV/2026/00002", "INV/2026/00003"])]
)
reversed_names = []
for inv in smoke_invoices:
    if inv.state == "posted" and inv.move_type == "out_invoice":
        try:
            with env.cr.savepoint():
                inv.justech_do_ncf_void_reason = "Limpieza pre-Go-Live Fase 16"
                if hasattr(inv, "action_void_ncf") and inv.justech_do_ncf:
                    inv.action_void_ncf()
                rev = inv._reverse_moves(default_values_list=[{"ref": "Reversión Go-Live F16"}])
                if rev:
                    rev.action_post()
                reversed_names.append(inv.name)
        except Exception as exc:  # noqa: BLE001
            cleanup.setdefault("smoke_invoice_errors", []).append(f"{inv.name}: {exc}")
cleanup["smoke_invoices_reversed"] = reversed_names

# Partners/productos smoke
smoke_partners = env["res.partner"].search([("name", "ilike", "SMOKE")])
if smoke_partners:
    linked = env["account.move"].search_count([("partner_id", "in", smoke_partners.ids), ("state", "=", "posted")])
    if not linked:
        cleanup["smoke_partners_deleted"] = len(smoke_partners)
        smoke_partners.unlink()
    else:
        cleanup["smoke_partners_skipped"] = "aún referenciados en asientos"

smoke_products = env["product.template"].search([("name", "ilike", "SMOKE")])
if smoke_products:
  used = env["sale.order.line"].search_count([("product_id", "in", smoke_products.product_variant_ids.ids)])
  used += env["account.move.line"].search_count([("product_id", "in", smoke_products.product_variant_ids.ids)])
  if not used:
      cleanup["smoke_products_deleted"] = len(smoke_products)
      smoke_products.unlink()

# Rangos NCF UAT/smoke
test_ranges = env["justech.do.ncf.range"].search(
    ["|", "|", ("name", "ilike", "SMOKE"), ("name", "ilike", "P13"), ("sequence_start", ">=", 9000)]
)
for rng in test_ranges:
    posted = env["account.move"].search_count(
        [("justech_do_ncf_range_id", "=", rng.id), ("state", "=", "posted"), ("justech_do_ncf_voided", "=", False)]
    )
    if posted:
        cleanup.setdefault("test_ncf_skipped", []).append(rng.name)
    else:
        env["justech.do.ncf.consumption"].search([("range_id", "=", rng.id)]).unlink()
        if rng.state == "active":
            rng.action_expire()
        rng.unlink()
        cleanup.setdefault("test_ncf_deleted", []).append(rng.name)

report["steps"]["cleanup"] = cleanup
env.cr.commit()

# --- 7. Validación flujo (si hay datos mínimos) ---
validation = {}
tax_18 = env["account.tax"].search(
    [("company_id", "=", company.id), ("amount", "=", 18), ("type_tax_use", "=", "sale")], limit=1
)
customer = env["res.partner"].search([("customer_rank", ">", 0), ("name", "not ilike", "SMOKE")], limit=1)
product = env["product.product"].search([("sale_ok", "=", True), ("name", "not ilike", "SMOKE")], limit=1)
vendor = env["res.partner"].search([("supplier_rank", ">", 0)], limit=1)
has_real_ncf = env["justech.do.ncf.range"].search_count(
    [("state", "=", "active"), ("sequence_start", "<", 9000)]
) >= 1

if customer and product and has_real_ncf:
    try:
        with env.cr.savepoint():
            so = env["sale.order"].create({"partner_id": customer.id})
            env["sale.order.line"].create(
                {"order_id": so.id, "product_id": product.id, "product_uom_qty": 1, "price_unit": 1000}
            )
            so.action_confirm()
            validation["quotation_order"] = so.state == "sale"
            inv = so._create_invoices()
            if inv:
                inv.action_post()
                validation["invoice_posted"] = inv.state == "posted"
                validation["ncf_assigned"] = bool(inv.justech_do_ncf)
                validation["itbis"] = any(abs(l.tax_ids.amount - 18) < 0.01 for l in inv.invoice_line_ids if l.tax_ids)
                pdf = env["ir.actions.report"]._render_qweb_pdf("account.account_invoices", inv.ids)
                validation["pdf"] = bool(pdf and pdf[0])
    except Exception as exc:  # noqa: BLE001
        validation["flow_error"] = str(exc)
        err(f"validación flujo: {exc}")
else:
    validation["skipped"] = "Faltan clientes/productos reales o rangos NCF DGII"
    if not has_real_ncf:
        pending("Validación flujo completo bloqueada — sin rangos NCF DGII reales")

report["steps"]["validation"] = validation

# --- Resumen final ---
report["summary"] = {
    "logo": logo_ok,
    "smtp": bool(report["steps"].get("smtp", {}).get("configured")),
    "users_count": len(created_users),
    "ncf_count": len(ncf_created),
    "clients": partners_created["clients"],
    "vendors": partners_created["vendors"],
    "products": products_created,
    "customers_total": env["res.partner"].search_count([("customer_rank", ">", 0)]),
    "vendors_total": env["res.partner"].search_count([("supplier_rank", ">", 0)]),
    "products_total": env["product.template"].search_count([]),
    "active_ncf_ranges": env["justech.do.ncf.range"].search_read(
        [("state", "=", "active")], ["name", "prefix", "authorization_number", "remaining_count"]
    ),
    "active_users": env["res.users"].search_read(
        [("share", "=", False), ("active", "=", True)], ["login", "name"]
    ),
}

if report["pending_client"]:
    report["ok"] = False

print("PHASE16_GOLIVE:" + json.dumps(report, ensure_ascii=False, indent=2, default=str))
