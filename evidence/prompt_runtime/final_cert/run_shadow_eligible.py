#!/usr/bin/env python3
"""Shadow eligible certification runner (concurrency-controlled, classified errors).

Harness resolves EXPECTED_HASH from runtime status / env / freeze — never a silent legacy default.
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.core.security import create_access_token

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if "/tmp" not in sys.path:
    sys.path.insert(0, "/tmp")

from prompt_hash_precheck import (  # noqa: E402
    PromptHashPrecheckError,
    annotate_hash_fields,
    classify_hash_mismatch,
    precheck_or_exit,
    write_run_freeze,
)

BASE = os.environ.get("FORENSIC_BASE_URL", "http://127.0.0.1:8000/api/v1")
_SHADOW_OUT = (os.environ.get("SHADOW_OUT") or "").strip()
if not _SHADOW_OUT:
    raise SystemExit("SHADOW_OUT is required (run-scoped /tmp/prompt_cert/<run_id>)")
if _SHADOW_OUT.rstrip("/") in {"/tmp/shadow_eligible_out", "/tmp/shadow_eligible_inner.log"}:
    raise SystemExit("legacy global SHADOW_OUT is forbidden; use /tmp/prompt_cert/<run_id>")
OUT = Path(_SHADOW_OUT)
OUT.mkdir(parents=True, exist_ok=True)
AUTH = json.loads(Path("/tmp/routing3_auth.json").read_text()) if Path("/tmp/routing3_auth.json").exists() else {
    "uid": "e520ca09-882a-4e8f-8d73-8045dc3c6245",
    "tid": "35e2edb5-23e8-403e-86cd-8535dc048720",
    "role": "owner",
}
UID, TID, ROLE = AUTH["uid"], AUTH["tid"], AUTH.get("role") or "owner"
SUITE = Path(os.environ.get("SUITE_PATH", "/tmp/SHADOW200_ELIGIBLE.json"))
# No hardcoded legacy default. Resolved in main() via prompt_hash_precheck.
EXPECTED_HASH: str | None = (os.environ.get("EXPECTED_HASH") or "").strip() or None
HASH_SOURCE: str | None = None
CONCURRENCY = max(1, int(os.environ.get("SHADOW_CONCURRENCY", "1")))
CASE_LIMIT = int(os.environ.get("CASE_LIMIT", "0") or "0")
CASE_START = int(os.environ.get("CASE_START", "0") or "0")
CONNECT_TIMEOUT = float(os.environ.get("SHADOW_CONNECT_TIMEOUT", "15"))
SESSION_TIMEOUT = float(os.environ.get("SHADOW_SESSION_TIMEOUT", "90"))
MESSAGE_TIMEOUT = float(os.environ.get("SHADOW_MESSAGE_TIMEOUT", "600"))
MAX_INFRA_RETRIES = int(os.environ.get("SHADOW_MAX_INFRA_RETRIES", "1"))
HEARTBEAT_SEC = 30
FREEZE_PATH = os.environ.get("PROMPT_FREEZE_PATH", "/tmp/PROMPT_FREEZE.json")

_sem = threading.Semaphore(CONCURRENCY)
_lock = threading.Lock()
_progress = {"done": 0, "total": 0, "started_at": time.time()}


@dataclass
class ApiError(Exception):
    kind: str  # timeout|auth|http|network|unknown
    status: int | None
    message: str
    correlation_id: str


def _tok() -> str:
    return create_access_token(subject=UID, tenant_id=UUID(TID), role=ROLE)


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
        kind = "auth" if e.code in (401, 403) else "http"
        if e.code in (400, 401, 403):
            raise ApiError(kind, e.code, raw[:500], correlation_id) from e
        if e.code in (502, 503, 504):
            raise ApiError("http", e.code, raw[:500], correlation_id) from e
        raise ApiError("http", e.code, raw[:500], correlation_id) from e
    except TimeoutError as e:
        raise ApiError("timeout", None, f"timeout after {timeout}s", correlation_id) from e
    except Exception as e:  # noqa: BLE001
        msg = str(e).lower()
        if "timed out" in msg or "timeout" in msg:
            raise ApiError("timeout", None, str(e)[:300], correlation_id) from e
        raise ApiError("network", None, str(e)[:300], correlation_id) from e


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


def word_stats(text: str) -> dict:
    t = text or ""
    words = re.findall(r"\b\w+\b", t, flags=re.UNICODE)
    return {"chars": len(t), "words": len(words)}


def classify_product(row: dict) -> str:
    """Return product_pass|product_fail|not_eligible|harness_configuration_error|…"""
    if row.get("error_class") in {
        "timeout_error",
        "auth_error",
        "environment_error",
        "harness_error",
        "harness_configuration_error",
    }:
        return row["error_class"]
    if not row.get("eligible_shadow"):
        return "not_eligible"
    observed = row.get("observed_prompt_hash") or row.get("prompt_hash")
    expected = row.get("expected_prompt_hash") or EXPECTED_HASH
    mismatch_cls = classify_hash_mismatch(observed, expected)
    if mismatch_cls:
        # Hash mismatch is never a product_fail.
        row["error_class"] = mismatch_cls
        return mismatch_cls
    if row.get("hallucination") or row.get("studio_guard_passed") is False:
        return "product_fail"
    if row.get("extra_subjects") or row.get("missing_subjects") or row.get("altered_subjects"):
        return "product_fail"
    if row.get("same_evidence_package") is False:
        return "product_fail"
    if row.get("fallback"):
        return "product_fail"
    if row.get("studio_guard_passed") is True and row.get("legacy_response") and row.get("studio_response"):
        return "product_pass"
    return "product_fail"


def extract_row(c: dict, r: dict, *, correlation_id: str, attempts: int, env_retry: bool) -> dict:
    ans = ((r.get("message") or {}).get("content") or "")
    rt = r.get("runtime_trace") or {}
    at = ((r.get("context") or {}).get("agent_trace") or {})
    provider = rt.get("provider_used") or at.get("provider_used")
    pr = deep_find({"rt": rt, "at": at, "ctx": r.get("context") or {}, "r": r}, "prompt_runtime")
    if not isinstance(pr, dict):
        pr = {}
    shadow = pr.get("shadow_comparison") if isinstance(pr.get("shadow_comparison"), dict) else None
    if shadow is None:
        sh = deep_find({"rt": rt, "at": at, "r": r}, "shadow_comparison")
        shadow = sh if isinstance(sh, dict) else None
    studio_raw = (shadow or {}).get("studio_raw") or ""
    reason = (shadow or {}).get("studio_guard_reason") or ""
    extras = []
    m = re.search(r"extra_subjects:(\[[^\]]*\])", reason)
    if m:
        try:
            extras = json.loads(m.group(1).replace("'", '"'))
        except Exception:  # noqa: BLE001
            extras = [m.group(1)]
    ph = (shadow or {}).get("studio_prompt_hash") or pr.get("compiled_prompt_hash")
    if isinstance(pr.get("shadow_meta"), dict):
        ph = ph or pr["shadow_meta"].get("compiled_prompt_hash")
    eligible = (
        provider == "huawei_modelarts"
        and bool(studio_raw.strip())
        and (shadow or {}).get("studio_guard_passed") is not None
        and not (shadow or {}).get("error")
    )
    hallucination = False
    if eligible and studio_raw:
        if extras or "extra_subjects" in reason:
            hallucination = True
        if (shadow or {}).get("studio_guard_passed") is False and any(
            x in reason for x in ("count_mismatch", "invented", "unknown_date", "guaranteed")
        ):
            hallucination = True
    row = {
        "case_id": c["id"],
        "category": c.get("category") or c.get("group"),
        "user": c["user"],
        "setup": c.get("setup") or [],
        "correlation_id": correlation_id,
        "conversation_id": None,
        "route": provider,
        "provider_used": provider,
        "model": rt.get("model_used") or at.get("model_used"),
        "legacy_response": ans,
        "legacy_latency_ms": r.get("_latency_ms"),
        "legacy_stats": word_stats(ans),
        "studio_response": studio_raw,
        "studio_latency_ms": (shadow or {}).get("studio_latency_ms"),
        "studio_input_tokens": (shadow or {}).get("studio_input_tokens"),
        "studio_output_tokens": (shadow or {}).get("studio_output_tokens"),
        "studio_guard_passed": (shadow or {}).get("studio_guard_passed"),
        "studio_guard_reason": reason,
        "legacy_guard": True,
        "same_evidence_package": (shadow or {}).get("same_evidence_package"),
        "extra_subjects": extras,
        "missing_subjects": [],
        "altered_subjects": [],
        "fallback": bool(pr.get("fallback_used")),
        "prompt_version": pr.get("prompt_semantic_version"),
        "prompt_version_id": pr.get("prompt_version_id"),
        "eligible_shadow": bool(eligible),
        "attempts": attempts,
        "environment_retry": env_retry,
        "auth_status": "ok",
        "error_class": None,
        "error": None,
        "hallucination": hallucination,
        "total_latency_ms": r.get("_latency_ms"),
    }
    annotate_hash_fields(
        row,
        observed=ph,
        expected=EXPECTED_HASH,
        hash_source=HASH_SOURCE,
    )
    row["result_class"] = classify_product(row)
    row["product_pass"] = row["result_class"] == "product_pass"
    row["product_fail"] = row["result_class"] == "product_fail"
    return row


def run_case(c: dict) -> dict:
    correlation_id = str(uuid4())
    attempts = 0
    env_retry = False
    last_err: ApiError | None = None
    while attempts <= MAX_INFRA_RETRIES:
        attempts += 1
        sid = None
        try:
            with _sem:
                t0 = time.perf_counter()
                s = api(
                    "POST",
                    "/lottery/chat/sessions",
                    {"title": f"elig-{c['id']}"},
                    timeout=SESSION_TIMEOUT,
                    correlation_id=correlation_id,
                )
                sid = s.get("id") or (s.get("session") or {}).get("id")
                for u in c.get("setup") or []:
                    api(
                        "POST",
                        f"/lottery/chat/sessions/{sid}/messages",
                        {"content": u},
                        timeout=MESSAGE_TIMEOUT,
                        correlation_id=correlation_id,
                    )
                t_msg = time.perf_counter()
                r = api(
                    "POST",
                    f"/lottery/chat/sessions/{sid}/messages",
                    {"content": c["user"]},
                    timeout=MESSAGE_TIMEOUT,
                    correlation_id=correlation_id,
                )
                r["_latency_ms"] = (time.perf_counter() - t_msg) * 1000.0
                r["_wall_ms"] = (time.perf_counter() - t0) * 1000.0
                row = extract_row(c, r, correlation_id=correlation_id, attempts=attempts, env_retry=env_retry)
                row["conversation_id"] = sid
                row["total_latency_ms"] = r["_wall_ms"]
                return row
        except ApiError as err:
            last_err = err
            retryable = err.kind in {"timeout", "network"} or (
                err.kind == "http" and err.status in (502, 503, 504)
            )
            if retryable and attempts <= MAX_INFRA_RETRIES:
                env_retry = True
                time.sleep(2)
                continue
            break
        except Exception as exc:  # noqa: BLE001
            last_err = ApiError("unknown", None, str(exc)[:400], correlation_id)
            break
        finally:
            if sid:
                try:
                    api(
                        "DELETE",
                        f"/lottery/chat/sessions/{sid}",
                        timeout=SESSION_TIMEOUT,
                        correlation_id=correlation_id,
                    )
                except Exception:  # noqa: BLE001
                    pass

    err = last_err or ApiError("unknown", None, "unknown", correlation_id)
    ec = {
        "timeout": "timeout_error",
        "auth": "auth_error",
        "http": "environment_error",
        "network": "environment_error",
        "unknown": "harness_error",
    }.get(err.kind, "harness_error")
    return {
        "case_id": c["id"],
        "category": c.get("category") or c.get("group"),
        "user": c.get("user"),
        "correlation_id": correlation_id,
        "error_class": ec,
        "result_class": ec,
        "error": f"HTTP {err.status}: {err.message}"[:500],
        "auth_status": "fail" if ec == "auth_error" else "unknown",
        "eligible_shadow": False,
        "hallucination": False,  # never on infra/auth/timeout
        "product_pass": False,
        "product_fail": False,
        "attempts": attempts,
        "environment_retry": env_retry,
        "fallback": False,
        "extra_subjects": [],
        "missing_subjects": [],
        "altered_subjects": [],
        "trace": traceback.format_exc()[-500:],
    }


def heartbeat_loop(stop: threading.Event) -> None:
    while not stop.wait(HEARTBEAT_SEC):
        with _lock:
            done = _progress["done"]
            total = _progress["total"]
            elapsed = time.time() - _progress["started_at"]
        rate = done / elapsed if elapsed > 0 and done else 0
        eta = ((total - done) / rate) if rate > 0 else None
        print(
            f"HEARTBEAT done={done}/{total} elapsed_s={int(elapsed)} "
            f"rate_cpm={rate * 60:.2f} eta_s={int(eta) if eta else 'n/a'}",
            flush=True,
        )
        try:
            hb = {
                "done": done,
                "total": total,
                "elapsed_s": int(elapsed),
                "rate_cpm": round(rate * 60, 2),
                "eta_s": int(eta) if eta else None,
                "at": datetime.now(timezone.utc).isoformat(),
            }
            (OUT / "heartbeat.json").write_text(
                json.dumps(hb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        except Exception:  # noqa: BLE001
            pass


def summarize(results: list[dict]) -> dict:
    eligible = [r for r in results if r.get("eligible_shadow")]
    product_pass = [r for r in results if r.get("result_class") == "product_pass"]
    product_fail = [r for r in results if r.get("result_class") == "product_fail"]

    def cnt(cls: str) -> int:
        return sum(1 for r in results if r.get("result_class") == cls or r.get("error_class") == cls)

    lats = sorted(r.get("studio_latency_ms") or 0 for r in eligible if r.get("studio_latency_ms"))
    walls = sorted(r.get("total_latency_ms") or r.get("legacy_latency_ms") or 0 for r in eligible)

    def pct(arr, p):
        if not arr:
            return None
        return arr[min(len(arr) - 1, int(p / 100 * (len(arr) - 1)))]

    summary = {
        "n": len(results),
        "eligible_completed": len(eligible),
        "eligible_product_pass": len(product_pass),
        "product_fail": len(product_fail),
        "environment_error": cnt("environment_error"),
        "auth_error": cnt("auth_error"),
        "timeout_error": cnt("timeout_error"),
        "harness_error": cnt("harness_error"),
        "harness_configuration_error": cnt("harness_configuration_error"),
        "not_eligible": cnt("not_eligible"),
        "hallucinations": sum(1 for r in results if r.get("hallucination")),
        "extra_subjects_cases": sum(1 for r in results if r.get("extra_subjects")),
        "missing_subjects_cases": sum(1 for r in results if r.get("missing_subjects")),
        "altered_subjects_cases": sum(1 for r in results if r.get("altered_subjects")),
        "studio_guard_pass": sum(1 for r in eligible if r.get("studio_guard_passed") is True),
        "hash_match": sum(1 for r in eligible if r.get("hash_match") is True or r.get("hash_ok") is True),
        "same_evidence_package": sum(1 for r in eligible if r.get("same_evidence_package") is True),
        "fallback_true": sum(1 for r in results if r.get("fallback")),
        "retries_used": sum(1 for r in results if r.get("environment_retry")),
        "expected_prompt_hash": EXPECTED_HASH,
        "hash_source": HASH_SOURCE,
        "concurrency": CONCURRENCY,
        "studio_p50_ms": pct(lats, 50),
        "studio_p95_ms": pct(lats, 95),
        "studio_p99_ms": pct(lats, 99),
        "wall_p50_ms": pct(walls, 50),
        "wall_p95_ms": pct(walls, 95),
        "wall_p99_ms": pct(walls, 99),
    }
    summary["PASS"] = (
        summary["eligible_completed"] == summary["n"]
        and summary["n"] > 0
        and summary["product_fail"] == 0
        and summary["hallucinations"] == 0
        and summary["extra_subjects_cases"] == 0
        and summary["missing_subjects_cases"] == 0
        and summary["altered_subjects_cases"] == 0
        and summary["studio_guard_pass"] == summary["eligible_completed"]
        and summary["hash_match"] == summary["eligible_completed"]
        and summary["same_evidence_package"] == summary["eligible_completed"]
        and summary["fallback_true"] == 0
        and summary["auth_error"] == 0
        and summary["timeout_error"] == 0
        and summary["environment_error"] == 0
        and summary["harness_error"] == 0
        and summary["harness_configuration_error"] == 0
        and summary["not_eligible"] == 0
        and summary["eligible_product_pass"] == summary["eligible_completed"]
    )
    return summary


def _resolve_hash_or_abort() -> None:
    global EXPECTED_HASH, HASH_SOURCE
    tok = create_access_token(subject=UID, tenant_id=UUID(TID), role=ROLE)
    headers = {"Authorization": f"Bearer {tok}", "X-Tenant-Id": TID}
    try:
        resolved = precheck_or_exit(
            base_url=BASE,
            auth_headers=headers,
            env_expected_hash=EXPECTED_HASH,
            freeze_path=FREEZE_PATH if Path(FREEZE_PATH).exists() else None,
        )
    except PromptHashPrecheckError as exc:
        print(str(exc), flush=True)
        raise SystemExit(2) from exc
    EXPECTED_HASH = resolved.expected_hash
    HASH_SOURCE = resolved.hash_source
    write_run_freeze(OUT / "PROMPT_FREEZE.json", resolved)
    print(
        "PROMPT_HASH_PRECHECK_OK "
        + json.dumps(
            {
                "prompt_version": resolved.active_semantic_version,
                "version_id": resolved.active_version_id,
                "expected_hash": resolved.expected_hash,
                "hash_source": resolved.hash_source,
                "active_hash": resolved.active_hash,
                "freeze_hash": resolved.freeze_hash,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


def main() -> None:
    _resolve_hash_or_abort()
    cases = json.loads(SUITE.read_text())["cases"]
    if CASE_START:
        cases = cases[CASE_START:]
    if CASE_LIMIT:
        cases = cases[:CASE_LIMIT]
    _progress["total"] = len(cases)
    _progress["started_at"] = time.time()
    checkpoint = OUT / "CHECKPOINT.json"
    results: list[dict] = []
    done_ids: set[str] = set()
    # Fresh runs only: never resume a prior suite checkpoint unless explicitly allowed.
    if os.environ.get("SHADOW_ALLOW_RESUME") == "1" and checkpoint.exists():
        prev = json.loads(checkpoint.read_text())
        results = list(prev.get("results") or [])
        done_ids = {r.get("case_id") for r in results if r.get("case_id")}
        print(f"RESUME from checkpoint n={len(results)}", flush=True)

    stop = threading.Event()
    hb = threading.Thread(target=heartbeat_loop, args=(stop,), daemon=True)
    hb.start()

    pending = [c for c in cases if c["id"] not in done_ids]
    print(
        f"START eligible_runner n={len(cases)} pending={len(pending)} concurrency={CONCURRENCY} "
        f"expected_hash={EXPECTED_HASH} hash_source={HASH_SOURCE} "
        f"at={datetime.now(timezone.utc).isoformat()}",
        flush=True,
    )

    def _one(c):
        row = run_case(c)
        print(
            c["id"],
            row.get("result_class"),
            row.get("provider_used") or row.get("error_class"),
            "elig=",
            row.get("eligible_shadow"),
            "hall=",
            row.get("hallucination"),
            "lat=",
            int(row.get("total_latency_ms") or row.get("legacy_latency_ms") or 0),
            flush=True,
        )
        return row

    if CONCURRENCY == 1:
        for c in pending:
            row = _one(c)
            results.append(row)
            with _lock:
                _progress["done"] = len(results)
            checkpoint.write_text(
                json.dumps({"results": results}, indent=2, ensure_ascii=False) + "\n"
            )
    else:
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
            futs = {ex.submit(_one, c): c for c in pending}
            for fut in as_completed(futs):
                results.append(fut.result())
                with _lock:
                    _progress["done"] = len(results)
                checkpoint.write_text(
                    json.dumps({"results": results}, indent=2, ensure_ascii=False) + "\n"
                )

    stop.set()
    # stable order
    order = {c["id"]: i for i, c in enumerate(cases)}
    results.sort(key=lambda r: order.get(r.get("case_id"), 10**9))
    summary = summarize(results)
    (OUT / "RESULTS.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False) + "\n"
    )
    print("SUMMARY", json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
