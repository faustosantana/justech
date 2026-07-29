#!/usr/bin/env python3
"""Directed reproduction of Cert200 RC1 fails: LONG_30.T21/T29, G01.T04."""

from __future__ import annotations

import json
import importlib.util
import re
import sys
import time
import urllib.request
from pathlib import Path
from uuid import UUID

from app.core.security import create_access_token

AUTH = json.loads(Path("/tmp/routing3_auth.json").read_text())
BASE = "http://127.0.0.1:8000/api/v1"
BANK = json.loads(Path("/tmp/QUESTION_BANK.json").read_text())

spec = importlib.util.spec_from_file_location("cert", "/tmp/run_certification_audit.py")
cert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cert)


def token() -> str:
    return create_access_token(
        subject=AUTH["uid"], tenant_id=UUID(AUTH["tid"]), role=AUTH.get("role") or "owner"
    )


def api(method: str, path: str, body: dict | None = None, timeout: int = 300) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token()}",
            "Content-Type": "application/json",
            "X-Tenant-Id": AUTH["tid"],
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return {"_http_status": resp.status, **(json.loads(raw) if raw else {})}
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        return {
            "_http_status": e.code,
            "_error": err[:1000],
            "message": {"content": f"[HTTP {e.code}] {err[:200]}"},
        }


def cases_for(group: str) -> list[dict]:
    for c in BANK["conversations"]:
        if c.get("conversation_group") == group:
            return list(c["cases"])
    raise SystemExit(f"group {group} missing")


def ctx_snap(resp: dict) -> dict:
    v4 = ((resp.get("context") or {}).get("conversation_v4") or {})
    return {
        "active_numbers": v4.get("active_numbers"),
        "active_pair": v4.get("active_pair"),
        "active_relation": v4.get("active_relation"),
        "active_filters": v4.get("active_filters"),
        "last_intent": v4.get("last_intent"),
        "pending_intent": v4.get("pending_intent"),
        "pending_slots": v4.get("pending_slots"),
        "active_investigation": v4.get("active_investigation"),
        "active_asset_id": v4.get("active_asset_id"),
    }


def run_sequence(group: str, stop_at: str) -> dict:
    cases = cases_for(group)
    created = api("POST", "/lottery/chat/sessions", {"title": f"directed-{group}-{stop_at}"})
    sid = str(created.get("id") or "")
    rows = []
    target = None
    for case in cases:
        t0 = time.perf_counter()
        resp = api(
            "POST",
            f"/lottery/chat/sessions/{sid}/messages",
            {"content": case["user_message"]},
        )
        ms = int((time.perf_counter() - t0) * 1000)
        text = ((resp.get("message") or {}).get("content") or "")
        repo = (
            cert.expected_for_case(case)
            if case.get("factual_validation_required")
            else None
        )
        ev = cert.evaluate_turn(case, resp, repo)
        hermes = resp.get("hermes_decision") or {}
        runtime = resp.get("runtime_trace") or {}
        row = {
            "case_id": case["case_id"],
            "user_message": case["user_message"],
            "expected_intent": case.get("expected_intent"),
            "expected_subjects": case.get("expected_subjects"),
            "expected_tool_family": case.get("expected_tool_family"),
            "expected_filters": case.get("expected_filters"),
            "got_intent": resp.get("intent"),
            "hermes_turn_type": hermes.get("turn_type"),
            "hermes_reason_code": hermes.get("reason_code")
            or runtime.get("reason_code"),
            "inherited_subjects": hermes.get("inherited_subjects"),
            "workspace_action": hermes.get("workspace_action"),
            "state": ctx_snap(resp),
            "repo_expected": repo,
            "answer": text[:500],
            "latency_ms": ms,
            "eval_pass": not (ev.get("fails") or []),
            "eval_fails": ev.get("fails") or [],
            "eval_notes": ev.get("notes") or [],
        }
        rows.append(row)
        print(
            f"{'PASS' if row['eval_pass'] else 'FAIL'} {case['case_id']} "
            f"{ms}ms :: {case['user_message'][:50]} | fails={row['eval_fails']}"
        )
        if case["case_id"] == stop_at:
            target = row
            break
    return {"session_id": sid, "group": group, "stop_at": stop_at, "turns": rows, "target": target}


def main() -> int:
    out = {
        "LONG_30.T21": run_sequence("LONG_30", "LONG_30.T21"),
        "LONG_30.T29": run_sequence("LONG_30", "LONG_30.T29"),
        "G01.T04": run_sequence("G01", "G01.T04"),
    }
    path = Path("/tmp/RC1_DIRECTED_3.json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print("WROTE", path)
    # summary
    for k, v in out.items():
        t = v["target"] or {}
        print("\n====", k, "====")
        print("prev:", [x["user_message"] for x in v["turns"][:-1][-5:]])
        print("msg:", t.get("user_message"))
        print("expected:", t.get("expected_intent"), t.get("expected_subjects"), t.get("expected_filters"))
        print("got_intent/hermes:", t.get("got_intent"), t.get("hermes_turn_type"), t.get("hermes_reason_code"))
        print("inherited:", t.get("inherited_subjects"))
        print("state:", t.get("state"))
        print("repo:", t.get("repo_expected"))
        print("fails:", t.get("eval_fails"), t.get("eval_notes"))
        print("answer:", (t.get("answer") or "")[:280])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
