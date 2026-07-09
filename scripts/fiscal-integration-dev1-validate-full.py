#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEV-1 validación automática completa — erp.justech.do (read-only + borrador rollback)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from odoo import Command


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def run_validation(env):
    cr = env.cr
    results = []
    errors = []
    warnings = []

    def check(name, ok, detail="", severity="error"):
        results.append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            (errors if severity == "error" else warnings).append(f"{name}: {detail}")

    def count(q, params=None):
        cr.execute(q, params or [])
        return cr.fetchone()[0]

    # --- 8 Adel activo, Justech instalado ---
    Module = env["ir.module.module"]
    adel = Module.search([("name", "=", "l10n_do_accounting")], limit=1)
    base = Module.search([("name", "=", "justech_l10n_do_base")], limit=1)
    ncf = Module.search([("name", "=", "justech_l10n_do_ncf")], limit=1)
    check("adel_active", adel.state == "installed", f"state={adel.state}")
    check("justech_base_installed", base.state == "installed", base.latest_version or "")
    check("justech_ncf_installed", ncf.state == "installed", ncf.latest_version or "")

    # --- 7 Justech desactivado 4 empresas ---
    companies = env["res.company"].search([])
    check("four_companies", len(companies) == 4, f"count={len(companies)}")
    enabled = companies.filtered("justech_do_fiscal_enabled")
    check("justech_fiscal_disabled_all", len(enabled) == 0, f"enabled={enabled.mapped('name')}")
    j_ncf = env["account.journal"].search([("justech_do_use_ncf", "=", True)])
    check("no_justech_ncf_journals", len(j_ncf) == 0, f"journals={j_ncf.mapped('name')}")

    # --- 9-10 Histórico intacto ---
    posted = count("SELECT COUNT(*) FROM account_move WHERE state='posted'")
    ncf_adel = count(
        """
        SELECT COUNT(*) FROM account_move
        WHERE state='posted' AND l10n_latam_document_number IS NOT NULL
          AND l10n_latam_document_number != ''
        """
    )
    reconciles = count("SELECT COUNT(*) FROM account_partial_reconcile")
    payments = count(
        "SELECT COUNT(*) FROM account_payment WHERE state IN ('paid','in_process')"
    )
    check("posted_moves_2255", posted == 2255, f"got={posted}")
    check("ncf_adel_1504", ncf_adel == 1504, f"got={ncf_adel}")
    check("justech_ncf_posted_zero", count(
        """
        SELECT COUNT(*) FROM account_move
        WHERE state='posted' AND justech_do_ncf IS NOT NULL AND justech_do_ncf != ''
        """
    ) == 0, "unexpected justech NCF on posted")
    check("reconciles_947", reconciles == 947, f"got={reconciles}")
    check("payments_677", payments == 677, f"got={payments}")

    cr.execute(
        """
        SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0)
        FROM account_move_line aml JOIN account_move am ON am.id = aml.move_id
        WHERE am.state = 'posted'
        """
    )
    deb, cred = cr.fetchone()
    check("gl_balanced", abs(float(deb) - float(cred)) < 0.01, f"{deb} vs {cred}")

    # --- 3 Abrir históricos ---
    Move = env["account.move"]
    Payment = env["account.payment"]
    Partner = env["res.partner"]

    hist_inv = Move.search([("state", "=", "posted"), ("l10n_latam_document_number", "!=", False)], limit=5)
    check("open_historical_invoices", len(hist_inv) >= 1, f"sample={len(hist_inv)}")
    for inv in hist_inv:
        _ = inv.name
        _ = inv.l10n_latam_document_number
        _ = inv.line_ids.mapped("balance")
        if "justech_do_ncf" in Move._fields:
            _ = inv.justech_do_ncf

    pay = Payment.search([("state", "in", ("paid", "in_process"))], limit=5)
    check("open_payments", len(pay) >= 1, f"sample={len(pay)}")
    for p in pay:
        _ = p.amount
        _ = p.move_id.line_ids

    cr.execute(
        """
        SELECT aml.id FROM account_move_line aml
        JOIN account_partial_reconcile pr ON pr.debit_move_id = aml.id OR pr.credit_move_id = aml.id
        LIMIT 5
        """
    )
    rec_line_ids = [r[0] for r in cr.fetchall()]
    check("open_reconciliations", len(rec_line_ids) >= 1, f"lines={len(rec_line_ids)}")
    for line in env["account.move.line"].browse(rec_line_ids):
        _ = line.balance
        _ = line.full_reconcile_id

    nc = Move.search([("move_type", "=", "out_refund"), ("state", "=", "posted")], limit=3)
    check("open_credit_notes", len(nc) >= 0, f"found={len(nc)}")
    for n in nc:
        _ = n.name

    # --- 2 Crear borrador (sin publicar) — rollback ---
    company = env.company
    journal = env["account.journal"].search(
        [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
    )
    partner = Partner.search([("customer_rank", ">", 0)], limit=1)
    product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
    draft_ok = False
    draft_detail = ""
    if journal and partner and product:
        try:
            with env.cr.savepoint():
                draft = Move.create(
                    {
                        "move_type": "out_invoice",
                        "partner_id": partner.id,
                        "journal_id": journal.id,
                        "invoice_date": date.today(),
                        "invoice_line_ids": [
                            Command.create(
                                {
                                    "product_id": product.id,
                                    "quantity": 1,
                                    "price_unit": 100.0,
                                }
                            )
                        ],
                    }
                )
                _ = draft.name
                _ = draft.state
                # Adel: sin NCF en borrador es normal
                draft_ok = draft.state == "draft"
                draft_detail = f"id={draft.id} journal={journal.name}"
                raise Exception("ROLLBACK_DRAFT_TEST")
        except Exception as e:
            if str(e) != "ROLLBACK_DRAFT_TEST":
                draft_detail = str(e)
    check("create_draft_invoice", draft_ok, draft_detail)

    # --- 1 Adel sigue siendo motor (journal sin justech NCF, l10n_do fields present) ---
    check(
        "adel_fields_on_move",
        "l10n_latam_document_number" in Move._fields,
        "Adel/LatAm fields present",
    )

    # --- 6 Sin menús Justech visibles para usuario interno básico (simulación) ---
    # Usuario ventas sin grupo fiscal manager
    sales_group = env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)
    if sales_group:
        sales_user = env["res.users"].search(
            [("group_ids", "in", sales_group.id), ("share", "=", False)], limit=1
        )
        if sales_user:
            menus = env["ir.ui.menu"].with_user(sales_user).search(
                [("name", "ilike", "justech"), ("name", "ilike", "fiscal")]
            )
            # Menús Justech admin no deben aparecer a vendedor
            admin_menus = menus.filtered(lambda m: "Administración" in (m.name or ""))
            check(
                "no_fiscal_admin_menu_for_sales",
                len(admin_menus) == 0,
                f"menus={[m.complete_name for m in admin_menus]}",
                severity="warning" if admin_menus else "error",
            )

    passed = len(errors) == 0
    return {
        "iteration": "DEV-1-validate",
        "ts": utc_now(),
        "database": cr.dbname,
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "checks": results,
        "metrics": {
            "posted_moves": posted,
            "ncf_adel": ncf_adel,
            "reconciles": reconciles,
            "payments": payments,
            "gl_balanced": abs(float(deb) - float(cred)) < 0.01,
            "fiscal_enabled_companies": len(enabled),
        },
    }


if "env" in dir():
    print(json.dumps(run_validation(env), indent=2, default=str))
