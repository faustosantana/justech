#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FASE 1 — Matriz de impuestos justech_dev (solo lectura)."""
from __future__ import annotations

import json
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _tax_name(tax):
    name = tax.name
    if isinstance(name, dict):
        return name.get("en_US") or next(iter(name.values()), "")
    return name or ""


def _current_dgii_classification(tax):
    """Clasificación heurística ACTUAL del código legacy (solo diagnóstico)."""
    name = _tax_name(tax).upper()
    use = tax.type_tax_use or ""
    amt = tax.amount or 0.0
    if tax.amount < 0 or (use == "purchase" and amt < 0):
        return "withholding (hellenia/negative)"
    if "ITBIS" in name or (amt in (18.0, 16.0, 9.0, 8.0) and use in ("purchase", "sale")):
        return "606_N / 607_J (ITBIS legacy)"
    if "ISC" in name:
        return "606_W (ISC legacy name match)"
    if "CDT" in name or "TELCO" in name:
        return "606_X (CDT — actualmente ERROR)"
    if "PROPINA" in name or "TIP" in name:
        return "606_Y (propina — no implementado)"
    if "GOV" in name or "ISR GOV" in name:
        return "623 / gov withholding"
    if amt == 0:
        return "exempt / zero"
    return "UNKNOWN (bloquea validación)"


def _recommended_dgii_classification(tax):
    """Clasificación recomendada según DGII y grupo fiscal."""
    name = _tax_name(tax).upper()
    use = tax.type_tax_use or ""
    amt = tax.amount or 0.0
    group = tax.tax_group_id.name if tax.tax_group_id else ""
    if isinstance(group, dict):
        group = group.get("en_US") or ""
    group_u = (group or "").upper()

    if tax.amount < 0:
        if "ITBIS" in name:
            return {"606": "O", "607": "K", "role": "withholding_itbis"}
        if "ISR" in name or "RENTA" in name:
            return {"606": "U", "607": "M", "role": "withholding_isr"}
        return {"606": "U/O", "607": "M/K", "role": "withholding_other"}

    if "ITBIS" in group_u or "ITBIS" in name:
        return {"606": "N", "607": "J", "role": "itbis"}
    if "ISC" in group_u or "ISC" in name:
        return {"606": "W", "607": None, "role": "isc"}
    if "CDT" in name or "TELCO" in name or "OTHER TAX" in group_u:
        return {"606": "X", "607": None, "role": "other_tax"}
    if "PROPINA" in name or "TIP" in name:
        return {"606": "Y", "607": None, "role": "legal_tip"}
    if amt == 0:
        return {"606": None, "607": None, "role": "exempt"}
    if "ISR" in name and "GOV" in name:
        return {"623": "E", "role": "gov_withholding"}
    return {"606": "X", "607": None, "role": "other_tax_fallback"}


def analyze_taxes(env):
    Tax = env["account.tax"]
    taxes = Tax.with_context(active_test=False).search([], order="type_tax_use, amount, id")
    rows = []
    cr = env.cr

    for tax in taxes:
        name = _tax_name(tax)
        # xmlid
        cr.execute(
            """
            SELECT module || '.' || name FROM ir_model_data
            WHERE model = 'account.tax' AND res_id = %s LIMIT 1
            """,
            (tax.id,),
        )
        xmlid_row = cr.fetchone()
        xmlid = xmlid_row[0] if xmlid_row else ""

        # account from repartition or legacy
        account_code = ""
        if tax.invoice_repartition_line_ids:
            accs = tax.invoice_repartition_line_ids.mapped("account_id.code")
            account_code = ",".join(filter(None, accs[:3]))

        # companies using tax
        cr.execute(
            """
            SELECT DISTINCT am.company_id, rc.name
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN res_company rc ON rc.id = am.company_id
            WHERE aml.tax_line_id = %s AND am.state = 'posted'
            ORDER BY am.company_id
            """,
            (tax.id,),
        )
        companies = [{"id": r[0], "name": r[1]} for r in cr.fetchall()]

        cr.execute(
            """
            SELECT COUNT(*) FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.tax_line_id = %s AND am.state = 'posted'
            """,
            (tax.id,),
        )
        move_line_count = cr.fetchone()[0]

        cr.execute(
            """
            SELECT COUNT(DISTINCT rel.account_move_line_id)
            FROM account_move_line_account_tax_rel rel
            JOIN account_move_line aml ON aml.id = rel.account_move_line_id
            JOIN account_move am ON am.id = aml.move_id
            WHERE rel.account_tax_id = %s AND am.state = 'posted'
            """,
            (tax.id,),
        )
        product_line_count = cr.fetchone()[0]

        group_name = tax.tax_group_id.name if tax.tax_group_id else ""
        if isinstance(group_name, dict):
            group_name = group_name.get("en_US") or ""

        rows.append(
            {
                "id": tax.id,
                "name": name,
                "amount": tax.amount,
                "amount_type": tax.amount_type,
                "type_tax_use": tax.type_tax_use,
                "tax_group_id": tax.tax_group_id.id or None,
                "tax_group": group_name,
                "xmlid": xmlid,
                "account_codes": account_code,
                "active": tax.active,
                "company_id": tax.company_id.id if tax.company_id else None,
                "companies_used": companies,
                "posted_tax_line_count": move_line_count,
                "posted_product_line_count": product_line_count,
                "dgii_current_legacy": _current_dgii_classification(tax),
                "dgii_recommended": _recommended_dgii_classification(tax),
            }
        )

    return {
        "ts": utc_now(),
        "database": cr.dbname,
        "tax_count": len(rows),
        "taxes": rows,
        "summary": {
            "purchase": len([r for r in rows if r["type_tax_use"] == "purchase"]),
            "sale": len([r for r in rows if r["type_tax_use"] == "sale"]),
            "with_negative_amount": len([r for r in rows if (r["amount"] or 0) < 0]),
            "unknown_legacy": len(
                [r for r in rows if "UNKNOWN" in r["dgii_current_legacy"]]
            ),
            "with_posted_usage": len([r for r in rows if r["posted_tax_line_count"] > 0]),
        },
    }


if "env" in dir():
    print(json.dumps(analyze_taxes(env), indent=2, default=str))
