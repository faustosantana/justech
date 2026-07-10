#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validación post-unificación Pagos + Auditoría Fiscal — erp.justech.do."""
from __future__ import annotations

import json
from datetime import datetime, timezone

EXPECTED_PAGOS = (
    "Pagos de clientes",
    "Pagos a proveedores",
    "Pagos abiertos (clientes)",
    "Pagos abiertos (proveedores)",
    "Conciliación bancaria",
)
EXPECTED_AUDIT = (
    "606 — Compras",
    "607 — Ventas",
    "608 — Comprobantes Anulados",
    "609 — Pagos al Exterior",
    "623 — Retenciones del Estado",
    "Tipos de Comprobante",
    "Rangos NCF",
    "Consumo NCF",
    "Administrar Retenciones",
    "Consumo NCF (Auditoría)",
    "NCF Anulados",
    "Historial Fiscal",
    "Revisión Fiscal",
    "Pendientes de Aprobación",
    "Centro de Administración Fiscal",
)
BASELINE_PAYMENTS = 738


def run(env):
    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "database": env.cr.dbname,
        "passed": False,
        "checks": [],
        "errors": [],
    }

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:500]})
        if not ok:
            report["errors"].append(f"{name}: {detail}")

    pay_root = env.ref("justech_l10n_do_treasury.menu_finance_payments_root", raise_if_not_found=False)
    if pay_root:
        children = env["ir.ui.menu"].search([("parent_id", "=", pay_root.id), ("active", "=", True)], order="sequence")
        names = children.mapped("name")
        check("pagos_menu_5", names == list(EXPECTED_PAGOS), names)
    else:
        check("pagos_menu_5", False, "menu_finance_payments_root missing")

    legacy = env["ir.ui.menu"].search(
        [("active", "=", True), "|", ("name", "ilike", "múltipl"), ("name", "ilike", "multiple")]
    )
    check("legacy_multi_hidden", not legacy, legacy.mapped("name"))

    audit = env.ref("justech_l10n_do_reports.menu_justech_do_audit_root", raise_if_not_found=False)
    if audit:
        children = env["ir.ui.menu"].search([("parent_id", "=", audit.id), ("active", "=", True)], order="sequence")
        names = children.mapped("name")
        check("audit_menu_15", len(children) == 15 and names == list(EXPECTED_AUDIT), names)
    else:
        check("audit_menu_15", False, "audit root missing")

    check("wizard_registry", "justech.payment.partner.wizard" in env, "justech.payment.partner.wizard")
    check("treasury_installed", bool(env["ir.module.module"].search([("name", "=", "justech_l10n_do_treasury"), ("state", "=", "installed")])))

    cr = env.cr
    cr.execute("SELECT COUNT(*) FROM account_payment")
    pay_count = cr.fetchone()[0]
    check("payments_count_intact", pay_count == BASELINE_PAYMENTS, f"{pay_count} vs {BASELINE_PAYMENTS}")

    cr.execute(
        "SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM account_move_line aml "
        "JOIN account_move am ON am.id=aml.move_id WHERE am.state='posted'"
    )
    d, c = cr.fetchone()
    check("gl_balanced", abs(float(d) - float(c)) < 0.01, f"{d} vs {c}")

    for company in env["res.company"].search([]):
        ok = bool(company.justech_do_fiscal_enabled)
        check(f"fiscal_enabled_{company.name}", ok, str(company.justech_do_fiscal_enabled))

    report["passed"] = not report["errors"]
    return report


if "env" in dir():
    out = run(env)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    if not out["passed"]:
        raise SystemExit(1)
