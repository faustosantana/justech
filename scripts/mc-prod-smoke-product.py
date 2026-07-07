#!/usr/bin/env python3
"""MC-PROD — Smoke producto USD comercial."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

TS = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
company = env.company
usd = env.ref("base.USD")
Policy = env["justech.multicurrency.policy"]
Item = env["product.pricelist.item"].sudo()
policy = Policy.get_policy(company)
usd_pl = Policy._find_or_create_public_pricelist(company, usd)

Rate = env["res.currency.rate"].sudo()
rate = Rate.search(
    [
        ("currency_id", "=", usd.id),
        ("company_id", "in", [company.id, False]),
        ("justech_archived", "=", False),
    ],
    order="name desc, id desc",
    limit=1,
)
rate_value = rate.inverse_company_rate if rate else 58.0

report = {
    "phase": "MC-PROD-smoke-product",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "ok": True,
    "checks": {},
    "artifacts": {},
}

def chk(ok, detail=""):
    return {"ok": bool(ok), "detail": str(detail)}

tmpl = env["product.template"].create(
    {
        "name": f"MC-PROD Smoke USD {TS}",
        "default_code": f"MC-PROD-USD-{TS}",
        "type": "consu",
        "company_id": company.id,
        "justech_sale_price": 100.0,
        "justech_sale_currency_id": usd.id,
        "justech_purchase_price": 70.0,
        "justech_purchase_currency_id": usd.id,
    }
)
expected_list = 100.0 * rate_value
expected_cost = 70.0 * rate_value
pl_item = Item.search(
    [
        ("pricelist_id", "=", usd_pl.id),
        ("product_tmpl_id", "=", tmpl.id),
        ("applied_on", "=", "1_product"),
    ],
    limit=1,
)

report["checks"]["sale_price_usd"] = chk(abs(tmpl.justech_sale_price - 100.0) < 0.01, tmpl.justech_sale_price)
report["checks"]["purchase_price_usd"] = chk(abs(tmpl.justech_purchase_price - 70.0) < 0.01, tmpl.justech_purchase_price)
report["checks"]["list_price_dop"] = chk(abs(tmpl.list_price - expected_list) < 0.5, f"{tmpl.list_price} ~ {expected_list:.2f}")
report["checks"]["standard_price_dop"] = chk(abs(tmpl.standard_price - expected_cost) < 0.5, f"{tmpl.standard_price} ~ {expected_cost:.2f}")
report["checks"]["usd_public_list_item"] = chk(bool(pl_item), "item" if pl_item else "missing")
if pl_item:
    report["checks"]["usd_public_list_fixed_100"] = chk(
        pl_item.compute_price == "fixed" and abs(pl_item.fixed_price - 100.0) < 0.01,
        f"{pl_item.compute_price} {pl_item.fixed_price}",
    )
else:
    report["checks"]["usd_public_list_fixed_100"] = chk(False, "no item")

report["artifacts"] = {
    "product_id": tmpl.id,
    "product_code": tmpl.default_code,
    "product_variant_id": tmpl.product_variant_ids[:1].id,
    "rate_used": rate_value,
    "usd_pricelist_id": usd_pl.id,
}

report["ok"] = all(v["ok"] for v in report["checks"].values())

out = os.environ.get("MC_PROD_SMOKE_PRODUCT_JSON", "/var/lib/odoo/mc-prod-smoke-product.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps(report, indent=2, ensure_ascii=False))
print(f"\n--- MC_PROD_SMOKE_PRODUCT_JSON={out} ---")
print(f"SMOKE_PRODUCT_OK={'true' if report['ok'] else 'false'}")
env.cr.commit()
if not report["ok"]:
    raise SystemExit(1)
