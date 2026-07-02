# -*- coding: utf-8 -*-
"""Fase 23.3B — Validación fix error 500 cotización (UI real + portal)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

OUT_DIR = "/evidence/phase23-3b-quotation-500-fix"
if not os.path.isdir("/evidence"):
    OUT_DIR = "/tmp/phase23-3b-quotation-500-fix"
os.makedirs(OUT_DIR, exist_ok=True)

report = {
    "phase": "23.3b-quotation-500-fix",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "root_cause": (
        "AttributeError: res.company sin get_hellenia_quotation_terms_display en worker HTTP "
        "(llamada Python en QWeb + registry no recargado tras upgrade)"
    ),
    "fix": "QWeb usa company.hellenia_quotation_terms con default inline; restart odoo tras upgrade",
    "module_version": None,
    "http_checks": {},
    "pdfs": {},
    "ok": True,
    "pass": False,
    "ready_for_prod": False,
}


def check_http(key, ok, status_code=None, detail=""):
    report["http_checks"][key] = {
        "status": "PASS" if ok else "FAIL",
        "http_status": status_code,
        "detail": str(detail)[:500],
    }
    if not ok:
        report["ok"] = False


mod = env["ir.module.module"].search([("name", "=", "hellenia_reports")], limit=1)
mod.button_immediate_upgrade()
env.cr.commit()
report["module_version"] = mod.latest_version

Report = env["ir.actions.report"]
SaleOrder = env["sale.order"]
company = env.company

orders = {}
for ref_suffix, key in (("1P", "quote_1"), ("5P", "quote_5"), ("15P", "quote_15")):
    so = SaleOrder.search([("client_order_ref", "=", f"P23-3-QUOTE-{ref_suffix}")], limit=1)
    if so:
        orders[key] = so

if not orders:
    for so in SaleOrder.search([("state", "in", ["draft", "sent"])], order="id desc", limit=3):
        orders[f"fallback_{so.id}"] = so

# PDF render (backend engine)
action = env.ref("sale.action_report_saleorder")
for key, so in orders.items():
    try:
        pdf_bytes, _fmt = Report._render_qweb_pdf(action.report_name, so.ids)
        line_count = len(so.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment))
        fname = f"quotation_{line_count}_product{'s' if line_count != 1 else ''}.pdf"
        path = os.path.join(OUT_DIR, fname)
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        report["pdfs"][key] = {
            "status": "OK",
            "order": so.name,
            "order_id": so.id,
            "file": fname,
            "size_bytes": len(pdf_bytes),
        }
    except Exception as exc:
        report["pdfs"][key] = {"status": "FAIL", "detail": str(exc)[:500]}
        report["ok"] = False

# Portal HTTP — orden 135 o primera disponible
portal_so = SaleOrder.browse(135)
if not portal_so.exists():
    portal_so = list(orders.values())[0] if orders else SaleOrder.search(
        [("state", "in", ["draft", "sent"])], limit=1
    )

if portal_so:
    token = portal_so.access_token
    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url", "https://test.hellenia.cloud")
    portal_url = (
        f"{base_url}/es/my/orders/{portal_so.id}"
        f"?access_token={token}&report_type=pdf"
    )
    report["portal_url_tested"] = portal_url.replace(token, "***") if token else portal_url

    if token:
        try:
            req = urllib.request.Request(portal_url, method="GET")
            with urllib.request.urlopen(req, timeout=90) as resp:
                code = resp.status
                body = resp.read(8)
            check_http(
                "portal_pdf",
                code == 200 and body[:4] == b"%PDF",
                code,
                f"PDF magic ok, {len(body)}+ bytes",
            )
        except urllib.error.HTTPError as exc:
            check_http("portal_pdf", False, exc.code, str(exc)[:300])
        except Exception as exc:
            check_http("portal_pdf", False, detail=str(exc)[:300])
    else:
        check_http("portal_pdf", False, detail="sin access_token en sale.order")

    # Backend report controller (usuario interno simulado vía report download)
    try:
        pdf_bytes, _ = Report._render_qweb_pdf(action.report_name, portal_so.ids)
        check_http("backend_pdf_render", len(pdf_bytes) > 1000, 200, f"{len(pdf_bytes)} bytes")
    except Exception as exc:
        check_http("backend_pdf_render", False, detail=str(exc)[:300])

report["pass"] = report["ok"] and all(
    v.get("status") == "PASS" for v in report["http_checks"].values()
) and all(v.get("status") == "OK" for v in report["pdfs"].values())

validation_path = os.path.join(OUT_DIR, "validation.json")
with open(validation_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("PHASE23_3B:" + json.dumps(report, indent=2, ensure_ascii=False))
