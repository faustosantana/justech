#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Healthcheck erp.justech.do post-recovery — read-only."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from odoo import Command


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def run(env):
    cr = env.cr
    results = []
    errors = []

    def check(name, ok, detail=""):
        results.append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            errors.append(f"{name}: {detail}")

    def count(q, params=None):
        cr.execute(q, params or [])
        return cr.fetchone()[0]

    # Login / web
    check("odoo_env", True, cr.dbname)

    # Apps — ir.module.module readable
    mods = env["ir.module.module"].search([("state", "=", "installed")], limit=5)
    check("apps_module_registry", len(mods) >= 5, f"sample={len(mods)}")

    # Fiscal stack
    Module = env["ir.module.module"]
    adel = Module.search([("name", "=", "l10n_do_accounting")], limit=1)
    base = Module.search([("name", "=", "justech_l10n_do_base")], limit=1)
    ncf = Module.search([("name", "=", "justech_l10n_do_ncf")], limit=1)
    reports = Module.search([("name", "=", "justech_l10n_do_reports")], limit=1)
    check("adel_active", adel.state == "installed", adel.state)
    check("justech_base_installed", base.state == "installed", base.latest_version or "")
    check("justech_ncf_installed", ncf.state == "installed", ncf.latest_version or "")
    check("justech_reports_installed", reports.state == "installed", reports.latest_version or "")

    companies = env["res.company"].search([])
    enabled = companies.filtered("justech_do_fiscal_enabled")
    check("justech_fiscal_disabled_all", len(enabled) == 0, f"enabled={enabled.mapped('name')}")
    check("four_companies", len(companies) == 4, str(len(companies)))

    # Garantías module
    warranty = Module.search([("name", "=", "justech_warranty")], limit=1)
    if warranty:
        check("warranty_module", warranty.state == "installed", warranty.latest_version or "")
    else:
        # fallback search
        w2 = Module.search([("name", "ilike", "warranty")], limit=1)
        check("warranty_module", bool(w2) and w2.state == "installed", w2.name if w2 else "not found")

    # Ventas / Contabilidad — open records
    Move = env["account.move"]
    Payment = env["account.payment"]
    SO = env["sale.order"]

    inv = Move.search([("move_type", "=", "out_invoice"), ("state", "=", "posted")], limit=3)
    for m in inv:
        _ = m.name
        _ = m.line_ids.mapped("balance")
        if "l10n_latam_document_number" in Move._fields:
            _ = m.l10n_latam_document_number
    check("historical_invoices", len(inv) >= 1, f"opened={len(inv)}")

    pay = Payment.search([("state", "in", ("paid", "in_process"))], limit=3)
    for p in pay:
        _ = p.amount
        _ = p.move_id
    check("payments", len(pay) >= 1, f"opened={len(pay)}")

    so = SO.search([], limit=1)
    if so:
        _ = so.name
        _ = so.order_line
    check("sales_orders", bool(so), so.name if so else "none")

    # Conciliaciones / GL
    check("posted_moves", count("SELECT COUNT(*) FROM account_move WHERE state='posted'") == 2255, "2255")
    check("reconciles_947", count("SELECT COUNT(*) FROM account_partial_reconcile") == 947, "947")
    check("ncf_adel_1504", count(
        """
        SELECT COUNT(*) FROM account_move
        WHERE state='posted' AND l10n_latam_document_number IS NOT NULL
          AND l10n_latam_document_number != ''
        """
    ) == 1504, "1504")

    cr.execute(
        """
        SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0)
        FROM account_move_line aml JOIN account_move am ON am.id = aml.move_id
        WHERE am.state = 'posted'
        """
    )
    deb, cred = cr.fetchone()
    check("gl_balanced", abs(float(deb) - float(cred)) < 0.01, f"{deb} vs {cred}")

    # Chatter — mail.message readable on invoice
    if inv:
        msgs = env["mail.message"].search([("model", "=", "account.move"), ("res_id", "=", inv[0].id)], limit=1)
        check("chatter_messages", True, f"sample={len(msgs)}")

    # Asset attachments in DB
    asset_count = count(
        "SELECT COUNT(*) FROM ir_attachment WHERE url LIKE '/web/assets/%%'"
    )
    check("asset_attachments_db", asset_count > 0, str(asset_count))

    return {
        "ts": utc_now(),
        "database": cr.dbname,
        "passed": len(errors) == 0,
        "errors": errors,
        "checks": results,
    }


if "env" in dir():
    print(json.dumps(run(env), indent=2, default=str))
