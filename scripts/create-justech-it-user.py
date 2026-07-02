#!/usr/bin/env python3
"""Fase 7 — Crear usuario técnico Justech IT (odoo shell).

Requiere variable de entorno JUSTECH_IT_PASSWORD (no inventar contraseña).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

LOGIN = "it@justech.do"
NAME = "Justech IT"
EMAIL = "it@justech.do"
LANG = "es_DO"
TZ = "America/Santo_Domingo"

password = os.environ.get("JUSTECH_IT_PASSWORD", "").strip()
if not password:
    print(
        json.dumps(
            {
                "ok": False,
                "error": "JUSTECH_IT_PASSWORD not set — user not created",
                "login": LOGIN,
            }
        )
    )
    raise SystemExit(2)

Group = env.ref
group_xmlids = [
    "base.group_system",
    "base.group_erp_manager",
    "account.group_account_manager",
    "sales_team.group_sale_manager",
    "purchase.group_purchase_manager",
    "stock.group_stock_manager",
    "base.group_no_one",
    "justech_l10n_do_base.group_justech_do_fiscal_manager",
]
if env["ir.module.module"].search([("name", "=", "point_of_sale"), ("state", "=", "installed")]):
    group_xmlids.append("point_of_sale.group_pos_manager")

group_ids = []
missing = []
for xid in group_xmlids:
    g = env.ref(xid, raise_if_not_found=False)
    if g:
        group_ids.append(g.id)
    else:
        missing.append(xid)

lang = env["res.lang"].search([("code", "=", LANG)], limit=1)
if not lang:
    lang = env["res.lang"].search([("code", "=", "es_DO")], limit=1)
if not lang:
    lang = env["res.lang"].search([("code", "=", "es_419")], limit=1)

user = env["res.users"].with_context(active_test=False).search([("login", "=", LOGIN)], limit=1)
vals = {
    "name": NAME,
    "login": LOGIN,
    "email": EMAIL,
    "active": True,
    "tz": TZ,
    "group_ids": [(6, 0, group_ids)],
}
if lang:
    vals["lang"] = lang.code

if user:
    user.write(vals)
    user.password = password
    action = "updated"
else:
    vals["password"] = password
    user = env["res.users"].create(vals)
    action = "created"

admin = env.ref("base.user_admin")
result = {
    "ok": True,
    "action": action,
    "database": env.cr.dbname,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "user": {"id": user.id, "login": user.login, "name": user.name, "active": user.active},
    "admin_preserved": {"id": admin.id, "login": admin.login, "active": admin.active},
    "groups_assigned": len(group_ids),
    "groups_missing": missing,
    "lang": user.lang,
    "tz": user.tz,
}
env.cr.commit()
print("JUSTECH_IT_USER:" + json.dumps(result, indent=2, ensure_ascii=False))
