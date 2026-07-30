#!/usr/bin/env python3
"""Seed / publish / activate Lottery Analyst Prompt 7.0.0-rc3 on DEV."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from uuid import UUID

from app.core.security import create_access_token

BASE = "http://127.0.0.1:8022/api/v1"
UID = "185d091c-0c1c-43db-b7b8-fb6b819b173a"
TID = "8ebfa281-cd3c-4017-8e47-c572a79d84b2"
OUT = Path(__file__).resolve().parent / "activate_rc3.json"
EXPECTED_HASH = "721dc1060214b08f604dcfa27aa2b67b86c7474f42cf0c5f232712e46c770e2a"


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
            raise RuntimeError(f"{e} body={raw[:1200]}") from e
        raise


def main() -> None:
    status0 = api("GET", "/lottery/admin/ai/prompt-runtime/status")
    print("status0", json.dumps({k: status0.get(k) for k in ("runtime_mode", "studio_enabled", "active", "shadow_llm")}, ensure_ascii=False))
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
            "validation_ok": (seeded.get("validation") or {}).get("ok"),
            "tokens": (seeded.get("validation") or {}).get("tokens_estimated"),
            "hash": (seeded.get("validation") or {}).get("compiled_prompt_hash"),
        },
    )
    assert pid, seeded
    try:
        api("POST", f"/lottery/admin/ai/prompts/{pid}/validate-draft", {})
    except Exception as exc:  # noqa: BLE001
        print("validate_draft_skip", str(exc)[:200])
    pub = api("POST", f"/lottery/admin/ai/prompts/{pid}/publish-immutable", {})
    pub_p = pub.get("prompt") or {}
    print("published", pub_p.get("status"), pub_p.get("checksum"), pub_p.get("version"))
    act = api("POST", f"/lottery/admin/ai/prompts/{pid}/activate-dev", {"reason": "phase3_rc3_subject_guard"})
    active = act.get("prompt") or {}
    status1 = api("GET", "/lottery/admin/ai/prompt-runtime/status")
    out = {
        "active_version_id": active.get("id"),
        "semantic_version": active.get("version"),
        "hash": active.get("checksum") or pub_p.get("checksum"),
        "expected_hash": EXPECTED_HASH,
        "hash_match": (active.get("checksum") or pub_p.get("checksum")) == EXPECTED_HASH,
        "runtime_status": {
            "runtime_mode": status1.get("runtime_mode"),
            "studio_enabled": status1.get("studio_enabled"),
            "shadow_llm": status1.get("shadow_llm"),
            "active": status1.get("active"),
        },
        "rc2_rollback_id": "45bf3281-a0c9-4792-80c4-9033d48d8f81",
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
