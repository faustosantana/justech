# -*- coding: utf-8 -*-
"""Fase 19.2 — Excluir fiscalmente data UAT/demo en TEST (sin borrar contabilidad)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from odoo import _, fields

MARKER = "PHASE19_2_CLEANUP:"
DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

EVIDENCE_DIR = os.environ.get("HELLENIA_PHASE19_EVIDENCE", "/evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)
JSON_PATH = os.path.join(EVIDENCE_DIR, "phase19-2-cleanup.json")

REASON = _("Exclusión fiscal Fase 19.2 — data UAT/demo/prueba (no reportable DGII).")

KEEP_REFS = {
    "P19-B11-ITBIS",
    "P19-B11-EXEMPT",
    "P19-B11-WH-ITBIS30",
    "P19-B13-WH-ISR10",
    "P19-B13-MULTI-WH",
    "P19-B11-NC",
}

PARTNER_MARKERS = (
    "UAT ",
    "UAT-",
    "Fase 4",
    "Fase 5",
    "PHASE4",
    "PHASE5",
    "PHASE19",
    "P19 Sin",
    "P19-ERR",
    "Proveedor prueba",
    "Proveedor Lab",
    "Mobiliario RD",
)

REF_PREFIXES = (
    "UAT-",
    "UAT_",
    "PHASE4-",
    "PHASE5-",
    "PHASE19-",
    "P19-ERR-",
    "P19-ERR",
)


def is_uat_demo_move(move):
    ref = (move.ref or "").strip()
    if ref in KEEP_REFS:
        return False
    ref_up = ref.upper()
    for prefix in REF_PREFIXES:
        if ref_up.startswith(prefix.upper()):
            return True
    partner_name = (move.partner_id.name or "").strip()
    for marker in PARTNER_MARKERS:
        if marker.lower() in partner_name.lower():
            return True
    if not move.justech_do_ncf and move.move_type in ("in_invoice", "in_refund"):
        if any(m.lower() in partner_name.lower() for m in ("uat", "prueba", "phase", "pilot")):
            return True
    return False


company = env.company
moves = env["account.move"].search(
    [
        ("company_id", "=", company.id),
        ("state", "=", "posted"),
        ("move_type", "in", ("in_invoice", "in_refund")),
    ]
)

excluded = env["account.move"]
kept = env["account.move"]
details = []

for move in moves:
    if is_uat_demo_move(move):
        move.write(
            {
                "justech_do_include_in_dgii": False,
                "justech_do_dgii_exclusion_reason": REASON,
                "justech_do_dgii_fiscal_state": "excluded",
            }
        )
        excluded |= move
        details.append(
            {
                "id": move.id,
                "name": move.name,
                "ref": move.ref,
                "partner": move.partner_id.display_name,
            }
        )
    else:
        kept |= move

env.cr.commit()

exporter = env["justech.do.dgii.606.exporter"]
today = fields.Date.context_today(env.user)
period_start = today.replace(day=1)
result = exporter.validate_period_606(company, period_start, today, refresh_states=True)
env.cr.commit()

report = {
    "phase": "19.2",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "excluded_count": len(excluded),
    "kept_count": len(kept),
    "excluded_sample": details[:30],
    "validation_counts": result["counts"],
    "pass": result["counts"]["incomplete"] == 0 and result["counts"]["valid"] > 0,
}

with open(JSON_PATH, "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=2, default=str)

print(f"{MARKER}{json.dumps(report, ensure_ascii=False, default=str)}")
