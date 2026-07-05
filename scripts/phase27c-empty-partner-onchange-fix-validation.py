# -*- coding: utf-8 -*-
"""Fase 27C — Validación onchange sin partner_id (cotización/factura)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DB = env.cr.dbname
if DB not in ("hellenia_test", "hellenia_prod"):
    raise SystemExit(f"ABORT: solo hellenia_test/hellenia_prod, actual={DB}")

ENV = "test" if DB == "hellenia_test" else "prod"
OUT = f"/tmp/phase27c-empty-partner-onchange-fix-{ENV}"
os.makedirs(OUT, exist_ok=True)

Partner = env["res.partner"]
SaleOrder = env["sale.order"]
Move = env["account.move"]

report = {
    "phase": f"27c-empty-partner-onchange-fix-{ENV}",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "status": "FAIL",
    "module_versions": {},
    "checks": {},
    "errors": [],
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


mod_base = env["ir.module.module"].search([("name", "=", "justech_l10n_do_base")], limit=1)
mod_ncf = env["ir.module.module"].search([("name", "=", "justech_l10n_do_ncf")], limit=1)
mod_report = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
report["module_versions"] = {
    "justech_l10n_do_base": mod_base.latest_version,
    "justech_l10n_do_ncf": mod_ncf.latest_version,
    "justech_report_design": mod_report.latest_version,
}
check("module_base_version", mod_base.latest_version == "19.0.1.4.2", mod_base.latest_version)
check("module_ncf_version", mod_ncf.latest_version == "19.0.1.5.1", mod_ncf.latest_version)
check("report_design_unchanged", mod_report.latest_version == "19.0.7.3.1", mod_report.latest_version)

doc_b01 = env.ref("justech_l10n_do_base.doc_type_b01")
doc_b02 = env.ref("justech_l10n_do_base.doc_type_b02")

# Método defensivo en contacto vacío
empty_partner = Partner.browse()
check(
    "partner_method_empty_recordset",
    empty_partner.justech_do_get_default_sale_document_type() is False,
    empty_partner.justech_do_get_default_sale_document_type(),
)

# Cotización nueva sin cliente — onchange no debe romper
so_new = SaleOrder.new({"partner_id": False})
try:
    so_new._onchange_partner_justech_do_document_type()
    so_empty_ok = True
    so_empty_detail = so_new.justech_do_document_type_id.id or False
except Exception as exc:
    so_empty_ok = False
    so_empty_detail = str(exc)
check("quotation_empty_partner_onchange", so_empty_ok, so_empty_detail)

# Cotización con cliente — hereda tipo por defecto
partner_b01 = Partner.search([("justech_do_default_document_type_id", "=", doc_b01.id)], limit=1)
if not partner_b01:
    partner_b01 = Partner.create(
        {"name": "P27C B01", "justech_do_default_document_type_id": doc_b01.id}
    )
so_with = SaleOrder.new({"partner_id": partner_b01.id})
so_with._onchange_partner_justech_do_document_type()
check(
    "quotation_partner_inherits_default",
    so_with.justech_do_document_type_id == doc_b01,
    so_with.justech_do_document_type_id.display_name if so_with.justech_do_document_type_id else False,
)

# Factura nueva sin cliente — onchange no debe romper
inv_new = Move.new({"move_type": "out_invoice", "partner_id": False})
try:
    inv_new._onchange_partner_justech_do_document_type()
    inv_empty_ok = True
    inv_empty_detail = inv_new.justech_do_document_type_id.id or False
except Exception as exc:
    inv_empty_ok = False
    inv_empty_detail = str(exc)
check("invoice_empty_partner_onchange", inv_empty_ok, inv_empty_detail)

# Factura con cliente — hereda tipo por defecto
inv_with = Move.new({"move_type": "out_invoice", "partner_id": partner_b01.id})
inv_with._onchange_partner_justech_do_document_type()
check(
    "invoice_partner_inherits_default",
    inv_with.justech_do_document_type_id == doc_b01,
    inv_with.justech_do_document_type_id.display_name if inv_with.justech_do_document_type_id else False,
)

# Override manual en factura — onchange no debe pisar valor existente
inv_override = Move.new(
    {
        "move_type": "out_invoice",
        "partner_id": partner_b01.id,
        "justech_do_document_type_id": doc_b02.id,
    }
)
inv_override._onchange_partner_justech_do_document_type()
check(
    "invoice_manual_override_preserved",
    inv_override.justech_do_document_type_id == doc_b02,
    inv_override.justech_do_document_type_id.display_name if inv_override.justech_do_document_type_id else False,
)

report["status"] = "PASS" if not report["errors"] else "FAIL"
with open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "env": ENV, "errors": report["errors"]}))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
