#!/usr/bin/env python3
"""Stress / cache / rollback / security checks for frozen Prompt Runtime (no behavior changes)."""
from __future__ import annotations

import concurrent.futures
import json
import time
import urllib.request
from pathlib import Path
from uuid import UUID

from app.core.security import create_access_token
from app.lottery.ai.prompt_runtime.cache import cache_get, cache_invalidate, cache_set
from app.lottery.ai.prompt_runtime.compiler import PromptStudioCompiler
from app.lottery.ai.prompt_runtime.seed_reasoning_studio_v7_rc3 import build_rc3_blocks

AUTH = json.loads(Path("/tmp/routing3_auth.json").read_text())
BASE = "http://127.0.0.1:8000/api/v1"
UID, TID, ROLE = AUTH["uid"], AUTH["tid"], AUTH.get("role") or "owner"
OUT = Path("/tmp/runtime_hardening.json")
EXPECTED = "41c64a0fc7c303222c2b492e82a0ea51cec6c16139bc2f0cde9ec9e9da642ff9"


def api(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    tok = create_access_token(subject=UID, tenant_id=UUID(TID), role=ROLE)
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "X-Tenant-Id": TID,
        },
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def one_chat(i: int) -> dict:
    t0 = time.perf_counter()
    s = api("POST", "/lottery/chat/sessions", {"title": f"stress-{i}"})
    sid = s.get("id") or s["session"]["id"]
    r = api(
        "POST",
        f"/lottery/chat/sessions/{sid}/messages",
        {"content": "¿Han coincidido el 50 y el 90 el mismo día?"},
    )
    ans = ((r.get("message") or {}).get("content") or "")
    return {"i": i, "ms": (time.perf_counter() - t0) * 1000, "ok": len(ans) > 10, "preview": ans[:80]}


def main() -> None:
    report: dict = {"expected_hash": EXPECTED}

    # --- cache / compiler ---
    t0 = time.perf_counter()
    c1 = PromptStudioCompiler.compile(build_rc3_blocks())
    compile_ms = (time.perf_counter() - t0) * 1000
    cache_invalidate("stress-key")
    cache_set(
        application="stress-key",
        version_id="rc3.4",
        body=c1["body"],
        compiled_prompt_hash=c1["compiled_prompt_hash"],
        semantic_version="7.0.0-rc3.4",
        ttl_seconds=60,
        meta={"hash": c1["compiled_prompt_hash"]},
    )
    t1 = time.perf_counter()
    hit = cache_get("stress-key")
    lookup_ms = (time.perf_counter() - t1) * 1000
    report["performance"] = {
        "compile_ms": round(compile_ms, 2),
        "cache_lookup_ms": round(lookup_ms, 2),
        "cache_hit": bool(hit),
        "compiled_hash": c1["compiled_prompt_hash"],
        "hash_match": c1["compiled_prompt_hash"] == EXPECTED,
    }

    # --- security scan of compiled prompt ---
    body = c1["body"].lower()
    leaks = []
    for needle in ("api_key", "sk-", "password", "Bearer ", "postgresql://", "/Users/", "secret"):
        if needle.lower() in body:
            leaks.append(needle)
    report["security"] = {
        "compiled_leaks": leaks,
        "pass": len(leaks) == 0 and "system prompt" not in body,
    }

    # --- status / pin ---
    st = api("GET", "/lottery/admin/ai/prompt-runtime/status")
    report["runtime_status"] = {
        "runtime_mode": st.get("runtime_mode"),
        "studio_enabled": st.get("studio_enabled"),
        "shadow_llm": st.get("shadow_llm"),
        "pinned_version_id": st.get("pinned_version_id"),
        "active_version": (st.get("active") or {}).get("version"),
        "active_hash": (st.get("active") or {}).get("checksum"),
        "forensic": st.get("forensic_trace_enabled"),
    }

    # --- rollback catalog (rc3.3 ↔ rc3.4) without backend restart ---
    RC33 = "96385092-612c-4cf6-8394-b5734ca872a3"
    RC34 = "c41ec4c5-1bd5-430f-85c5-e9546e176709"
    rollback = {"ok": False}
    try:
        # ensure published
        api("POST", f"/lottery/admin/ai/prompts/{RC33}/activate-dev", {"reason": "hardening_rollback_a"})
        a = api("GET", "/lottery/admin/ai/prompt-runtime/status")
        api("POST", f"/lottery/admin/ai/prompts/{RC34}/activate-dev", {"reason": "hardening_rollback_b"})
        b = api("GET", "/lottery/admin/ai/prompt-runtime/status")
        rollback = {
            "ok": (b.get("active") or {}).get("version") == "7.0.0-rc3.4",
            "mid_version": (a.get("active") or {}).get("version"),
            "final_version": (b.get("active") or {}).get("version"),
            "final_hash": (b.get("active") or {}).get("checksum"),
            "no_restart": True,
        }
    except Exception as exc:  # noqa: BLE001
        rollback = {"ok": False, "error": str(exc)[:300]}
    report["rollback"] = rollback

    # --- concurrent stress (8 parallel chats) ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(one_chat, i) for i in range(8)]
        rows = [f.result() for f in concurrent.futures.as_completed(futs)]
    report["stress"] = {
        "n": len(rows),
        "ok": sum(1 for r in rows if r["ok"]),
        "p95_ms": sorted(r["ms"] for r in rows)[min(len(rows) - 1, int(0.95 * (len(rows) - 1)))],
        "pass": all(r["ok"] for r in rows),
    }

    report["PASS"] = (
        report["performance"]["hash_match"]
        and report["security"]["pass"]
        and report["rollback"].get("ok")
        and report["stress"]["pass"]
        and report["runtime_status"].get("runtime_mode") == "shadow"
    )
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
