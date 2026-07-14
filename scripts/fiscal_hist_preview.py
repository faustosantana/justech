#!/usr/bin/env python3
"""READ-ONLY preview: historical fiscal reconstruction from invoices."""
import csv
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

EV = Path("/root/backups/justgroup/fiscal-hist-preserve-20260714")
EV.mkdir(parents=True, exist_ok=True)
CUTOFF = "2026-07-14"  # go-live date (UTC day)


def psql(sql: str) -> str:
    return subprocess.check_output(
        ["sudo", "-u", "postgres", "psql", "-d", "justech", "-At", "-F", "\t", "-c", sql],
        text=True,
        errors="replace",
    )


# Partner invoice history using latam NCF (legacy) + justech NCF
inv_sql = f"""
SELECT am.partner_id,
       am.company_id,
       c.name,
       am.id,
       am.name,
       coalesce(am.invoice_date::text,''),
       coalesce(nullif(am.justech_do_ncf,''), nullif(am.l10n_latam_document_number,''), ''),
       coalesce(dt.prefix,
                left(coalesce(nullif(am.justech_do_ncf,''), nullif(am.l10n_latam_document_number,''), ''), 3),
                '')
FROM account_move am
JOIN res_company c ON c.id = am.company_id
LEFT JOIN justech_do_fiscal_document_type dt ON dt.id = am.justech_do_document_type_id
WHERE am.move_type = 'out_invoice'
  AND am.state = 'posted'
  AND am.partner_id IS NOT NULL
"""

# Also confirmed SOs and payments as historical signals
sig_sql = """
SELECT 'so' AS kind, partner_id, company_id, count(*)
FROM sale_order WHERE state IN ('sale','done') AND partner_id IS NOT NULL
GROUP BY partner_id, company_id
UNION ALL
SELECT 'pay', partner_id, company_id, count(*)
FROM account_payment WHERE partner_id IS NOT NULL AND state NOT IN ('draft','cancel')
GROUP BY partner_id, company_id
"""

partners_sql = """
SELECT p.id,
       replace(coalesce(p.name,''), E'\\t', ' '),
       coalesce(p.vat,''),
       coalesce(p.l10n_do_dgii_tax_payer_type,''),
       coalesce(p.justech_do_rnc_status,''),
       coalesce(dd.prefix,''),
       p.customer_rank,
       p.is_company,
       coalesce(c.code,''),
       coalesce(p.create_date::date::text,''),
       coalesce(p.company_id,0)
FROM res_partner p
LEFT JOIN res_country c ON c.id = p.country_id
LEFT JOIN justech_do_fiscal_document_type dd ON dd.id = p.justech_do_default_document_type_id
WHERE p.active AND p.parent_id IS NULL AND p.customer_rank > 0
"""

docs = {
    r.split("\t")[0]: r.split("\t")[1]
    for r in psql(
        "SELECT prefix, id::text FROM justech_do_fiscal_document_type WHERE is_sale_document AND move_type='out_invoice'"
    ).splitlines()
    if "\t" in r
}

# Invert docs prefix->id
prefix_to_id = {}
for line in psql(
    "SELECT prefix, id FROM justech_do_fiscal_document_type WHERE coalesce(is_sale_document,false) AND coalesce(move_type,'out_invoice')='out_invoice'"
).splitlines():
    if "\t" in line:
        pref, did = line.split("\t", 1)
        prefix_to_id[pref] = int(did)

inv_by_partner = defaultdict(list)
for line in psql(inv_sql).splitlines():
    parts = line.split("\t")
    if len(parts) < 8:
        continue
    pid, cid, cname, mid, mname, idate, ncf, pref = parts[:8]
    # ignore non NCF-like prefixes
    if pref and not pref.startswith("B") and pref != "E":
        if not (ncf.startswith("B") or ncf.startswith("E")):
            continue
        pref = ncf[:3] if len(ncf) >= 3 else pref
    if pref in ("PRO",) or (ncf or "").startswith("PROFORMA"):
        continue
    inv_by_partner[int(pid)].append(
        {
            "company_id": int(cid),
            "company": cname,
            "move_id": int(mid),
            "move": mname,
            "date": idate,
            "ncf": ncf,
            "prefix": pref if pref.startswith("B") else (ncf[:3] if ncf.startswith("B") else ""),
        }
    )

signals = defaultdict(lambda: defaultdict(int))
for line in psql(sig_sql).splitlines():
    parts = line.split("\t")
    if len(parts) < 4:
        continue
    kind, pid, cid, cnt = parts[:4]
    signals[int(pid)][(kind, int(cid))] = int(cnt)

rows = []
for line in psql(partners_sql).splitlines():
    parts = line.split("\t")
    if len(parts) < 11:
        continue
    (
        pid,
        name,
        vat,
        payer,
        rnc_status,
        default_doc,
        cr,
        is_company,
        country,
        create_date,
        company_id,
    ) = parts[:11]
    pid = int(pid)
    invs = inv_by_partner.get(pid, [])
    has_so_or_pay = bool(signals.get(pid))
    # Histórico = evidencia operativa (factura/NCF, SO confirmado o pago).
    # NO usar create_date ni customer_rank solos.
    is_historical = bool(invs) or has_so_or_pay

    # per-company reconstruction
    by_co = defaultdict(list)
    for inv in invs:
        if inv["prefix"].startswith("B"):
            by_co[inv["company_id"]].append(inv)

    co_results = []
    consistent_global = True
    proposed_prefixes = set()
    for cid, items in by_co.items():
        # prefer out_invoice prefixes B01/B02/B14/B15/B16 as principal (exclude B04 credit)
        principal = [i for i in items if i["prefix"] in ("B01", "B02", "B14", "B15", "B16", "B12")]
        use = principal or items
        ctr = Counter(i["prefix"] for i in use if i["prefix"])
        if not ctr:
            continue
        top_pref, top_n = ctr.most_common(1)[0]
        total = sum(ctr.values())
        ratio = top_n / total if total else 0
        last = sorted(use, key=lambda x: (x["date"], x["move_id"]))[-1]
        status = "consistent" if ratio >= 0.8 and len(ctr) == 1 or ratio >= 0.9 else (
            "consistent" if ratio >= 0.8 else "mixed"
        )
        if status != "consistent":
            consistent_global = False
        proposed_prefixes.add(top_pref)
        co_results.append(
            {
                "company_id": cid,
                "company": items[0]["company"],
                "proposed_prefix": top_pref,
                "count_top": top_n,
                "count_total": total,
                "ratio": round(ratio, 3),
                "types": dict(ctr),
                "status": status,
                "last_invoice": last["move"],
                "last_ncf": last["ncf"],
                "last_date": last["date"],
            }
        )

    if not invs and is_historical and has_so_or_pay:
        bucket = "historical_no_invoice_ncf"
    elif not is_historical:
        bucket = "new_pending"
    elif not co_results:
        bucket = "historical_no_usable_ncf"
    elif len(proposed_prefixes) > 1:
        # different companies may legitimately differ; mark multi-company-ok separately
        bucket = "historical_multi_company_types"
        # still can be consistent per company
        if all(r["status"] == "consistent" for r in co_results):
            bucket = "historical_consistent_per_company"
        else:
            bucket = "historical_inconsistent"
            consistent_global = False
    elif all(r["status"] == "consistent" for r in co_results):
        bucket = "historical_consistent"
    else:
        bucket = "historical_inconsistent"
        consistent_global = False

    rows.append(
        {
            "id": pid,
            "name": name,
            "vat": vat,
            "payer": payer,
            "rnc_status": rnc_status,
            "default_doc": default_doc,
            "customer_rank": int(cr),
            "is_company": is_company == "t",
            "country": country,
            "create_date": create_date,
            "is_historical": is_historical,
            "invoice_count": len(invs),
            "bucket": bucket,
            "proposed_prefixes": sorted(proposed_prefixes),
            "companies": co_results,
        }
    )

# Capital Dbg detail
capital = [r for r in rows if "130279896" in (r["vat"] or "") or "capital dbg" in r["name"].lower()]
buckets = Counter(r["bucket"] for r in rows)
hist = [r for r in rows if r["is_historical"]]
new = [r for r in rows if not r["is_historical"]]
consistent = [r for r in rows if r["bucket"] in ("historical_consistent", "historical_consistent_per_company")]
inconsistent = [r for r in rows if r["bucket"] == "historical_inconsistent"]

summary = {
    "cutoff": CUTOFF,
    "customers": len(rows),
    "historical": len(hist),
    "new": len(new),
    "buckets": dict(buckets),
    "consistent": len(consistent),
    "inconsistent": len(inconsistent),
    "capital_dbg": capital,
    "confirmable_auto_sample": [
        {
            "id": r["id"],
            "name": r["name"],
            "vat": r["vat"],
            "proposed": r["proposed_prefixes"],
            "companies": r["companies"],
            "current_default": r["default_doc"],
            "rnc_status": r["rnc_status"],
        }
        for r in consistent[:30]
    ],
    "inconsistent_sample": [
        {
            "id": r["id"],
            "name": r["name"],
            "companies": r["companies"],
        }
        for r in inconsistent[:30]
    ],
}
(EV / "preview_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

with open(EV / "preview_all_customers.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(
        f,
        fieldnames=[
            "id",
            "name",
            "vat",
            "bucket",
            "is_historical",
            "invoice_count",
            "proposed_prefixes",
            "default_doc",
            "rnc_status",
            "payer",
            "country",
        ],
    )
    w.writeheader()
    for r in rows:
        w.writerow(
            {
                "id": r["id"],
                "name": r["name"],
                "vat": r["vat"],
                "bucket": r["bucket"],
                "is_historical": r["is_historical"],
                "invoice_count": r["invoice_count"],
                "proposed_prefixes": "|".join(r["proposed_prefixes"]),
                "default_doc": r["default_doc"],
                "rnc_status": r["rnc_status"],
                "payer": r["payer"],
                "country": r["country"],
            }
        )

print("CUSTOMERS", len(rows))
print("HIST", len(hist), "NEW", len(new))
print("BUCKETS", dict(buckets))
print("CONSISTENT", len(consistent), "INCONSISTENT", len(inconsistent))
print("CAPITAL", json.dumps(capital, ensure_ascii=False, indent=2)[:2000])
