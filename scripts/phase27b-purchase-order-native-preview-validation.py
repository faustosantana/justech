# -*- coding: utf-8 -*-
"""Fase 27B — Validación vista previa nativa Orden de Compra."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB not in ("hellenia_test", "hellenia_prod"):
    raise SystemExit(f"ABORT: solo hellenia_test/hellenia_prod, actual={DB}")

ENV = "test" if DB == "hellenia_test" else "prod"
OUT_DIR = f"/tmp/phase27b-po-native-preview-{ENV}"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_JT = "justech_report_design.report_justech_purchase_order_document"
MAIN_ACTION = "purchase.action_report_purchase_order"

report = {
    "phase": f"27b-po-native-preview-{ENV}",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "environment": ENV,
    "status": "FAIL",
    "module_version": None,
    "checks": {},
    "purchase_order": {},
    "ui": {},
    "errors": [],
}


def check(key, ok, detail=""):
    report["checks"][key] = {"status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]}
    if not ok:
        report["errors"].append(key)


def pdf_ok(data):
    return data and data[:4] == b"%PDF"


mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
report["module_version"] = mod.latest_version

PO = env["purchase.order"]
Report = env["ir.actions.report"]
main_action = env.ref(MAIN_ACTION)

po = PO.search([("order_line", "!=", False)], limit=1, order="id desc")
if not po:
    raise SystemExit("No purchase order found")

report["purchase_order"] = {"id": po.id, "name": po.name, "state": po.state}

check("module_version", mod.latest_version == "19.0.7.3.1", mod.latest_version)

# Botón en formulario
form = PO.get_view(view_type="form")
form_arch = form.get("arch", "")
check("button_vista_previa", "action_preview_purchase_order" in form_arch and "Vista previa" in form_arch, True)

# Acción preview nativa (NO /report/html directo)
act = po.action_preview_purchase_order()
preview_url = act.get("url", "")
check("preview_action_url", act.get("type") == "ir.actions.act_url", act.get("type"))
check("preview_target_self", act.get("target") == "self", act.get("target"))
check("preview_portal_mode", "/preview" in preview_url and "/my/purchase/" in preview_url, preview_url)
check("preview_not_bare_html", "/report/html/" not in preview_url, preview_url)
report["ui"]["preview_url"] = preview_url

# URLs iframe / PDF oficial
html_url = po.get_portal_url(suffix="/jt_report_html")
pdf_dl_url = po.get_portal_url(suffix="/jt_report_pdf", download=True)
report["ui"]["iframe_url"] = html_url
report["ui"]["download_url"] = pdf_dl_url

# HTTP autenticado — portal preview page
portal_ok = False
iframe_ok = False
download_ok = False
portal_body = ""
try:
    import requests
    from odoo import http

    base = env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
    user = env["res.users"].search([("login", "=", "admin"), ("share", "=", False)], limit=1) or env.user
    root = http.root
    session = root.session_store.new()
    session.update(
        {
            "db": DB,
            "uid": user.id,
            "login": user.login,
            "session_token": user._compute_session_token(session.sid),
        }
    )
    root.session_store.save(session)
    sess = requests.Session()
    sess.cookies.set("session_id", session.sid)

    portal_resp = sess.get(base + preview_url.replace(base, ""), timeout=60)
    portal_body = portal_resp.text or ""
    portal_ok = portal_resp.status_code == 200
    has_iframe = "purchase_order_html" in portal_body
    has_download = "o_download_btn" in portal_body and "jt_report_pdf" in portal_body
    has_print = "o_portal_po_print" in portal_body
    has_back = (
        "Back to edit mode" in portal_body
        or "portal_back_in_edit_mode" in portal_body
        or "action-purchase.purchase_rfq" in portal_body
    )
    check("portal_page_ok", portal_ok, portal_resp.status_code)
    check("portal_has_iframe", has_iframe, has_iframe)
    check("portal_has_download", has_download, has_download)
    check("portal_has_print", has_print, has_print)
    check("portal_has_back_edit", has_back, has_back)

    with open(os.path.join(OUT_DIR, "00_portal_preview.html"), "w", encoding="utf-8") as fh:
        fh.write(portal_body)

    iframe_resp = sess.get(html_url if html_url.startswith("http") else base + html_url, timeout=60)
    iframe_body = iframe_resp.text or ""
    iframe_ok = iframe_resp.status_code == 200 and "jt-po-band" in iframe_body
    check("iframe_hellenia_design", iframe_ok, f"status={iframe_resp.status_code} band={'jt-po-band' in iframe_body}")
    with open(os.path.join(OUT_DIR, "00_iframe_report.html"), "w", encoding="utf-8") as fh:
        fh.write(iframe_body)

    dl_resp = sess.get(pdf_dl_url if pdf_dl_url.startswith("http") else base + pdf_dl_url, timeout=60)
    download_ok = dl_resp.status_code == 200 and dl_resp.content[:4] == b"%PDF"
    check("download_pdf_ok", download_ok, len(dl_resp.content) if dl_resp.content else 0)
    if download_ok:
        with open(os.path.join(OUT_DIR, "02_preview_download.pdf"), "wb") as fh:
            fh.write(dl_resp.content)

except Exception as exc:
    check("portal_page_ok", False, str(exc))
    check("iframe_hellenia_design", False, str(exc))
    check("download_pdf_ok", False, str(exc))

# Menú Imprimir oficial sigue OK
pdf_bytes, _ = Report._render_qweb_pdf(main_action.report_name, po.ids)
check("print_menu_pdf_ok", pdf_ok(pdf_bytes), len(pdf_bytes))
pdf_path = os.path.join(OUT_DIR, "01_official_print_menu.pdf")
with open(pdf_path, "wb") as fh:
    fh.write(pdf_bytes)

# Enviar RFQ/PO
send_act = po.action_rfq_send()
check("send_rfq_ok", send_act.get("type") is not None, send_act.get("type"))

with open(os.path.join(OUT_DIR, "form_ui_snippet.txt"), "w", encoding="utf-8") as fh:
    buttons = re.findall(r'<button[^>]*string="([^"]*)"', form_arch)
    fh.write("Botones header:\n" + "\n".join(f"- {b}" for b in buttons))
    fh.write(f"\n\nPreview URL: {preview_url}\n")
    fh.write(f"Iframe URL: {html_url}\n")

critical = [
    "module_version",
    "button_vista_previa",
    "preview_action_url",
    "preview_target_self",
    "preview_portal_mode",
    "preview_not_bare_html",
    "portal_has_iframe",
    "portal_has_download",
    "portal_has_print",
    "portal_has_back_edit",
    "iframe_hellenia_design",
    "download_pdf_ok",
    "print_menu_pdf_ok",
    "send_rfq_ok",
]

all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical if k in report["checks"])
report["status"] = "PASS" if all_pass else "FAIL"
report["pass"] = report["status"] == "PASS"

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "env": ENV, "errors": report["errors"], "po": po.name}))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
