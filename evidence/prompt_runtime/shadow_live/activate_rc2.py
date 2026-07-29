#!/usr/bin/env python3
"""Seed / publish / activate Reasoning Studio rc2 on DEV (8022)."""
from __future__ import annotations

import json
import urllib.request
from uuid import UUID

from app.core.security import create_access_token

BASE = "http://127.0.0.1:8022/api/v1"
UID = "185d091c-0c1c-43db-b7b8-fb6b819b173a"
TID = "8ebfa281-cd3c-4017-8e47-c572a79d84b2"


def api(method: str, path: str, body=None):
    data = None if body is None else json.dumps(body).encode()
    tok = create_access_token(subject=UID, tenant_id=UUID(TID), role="owner")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "X-Tenant-Id": TID,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        if hasattr(e, "read"):
            raw = e.read().decode()  # type: ignore[attr-defined]
            raise RuntimeError(f"{e} body={raw[:800]}") from e
        raise


def main() -> None:
    status0 = api("GET", "/lottery/admin/ai/prompt-runtime/status")
    print("status0", json.dumps({k: status0.get(k) for k in ("runtime_mode", "studio_enabled", "active")}, ensure_ascii=False))
    seeded = api("POST", "/lottery/admin/ai/prompt-runtime/seed-candidate", {})
    prompt = seeded.get("prompt") or {}
    pid = prompt.get("id")
    print(
        "seeded",
        {
            "created": seeded.get("created"),
            "id": pid,
            "version": prompt.get("version"),
            "status": prompt.get("status"),
            "validation": seeded.get("validation"),
        },
    )
    assert pid, seeded
    # validate-draft (optional)
    try:
        api("POST", f"/lottery/admin/ai/prompts/{pid}/validate-draft", {})
    except Exception as exc:  # noqa: BLE001
        print("validate_draft_skip", str(exc)[:200])
    pub = api("POST", f"/lottery/admin/ai/prompts/{pid}/publish-immutable", {})
    print("published", (pub.get("prompt") or {}).get("status"), (pub.get("prompt") or {}).get("checksum"))
    act = api("POST", f"/lottery/admin/ai/prompts/{pid}/activate-dev", {"reason": "shadow_live_rc2"})
    active = act.get("prompt") or {}
    print(
        "activated",
        {
            "id": active.get("id"),
            "version": active.get("version"),
            "status": active.get("status"),
            "checksum": active.get("checksum"),
        },
    )
    status1 = api("GET", "/lottery/admin/ai/prompt-runtime/status")
    out = {
        "active_version_id": active.get("id"),
        "semantic_version": active.get("version"),
        "hash": active.get("checksum"),
        "runtime_status": {
            "runtime_mode": status1.get("runtime_mode"),
            "studio_enabled": status1.get("studio_enabled"),
            "shadow_llm": status1.get("shadow_llm"),
            "active": status1.get("active"),
        },
    }
    Path = __import__("pathlib").Path
    Path("/tmp/prompt_runtime_activate.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
