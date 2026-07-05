#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C1 — Diagnóstico read-only partners sin RNC en facturas TEST.

SOLO LECTURA: search + SQL SELECT. Sin create/write/unlink.
Salida: C1_PARTNERS_RNC_DIAGNOSTIC:{json}
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

company = env.company
TODAY = date.today()
YEAR = TODAY.year

report = {
    "phase": "C1-partners-rnc-diagnostic",
    "mode": "read_only",
    "database": DB,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "company": {"id": company.id, "name": company.name},
    "summary": {},
    "partners": [],
    "invoices_detail": [],
    "classifications": {},
    "ncf_without_rnc": [],
    "dgii_607_impact": {},
    "correction_plan": {},
    "risks": [],
}

SMOKE_PATTERNS = re.compile(
    r"smoke|^\s*p\d{1,2}[a-z]?[-_]|phase\s*\d|lab[-_]|test[-_]|prueba|demo|dummy|forensic|cert|uat",
    re.I,
)
CONSUMIDOR_PATTERNS = re.compile(
    r"consumidor|consumo\s*final|cliente\s*gen|varios|cf\b|mostrador",
    re.I,
)


def classify_partner(name, ref, email, invoice_count, total_amount):
    name = (name or "").strip()
    ref = (ref or "").strip()
    labels = []
    if not name and not ref:
        labels.append("incomplete_contact")
    if SMOKE_PATTERNS.search(name) or SMOKE_PATTERNS.search(ref):
        labels.append("smoke_test")
    if CONSUMIDOR_PATTERNS.search(name):
        labels.append("consumidor_final_candidate")
    if invoice_count >= 10 and total_amount >= 100000 and "smoke_test" not in labels:
        labels.append("real_client_candidate")
    if invoice_count <= 2 and total_amount < 50000 and not labels:
        labels.append("incomplete_contact")
    if not labels:
        labels.append("review_required")
    primary = labels[0]
    if "smoke_test" in labels:
        primary = "smoke_test"
    elif "consumidor_final_candidate" in labels:
        primary = "consumidor_final_candidate"
    elif "real_client_candidate" in labels:
        primary = "real_client_candidate"
    return primary, labels


# --- 1. Core query: posted customer invoices without partner VAT ---
env.cr.execute("""
    SELECT
        am.id,
        am.name,
        am.date,
        am.invoice_date,
        am.amount_total,
        am.amount_untaxed,
        am.payment_state,
        am.partner_id,
        rp.name AS partner_name,
        rp.ref AS partner_ref,
        rp.vat AS partner_vat,
        rp.email AS partner_email,
        rp.active AS partner_active,
        rp.commercial_partner_id,
        aj.code AS journal_code,
        aj.name AS journal_name,
        am.justech_do_ncf,
        am.move_type,
        dt.code AS doc_type_code,
        dt.name AS doc_type_name
    FROM account_move am
    JOIN res_partner rp ON rp.id = am.partner_id
    LEFT JOIN account_journal aj ON aj.id = am.journal_id
    LEFT JOIN justech_do_fiscal_document_type dt ON dt.id = am.justech_do_document_type_id
    WHERE am.state = 'posted'
      AND am.move_type IN ('out_invoice', 'out_refund')
      AND am.company_id = %s
      AND COALESCE(NULLIF(TRIM(rp.vat), ''), '') = ''
    ORDER BY am.date, am.name
""", (company.id,))
rows = env.cr.dictfetchall()

# --- 2. Aggregate by partner ---
by_partner = defaultdict(lambda: {
    "partner_id": None,
    "partner_name": "",
    "partner_ref": "",
    "partner_email": "",
    "partner_active": True,
    "commercial_partner_id": None,
    "invoice_count": 0,
    "credit_note_count": 0,
    "total_amount": 0.0,
    "date_min": None,
    "date_max": None,
    "journals": Counter(),
    "doc_types": Counter(),
    "ncf_count": 0,
    "ncf_samples": [],
    "invoice_names": [],
    "move_types": Counter(),
})

for r in rows:
    pid = r["partner_id"]
    p = by_partner[pid]
    p["partner_id"] = pid
    p["partner_name"] = r["partner_name"]
    p["partner_ref"] = r["partner_ref"] or ""
    p["partner_email"] = r["partner_email"] or ""
    p["partner_active"] = r["partner_active"]
    p["commercial_partner_id"] = r["commercial_partner_id"]
    amt = float(r["amount_total"] or 0)
    inv_date = r["invoice_date"] or r["date"]
    move_type = r["move_type"]
    p["move_types"][move_type] += 1
    if move_type == "out_refund":
        p["credit_note_count"] += 1
    else:
        p["invoice_count"] += 1
    p["total_amount"] += amt
    if inv_date:
        ds = str(inv_date)
        p["date_min"] = ds if p["date_min"] is None or ds < p["date_min"] else p["date_min"]
        p["date_max"] = ds if p["date_max"] is None or ds > p["date_max"] else p["date_max"]
    if r["journal_code"]:
        p["journals"][r["journal_code"]] += 1
    dt_key = r["doc_type_code"] or r["doc_type_name"] or "sin_tipo"
    p["doc_types"][dt_key] += 1
    if r["justech_do_ncf"]:
        p["ncf_count"] += 1
        if len(p["ncf_samples"]) < 5:
            p["ncf_samples"].append(r["justech_do_ncf"])
    if len(p["invoice_names"]) < 10:
        p["invoice_names"].append(r["name"])

# --- 3. Duplicate name detection (no VAT partners) ---
name_groups = defaultdict(list)
for pid, p in by_partner.items():
    key = re.sub(r"\s+", " ", (p["partner_name"] or "").lower().strip())
    if key:
        name_groups[key].append(pid)

duplicate_clusters = [
    {"normalized_name": k, "partner_ids": v, "count": len(v)}
    for k, v in name_groups.items()
    if len(v) > 1
]

# --- 4. Build partner records with classification ---
class_counts = Counter()
for pid, p in sorted(by_partner.items(), key=lambda x: -x[1]["total_amount"]):
    inv_count = p["invoice_count"] + p["credit_note_count"]
    primary, labels = classify_partner(
        p["partner_name"], p["partner_ref"], p["partner_email"],
        inv_count, p["total_amount"],
    )
    if any(d["partner_ids"] for d in duplicate_clusters if pid in d["partner_ids"] and d["count"] > 1):
        if "duplicate_cluster" not in labels:
            labels.append("duplicate_cluster")
        if primary == "review_required":
            primary = "duplicate_candidate"
    class_counts[primary] += 1
    report["partners"].append({
        "partner_id": pid,
        "name": p["partner_name"],
        "ref": p["partner_ref"],
        "email": p["partner_email"],
        "active": p["partner_active"],
        "commercial_partner_id": p["commercial_partner_id"],
        "invoice_count": p["invoice_count"],
        "credit_note_count": p["credit_note_count"],
        "total_amount": round(p["total_amount"], 2),
        "date_min": p["date_min"],
        "date_max": p["date_max"],
        "journals": dict(p["journals"]),
        "doc_types": dict(p["doc_types"]),
        "ncf_count": p["ncf_count"],
        "ncf_samples": p["ncf_samples"],
        "sample_invoices": p["invoice_names"],
        "classification": primary,
        "classification_labels": labels,
    })

# --- 5. NCF without RNC ---
ncf_without_rnc = [
    {
        "invoice": r["name"],
        "date": str(r["invoice_date"] or r["date"]),
        "partner_id": r["partner_id"],
        "partner_name": r["partner_name"],
        "ncf": r["justech_do_ncf"],
        "doc_type": r["doc_type_code"],
        "amount_total": float(r["amount_total"] or 0),
        "move_type": r["move_type"],
    }
    for r in rows
    if r["justech_do_ncf"]
]
report["ncf_without_rnc"] = ncf_without_rnc

# --- 6. DGII 607 impact (read-only estimate) ---
period_code = TODAY.strftime("%Y%m")
dgii_607 = {"period": period_code, "method": "readonly_estimate"}
if "justech.do.dgii.period" in env:
    try:
        df, dt = env["justech.do.dgii.period"].period_bounds_from_code(period_code)
        dgii_607["date_from"] = str(df)
        dgii_607["date_to"] = str(dt)
        period_rows = [
            r for r in rows
            if r["invoice_date"] and df <= r["invoice_date"] <= dt
        ]
        dgii_607["invoices_no_rnc_in_period"] = len(period_rows)
        dgii_607["amount_no_rnc_in_period"] = round(sum(float(r["amount_total"] or 0) for r in period_rows), 2)
        if "justech.do.dgii.607.exporter" in env:
            exp = env["justech.do.dgii.607.exporter"]
            result = exp.validate_period_607(company, df, dt, refresh_states=False)
            dgii_607["validate_607_counts"] = result.get("counts", {})
            dgii_607["validate_607_ok"] = result.get("ok", True)
    except Exception as exc:
        dgii_607["error"] = str(exc)[:500]

# YTD impact
ytd_rows = [r for r in rows if r["invoice_date"] and r["invoice_date"].year == YEAR]
dgii_607["ytd_invoices_no_rnc"] = len(ytd_rows)
dgii_607["ytd_amount_no_rnc"] = round(sum(float(r["amount_total"] or 0) for r in ytd_rows), 2)
report["dgii_607_impact"] = dgii_607

# --- 7. Totals for all posted out invoices (context) ---
env.cr.execute("""
    SELECT COUNT(*) FROM account_move am
    JOIN res_partner rp ON rp.id = am.partner_id
    WHERE am.state='posted' AND am.move_type IN ('out_invoice','out_refund')
      AND am.company_id=%s
""", (company.id,))
total_posted = env.cr.fetchone()[0]
env.cr.execute("""
    SELECT COUNT(*) FROM account_move am
    JOIN res_partner rp ON rp.id = am.partner_id
    WHERE am.state='posted' AND am.move_type IN ('out_invoice','out_refund')
      AND am.company_id=%s
      AND COALESCE(NULLIF(TRIM(rp.vat), ''), '') = ''
""", (company.id,))
no_rnc_count = env.cr.fetchone()[0]

report["summary"] = {
    "posted_customer_moves_total": total_posted,
    "posted_no_rnc_count": no_rnc_count,
    "posted_no_rnc_pct": round(100.0 * no_rnc_count / total_posted, 1) if total_posted else 0,
    "unique_partners_no_rnc": len(by_partner),
    "total_amount_no_rnc": round(sum(float(r["amount_total"] or 0) for r in rows), 2),
    "with_ncf_count": len(ncf_without_rnc),
    "without_ncf_count": no_rnc_count - len([r for r in rows if not r["justech_do_ncf"]]),
    "duplicate_name_clusters": len(duplicate_clusters),
    "classification_counts": dict(class_counts),
}

report["classifications"] = {
    "definitions": {
        "smoke_test": "Nombre/ref patrón prueba (SMOKE, Phase, LAB, P21…)",
        "consumidor_final_candidate": "Nombre tipo consumidor final",
        "real_client_candidate": "Volumen/monto alto — posible cliente real sin RNC",
        "duplicate_candidate": "Nombre duplicado con otros partners sin VAT",
        "incomplete_contact": "Pocos movimientos o datos mínimos",
        "review_required": "Revisión manual contador",
    },
    "duplicate_clusters": duplicate_clusters[:50],
}

# --- 8. Correction plan (proposal only) ---
by_class = defaultdict(list)
for p in report["partners"]:
    by_class[p["classification"]].append(p["partner_id"])

report["correction_plan"] = {
    "smoke_test": {
        "action": "Archivar partners + excluir de 607 o migrar a partner lab con RNC válido; evaluar NC/anulación facturas fiscales",
        "owner": "Justech + contador",
        "partner_ids": by_class.get("smoke_test", []),
        "invoice_estimate": sum(p["invoice_count"] + p["credit_note_count"] for p in report["partners"] if p["classification"] == "smoke_test"),
    },
    "consumidor_final_candidate": {
        "action": "Asignar RNC genérico DGII consumidor final (001-0000000-0) o partner CF maestro; validar tipo B02",
        "owner": "Contador",
        "partner_ids": by_class.get("consumidor_final_candidate", []),
    },
    "duplicate_candidate": {
        "action": "Fusionar partners duplicados; reasignar facturas al maestro; completar RNC",
        "owner": "Justech (merge) + contador (RNC)",
        "partner_ids": by_class.get("duplicate_candidate", []),
        "clusters": duplicate_clusters,
    },
    "real_client_candidate": {
        "action": "Completar RNC real antes de declarar; bloquear post futuro sin VAT",
        "owner": "Contador + operaciones",
        "partner_ids": by_class.get("real_client_candidate", []),
    },
    "incomplete_contact": {
        "action": "Completar ficha partner o archivar si es basura",
        "owner": "Justech config",
        "partner_ids": by_class.get("incomplete_contact", []),
    },
    "review_required": {
        "action": "Revisión caso por caso",
        "owner": "Contador",
        "partner_ids": by_class.get("review_required", []),
    },
    "ncf_without_rnc": {
        "action": "Prioridad alta: facturas fiscales válidas sin RNC — corregir partner y validar 607; NC si corresponde",
        "count": len(ncf_without_rnc),
        "owner": "Contador + Justech",
    },
    "code_prevention": {
        "action": "Validación pre-post RNC obligatorio en justech_l10n_do_ncf / hellenia_ux",
        "owner": "Justech código (post-aprobación C1)",
    },
    "config_prevention": {
        "action": "Partner consumidor final maestro; reglas DGII exclusion para datos lab",
        "owner": "Justech configuración",
    },
}

# Risks
if no_rnc_count > 0:
    report["risks"].append({
        "id": "FISC-C1-01",
        "severity": "critical",
        "message": f"{no_rnc_count} comprobantes posted sin RNC ({report['summary']['posted_no_rnc_pct']}% del total)",
    })
if len(ncf_without_rnc) > 0:
    report["risks"].append({
        "id": "FISC-C1-02",
        "severity": "critical",
        "message": f"{len(ncf_without_rnc)} facturas con NCF asignado pero partner sin RNC — 607 inválido",
    })
if class_counts.get("real_client_candidate", 0) > 0:
    report["risks"].append({
        "id": "FISC-C1-03",
        "severity": "high",
        "message": f"{class_counts['real_client_candidate']} partners con perfil cliente real sin RNC",
    })
if duplicate_clusters:
    report["risks"].append({
        "id": "FISC-C1-04",
        "severity": "medium",
        "message": f"{len(duplicate_clusters)} clusters de nombres duplicados sin VAT",
    })

# Invoice detail sample (first 100)
report["invoices_detail"] = [
    {
        "id": r["id"],
        "name": r["name"],
        "date": str(r["invoice_date"] or r["date"]),
        "partner_id": r["partner_id"],
        "partner_name": r["partner_name"],
        "amount_total": float(r["amount_total"] or 0),
        "journal": r["journal_code"],
        "ncf": r["justech_do_ncf"],
        "doc_type": r["doc_type_code"],
    }
    for r in rows[:100]
]
report["invoices_detail_truncated"] = len(rows) > 100
report["invoices_detail_total"] = len(rows)

print("C1_PARTNERS_RNC_DIAGNOSTIC:" + json.dumps(report, ensure_ascii=False, indent=2, default=str))
