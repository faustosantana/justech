#!/usr/bin/env python3
"""MC-PROD — Smoke cotización + factura USD."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from odoo import fields

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

TS = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
TODAY = fields.Date.today()
company = env.company
usd = env.ref("base.USD")
dop = env.ref("base.DOP")
Policy = env["justech.multicurrency.policy"]
policy = Policy.get_policy(company)
usd_pl = Policy._find_or_create_public_pricelist(company, usd)

product_code = os.environ.get("MC_PROD_PRODUCT_CODE")
if product_code:
    tmpl = env["product.template"].search([("default_code", "=", product_code)], limit=1)
else:
    tmpl = env["product.template"].search([("default_code", "like", "MC-PROD-USD-%")], order="id desc", limit=1)
if not tmpl:
    raise SystemExit("ABORT: producto smoke no encontrado")
prod = tmpl.product_variant_ids[:1]

report = {
    "phase": "MC-PROD-smoke-sale-invoice",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "ok": True,
    "checks": {},
    "artifacts": {},
}

def chk(ok, detail=""):
    return {"ok": bool(ok), "detail": str(detail)}

fiscal_mgr = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False)
if fiscal_mgr and fiscal_mgr not in env.user.group_ids:
    env.user.write({"group_ids": [(4, fiscal_mgr.id)]})

partner = env["res.partner"].create(
    {
        "name": f"MC-PROD Customer USD {TS}",
        "customer_rank": 1,
        "company_id": company.id,
    }
)
partner.with_company(company).property_product_pricelist = usd_pl

report["checks"]["customer_usd_pricelist"] = chk(
    partner.with_company(company).property_product_pricelist == usd_pl,
    partner.with_company(company).property_product_pricelist.display_name,
)

so = env["sale.order"].create({"partner_id": partner.id, "company_id": company.id})
env["sale.order.line"].create(
    {"order_id": so.id, "product_id": prod.id, "product_uom_qty": 1.0}
)
line = so.order_line[:1]
report["checks"]["quote_currency_usd"] = chk(so.currency_id == usd, so.currency_id.name)
report["checks"]["line_price_100_usd"] = chk(abs(line.price_unit - 100.0) < 0.5, line.price_unit)

try:
    so.action_confirm()
    so._create_invoices()
    inv = so.invoice_ids.filtered(lambda m: m.state != "cancel")[:1]
    if not inv:
        raise RuntimeError("No se generó factura")
    inv.invoice_date = TODAY
    inv.action_post()
    move = inv
    company_cur = company.currency_id
    aml_dop = move.line_ids.filtered(lambda l: l.debit or l.credit)

    report["checks"]["invoice_posted"] = chk(inv.state == "posted", inv.state)
    report["checks"]["invoice_currency_usd"] = chk(inv.currency_id == usd, inv.currency_id.name)
    report["checks"]["company_currency_dop"] = chk(company_cur == dop, company_cur.name)
    report["checks"]["move_balanced"] = chk(
        abs(sum(move.line_ids.mapped("debit")) - sum(move.line_ids.mapped("credit"))) < 0.05,
        "balanced",
    )
    report["checks"]["aml_in_company_currency"] = chk(
        bool(aml_dop) and all(l.company_currency_id == company_cur for l in aml_dop),
        f"{len(aml_dop)} lines DOP",
    )
    report["checks"]["aml_dop_amounts_positive"] = chk(sum(aml_dop.mapped("debit")) > 0, f"debit={sum(aml_dop.mapped('debit')):.2f}")

    if "justech_do_ncf" in inv._fields:
        report["checks"]["ncf_present"] = chk(bool(inv.justech_do_ncf), inv.justech_do_ncf or "missing")
    else:
        report["checks"]["ncf_present"] = chk(True, "campo NCF ausente")

    try:
        pdf = env["ir.actions.report"]._render_qweb_pdf("account.account_invoices", inv.ids)
        report["checks"]["invoice_pdf"] = chk(pdf and len(pdf[0]) > 500, f"{len(pdf[0]) if pdf else 0} bytes")
    except Exception as exc:
        report["checks"]["invoice_pdf"] = chk(False, str(exc)[:120])

    report["artifacts"] = {
        "partner_id": partner.id,
        "sale_order_id": so.id,
        "sale_order_name": so.name,
        "invoice_id": inv.id,
        "invoice_name": inv.name,
        "ncf": getattr(inv, "justech_do_ncf", "") or "",
        "product_code": tmpl.default_code,
    }
except Exception as exc:
    report["checks"]["invoice_posted"] = chk(False, str(exc)[:200])
    report["ok"] = False

report["ok"] = report["ok"] and all(v["ok"] for v in report["checks"].values())

out = os.environ.get("MC_PROD_SMOKE_SALE_JSON", "/var/lib/odoo/mc-prod-smoke-sale-invoice.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps(report, indent=2, ensure_ascii=False))
print(f"\n--- MC_PROD_SMOKE_SALE_JSON={out} ---")
print(f"SMOKE_SALE_OK={'true' if report['ok'] else 'false'}")
env.cr.commit()
if not report["ok"]:
    raise SystemExit(1)
