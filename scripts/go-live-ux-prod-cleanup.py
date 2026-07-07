#!/usr/bin/env python3
"""GO-LIVE-UX — Limpieza datos visibles en PROD (NCF nombres, impuesto compra)."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT = os.environ.get("GOLIVE_UX_EVIDENCE", "/var/lib/odoo/go-live-ux")
os.makedirs(OUT, exist_ok=True)

TEST_NAME_RE = re.compile(r"COA|TEST|SMOKE|QA|CERT|P13|FISCALRD|DEMO|DEBUG|DEV|SAMPLE|FAKE|MOCK", re.I)

# NCF-LEGAL-1: nombres alineados a tipos documentales DGII (justech.do.fiscal.document.type)
NCF_DISPLAY_BY_PREFIX = {
    "B01": "B01 Factura de Crédito Fiscal",
    "B02": "B02 Factura de Consumo",
    "B03": "B03 Nota de Débito",
    "B04": "B04 Nota de Crédito",
    "B11": "B11 Comprobante de Compras",
    "B12": "B12 Registro Único de Ingresos",
    "B13": "B13 Gastos Menores",
    "B14": "B14 Regímenes Especiales de Tributación",
    "B15": "B15 Comprobante Gubernamental",
    "B16": "B16 Comprobante para Exportaciones",
    "B17": "B17 Comprobante para Pagos al Exterior",
}

report = {
    "phase": "GO-LIVE-UX-data-cleanup",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "ok": True,
    "ncf_renames": [],
    "tax_fix": {},
    "errors": [],
}


def err(msg):
    report["ok"] = False
    report["errors"].append(msg)


# --- NCF range visible names ---
Range = env["justech.do.ncf.range"].sudo()
for rng in Range.search([]):
    prefix = (rng.prefix or "").upper()
    target = NCF_DISPLAY_BY_PREFIX.get(prefix)
    if not target:
        continue
    before = rng.name
    if before != target or TEST_NAME_RE.search(before or ""):
        rng.write({"name": target})
        report["ncf_renames"].append({"id": rng.id, "prefix": prefix, "before": before, "after": target})

# --- Purchase tax display name ---
purchase_tax = env["account.tax"].sudo().search(
    [
        ("company_id", "=", env.company.id),
        ("type_tax_use", "=", "purchase"),
        ("amount", "=", 18),
        ("name", "ilike", "Cost Good"),
    ],
    limit=1,
)
if purchase_tax:
    sale_itbis = env["account.tax"].sudo().search(
        [
            ("company_id", "=", env.company.id),
            ("type_tax_use", "=", "sale"),
            ("amount", "=", 18),
            ("name", "ilike", "ITBIS"),
        ],
        limit=1,
    )
    report["tax_fix"] = {
        "id": purchase_tax.id,
        "before": purchase_tax.name,
        "amount": purchase_tax.amount,
        "type_tax_use": purchase_tax.type_tax_use,
        "sale_itbis_reference": sale_itbis.name if sale_itbis else None,
        "same_rate_as_sale_itbis": bool(sale_itbis and sale_itbis.amount == purchase_tax.amount),
    }
    if purchase_tax.amount == 18 and purchase_tax.type_tax_use == "purchase":
        new_name = "18% ITBIS Compras"
        if purchase_tax.name != new_name:
            purchase_tax.write({"name": new_name})
            report["tax_fix"]["after"] = new_name
        else:
            report["tax_fix"]["after"] = new_name
    else:
        err("purchase_tax_not_eligible_for_rename")
else:
    report["tax_fix"] = {"skipped": True, "reason": "18% Cost Good not found"}

env["hellenia.ui.menu.customizer"].apply_all()
env.cr.commit()

with open(os.path.join(OUT, "data_cleanup.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps(report, indent=2, ensure_ascii=False))
print(f"\nGOLIVE_UX_DATA_OK={'true' if report['ok'] else 'false'}")
if not report["ok"]:
    raise SystemExit(1)
