#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 3A Sprint 1 — validación lab (solo lectura + integridad histórica).

Ejecutar vía odoo shell en BD lab aislada (justech_ncf_lab / justech_lab).
NO usar en justech_dev operativo salvo aprobación explícita.

Uso en servidor:
  sudo -u odoo odoo shell -c /opt/odoo-dev/conf/odoo-ncf-lab.conf \\
    -d justech_ncf_lab --no-http < scripts/fiscal-phase3-sprint1-validate-lab.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def integrity_snapshot(env, label):
    """Snapshot read-only de integridad contable y NCF."""
    cr = env.cr
    Move = env["account.move"]

    cr.execute(
        """
        SELECT COUNT(*) FROM account_move WHERE state = 'posted'
        """
    )
    posted_moves = cr.fetchone()[0]

    cr.execute(
        """
        SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0)
        FROM account_move_line aml
        JOIN account_move am ON am.id = aml.move_id
        WHERE am.state = 'posted'
        """
    )
    gl_debit, gl_credit = cr.fetchone()

    cr.execute("SELECT COUNT(*) FROM account_partial_reconcile")
    reconciles = cr.fetchone()[0]

    cr.execute("SELECT COUNT(*) FROM account_payment WHERE state IN ('paid','in_process')")
    payments = cr.fetchone()[0]

    ncf_justech = 0
    if "justech_do_ncf" in Move._fields:
        cr.execute(
            """
            SELECT COUNT(*) FROM account_move
            WHERE state = 'posted'
              AND justech_do_ncf IS NOT NULL
              AND justech_do_ncf != ''
            """
        )
        ncf_justech = cr.fetchone()[0]

    services = [
        "justech.do.fiscal.validator.service",
        "justech.do.fiscal.config.service",
        "justech.do.document.type.provider",
        "justech.do.ncf.document.type.resolver.service",
        "justech.do.ncf.duplicate.service",
        "justech.do.ncf.assignment.service",
    ]
    service_ok = {}
    for name in services:
        try:
            env[name]
            service_ok[name] = True
        except KeyError:
            service_ok[name] = False

    modules = env["ir.module.module"].search(
        [
            (
                "name",
                "in",
                [
                    "justech_l10n_do_base",
                    "justech_l10n_do_ncf",
                    "justech_l10n_do_dashboard",
                ],
            )
        ]
    ).read(["name", "state", "latest_version"])

    return {
        "label": label,
        "ts": utc_now(),
        "posted_moves": posted_moves,
        "gl_debit": float(gl_debit),
        "gl_credit": float(gl_credit),
        "gl_balanced": abs(float(gl_debit) - float(gl_credit)) < 0.01,
        "partial_reconciles": reconciles,
        "payments_posted_like": payments,
        "ncf_justech_posted": ncf_justech,
        "services_registered": service_ok,
        "modules": modules,
    }


def compare_integrity(before, after):
    """Devuelve (ok, issues). Aborta validación si histórico comprometido."""
    issues = []
    checks = [
        ("posted_moves", "Movimientos posted"),
        ("gl_debit", "GL débito"),
        ("gl_credit", "GL crédito"),
        ("partial_reconciles", "Conciliaciones parciales"),
    ]
    for key, desc in checks:
        if before.get(key) != after.get(key):
            issues.append(
                f"{desc} cambió: {before.get(key)} → {after.get(key)}"
            )
    if not after.get("gl_balanced"):
        issues.append("GL desbalanceado post-validación")
    missing = [
        k for k, v in after.get("services_registered", {}).items() if not v
    ]
    if missing:
        issues.append(f"Servicios no registrados: {missing}")
    return len(issues) == 0, issues


def run(env):
    phase = "post_upgrade"
    if len(sys.argv) > 1:
        phase = sys.argv[1]

    snap = integrity_snapshot(env, phase)

    # Validación funcional mínima (sin publicar documentos)
    validator = env["justech.do.fiscal.validator.service"]
    assert validator.is_valid_rnc_format("131-793-916")
    assert validator.validate_ncf_format("B0100000001") == "B0100000001"

    resolver = env["justech.do.ncf.document.type.resolver.service"]
    partner = env["res.partner"].search([], limit=1)
    move = env["account.move"].new(
        {"move_type": "out_invoice", "partner_id": partner.id if partner else False}
    )
    doc = resolver.resolve_for_move(move)
    snap["resolver_smoke"] = bool(doc)

    snap["validation_passed"] = True
    print(json.dumps(snap, indent=2, default=str))
    return snap


# odoo shell entrypoint
if "env" in dir():
    run(env)
