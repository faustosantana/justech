#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validación 606 por período YYYYMM — comparación antes/después (solo lectura)."""
from __future__ import annotations

import json
import re
from calendar import monthrange
from datetime import date, datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def period_bounds(period_code: str):
    year = int(period_code[:4])
    month = int(period_code[4:6])
    last = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def classify_error(err: str):
    low = (err or "").lower()
    if "no tiene ncf" in low or "falta ncf" in low:
        return "missing_ncf"
    if "proveedor" in low and ("rnc" in low or "cédula" in low or "cedula" in low):
        return "partner_id"
    if "tipo de identificación" in low or "identificacion" in low:
        return "partner_id_type"
    if "impuesto" in low:
        return "tax"
    if "retención" in low or "retencion" in low:
        return "withholding"
    if "fecha" in low and "período" in low or "periodo" in low:
        return "date_period"
    return "other"


def _get_ncf_for_move(env, move, provider=None):
    if provider:
        return provider.get_ncf(move), provider.get_supported_sources(move)
    ncf = ""
    if "justech_do_ncf" in move._fields and move.justech_do_ncf:
        ncf = (move.justech_do_ncf or "").strip()
    elif "l10n_latam_document_number" in move._fields and move.l10n_latam_document_number:
        ncf = (move.l10n_latam_document_number or "").strip()
        return ncf, "adel_latam"
    source = "justech" if ncf else "none"
    return ncf, source


def validate_606_period(env, period_code: str, company=None):
    company = company or env.company
    date_from, date_to = period_bounds(period_code)
    exporter = env["justech.do.dgii.606.exporter"]
    provider = env.get("justech.do.fiscal.data.provider")
    result = exporter.validate_period(company, date_from, date_to, refresh_states=False)

    errors_flat = result.get("errors_flat") or []
    move_errors = result.get("move_errors") or {}
    counts = result.get("counts") or {}

    missing_ncf_moves = []
    for move_id, errs in move_errors.items():
        ncf_errs = [e for e in errs if classify_error(e) == "missing_ncf"]
        if ncf_errs:
            move = env["account.move"].browse(move_id)
            ncf, source = _get_ncf_for_move(env, move, provider)
            missing_ncf_moves.append(
                {
                    "move_id": move_id,
                    "move_name": move.name or move.ref,
                    "justech_do_ncf": getattr(move, "justech_do_ncf", None) or "",
                    "l10n_latam_document_number": getattr(move, "l10n_latam_document_number", None)
                    or "",
                    "provider_ncf": ncf,
                    "provider_source": source,
                    "errors": ncf_errs,
                }
            )

    by_category = {}
    for err in errors_flat:
        cat = classify_error(err)
        by_category[cat] = by_category.get(cat, 0) + 1

    target_ncf = "E310000019120"
    target_move = env["account.move"].search(
        [
            ("l10n_latam_document_number", "=", target_ncf),
            ("state", "=", "posted"),
        ],
        limit=1,
    )
    target_info = None
    if target_move:
        in_period = (
            target_move.invoice_date
            and date_from <= target_move.invoice_date <= date_to
            and target_move.move_type in ("in_invoice", "in_refund")
        )
        target_errs = move_errors.get(target_move.id) or []
        if not target_errs and in_period:
            target_errs = exporter._dgii_validate_single_move(target_move, date_from, date_to)
        ncf, source = _get_ncf_for_move(env, target_move, provider)
        target_info = {
            "move_id": target_move.id,
            "move_name": target_move.name,
            "in_period": in_period,
            "invoice_date": str(target_move.invoice_date) if target_move.invoice_date else None,
            "move_type": target_move.move_type,
            "l10n_latam_document_number": target_move.l10n_latam_document_number,
            "justech_do_ncf": getattr(target_move, "justech_do_ncf", None) or "",
            "provider_ncf": ncf,
            "provider_source": source,
            "errors": target_errs,
            "missing_ncf_error": any(classify_error(e) == "missing_ncf" for e in target_errs),
        }

    return {
        "ts": utc_now(),
        "database": env.cr.dbname,
        "period_code": period_code,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "company_id": company.id,
        "company_name": company.name,
        "provider_installed": bool(provider),
        "counts": counts,
        "total_errors": len(errors_flat),
        "errors_by_category": by_category,
        "missing_ncf_count": len(missing_ncf_moves),
        "missing_ncf_moves_sample": missing_ncf_moves[:25],
        "target_ecf_E310000019120": target_info,
        "errors_sample": errors_flat[:40],
        "ok": True,
    }


if "env" in dir():
    import sys

    period = "202606"
    if len(sys.argv) > 1:
        period = sys.argv[1]
    print(json.dumps(validate_606_period(env, period), indent=2, default=str))
