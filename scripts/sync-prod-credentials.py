#!/usr/bin/env python3
"""Sincronizar credenciales admin e it@justech.do desde DEV (hashes pbkdf2).

Ejecutar en odoo shell de PRODUCCIÓN. Variables de entorno:
  SYNC_ADMIN_HASH — hash password admin desde hellenia_dev
  SYNC_IT_HASH — hash password it@justech.do desde hellenia_dev
  SYNC_IT_NAME, SYNC_IT_EMAIL, SYNC_IT_LANG, SYNC_IT_TZ — metadatos usuario IT
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

IT_LOGIN = "it@justech.do"
GROUP_XMLIDS = [
    "base.group_system",
    "base.group_erp_manager",
    "account.group_account_manager",
    "sales_team.group_sale_manager",
    "purchase.group_purchase_manager",
    "stock.group_stock_manager",
    "base.group_no_one",
    "justech_l10n_do_base.group_justech_do_fiscal_manager",
]

report = {
    "phase": "prod-credentials",
    "database": env.cr.dbname,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "users": {},
    "ok": True,
    "errors": [],
}


def fail(msg: str) -> None:
    report["ok"] = False
    report["errors"].append(msg)


def apply_hash(login: str, pw_hash: str) -> None:
    if not pw_hash or not pw_hash.startswith("$"):
        fail(f"Hash inválido para {login}")
        return
    env.cr.execute(
        "UPDATE res_users SET password = %s WHERE login = %s AND active = true",
        (pw_hash, login),
    )
    report["users"][login] = {"action": "hash_applied", "rows": env.cr.rowcount}


admin_hash = os.environ.get("SYNC_ADMIN_HASH", "").strip()
it_hash = os.environ.get("SYNC_IT_HASH", "").strip()

if admin_hash:
    apply_hash("admin", admin_hash)
else:
    fail("SYNC_ADMIN_HASH no definido")

Users = env["res.users"].with_context(active_test=False)
it_user = Users.search([("login", "=", IT_LOGIN)], limit=1)

if not it_user and it_hash:
    group_ids = []
    for xid in GROUP_XMLIDS:
        g = env.ref(xid, raise_if_not_found=False)
        if g:
            group_ids.append(g.id)
    lang = os.environ.get("SYNC_IT_LANG", "es_DO")
    tz = os.environ.get("SYNC_IT_TZ", "America/Santo_Domingo")
    name = os.environ.get("SYNC_IT_NAME", "Justech IT")
    email = os.environ.get("SYNC_IT_EMAIL", IT_LOGIN)
    it_user = Users.create(
        {
            "name": name,
            "login": IT_LOGIN,
            "email": email,
            "active": True,
            "lang": lang,
            "tz": tz,
            "group_ids": [(6, 0, group_ids)],
        }
    )
    report["users"][IT_LOGIN] = {"action": "created", "id": it_user.id}
    apply_hash(IT_LOGIN, it_hash)
elif it_user and it_hash:
    it_user.write(
        {
            "name": os.environ.get("SYNC_IT_NAME", it_user.name),
            "email": os.environ.get("SYNC_IT_EMAIL", it_user.email),
            "lang": os.environ.get("SYNC_IT_LANG", it_user.lang),
            "tz": os.environ.get("SYNC_IT_TZ", it_user.tz),
            "active": True,
        }
    )
    report["users"][IT_LOGIN] = {"action": "updated", "id": it_user.id}
    apply_hash(IT_LOGIN, it_hash)
elif not it_hash:
    fail("SYNC_IT_HASH no definido")

env.cr.commit()
print("SYNC_PROD_CREDENTIALS:" + json.dumps(report, ensure_ascii=False, default=str))
