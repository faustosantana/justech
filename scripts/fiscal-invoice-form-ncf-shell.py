#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shell validation: fiscal display fields via FDP on historical + new invoices."""
import json
from datetime import datetime, timezone

Move = env["account.move"]
FDP = env["justech.do.fiscal.data.provider"]
Company = env["res.company"]

report = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "passed": False,
    "companies": {},
    "samples": {},
    "integrity": {},
    "empty_bad": False,
}

COMPANY_NAMES = ["PlugSafe", "Omni Solutions", "Just Office", "JUSTECH"]


def sample(key, domain, company=None):
    d = list(domain)
    if company:
        d = [("company_id", "=", company.id)] + d
    rec = Move.search(d, limit=1, order="id desc")
    if not rec:
        report["samples"][key] = {"ok": False, "detail": "not found"}
        return None
    ncf = FDP.get_ncf(rec)
    tipo = FDP.get_document_type_name(rec) or ""
    src = FDP.get_supported_sources(rec)
    form_ncf = rec.justech_fiscal_ncf
    form_tipo = rec.justech_fiscal_document_type
    has_raw = bool(
        (getattr(rec, "justech_do_ncf", False) or False)
        or (getattr(rec, "l10n_latam_document_number", False) or False)
    )
    empty_bad = has_raw and (not form_ncf or not form_tipo)
    if empty_bad:
        report["empty_bad"] = True
    ok = (form_ncf == ncf) and (bool(form_ncf) if has_raw else True) and (bool(form_tipo) if has_raw else True)
    report["samples"][key] = {
        "ok": ok,
        "id": rec.id,
        "name": rec.name,
        "company": rec.company_id.name,
        "move_type": rec.move_type,
        "justech_do_ncf": rec.justech_do_ncf or False,
        "latam": rec.l10n_latam_document_number or False,
        "form_ncf": form_ncf,
        "form_tipo": form_tipo,
        "form_source": rec.justech_fiscal_source,
        "form_status": rec.justech_fiscal_status,
        "expense": rec.justech_fiscal_expense_type,
        "vat": rec.justech_fiscal_partner_vat,
        "fdp_ncf": ncf,
        "fdp_src": src,
        "empty_bad": empty_bad,
    }
    return rec


# Global samples (any company)
sample("purchase_b01_march", [("name", "=", "FP/2026/03/0001")])
sample("purchase_e31_march", [("name", "=", "FP/2026/03/0004")])
sample(
    "sale_b01_march",
    [
        ("state", "=", "posted"),
        ("move_type", "=", "out_invoice"),
        ("l10n_latam_document_number", "=ilike", "B01%"),
        ("justech_do_ncf", "=", False),
        ("invoice_date", ">=", "2026-03-01"),
        ("invoice_date", "<=", "2026-03-31"),
    ],
)
sample(
    "sale_b02_march",
    [
        ("state", "=", "posted"),
        ("move_type", "=", "out_invoice"),
        ("l10n_latam_document_number", "=ilike", "B02%"),
        ("justech_do_ncf", "=", False),
        ("invoice_date", ">=", "2026-03-01"),
        ("invoice_date", "<=", "2026-03-31"),
    ],
)
sample(
    "purchase_e31_hist",
    [
        ("state", "=", "posted"),
        ("move_type", "=", "in_invoice"),
        ("l10n_latam_document_number", "=ilike", "E31%"),
        ("justech_do_ncf", "=", False),
    ],
)
# E31 de venta: en este dataset histórico no hay out_invoice E31 (solo compras proveedor)
sample(
    "credit_note_hist",
    [
        ("state", "=", "posted"),
        ("move_type", "in", ["out_refund", "in_refund"]),
        "|",
        ("justech_do_ncf", "!=", False),
        ("l10n_latam_document_number", "!=", False),
    ],
)
sample(
    "new_justech_sale",
    [
        ("state", "=", "posted"),
        ("move_type", "=", "out_invoice"),
        ("justech_do_ncf", "!=", False),
    ],
)
sample(
    "new_justech_purchase",
    [
        ("state", "=", "posted"),
        ("move_type", "=", "in_invoice"),
        ("justech_do_ncf", "!=", False),
    ],
)

# Per company: at least one historical with latam NCF and display filled
for cname in COMPANY_NAMES:
    company = Company.search([("name", "ilike", cname)], limit=1)
    if not company:
        report["companies"][cname] = {"ok": False, "detail": "company not found"}
        continue
    hist = Move.search(
        [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("move_type", "in", ["out_invoice", "in_invoice"]),
            ("l10n_latam_document_number", "!=", False),
            ("justech_do_ncf", "=", False),
        ],
        limit=3,
        order="id desc",
    )
    details = []
    all_ok = True
    for m in hist:
        ok = bool(m.justech_fiscal_ncf and m.justech_fiscal_document_type)
        if not ok:
            all_ok = False
            report["empty_bad"] = True
        details.append(
            {
                "name": m.name,
                "ncf": m.justech_fiscal_ncf,
                "tipo": m.justech_fiscal_document_type,
                "ok": ok,
            }
        )
    # also new justech if any
    neu = Move.search(
        [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("justech_do_ncf", "!=", False),
        ],
        limit=1,
        order="id desc",
    )
    neu_ok = True
    neu_detail = None
    if neu:
        neu_ok = bool(neu.justech_fiscal_ncf) and neu.justech_fiscal_ncf == neu.justech_do_ncf
        neu_detail = {
            "name": neu.name,
            "ncf": neu.justech_fiscal_ncf,
            "latam": neu.l10n_latam_document_number,
            "dual_write": neu.justech_do_ncf == (neu.l10n_latam_document_number or ""),
            "ok": neu_ok,
        }
        if not neu_ok:
            all_ok = False
    report["companies"][cname] = {
        "ok": all_ok and (bool(hist) or bool(neu)),
        "company_id": company.id,
        "hist": details,
        "new": neu_detail,
    }

# Integrity: payments count + no empty when source exists (sample 50)
bad = Move.search_count(
    [
        ("state", "=", "posted"),
        ("move_type", "in", ["out_invoice", "in_invoice", "out_refund", "in_refund"]),
        "|",
        ("justech_do_ncf", "!=", False),
        ("l10n_latam_document_number", "!=", False),
    ]
)
# Check a batch for empty display
batch = Move.search(
    [
        ("state", "=", "posted"),
        ("move_type", "in", ["out_invoice", "in_invoice", "out_refund", "in_refund"]),
        "|",
        ("justech_do_ncf", "!=", False),
        ("l10n_latam_document_number", "!=", False),
    ],
    limit=80,
    order="id desc",
)
empty_count = 0
for m in batch:
    if not m.justech_fiscal_ncf or not m.justech_fiscal_document_type:
        empty_count += 1
        report["empty_bad"] = True

payments = env["account.payment"].search_count([])
report["integrity"] = {
    "posted_with_ncf_source": bad,
    "batch_checked": len(batch),
    "batch_empty_display": empty_count,
    "payments_count": payments,
}

# Consistency form vs FDP vs latam/justech for samples
consist_ok = all(s.get("ok") for s in report["samples"].values() if s)
companies_ok = all(c.get("ok") for c in report["companies"].values())
report["passed"] = (
    consist_ok
    and companies_ok
    and not report["empty_bad"]
    and empty_count == 0
)

print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
