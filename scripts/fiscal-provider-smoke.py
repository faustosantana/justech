#!/usr/bin/env python3
"""Smoke read-only: verifica que el Fiscal Data Provider lee NCF Adel en justech_dev."""
import json
import os
import sys

import odoo
from odoo import api, SUPERUSER_ID


def main():
    db = os.environ.get("PGDATABASE") or os.environ.get("ODOO_DB") or "justech_dev"
    target_ncf = sys.argv[1] if len(sys.argv) > 1 else "E310000019120"
    odoo.tools.config.parse_config([])
    registry = odoo.registry(db)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        Move = env["account.move"]
        provider = env["justech.do.fiscal.data.provider"]
        exporter = env["justech.do.dgii.606.exporter"]
        domain = []
        if "l10n_latam_document_number" in Move._fields:
            domain = [("l10n_latam_document_number", "=", target_ncf)]
        elif "justech_do_ncf" in Move._fields:
            domain = [("justech_do_ncf", "=", target_ncf)]
        else:
            print(json.dumps({"ok": False, "error": "No fiscal NCF fields on account.move"}))
            return 1
        move = Move.search(domain + [("state", "=", "posted")], limit=1)
        result = {
            "database": db,
            "target_ncf": target_ncf,
            "move_found": bool(move),
            "move_id": move.id if move else None,
            "move_name": move.name if move else None,
            "provider_ncf": provider.get_ncf(move) if move else None,
            "provider_source": provider.get_supported_sources(move) if move else None,
            "provider_prefix": provider.get_document_type_prefix(move) if move else None,
            "justech_do_ncf": getattr(move, "justech_do_ncf", None) if move else None,
            "l10n_latam_document_number": getattr(move, "l10n_latam_document_number", None)
            if move
            else None,
        }
        if move:
            from datetime import date

            dfrom = move.invoice_date.replace(day=1) if move.invoice_date else date.today().replace(day=1)
            dto = move.invoice_date or dfrom
            errors = exporter._dgii_validate_single_move(move, dfrom, dto)
            result["606_ncf_errors"] = [e for e in errors if "NCF" in e]
            result["606_valid_for_ncf"] = not result["606_ncf_errors"]
        result["ok"] = bool(move and result.get("provider_ncf") == target_ncf and result.get("606_valid_for_ncf"))
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
