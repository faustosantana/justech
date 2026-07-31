#!/usr/bin/env python3
"""Routing200 — verify Studio does not intervene on non-Huawei routes.

Separate from Shadow200 (eligible dual-LLM quality). Product frozen.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.core.security import create_access_token

BASE = os.environ.get("FORENSIC_BASE_URL", "http://127.0.0.1:8000/api/v1")
OUT = Path(os.environ.get("ROUTING_OUT", "/tmp/routing200_out"))
OUT.mkdir(parents=True, exist_ok=True)
AUTH = json.loads(Path("/tmp/routing3_auth.json").read_text()) if Path("/tmp/routing3_auth.json").exists() else {
    "uid": "e520ca09-882a-4e8f-8d73-8045dc3c6245",
    "tid": "35e2edb5-23e8-403e-86cd-8535dc048720",
    "role": "owner",
}
UID, TID, ROLE = AUTH["uid"], AUTH["tid"], AUTH.get("role") or "owner"
SUITE = Path(os.environ.get("SUITE_PATH", "/tmp/ROUTING200.json"))
CONCURRENCY = max(1, int(os.environ.get("ROUTING_CONCURRENCY", "1")))
CASE_LIMIT = int(os.environ.get("CASE_LIMIT", "0") or "0")
CASE_START = int(os.environ.get("CASE_START", "0") or "0")
CONNECT_TIMEOUT = float(os.environ.get("ROUTING_CONNECT_TIMEOUT", "15"))
SESSION_TIMEOUT = float(os.environ.get("ROUTING_SESSION_TIMEOUT", "90"))
MESSAGE_TIMEOUT = float(os.environ.get("ROUTING_MESSAGE_TIMEOUT", "180"))
MAX_INFRA_RETRIES = int(os.environ.get("ROUTING_MAX_INFRA_RETRIES", "1"))
HEARTBEAT_SEC = 30

_sem = threading.Semaphore(CONCURRENCY)
_lock = threading.Lock()
_progress = {"done": 0, "total": 0, "started_at": time.time()}

HUAWEI_MARKERS = {"huawei_modelarts", "huawei", "modelarts"}


def _tok() -> str:
    return create_access_token(subject=UID, tenant_id=UUID(TID), role=ROLE)


def deep_find(blob, key: str):
    stack = [blob]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if key in cur and cur[key] is not None:
                return cur[key]
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


def api(method: str, path: str, body=None, *, timeout: float, correlation_id: str) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {_tok()}",
            "Content-Type": "application/json",
            "X-Tenant-Id": TID,
            "X-Correlation-Id": correlation_id,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode()
        except Exception:  # noqa: BLE001
            raw = str(e)
        raise RuntimeError(f"HTTP {e.code}: {raw[:400]}") from e
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(str(e)[:400]) from e


def is_huawei(provider: str | None) -> bool:
    p = (provider or "").lower()
    return any(m in p for m in HUAWEI_MARKERS)


def run_case(case: dict) -> dict:
    cid = case["id"]
    corr = f"routing200-{cid}-{uuid4().hex[:8]}"
    expect_huawei = bool((case.get("expect") or {}).get("huawei"))
    row = {
        "case_id": cid,
        "category": case.get("category"),
        "correlation_id": corr,
        "expect_huawei": expect_huawei,
        "result_class": "harness_error",
        "route_ok": False,
        "studio_intervened": None,
        "provider_used": None,
        "error": None,
        "attempts": 0,
    }
    with _sem:
        attempt = 0
        while attempt <= MAX_INFRA_RETRIES:
            attempt += 1
            row["attempts"] = attempt
            sid = None
            try:
                t0 = time.perf_counter()
                sess = api(
                    "POST",
                    "/lottery/chat/sessions",
                    {"title": f"routing200-{cid}"},
                    timeout=SESSION_TIMEOUT,
                    correlation_id=corr,
                )
                sid = sess.get("id") or (sess.get("session") or {}).get("id")
                for setup in case.get("setup") or []:
                    api(
                        "POST",
                        f"/lottery/chat/sessions/{sid}/messages",
                        {"content": setup},
                        timeout=MESSAGE_TIMEOUT,
                        correlation_id=corr,
                    )
                r = api(
                    "POST",
                    f"/lottery/chat/sessions/{sid}/messages",
                    {"content": case["user"]},
                    timeout=MESSAGE_TIMEOUT,
                    correlation_id=corr,
                )
                row["total_latency_ms"] = (time.perf_counter() - t0) * 1000.0
                rt = r.get("runtime") or {}
                at = r.get("assistant") or {}
                provider = (
                    rt.get("provider_used")
                    or at.get("provider_used")
                    or deep_find(r, "provider_used")
                )
                row["provider_used"] = provider
                sh = deep_find(r, "shadow_comparison")
                pr = deep_find(r, "prompt_runtime")
                studio_called = bool(
                    sh
                    or (isinstance(pr, dict) and pr.get("studio_invoked"))
                    or deep_find(r, "studio_response")
                )
                # Shadow telemetry may exist only on Huawei dual path
                row["studio_intervened"] = bool(studio_called and is_huawei(provider))
                got_huawei = is_huawei(provider)
                if expect_huawei:
                    route_ok = got_huawei
                else:
                    route_ok = (not got_huawei) and (not row["studio_intervened"])
                row["route_ok"] = route_ok
                row["result_class"] = "product_pass" if route_ok else "product_fail"
                row["assistant_snip"] = ((at.get("content") or r.get("content") or "")[:240])
                break
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                retryable = "timeout" in msg.lower() or any(x in msg for x in ("502", "503", "504"))
                if "401" in msg or "403" in msg:
                    row["result_class"] = "auth_error"
                    row["error"] = msg[:400]
                    break
                if retryable and attempt <= MAX_INFRA_RETRIES:
                    continue
                if "timeout" in msg.lower():
                    row["result_class"] = "timeout_error"
                elif any(x in msg for x in ("502", "503", "504", "HTTP 5")):
                    row["result_class"] = "environment_error"
                else:
                    row["result_class"] = "harness_error"
                row["error"] = msg[:400]
                break
            finally:
                if sid:
                    try:
                        api(
                            "DELETE",
                            f"/lottery/chat/sessions/{sid}",
                            timeout=SESSION_TIMEOUT,
                            correlation_id=corr,
                        )
                    except Exception:  # noqa: BLE001
                        pass
    with _lock:
        _progress["done"] += 1
        done = _progress["done"]
        total = _progress["total"]
        print(
            cid,
            row["result_class"],
            row.get("provider_used"),
            "route_ok=",
            row["route_ok"],
            "lat=",
            int(row.get("total_latency_ms") or 0),
            flush=True,
        )
        # checkpoint every case
        cp = OUT / "CHECKPOINT.json"
        prev = []
        if cp.exists():
            try:
                prev = json.loads(cp.read_text()).get("results") or []
            except Exception:  # noqa: BLE001
                prev = []
        by_id = {x["case_id"]: x for x in prev}
        by_id[cid] = row
        results = list(by_id.values())
        cp.write_text(json.dumps({"done": done, "total": total, "results": results}, indent=2))
    return row


def heartbeat():
    while True:
        time.sleep(HEARTBEAT_SEC)
        with _lock:
            done = _progress["done"]
            total = _progress["total"]
            if done >= total and total:
                return
            elapsed = max(1.0, time.time() - _progress["started_at"])
            rate = done / (elapsed / 60.0) if done else 0.0
            eta = int((total - done) / rate * 60) if rate else "n/a"
            print(
                f"HEARTBEAT done={done}/{total} elapsed_s={int(elapsed)} "
                f"rate_cpm={rate:.2f} eta_s={eta}",
                flush=True,
            )


def main():
    suite = json.loads(SUITE.read_text())
    cases = suite["cases"][CASE_START:]
    if CASE_LIMIT:
        cases = cases[:CASE_LIMIT]
    _progress["total"] = len(cases)
    _progress["started_at"] = time.time()
    print(
        f"START routing200 n={len(cases)} concurrency={CONCURRENCY} "
        f"at={datetime.now(timezone.utc).isoformat()}",
        flush=True,
    )
    hb = threading.Thread(target=heartbeat, daemon=True)
    hb.start()
    results = []
    # Sequential preferred (concurrency=1); ThreadPool still honors semaphore
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(run_case, c): c["id"] for c in cases}
        for fut in as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda r: r["case_id"])
    n = len(results)
    route_ok = sum(1 for r in results if r.get("route_ok"))
    product_fail = sum(1 for r in results if r.get("result_class") == "product_fail")
    env = sum(1 for r in results if r.get("result_class") == "environment_error")
    auth = sum(1 for r in results if r.get("result_class") == "auth_error")
    to = sum(1 for r in results if r.get("result_class") == "timeout_error")
    huawei_unexpected = sum(
        1
        for r in results
        if (not r.get("expect_huawei")) and is_huawei(r.get("provider_used"))
    )
    studio_leak = sum(1 for r in results if r.get("studio_intervened") and not r.get("expect_huawei"))
    summary = {
        "suite": "ROUTING200",
        "n": n,
        "route_ok": route_ok,
        "product_fail": product_fail,
        "environment_error": env,
        "auth_error": auth,
        "timeout_error": to,
        "huawei_unexpected": huawei_unexpected,
        "studio_intervened_unexpected": studio_leak,
        "concurrency": CONCURRENCY,
        "PASS": route_ok == n and product_fail == 0 and env == 0 and auth == 0 and to == 0,
    }
    (OUT / "RESULTS.json").write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
