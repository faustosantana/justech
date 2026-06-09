"""Emite tokens de sesión E2E (solo dev/QA). Credenciales desde seed."""

from __future__ import annotations

import asyncio
import json
import sys

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD


async def _login() -> dict:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "tenant_slug": "justech",
            },
        )
        response.raise_for_status()
        return response.json()


def main() -> None:
    payload = asyncio.run(_login())
    out = {
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "tenant_id": payload.get("tenant_id"),
    }
    dest = sys.argv[1] if len(sys.argv) > 1 else None
    if dest:
        from pathlib import Path

        Path(dest).write_text(json.dumps(out), encoding="utf-8")
        print(f"tokens written: {dest}")
    else:
        json.dump(out, sys.stdout)


if __name__ == "__main__":
    main()
