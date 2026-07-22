"""Espera reconexión OAuth M365 y ejecuta cierre operativo autollenado."""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.m365_account import M365UserAccount
from app.models.tenant import Tenant
from app.models.user import User
from app.scripts.seed import ADMIN_EMAIL
from app.services.m365_official_template_sync_service import M365OfficialTemplateSyncService


async def _oauth_connected(db) -> tuple[bool, str | None]:
    accs = (
        await db.execute(
            select(M365UserAccount).where(
                M365UserAccount.connection_mode == "oauth",
                M365UserAccount.connection_status == "connected",
                M365UserAccount.is_active.is_(True),
            )
        )
    ).scalars().all()
    if not accs:
        return False, None
    return True, accs[0].email


async def main() -> int:
    max_wait_sec = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
    poll_sec = 15
    started = time.monotonic()
    print(f"[{datetime.now(timezone.utc).isoformat()}] Esperando OAuth M365 (max {max_wait_sec}s)…")

    while time.monotonic() - started < max_wait_sec:
        async with AsyncSessionLocal() as db:
            ok, email = await _oauth_connected(db)
            if ok:
                print(f"OAuth conectado: {email}")
                tenant = (await db.execute(select(Tenant).where(Tenant.slug == "justech"))).scalar_one()
                admin = (await db.execute(select(User).where(User.email == ADMIN_EMAIL))).scalar_one()
                svc = M365OfficialTemplateSyncService(db, tenant.id, admin.id)
                print("Ejecutando sync oficial…")
                result = await svc.sync_repository_and_cache()
                print(
                    f"Repo: ok={result.repository_ok} synced={result.repository_synced} "
                    f"| Cache: ok={result.cache.ok} skip={result.cache.skipped} fail={result.cache.failed}"
                )
                if result.cache.failures:
                    for f in result.cache.failures[:10]:
                        print(f"  cache_fail: {f}")
                op = result.operational
                print(
                    f"Estado: cache={op.cache_count} missing={op.cache_missing_docx} "
                    f"oauth={op.oauth_connected}"
                )
                return 0
        await asyncio.sleep(poll_sec)
        elapsed = int(time.monotonic() - started)
        print(f"  … aún desconectado ({elapsed}s)")

    print("Timeout — OAuth no reconectado.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
