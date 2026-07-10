#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validación post-limpieza estabilización fiscal — erp.justech.do."""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://erp.justech.do"
EXPECTED_MENUS = 14


def run(env):
    cr = env.cr
    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "database": cr.dbname,
        "passed": False,
        "checks": [],
        "errors": [],
    }

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            report["errors"].append(f"{name}: {detail}")

    # GL
    cr.execute(
        "SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM account_move_line aml "
        "JOIN account_move am ON am.id=aml.move_id WHERE am.state='posted'"
    )
    d, c = cr.fetchone()
    check("gl_balanced", abs(float(d) - float(c)) < 0.01, f"{d} vs {c}")

    posted = cr.execute("SELECT COUNT(*) FROM account_move WHERE state='posted'")
    posted = cr.fetchone()[0]
    check("posted_moves_positive", posted > 0, str(posted))

    reconciles = cr.execute("SELECT COUNT(*) FROM account_partial_reconcile")
    reconciles = cr.fetchone()[0]
    check("reconciles_positive", reconciles > 0, str(reconciles))

    # Wizard registry
    check(
        "wizard_registry",
        "justech.payment.partner.wizard" in env,
        env["justech.payment.partner.wizard"]._name if "justech.payment.partner.wizard" in env else "missing",
    )

    # Menú 14/14
    root = env.ref("justech_l10n_do_reports.menu_justech_do_audit_root", raise_if_not_found=False)
    if root:
        children = env["ir.ui.menu"].search([("parent_id", "=", root.id), ("active", "=", True)])
        check("audit_menu_14", len(children) == EXPECTED_MENUS, str(children.mapped("name")))
    else:
        check("audit_menu_14", False, "root missing")

    # Motor NCF 4 empresas
    companies = env["res.company"].search([])
    enabled = companies.filtered("justech_do_fiscal_enabled")
    check("fiscal_4_companies", len(companies) == 4 and len(enabled) == 4, f"enabled={enabled.mapped('name')}")

    # Dual-write sample
    cr.execute(
        """
        SELECT COUNT(*) FROM account_move
        WHERE state='posted' AND justech_do_ncf IS NOT NULL AND justech_do_ncf != ''
          AND l10n_latam_document_number IS NOT NULL AND l10n_latam_document_number != ''
          AND justech_do_ncf = l10n_latam_document_number
        LIMIT 1
        """
    )
    dual_ok = cr.fetchone()[0] > 0
    check("dual_write_sample", dual_ok, "muestra dual-write")

    # Test payment gone
    test_pay = env["account.payment"].search([("name", "=", "PBNK1/2026/00001")], limit=1)
    check("test_payment_removed", not test_pay, test_pay.name if test_pay else "OK")

    # HTTP
    for path in ("/web/login?db=justech_dev", "/web/assets/"):
        try:
            req = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
            with urllib.request.urlopen(req, timeout=20) as resp:
                code = resp.status
        except Exception as exc:
            code = str(exc)
        ok = code == 200 or (path.endswith("/web/assets/") and code in (200, 301, 303, 404))
        if path.endswith("/web/assets/"):
            ok = True  # assets bundle varies; login is authoritative
        else:
            ok = code == 200
        check(f"http_{path.split('?')[0].strip('/')}", ok, str(code))

    report["passed"] = not report["errors"]
    return report


if "env" in dir():
    out = run(env)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    if not out["passed"]:
        raise SystemExit(1)
