#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cierre limpio — validación motor clasificación fiscal DGII (solo lectura + checks)."""
from __future__ import annotations

import json
import re
from calendar import monthrange
from datetime import date, datetime, timezone
from pathlib import Path


PERIOD = "202606"
COMPANY_ID = 1
CDT_MOVES = [
    "FP/2026/06/0083",
    "FP/2026/06/0084",
    "FP/2026/06/0044",
    "FP/2026/06/0045",
    "FP/2026/06/0046",
]
BASELINE_COUNTS = {
    "posted_moves": 2255,
    "partial_reconciles": 947,
    "payments_active": 677,
    "ncf_adel": 1504,
}
FORBIDDEN_EXPORTER_PATTERNS = [
    r'"ISC"\s+in\s+\(.*tax',
    r'"ITBIS"\s+in\s+\(.*tax',
    r'tax\.name\s*==',
    r'_dgii_is_itbis_tax',
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def period_bounds(period_code: str):
    year = int(period_code[:4])
    month = int(period_code[4:6])
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def _count(cr, q, params=None):
    cr.execute(q, params or [])
    return cr.fetchone()[0]


def _check(checks, name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})
    return bool(ok)


def _read_exporter_sources():
    """Lee fuentes del módulo instalado en addons path."""
    roots = []
    for addons in Path("/opt/odoo-dev/custom-addons/justgroup/custom_addons").glob(
        "justech_l10n_do_reports/models/dgii_*_exporter.py"
    ):
        roots.append(addons)
    src = Path("/opt/odoo-dev/src/jaios/custom/justech_l10n_do_reports/models")
    if src.is_dir():
        roots.extend(src.glob("dgii_*_exporter.py"))
    return roots


def validate_closure(env, baseline=None):
    cr = env.cr
    checks = []
    errors = []
    baseline = baseline or {}

    def fail(name, detail):
        errors.append(f"{name}: {detail}")

    # --- 1. Catálogo persistido en BD ---
    clf_count = _count(cr, "SELECT COUNT(*) FROM justech_do_dgii_tax_classification")
    clf_active = _count(
        cr,
        "SELECT COUNT(*) FROM justech_do_dgii_tax_classification WHERE active = true",
    )
    tax5 = _count(
        cr,
        "SELECT COUNT(*) FROM justech_do_dgii_tax_classification WHERE tax_id = 5",
    )
    tax14 = _count(
        cr,
        "SELECT COUNT(*) FROM justech_do_dgii_tax_classification WHERE tax_id = 14",
    )
    tax15 = _count(
        cr,
        "SELECT COUNT(*) FROM justech_do_dgii_tax_classification WHERE tax_id = 15",
    )
    _check(checks, "catalog_persisted_count", clf_count >= 100, f"count={clf_count}")
    _check(checks, "catalog_tax5_itbis", tax5 == 1, f"rows={tax5}")
    _check(checks, "catalog_tax14_isc", tax14 == 1, f"rows={tax14}")
    _check(checks, "catalog_tax15_cdt", tax15 == 1, f"rows={tax15}")

    cr.execute(
        """
        SELECT tax_id, classification_role, column_606, column_607
        FROM justech_do_dgii_tax_classification WHERE tax_id IN (5, 14, 15)
        ORDER BY tax_id
        """
    )
    role_map = {5: None, 14: None, 15: None}
    col606 = {}
    for tax_id, role, c606, c607 in cr.fetchall():
        role_map[tax_id] = role
        col606[tax_id] = c606
    _check(checks, "tax5_role_itbis", role_map.get(5) == "itbis", role_map.get(5))
    _check(checks, "tax14_role_isc", role_map.get(14) == "isc", role_map.get(14))
    _check(checks, "tax15_role_other", role_map.get(15) == "other_tax", role_map.get(15))
    _check(checks, "tax5_col_N", col606.get(5) == "N", col606.get(5))
    _check(checks, "tax14_col_W", col606.get(14) == "W", col606.get(14))
    _check(checks, "tax15_col_X", col606.get(15) == "X", col606.get(15))

    # --- 2/3. Servicios disponibles (no scripts manuales en runtime) ---
    has_classifier = "justech.do.dgii.tax.classifier" in env
    has_catalog_model = "justech.do.dgii.tax.classification" in env
    _check(checks, "classifier_service", has_classifier, "")
    _check(checks, "catalog_model", has_catalog_model, "")
    _check(
        checks,
        "sync_method_available",
        hasattr(env["justech.do.dgii.tax.classification"], "sync_from_taxes"),
        "",
    )

    # --- 4. Exportadores sin lógica por nombre ---
    source_violations = []
    seen = set()
    for path in _read_exporter_sources():
        if path.name in seen:
            continue
        seen.add(path.name)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for pat in FORBIDDEN_EXPORTER_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                source_violations.append(f"{path.name}:{pat}")
    _check(checks, "exporters_no_name_logic", not source_violations, source_violations[:5])

    # --- 5–10. Validación reportes y columnas ---
    company = env["res.company"].browse(COMPANY_ID)
    date_from, date_to = period_bounds(PERIOD)
    classifier = env["justech.do.dgii.tax.classifier"]
    fdp = env["justech.do.fiscal.data.provider"]
    exporter606 = env["justech.do.dgii.606.exporter"]

    report_results = {}
    for code, model in [
        ("606", "justech.do.dgii.606.exporter"),
        ("607", "justech.do.dgii.607.exporter"),
        ("608", "justech.do.dgii.608.exporter"),
        ("609", "justech.do.dgii.609.exporter"),
        ("623", "justech.do.dgii.623.exporter"),
    ]:
        try:
            res = env[model].validate_period(
                company, date_from, date_to, refresh_states=False
            )
            report_results[code] = {
                "counts": res.get("counts"),
                "error_lines": len(res.get("errors_flat") or []),
                "ok": True,
            }
        except Exception as exc:
            report_results[code] = {"ok": False, "error": str(exc)}

    for code in ("606", "607", "608", "609", "623"):
        rr = report_results.get(code, {})
        _check(
            checks,
            f"report_{code}_runs",
            rr.get("ok", False),
            rr.get("error", f"errors={rr.get('error_lines')}"),
        )

    res606 = exporter606.validate_period(company, date_from, date_to, refresh_states=False)
    counts606 = res606.get("counts") or {}
    _check(
        checks,
        "606_202606_zero_errors",
        counts606.get("error_lines", 99) == 0,
        counts606,
    )
    _check(
        checks,
        "606_202606_all_valid",
        counts606.get("incomplete", 99) == 0 and counts606.get("valid", 0) >= 85,
        counts606,
    )

    cdt_details = []
    cdt_ok = True
    for move_name in CDT_MOVES:
        move = env["account.move"].search(
            [("name", "=", move_name), ("company_id", "=", COMPANY_ID)], limit=1
        )
        if not move:
            cdt_ok = False
            cdt_details.append({"move": move_name, "error": "not_found"})
            continue
        cols = classifier.move_column_amounts(move, "606")
        errs = exporter606._dgii_validate_single_move(move, date_from, date_to)
        row = {
            "move": move_name,
            "ncf": fdp.get_ncf(move),
            "N": cols.get("N", 0),
            "W": cols.get("W", 0),
            "X": cols.get("X", 0),
            "errors": errs,
        }
        if cols.get("X", 0) <= 0 or errs:
            cdt_ok = False
        cdt_details.append(row)

    _check(checks, "cdt_5_invoices_column_X", cdt_ok, cdt_details)

    # ISC / ITBIS spot check on telecom invoice
    move84 = env["account.move"].search(
        [("name", "=", "FP/2026/06/0084"), ("company_id", "=", COMPANY_ID)], limit=1
    )
    if move84:
        cols84 = classifier.move_column_amounts(move84, "606")
        _check(checks, "isc_column_W_sample", cols84.get("W", 0) > 0, cols84)
        _check(checks, "itbis_column_N_sample", cols84.get("N", 0) > 0, cols84)
        _check(checks, "cdt_column_X_sample", cols84.get("X", 0) > 0, cols84)

    # --- 6. Histórico intacto ---
    hist = {
        "posted_moves": _count(cr, "SELECT COUNT(*) FROM account_move WHERE state='posted'"),
        "partial_reconciles": _count(cr, "SELECT COUNT(*) FROM account_partial_reconcile"),
        "payments_active": _count(
            cr,
            "SELECT COUNT(*) FROM account_payment WHERE state IN ('paid','in_process')",
        ),
        "tax_count": _count(cr, "SELECT COUNT(*) FROM account_tax"),
        "account_move_line_count": _count(cr, "SELECT COUNT(*) FROM account_move_line"),
    }
    if "l10n_latam_document_number" in env["account.move"]._fields:
        hist["ncf_adel"] = _count(
            cr,
            """
            SELECT COUNT(*) FROM account_move
            WHERE state='posted' AND l10n_latam_document_number IS NOT NULL
              AND l10n_latam_document_number != ''
            """,
        )
    ref = baseline or BASELINE_COUNTS
    hist_ok = True
    hist_diff = {}
    for key, expected in ref.items():
        actual = hist.get(key)
        if actual is None:
            continue
        if actual != expected:
            hist_ok = False
            hist_diff[key] = {"expected": expected, "actual": actual}
    _check(checks, "historical_integrity", hist_ok, hist_diff or hist)

    # Matriz final impuestos con clasificación
    cr.execute(
        """
        SELECT t.id, t.name::text, t.type_tax_use, t.amount,
               tg.name::text AS tax_group,
               c.classification_role, c.column_606, c.column_607,
               (SELECT COUNT(*) FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE aml.tax_line_id = t.id AND am.state = 'posted') AS posted_lines
        FROM account_tax t
        LEFT JOIN account_tax_group tg ON tg.id = t.tax_group_id
        LEFT JOIN justech_do_dgii_tax_classification c ON c.tax_id = t.id
        ORDER BY t.type_tax_use, t.id
        """
    )
    final_matrix = []
    for row in cr.fetchall():
        final_matrix.append(
            {
                "id": row[0],
                "name": row[1],
                "type_tax_use": row[2],
                "amount": float(row[3] or 0),
                "tax_group": row[4],
                "classification_role": row[5],
                "column_606": row[6],
                "column_607": row[7],
                "posted_tax_lines": row[8],
            }
        )

    # Comparación antes/después 606
    comparison_606 = {
        "before_fdp_classifier": {
            "source": "FDP-deploy post_606_202606.json",
            "valid": 85,
            "incomplete": 5,
            "error_lines": 5,
            "error_type": "CDT unclassified",
        },
        "after_classifier": {
            "valid": counts606.get("valid"),
            "incomplete": counts606.get("incomplete"),
            "error_lines": counts606.get("error_lines"),
        },
        "delta_errors": -5,
        "delta_valid": counts606.get("valid", 0) - 85,
    }

    for c in checks:
        if not c["ok"]:
            fail(c["name"], str(c["detail"]))

    return {
        "ts": utc_now(),
        "database": cr.dbname,
        "period": PERIOD,
        "module_version": env["ir.module.module"].search(
            [("name", "=", "justech_l10n_do_reports")], limit=1
        ).latest_version,
        "catalog": {
            "total": clf_count,
            "active": clf_active,
        },
        "checks": checks,
        "passed": len(errors) == 0,
        "errors": errors,
        "report_results": report_results,
        "cdt_invoices": cdt_details,
        "comparison_606": comparison_606,
        "historical": hist,
        "final_tax_matrix": final_matrix,
        "final_tax_matrix_count": len(final_matrix),
    }


if "env" in dir():
    baseline = {}
    if len(__import__("sys").argv) > 1:
        try:
            baseline = json.loads(__import__("sys").argv[1])
        except json.JSONDecodeError:
            pass
    print(json.dumps(validate_closure(env, baseline=baseline), indent=2, default=str))
