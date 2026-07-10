#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnóstico jerarquía menú Auditoría Fiscal — Odoo 19 (sin menu.xml_id)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

EXPECTED = (
    "606 — Compras",
    "607 — Ventas",
    "608 — Comprobantes Anulados",
    "609 — Pagos al Exterior",
    "623 — Retenciones del Estado",
    "Tipos de Comprobante",
    "Rangos NCF",
    "Consumo NCF",
    "NCF Anulados",
    "Historial Fiscal",
    "Revisión Fiscal",
    "Pendientes de Aprobación",
    "Administrar Retenciones",
    "Centro de Administración Fiscal",
)


def menu_xml_id(env, menu):
    data = env["ir.model.data"].search(
        [("model", "=", "ir.ui.menu"), ("res_id", "=", menu.id)],
        limit=1,
    )
    return f"{data.module}.{data.name}" if data else None


def run(env):
    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "database": env.cr.dbname,
        "passed": False,
        "errors": [],
        "hierarchy": [],
        "children": [],
    }

    root = env.ref("justech_l10n_do_reports.menu_justech_do_audit_root", raise_if_not_found=False)
    if not root:
        report["errors"].append("menu_justech_do_audit_root no encontrado")
        return report

    finance = env.ref("accountant.menu_accounting", raise_if_not_found=False)
    if not finance:
        finance = env.ref("account.menu_finance", raise_if_not_found=False)
    if not finance or root.parent_id.id != finance.id:
        report["errors"].append(
            f"Auditoría Fiscal no cuelga de Contabilidad "
            f"(parent={root.parent_id.name if root.parent_id else None})"
        )

    chain = []
    node = root
    while node:
        chain.append(
            {
                "name": node.name,
                "xml_id": menu_xml_id(env, node),
                "active": node.active,
            }
        )
        node = node.parent_id
    report["hierarchy"] = chain

    children = env["ir.ui.menu"].search(
        [("parent_id", "=", root.id), ("active", "=", True)],
        order="sequence, id",
    )
    names = []
    for ch in children:
        names.append(ch.name)
        report["children"].append(
            {
                "sequence": ch.sequence,
                "name": ch.name,
                "xml_id": menu_xml_id(env, ch),
                "action": ch.action and ch.action.name,
            }
        )

    if len(children) != 14:
        report["errors"].append(f"Se esperaban 14 opciones activas, hay {len(children)}")

    if len(set(names)) != len(names):
        report["errors"].append(f"Nombres duplicados: {names}")

    for expected in EXPECTED:
        if expected not in names:
            report["errors"].append(f"Falta opción: {expected}")

    for name in names:
        if name not in EXPECTED:
            report["errors"].append(f"Opción no autorizada: {name}")

    report["passed"] = not report["errors"]
    return report


if "env" in dir():
    out = run(env)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    if not out["passed"]:
        raise SystemExit(1)
