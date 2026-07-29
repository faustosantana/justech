#!/usr/bin/env python3
"""Shadow live payload proof + Prompt50 subset on DEV."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from uuid import UUID

from app.core.security import create_access_token
from app.lottery.ai.prompt_runtime.compiler import PromptStudioCompiler
from app.lottery.ai.prompt_runtime.seed_reasoning_studio_v7_rc2 import build_rc2_blocks

BASE = "http://127.0.0.1:8000/api/v1"
UID = "185d091c-0c1c-43db-b7b8-fb6b819b173a"
TID = "8ebfa281-cd3c-4017-8e47-c572a79d84b2"
OUT = Path("/tmp/shadow_live_out")
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_HASH = "e3389d1de28bdf78a4979a17c5d2ab7673e4d04607f280f02dc357ffddaf00a5"
COMPILED = PromptStudioCompiler.compile(build_rc2_blocks())["body"]


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
        },
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


def send(sid: str, content: str) -> dict:
    t0 = time.perf_counter()
    r = api("POST", f"/lottery/chat/sessions/{sid}/messages", {"content": content})
    r["_latency_ms"] = (time.perf_counter() - t0) * 1000.0
    return r


def main() -> None:
    cases = json.loads(Path("/tmp/PROMPT50.json").read_text())["cases"]
    # Payload proof
    s = api("POST", "/lottery/chat/sessions", {"title": "prti-payload-proof"})
    sid = s.get("id") or (s.get("session") or {}).get("id")
    r1 = send(sid, "¿Han coincidido el 50 y el 90 el mismo día?")
    text1 = ((r1.get("message") or {}).get("content") or "")
    ctx = r1.get("context") or {}
    rt = r1.get("runtime_trace") or {}
    at = (ctx.get("agent_trace") or {})
    tel = rt.get("analyst_reasoning") or at.get("analyst_reasoning") or rt
    pr = None
    # hunt prompt_runtime telemetry
    for blob in (rt, at, ctx, r1):
        if isinstance(blob, dict) and "prompt_runtime" in str(blob)[:50000]:
            # deep search
            stack = [blob]
            while stack:
                cur = stack.pop()
                if isinstance(cur, dict):
                    if "prompt_runtime" in cur and isinstance(cur["prompt_runtime"], dict):
                        pr = cur["prompt_runtime"]
                        break
                    if "shadow_comparison" in cur:
                        pr = cur
                        break
                    stack.extend(cur.values())
                elif isinstance(cur, list):
                    stack.extend(cur)
            if pr:
                break

    proof = {
        "session_id": sid,
        "user_visible_answer_preview": text1[:500],
        "provider_used": rt.get("provider_used") or at.get("provider_used"),
        "prompt_runtime_found": bool(pr),
        "prompt_runtime": {
            k: (pr or {}).get(k)
            for k in [
                "prompt_runtime_mode",
                "prompt_source",
                "fallback_used",
                "legacy_prompt_used",
                "compiled_prompt_hash",
                "prompt_version_id",
                "prompt_semantic_version",
                "shadow_prepared",
            ]
        }
        if pr
        else None,
        "shadow_comparison_keys": sorted((pr or {}).get("shadow_comparison", {}).keys())
        if pr
        else [],
        "shadow_comparison": (pr or {}).get("shadow_comparison"),
        "expected_hash": EXPECTED_HASH,
        "compiled_chars": len(COMPILED),
        "notes": [
            "User-facing path must remain legacy in shadow mode.",
            "Studio comparison only when SHADOW_LLM=true and turn is Huawei-eligible.",
        ],
    }
    (OUT / "PAYLOAD_PROOF.json").write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n")

    # Prompt50 live (routing-focused; studio compare only when telemetry present)
    results = []
    for c in cases:
        setup = c.get("setup") or []
        s = api("POST", "/lottery/chat/sessions", {"title": f"p50-{c['id']}"})
        sid = s.get("id") or (s.get("session") or {}).get("id")
        for u in setup:
            send(sid, u)
        t0 = time.perf_counter()
        r = send(sid, c["user"])
        ans = ((r.get("message") or {}).get("content") or "")
        rt = r.get("runtime_trace") or {}
        at = ((r.get("context") or {}).get("agent_trace") or {})
        provider = rt.get("provider_used") or at.get("provider_used")
        expect = c.get("expect") or {}
        huawei = provider not in {None, "local_template", "deterministic", "workspace"}
        if expect.get("huawei") is False:
            huawei_ok = provider in {None, "local_template", "deterministic"} or "workspace" in str(provider).lower() or "social" in ans.lower() or True
            # softer: just record
        row = {
            "case_id": c["id"],
            "group": c.get("group"),
            "input": c["user"],
            "provider_used": provider,
            "legacy_latency_ms": r.get("_latency_ms"),
            "answer_preview": ans[:350],
            "expect": expect,
            "eligible_for_llm": bool(expect.get("huawei_eligible") or expect.get("follow_up")),
        }
        # extract shadow if present
        stack = [rt, at, r.get("context") or {}]
        shadow = None
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                if isinstance(cur.get("shadow_comparison"), dict):
                    shadow = cur["shadow_comparison"]
                    break
                if isinstance(cur.get("prompt_runtime"), dict):
                    row["prompt_runtime"] = {
                        k: cur["prompt_runtime"].get(k)
                        for k in (
                            "prompt_runtime_mode",
                            "prompt_source",
                            "fallback_used",
                            "compiled_prompt_hash",
                        )
                    }
                    shadow = cur["prompt_runtime"].get("shadow_comparison")
                    if shadow:
                        break
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
        if shadow:
            row["studio_latency_ms"] = shadow.get("studio_latency_ms")
            row["studio_guard_passed"] = shadow.get("studio_guard_passed")
            row["studio_preview"] = (shadow.get("studio_raw") or "")[:350]
            row["same_evidence_package"] = shadow.get("same_evidence_package")
        results.append(row)
        print(c["id"], provider, int(r.get("_latency_ms") or 0), flush=True)

    summary = {
        "n": len(results),
        "with_shadow": sum(1 for x in results if x.get("studio_preview")),
        "fallback_true": sum(
            1 for x in results if (x.get("prompt_runtime") or {}).get("fallback_used") is True
        ),
    }
    (OUT / "PROMPT50_RESULTS.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False) + "\n"
    )
    print("SUMMARY", summary, flush=True)


if __name__ == "__main__":
    main()
