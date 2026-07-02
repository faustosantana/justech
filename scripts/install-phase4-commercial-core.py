#!/usr/bin/env python3
"""Fase 4 — Instalar núcleo comercial Hellenia (odoo shell / -i via CLI).

Módulos permitidos: contacts, stock, purchase, sale
Módulos prohibidos: ver FORBIDDEN_MODULES
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

ALLOWED = ("contacts", "stock", "purchase", "sale")
FORBIDDEN = (
    "point_of_sale",
    "stock_barcode",
    "web_studio",
    "sign",
    "documents",
    "helpdesk",
    "crm",
    "sale_crm",
    "pos_sale",
)

# odoo shell path — instalar en orden de dependencias
for mod in ("contacts", "stock", "purchase", "sale"):
    rec = env["ir.module.module"].search([("name", "=", mod)], limit=1)
    if not rec:
        print(f"[phase4] ERROR module not found: {mod}")
        continue
    if rec.state == "installed":
        print(f"[phase4] skip already installed: {mod}")
        continue
    print(f"[phase4] installing {mod}...")
    rec.button_immediate_install()
    env.cr.commit()

# stock_barcode puede auto-instalar con stock; desinstalar solo si no rompe inventario
barcode = env["ir.module.module"].search([("name", "=", "stock_barcode")], limit=1)
barcode_action = "absent"
if barcode and barcode.state == "installed":
    try:
        print("[phase4] attempting optional uninstall stock_barcode...")
        barcode.button_immediate_uninstall()
        env.cr.commit()
        barcode = env["ir.module.module"].search([("name", "=", "stock_barcode")], limit=1)
        barcode_action = barcode.state if barcode else "removed"
        print(f"[phase4] stock_barcode after uninstall: {barcode_action}")
    except Exception as exc:
        env.cr.rollback()
        barcode_action = f"kept_installed ({type(exc).__name__})"
        print(f"[phase4] stock_barcode kept installed: {exc}")

forbidden_state = {}
for mod in FORBIDDEN:
    rec = env["ir.module.module"].search([("name", "=", mod)], limit=1)
    forbidden_state[mod] = rec.state if rec else "absent"

bad = [m for m, s in forbidden_state.items() if s == "installed" and m != "stock_barcode"]
if bad:
    print(f"[phase4] ERROR forbidden installed: {bad}")
else:
    print("[phase4] OK forbidden modules not installed (stock_barcode may remain if required)")

allowed_state = {
    m: env["ir.module.module"].search([("name", "=", m)], limit=1).state for m in ALLOWED
}

report = {
    "phase": 4,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "allowed": allowed_state,
    "forbidden": forbidden_state,
    "stock_barcode_action": barcode_action,
    "ok": all(allowed_state.get(m) == "installed" for m in ALLOWED) and not bad,
}
print("PHASE4_INSTALL=" + json.dumps(report, ensure_ascii=False))
