# -*- coding: utf-8 -*-
"""Fase 27B — Validación UX campo Comprobante fiscal por defecto (solo vista)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
ENV = "prod" if DB == "hellenia_prod" else "test"
OUT = f"/tmp/phase27b-partner-doc-type-ux-{ENV}"
os.makedirs(OUT, exist_ok=True)

Partner = env["res.partner"]
form = Partner.get_view(view_type="form")
arch = form.get("arch", "")

report = {
    "phase": f"27b-partner-doc-type-ux-{ENV}",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "checks": {},
}

checks = {
    "field_after_vat": arch.find('name="vat"') < arch.find("justech_do_default_document_type_id"),
    "label_comprobante_fiscal": 'string="Comprobante fiscal por defecto"' in arch,
    "help_tooltip": "se sugerirá automáticamente al crear cotizaciones y facturas" in arch,
    "dropdown_placeholder": "Seleccionar comprobante fiscal" in arch,
    "no_create_option": "no_create" in arch,
    "module_version": env["ir.module.module"].search(
        [("name", "=", "justech_l10n_do_base")], limit=1
    ).latest_version
    == "19.0.1.4.1",
    "backend_field_unchanged": hasattr(Partner, "justech_do_default_document_type_id"),
}

for key, ok in checks.items():
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": ok}

report["status"] = "PASS" if all(c["status"] == "PASS" for c in report["checks"].values()) else "FAIL"
with open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "env": ENV}))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
