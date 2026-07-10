#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera sesión HTTP admin para validación UI erp.justech.do (odoo shell)."""
from __future__ import annotations

import json

from odoo import http

DB = env.cr.dbname
BASE = env["ir.config_parameter"].sudo().get_param("web.base.url", "https://erp.justech.do").rstrip("/")

user = env["res.users"].search([("login", "=", "jinette@dynamicspm.com"), ("active", "=", True)], limit=1)
if not user:
    user = env["res.users"].search(
        [("login", "=", "administracion@justech.do"), ("active", "=", True)], limit=1
    )
if not user:
    user = env.ref("base.user_admin")

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

print(
    json.dumps(
        {
            "base_url": BASE,
            "database": DB,
            "session_id": session.sid,
            "user_login": user.login,
            "user_id": user.id,
        },
        indent=2,
    )
)
