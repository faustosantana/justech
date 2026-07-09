#!/usr/bin/env python3
# -*- coding: utf-8__
"""DEV-2 smoke 606/607 read-only — erp.justech.do."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def smoke_606_607(env):
    cr = env.cr
    errors = []
    out = {"ts": utc_now(), "database": cr.dbname}

    mod = env["ir.module.module"].search([("name", "=", "justech_l10n_do_reports")], limit=1)
    out["reports_installed"] = mod.state == "installed"
    if mod.state != "installed":
        errors.append("reports_not_installed")

    cr.execute(
        """
        SELECT COUNT(*) FROM account_move
        WHERE state='posted' AND move_type IN ('out_invoice','out_refund')
          AND l10n_latam_document_number IS NOT NULL AND l10n_latam_document_number != ''
        """
    )
    out["moves_607_eligible"] = cr.fetchone()[0]

    cr.execute(
        """
        SELECT COUNT(*) FROM account_move
        WHERE state='posted' AND move_type IN ('in_invoice','in_refund')
          AND l10n_latam_document_number IS NOT NULL AND l10n_latam_document_number != ''
        """
    )
    out["moves_606_eligible"] = cr.fetchone()[0]

    if "justech.do.dgii.606.exporter" in env:
        exp606 = env["justech.do.dgii.606.exporter"]
        out["exporter_606_model"] = True
    else:
        errors.append("exporter_606_missing")

    if "justech.do.dgii.607.exporter" in env:
        out["exporter_607_model"] = True
    else:
        errors.append("exporter_607_missing")

    if "justech.do.fiscal.report.wizard" in env:
        wiz = env["justech.do.fiscal.report.wizard"]
        w607 = wiz.new({"report_type": "607"})
        w606 = wiz.new({"report_type": "606"})
        out["wizard_607_ok"] = bool(w607)
        out["wizard_606_ok"] = bool(w606)
    else:
        errors.append("wizard_missing")

    # Read-only: contar reportes existentes sin crear
    if "justech.do.fiscal.report" in env:
        Report = env["justech.do.fiscal.report"]
        out["existing_reports"] = Report.search_count([])
        out["existing_606"] = Report.search_count([("report_type", "=", "606")])
        out["existing_607"] = Report.search_count([("report_type", "=", "607")])

    out["errors"] = errors
    out["ok"] = len(errors) == 0
    return out


if "env" in dir():
    print(json.dumps(smoke_606_607(env), indent=2, default=str))
