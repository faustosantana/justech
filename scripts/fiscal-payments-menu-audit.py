#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auditoría menús Pagos + Auditoría Fiscal — erp.justech.do / Odoo 19."""
from __future__ import annotations

import json
from datetime import datetime, timezone

PAYMENT_KEYWORDS = (
    "pago", "payment", "cobro", "tesorer", "treasury", "concili",
    "reconcil", "retenc", "withhold", "bank",
)
FISCAL_KEYWORDS = (
    "fiscal", "ncf", "dgii", "606", "607", "608", "609", "623",
    "comprobante", "auditor", "retenc",
)


def menu_xml_id(env, menu):
    data = env["ir.model.data"].search(
        [("model", "=", "ir.ui.menu"), ("res_id", "=", menu.id)],
        limit=1,
    )
    if not data:
        return None
    return f"{data.module}.{data.name}", bool(data.noupdate)


def action_info(action):
    if not action:
        return None
    return {
        "id": action.id,
        "name": action.name,
        "type": action.type,
        "res_model": getattr(action, "res_model", None),
        "binding_model": getattr(action, "binding_model_id", False)
        and action.binding_model_id.model,
    }


def run(env):
    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "database": env.cr.dbname,
        "modules": {},
        "payments_menus": [],
        "fiscal_menus": [],
        "duplicates": [],
        "obsolete_actions": [],
        "hidden_by_groups": [],
        "noupdate_menus": [],
        "errors": [],
    }

    # Installed payment/fiscal modules
    mods = env["ir.module.module"].search(
        [
            ("state", "=", "installed"),
            "|",
            ("name", "ilike", "payment"),
            "|",
            ("name", "ilike", "hellenia"),
            "|",
            ("name", "ilike", "justech"),
            ("name", "ilike", "treasury"),
        ]
    )
    for m in mods.sorted("name"):
        report["modules"][m.name] = m.latest_version or m.installed_version

    Menu = env["ir.ui.menu"]
    all_menus = Menu.with_context(active_test=False).search([])

    def classify(name, xml_id):
        n = (name or "").lower()
        x = (xml_id or "").lower()
        blob = f"{n} {x}"
        is_pay = any(k in blob for k in PAYMENT_KEYWORDS)
        is_fiscal = any(k in blob for k in FISCAL_KEYWORDS)
        return is_pay, is_fiscal

    seen_names = {}
    for menu in all_menus:
        xml_pair = menu_xml_id(env, menu)
        xml_id = xml_pair[0] if xml_pair else None
        noupdate = xml_pair[1] if xml_pair else False
        is_pay, is_fiscal = classify(menu.name, xml_id)
        if not is_pay and not is_fiscal:
            continue

        parent_chain = []
        node = menu
        while node:
            parent_chain.append(node.name)
            node = node.parent_id
        parent_chain.reverse()

        entry = {
            "id": menu.id,
            "name": menu.name,
            "xml_id": xml_id,
            "active": menu.active,
            "sequence": menu.sequence,
            "parent": menu.parent_id.name if menu.parent_id else None,
            "parent_chain": parent_chain,
            "groups": menu.group_ids.mapped("name"),
            "action": action_info(menu.action),
            "noupdate": noupdate,
        }

        if is_pay:
            report["payments_menus"].append(entry)
        if is_fiscal:
            report["fiscal_menus"].append(entry)

        key = (menu.parent_id.id if menu.parent_id else 0, menu.name)
        if key in seen_names:
            report["duplicates"].append(
                {"name": menu.name, "parent": menu.parent_id.name, "ids": [seen_names[key], menu.id]}
            )
        else:
            seen_names[key] = menu.id

        if noupdate:
            report["noupdate_menus"].append({"id": menu.id, "name": menu.name, "xml_id": xml_id})

        if menu.group_ids:
            report["hidden_by_groups"].append(
                {"id": menu.id, "name": menu.name, "groups": menu.group_ids.mapped("name")}
            )

        act = menu.action
        if act and act.type == "ir.actions.act_window" and act.res_model:
            if act.res_model not in env:
                report["obsolete_actions"].append(
                    {"menu": menu.name, "model": act.res_model, "action_id": act.id}
                )

    # Pagos hub under Contabilidad
    finance = env.ref("account.menu_finance", raise_if_not_found=False)
    pay_roots = Menu.search(
        [
            ("parent_id", "=", finance.id if finance else False),
            ("name", "ilike", "pago"),
        ]
    )
    report["pagos_hub"] = []
    for root in pay_roots:
        children = Menu.search([("parent_id", "=", root.id)], order="sequence, id")
        report["pagos_hub"].append(
            {
                "root_id": root.id,
                "root_name": root.name,
                "root_xml_id": menu_xml_id(env, root)[0] if menu_xml_id(env, root) else None,
                "children": [
                    {"sequence": c.sequence, "name": c.name, "active": c.active, "id": c.id}
                    for c in children
                ],
            }
        )

    # Auditoría Fiscal children
    audit_root = env.ref(
        "justech_l10n_do_reports.menu_justech_do_audit_root", raise_if_not_found=False
    )
    if audit_root:
        children = Menu.search(
            [("parent_id", "=", audit_root.id), ("active", "=", True)],
            order="sequence, id",
        )
        report["audit_fiscal"] = [
            {
                "sequence": c.sequence,
                "name": c.name,
                "xml_id": menu_xml_id(env, c)[0] if menu_xml_id(env, c) else None,
                "action_model": c.action.res_model if c.action and hasattr(c.action, "res_model") else None,
            }
            for c in children
        ]
    else:
        report["audit_fiscal"] = []
        report["errors"].append("menu_justech_do_audit_root no encontrado")

    # Historical payment counts by origin
    cr = env.cr
    cr.execute("SELECT COUNT(*) FROM account_payment")
    report["history"] = {
        "payments_total": cr.fetchone()[0],
        "reconciles": cr.execute("SELECT COUNT(*) FROM account_partial_reconcile") or cr.fetchone()[0],
    }
    cr.execute("SELECT COUNT(*) FROM account_partial_reconcile")
    report["history"]["reconciles"] = cr.fetchone()[0]
    cr.execute(
        "SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM account_move_line aml "
        "JOIN account_move am ON am.id=aml.move_id WHERE am.state='posted'"
    )
    d, c = cr.fetchone()
    report["history"]["gl_debit"] = float(d)
    report["history"]["gl_credit"] = float(c)

    hellenia_w = env["ir.model"].search([("model", "=", "hellenia.payment.partner.wizard")], limit=1)
    justech_w = env["ir.model"].search([("model", "=", "justech.payment.partner.wizard")], limit=1)
    report["wizards"] = {
        "hellenia_payment_partner_wizard": bool(hellenia_w),
        "justech_payment_partner_wizard": bool(justech_w),
    }

    report["passed"] = True
    return report


if "env" in dir():
    out = run(env)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
