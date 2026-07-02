# -*- coding: utf-8 -*-
"""Genera sesión HTTP + URL PO para capturas UI vista previa nativa."""
from __future__ import annotations

import json

DB = env.cr.dbname
user = env["res.users"].search([("login", "=", "admin"), ("share", "=", False)], limit=1) or env.user
po = env["purchase.order"].search([("order_line", "!=", False)], limit=1, order="id desc")
if not po:
    raise SystemExit("No PO found")

from odoo import http

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

base = env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
env_name = "prod" if DB == "hellenia_prod" else "test"
out_path = f"/tmp/odoo_{env_name}_session_po_native_preview.json"
out = {
    "database": DB,
    "uid": user.id,
    "login": user.login,
    "session_id": session.sid,
    "po_id": po.id,
    "po_name": po.name,
    "po_url": f"{base}/odoo/action-purchase.purchase_rfq/{po.id}",
}
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
print(json.dumps(out))
