#!/usr/bin/env python3
"""Fase 7 — Inventario de usuarios Odoo (odoo shell)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

env_name = env.cr.dbname
users = env["res.users"].with_context(active_test=False).search([])
rows = []
for u in users:
    groups = u.group_ids.mapped("full_name") or u.group_ids.mapped("name")
    rows.append(
        {
            "id": u.id,
            "login": u.login,
            "name": u.name,
            "email": u.email or "",
            "active": u.active,
            "groups": sorted(groups),
            "share": u.share,
        }
    )

report = {
    "database": env_name,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "user_count": len(rows),
    "users": sorted(rows, key=lambda r: (not r["active"], r["login"])),
}
print("USER_AUDIT:" + json.dumps(report, indent=2, ensure_ascii=False, default=str))
