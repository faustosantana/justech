#!/usr/bin/env python3
"""Fase 12 — Limpieza datos de prueba Hellenia (DEV/TEST).

Elimina datos transaccionales y maestros de prueba.
Conserva: configuración, parametrización, módulos, seguridad, localización Justech.

NO ejecutar en producción.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

# Patrones Hellenia / UAT / laboratorio (específicos cliente — no Justech producto)
PARTNER_REF_PATTERNS = ("UAT%", "UAT-PILOT%", "PHASE4%", "PHASE6%", "PILOT%")
PARTNER_NAME_HINTS = re.compile(
    r"UAT|piloto|prueba fase|phase6 lab|proveedor prueba|cliente prueba",
    re.I,
)
PRODUCT_CODE_PATTERNS = ("UAT%", "UAT-PILOT%", "PHASE4%", "PHASE6%")
PRODUCT_NAME_HINTS = re.compile(r"UAT|piloto|phase6 lab|phase4 producto|prueba", re.I)
NCF_RANGE_PATTERNS = ("UAT%", "Phase6%", "TEST%", "Lab%")

report = {
    "phase": 12,
    "block": 1,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "deleted": {},
    "skipped": [],
    "remaining": {},
    "ok": True,
    "errors": [],
}


def log_action(action: str, count: int = 0, detail: str = "") -> None:
    report["deleted"][action] = {"count": count, "detail": detail}


def skip(reason: str) -> None:
    report["skipped"].append(reason)


def err(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


def safe_unlink(records, label: str) -> int:
    if not records:
        return 0
    try:
        n = len(records)
        records.unlink()
        log_action(label, n)
        return n
    except Exception as exc:  # noqa: BLE001
        skip(f"{label}: {exc}")
        return 0


# --- 1. Reportes fiscales de prueba ---
FiscalReport = env["justech.do.fiscal.report"]
reports = FiscalReport.search([])
safe_unlink(reports, "fiscal_reports")

# --- 2. Borradores transaccionales ---
for model, label in [
    ("account.move", "draft_invoices"),
    ("sale.order", "draft_sale_orders"),
    ("purchase.order", "draft_purchase_orders"),
    ("stock.picking", "draft_pickings"),
]:
    if model not in env:
        continue
    drafts = env[model].search([("state", "in", ["draft", "cancel"])])
    # Filtrar solo relacionados a prueba si hay muchos borradores legítimos
    if model == "account.move":
        test_drafts = drafts.filtered(
            lambda m: m.partner_id and (
                (m.partner_id.ref and any(
                    m.partner_id.ref.startswith(p.rstrip("%"))
                    for p in PARTNER_REF_PATTERNS
                ))
                or PARTNER_NAME_HINTS.search(m.partner_id.name or "")
            )
        )
        safe_unlink(test_drafts or drafts[:0], label)
    else:
        safe_unlink(drafts.filtered(lambda r: r.name and "UAT" in (r.name or "")), label)

# --- 3. Rangos NCF de prueba (sin consumo posted crítico) ---
Range = env["justech.do.ncf.range"]
test_ranges = Range.browse()
for pat in NCF_RANGE_PATTERNS:
    test_ranges |= Range.search([("name", "ilike", pat.replace("%", ""))])
test_ranges |= Range.search([("authorization_number", "ilike", "TEST")])
test_ranges |= Range.search([("authorization_number", "ilike", "UAT")])

test_range_ids = list(set(test_ranges.ids))
for rid in test_range_ids:
    rng = Range.browse(rid)
    if not rng.exists():
        continue
    rng_name = rng.name
    posted_moves = env["account.move"].search_count(
        [
            ("justech_do_ncf_range_id", "=", rid),
            ("state", "=", "posted"),
        ]
    )
    if posted_moves:
        skip(f"ncf_range {rng_name}: {posted_moves} facturas publicadas — requiere restauración BD o cierre manual")
        continue
    consumptions = env["justech.do.ncf.consumption"].search([("range_id", "=", rid)])
    safe_unlink(consumptions, f"ncf_consumption_{rid}")
    try:
        if rng.state == "active":
            rng.write({"state": "cancelled"})
        rng.unlink()
        log_action("ncf_ranges", 1, rng_name)
    except Exception as exc:  # noqa: BLE001
        skip(f"ncf_range {rng_name}: {exc}")

# --- 4. Partners de prueba ---
Partner = env["res.partner"]
test_partners = Partner.browse()
for pat in PARTNER_REF_PATTERNS:
    test_partners |= Partner.search([("ref", "ilike", pat.replace("%", ""))])
test_partners |= Partner.search([("comment", "ilike", "UAT")])
test_partners |= Partner.search([("comment", "ilike", "piloto")])
test_partners = test_partners.filtered(lambda p: p.ref != "133621282")  # no empresa

for pid in list(test_partners.ids):
    partner = Partner.browse(pid)
    if not partner.exists():
        continue
    pref = partner.ref or partner.name
    move_count = env["account.move"].search_count([("partner_id", "=", pid)])
    so_count = env["sale.order"].search_count([("partner_id", "=", pid)]) if "sale.order" in env else 0
    if move_count or so_count:
        skip(f"partner {pref}: {move_count} moves, {so_count} SO")
        continue
    try:
        partner.unlink()
        log_action("partners", 1, pref)
    except Exception as exc:  # noqa: BLE001
        skip(f"partner {pref}: {exc}")

# --- 5. Productos de prueba ---
Product = env["product.product"]
test_products = Product.browse()
for pat in PRODUCT_CODE_PATTERNS:
    test_products |= Product.search([("default_code", "ilike", pat.replace("%", ""))])
test_products |= Product.search([("name", "ilike", "UAT ")])
test_products |= Product.search([("name", "ilike", "Phase6")])

for prod_id in list(test_products.ids):
    prod = Product.browse(prod_id)
    if not prod.exists():
        continue
    plabel = prod.default_code or prod.name
    move_lines = env["account.move.line"].search_count([("product_id", "=", prod_id)])
    if move_lines:
        skip(f"product {plabel}: usado en {move_lines} líneas")
        continue
    try:
        prod.unlink()
        log_action("products", 1, plabel)
    except Exception as exc:  # noqa: BLE001
        skip(f"product {plabel}: {exc}")

# --- 6. Usuarios temporales de prueba ---
Users = env["res.users"].with_context(active_test=False)
temp_users = Users.search([
    ("login", "ilike", "%hellenia.test%"),
    ("login", "not in", ["admin", "it@justech.do"]),
])
for u in temp_users:
    if u.id == env.ref("base.user_admin").id:
        continue
    try:
        u.unlink()
        log_action("temp_users", 1, u.login)
    except Exception as exc:  # noqa: BLE001
        skip(f"user {u.login}: {exc}")

# --- Conteo residual ---
report["remaining"] = {
    "partners_uat": Partner.search_count([("ref", "ilike", "UAT")]),
    "products_uat": Product.search_count([("default_code", "ilike", "UAT")]),
    "ncf_ranges_uat": Range.search_count([("name", "ilike", "UAT")]),
    "fiscal_reports": FiscalReport.search_count([]),
    "posted_moves_total": env["account.move"].search_count([("state", "=", "posted")]),
    "posted_moves_uat_partners": env["account.move"].search_count([
        ("state", "=", "posted"),
        ("partner_id.ref", "ilike", "UAT"),
    ]),
}

if report["remaining"]["posted_moves_uat_partners"] > 0:
    report["ok"] = False
    err(
        f"Quedan {report['remaining']['posted_moves_uat_partners']} asientos publicados con partners UAT — "
        "restaurar backup pre-UAT recomendado"
    )

if report["remaining"]["partners_uat"] == 0 and report["remaining"]["ncf_ranges_uat"] == 0:
    if report["remaining"]["posted_moves_uat_partners"] == 0:
        report["clean_state"] = True
    else:
        report["clean_state"] = False
else:
    report["clean_state"] = False

print("PHASE12_CLEANUP:" + json.dumps(report, ensure_ascii=False, default=str))
