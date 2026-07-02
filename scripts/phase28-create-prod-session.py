# -*- coding: utf-8 -*-
"""Genera sesión HTTP para usuario it@justech.do en PROD (UI Playwright)."""
from __future__ import annotations

import json

DB = env.cr.dbname
user = env["res.users"].browse(5)
if not user.exists():
    user = env["res.users"].search([("login", "=", "it@justech.do")], limit=1)
if not user:
    raise SystemExit("User it@justech.do not found")

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

out = {
    "database": DB,
    "uid": user.id,
    "login": user.login,
    "session_id": session.sid,
}
with open("/tmp/odoo_prod_session_phase28.json", "w") as f:
    json.dump(out, f)
print(json.dumps(out))
