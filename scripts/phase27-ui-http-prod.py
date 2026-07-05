# -*- coding: utf-8 -*-
"""Simula rutas HTTP UI en PROD (no shell QWeb) para factura 132."""
from __future__ import annotations

import json
import os
import sys
import uuid

import requests

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

BASE = env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
INV = env["account.move"].search([("name", "=", "INV/2026/00006")], limit=1)
if not INV:
    raise SystemExit("Invoice INV/2026/00006 not found")

if not INV.access_token:
    INV.sudo().write({"access_token": str(uuid.uuid4())})
    env.cr.commit()

# Usuario interno real (no superuser shell) — preferir admin de negocio
user = env["res.users"].search(
    [("login", "=", "admin"), ("share", "=", False)], limit=1
) or env["res.users"].search([("share", "=", False), ("active", "=", True)], limit=1)

# Sesión HTTP válida contra el servidor en ejecución
from odoo import http
from odoo.service import security

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
session_id = session.sid

out = {
    "base_url": BASE,
    "database": DB,
    "invoice": {"id": INV.id, "name": INV.name},
    "session_user": {"id": user.id, "login": user.login},
    "tests": {},
}

sess = requests.Session()
sess.cookies.set("session_id", session_id)

# --- Portal Vista previa (iframe HTML) ---
portal_html_url = (
    f"{BASE}/my/invoices/{INV.id}"
    f"?access_token={INV.access_token}&report_type=html"
)
try:
    r = sess.get(portal_html_url, timeout=60)
    body = r.text or ""
    out["tests"]["portal_report_type_html"] = {
        "url": portal_html_url,
        "status": r.status_code,
        "bytes": len(r.content),
        "has_jt_band": "jt-inv-band" in body,
        "has_qweb_error": "QWebError" in body or "hellenia_legal_notice" in body,
        "snippet": body[:300],
    }
except Exception as exc:
    out["tests"]["portal_report_type_html"] = {"error": str(exc)}

# --- call_button: preview_invoice ---
try:
    r = sess.post(
        f"{BASE}/web/dataset/call_button/account.move/preview_invoice",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "args": [[INV.id]],
                "kwargs": {"context": env.context},
            },
            "id": 1,
        },
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    data = r.json()
    result = data.get("result") or {}
    out["tests"]["call_button_preview_invoice"] = {
        "status_http": r.status_code,
        "error": data.get("error"),
        "action_type": result.get("type"),
        "action_url": result.get("url"),
    }
except Exception as exc:
    out["tests"]["call_button_preview_invoice"] = {"error": str(exc)}

# --- call_button: action_print_pdf ---
try:
    r = sess.post(
        f"{BASE}/web/dataset/call_button/account.move/action_print_pdf",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "args": [[INV.id]],
                "kwargs": {"context": dict(env.context, active_id=INV.id, active_ids=[INV.id])},
            },
            "id": 2,
        },
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    data = r.json()
    result = data.get("result") or {}
    out["tests"]["call_button_action_print_pdf"] = {
        "status_http": r.status_code,
        "error": data.get("error"),
        "action_type": result.get("type"),
        "report_name": result.get("report_name"),
        "res_model": result.get("res_model"),
    }
except Exception as exc:
    out["tests"]["call_button_action_print_pdf"] = {"error": str(exc)}

# --- Menú Imprimir → Invoice PDF (/report/download) ---
report = env.ref("account.account_invoices")
dl_payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "data": json.dumps(
            [
                "/report/download",
                "qweb-pdf",
                report.report_name,
                [INV.id],
                {"report_type": "qweb-pdf"},
            ]
        )
    },
    "id": 3,
}
try:
    r = sess.post(
        f"{BASE}/report/download",
        data=dl_payload,
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    out["tests"]["report_download"] = {
        "url": f"{BASE}/report/download",
        "status_http": r.status_code,
        "bytes": len(r.content),
        "is_pdf": r.content[:4] == b"%PDF" if r.content else False,
        "content_type": r.headers.get("Content-Type"),
        "report_name": report.report_name,
        "action_xml_id": "account.account_invoices",
    }
except Exception as exc:
    out["tests"]["report_download"] = {"error": str(exc)}

# --- Enviar (abre wizard) ---
try:
    r = sess.post(
        f"{BASE}/web/dataset/call_button/account.move/action_invoice_sent",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "args": [[INV.id]],
                "kwargs": {"context": dict(env.context, active_id=INV.id, active_ids=[INV.id])},
            },
            "id": 4,
        },
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    data = r.json()
    result = data.get("result") or {}
    out["tests"]["call_button_action_invoice_sent"] = {
        "status_http": r.status_code,
        "error": data.get("error"),
        "action_type": result.get("type"),
        "res_model": result.get("res_model"),
        "name": result.get("name"),
    }
except Exception as exc:
    out["tests"]["call_button_action_invoice_sent"] = {"error": str(exc)}

out_dir = "/tmp/phase27-ui-http-prod"
os.makedirs(out_dir, exist_ok=True)
path = os.path.join(out_dir, "ui_http.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print(json.dumps(out, indent=2, ensure_ascii=False))
