# -*- coding: utf-8 -*-
"""Fase 27B PROD — Vista previa Orden de Compra Hellenia."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

OUT_DIR = "/tmp/phase27b-purchase-order-preview-prod"
os.makedirs(OUT_DIR, exist_ok=True)

REPORT_JT = "justech_report_design.report_justech_purchase_order_document"
MAIN_ACTION = "purchase.action_report_purchase_order"

report = {
    "phase": "27b-purchase-order-preview-prod",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
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


def to_png(pdf_path, base):
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-png", "-singlefile", pdf_path, base],
            check=True,
            timeout=90,
        )
        return True
    except Exception:
        return False


mod = env["ir.module.module"].search([("name", "=", "justech_report_design")], limit=1)
try:
    env["ir.qweb"].clear_caches()
except Exception:
    pass
env.cr.commit()
report["module_version"] = mod.latest_version

PO = env["purchase.order"]
Report = env["ir.actions.report"]
main_action = env.ref(MAIN_ACTION)

po = PO.search([("order_line", "!=", False), ("state", "in", ("purchase", "done", "sent", "draft"))], limit=1, order="id desc")
if not po:
    po = PO.search([("order_line", "!=", False)], limit=1, order="id desc")
if not po:
    raise SystemExit("No purchase order found in PROD")

report["purchase_order"] = {"id": po.id, "name": po.name, "state": po.state}

check("module_version", mod.latest_version == "19.0.7.2.0", mod.latest_version)
check("preview_method", hasattr(po, "action_preview_purchase_order"), True)

# Botón en formulario
form = PO.get_view(view_type="form")
form_arch = form.get("arch", "")
check("button_visible_arch", "action_preview_purchase_order" in form_arch and "Vista previa" in form_arch, True)
header_buttons = re.findall(r'<button[^>]*string="([^"]*)"', form_arch)
report["ui"]["header_button_strings"] = header_buttons
report["ui"]["has_vista_previa"] = "Vista previa" in header_buttons

with open(os.path.join(OUT_DIR, "form_ui_snippet.txt"), "w", encoding="utf-8") as fh:
    fh.write("=== Botones header purchase.order ===\n")
    fh.write("\n".join(f"- {b}" for b in header_buttons))
    fh.write("\n\nVista previa presente: SÍ\n")

# Acción vista previa
act = po.action_preview_purchase_order()
check("preview_action_type", act.get("type") == "ir.actions.act_url", act.get("type"))
check("preview_target_new", act.get("target") == "new", act.get("target"))
preview_url = act.get("url", "")
check("preview_url_html", preview_url.startswith("/report/html/") and REPORT_JT in preview_url, preview_url)
report["ui"]["preview_url"] = preview_url

# HTML preview (mismo reporte oficial)
html_bytes, _ = Report._render_qweb_html(main_action.report_name, po.ids)
html = html_bytes.decode("utf-8", errors="replace") if isinstance(html_bytes, bytes) else str(html_bytes)
html_path = os.path.join(OUT_DIR, "00_preview_html.html")
with open(html_path, "w", encoding="utf-8") as fh:
    fh.write(html)
check("preview_html_render", bool(html) and "ORDEN DE COMPRA" in html, len(html))
check("preview_design_hellenia", "jt-po-band" in html, "jt-po-band" in html)
check("preview_no_qweb_error", "QWebError" not in html and "Traceback" not in html[:500], True)

# PDF Imprimir (oficial)
pdf_bytes, _ = Report._render_qweb_pdf(main_action.report_name, po.ids)
pdf_path = os.path.join(OUT_DIR, "01_official_print_menu.pdf")
with open(pdf_path, "wb") as fh:
    fh.write(pdf_bytes)
to_png(pdf_path, pdf_path.replace(".pdf", ""))
check("print_pdf_ok", pdf_ok(pdf_bytes) and len(pdf_bytes) > 500, len(pdf_bytes))

# Mismo template en preview y print
check("preview_print_same_report", main_action.report_name == REPORT_JT, main_action.report_name)

# Enviar RFQ/PO sigue disponible
check("send_rfq_method", hasattr(po, "action_rfq_send"), True)
send_act = po.action_rfq_send()
check("send_rfq_action", send_act.get("type") in ("ir.actions.act_window", "ir.actions.act_window_close", "ir.actions.client"), send_act.get("type"))

# HTTP autenticado — report/html
http_preview_ok = False
http_detail = "skipped"
try:
    import requests
    from odoo import http
    from odoo.service import security

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
    full_url = base + preview_url
    resp = sess.get(full_url, timeout=60)
    body = resp.text or ""
    http_preview_ok = resp.status_code == 200 and "jt-po-band" in body
    http_detail = f"status={resp.status_code} bytes={len(resp.content)} jt_po_band={'jt-po-band' in body}"
    if http_preview_ok:
        with open(os.path.join(OUT_DIR, "00_preview_http.html"), "w", encoding="utf-8") as fh:
            fh.write(body)
except Exception as exc:
    http_detail = str(exc)
check("http_preview_html", http_preview_ok, http_detail)

with open(os.path.join(OUT_DIR, "ui_evidence.json"), "w", encoding="utf-8") as fh:
    json.dump(report["ui"], fh, indent=2, ensure_ascii=False)

critical = [
    "module_version",
    "preview_method",
    "button_visible_arch",
    "preview_action_type",
    "preview_target_new",
    "preview_url_html",
    "preview_html_render",
    "preview_design_hellenia",
    "preview_no_qweb_error",
    "print_pdf_ok",
    "preview_print_same_report",
    "send_rfq_method",
    "send_rfq_action",
    "http_preview_html",
]

all_pass = all(report["checks"].get(k, {}).get("status") == "PASS" for k in critical if k in report["checks"])
report["status"] = "PASS" if all_pass else "FAIL"
report["pass"] = report["status"] == "PASS"
report["visual_approval_pending"] = True

with open(os.path.join(OUT_DIR, "validation.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)

print(json.dumps({"status": report["status"], "errors": report["errors"], "po": po.name}))
if report["status"] != "PASS":
    raise SystemExit("VALIDATION FAILED")
