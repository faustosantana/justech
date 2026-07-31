#!/usr/bin/env python3
"""Shadow certification harness — Shadow200 / Shadow500 (DEV, frozen rc3.4).

Records legacy + studio shadow comparison without changing runtime behavior.
Skips dual-LLM expectation for non-Huawei providers (social/workspace/local).
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path
from uuid import UUID

from app.core.security import create_access_token

BASE = os.environ.get("FORENSIC_BASE_URL", "http://127.0.0.1:8000/api/v1")
OUT = Path(os.environ.get("SHADOW_OUT", "/tmp/shadow_cert_out"))
OUT.mkdir(parents=True, exist_ok=True)
AUTH = json.loads(Path("/tmp/routing3_auth.json").read_text()) if Path("/tmp/routing3_auth.json").exists() else {
    "uid": "e520ca09-882a-4e8f-8d73-8045dc3c6245",
    "tid": "35e2edb5-23e8-403e-86cd-8535dc048720",
    "role": "owner",
}
UID, TID, ROLE = AUTH["uid"], AUTH["tid"], AUTH.get("role") or "owner"
SUITE = Path(os.environ.get("SUITE_PATH", "/tmp/SHADOW200.json"))
LIMIT = int(os.environ.get("CASE_LIMIT", "0") or "0")
START = int(os.environ.get("CASE_START", "0") or "0")
EXPECTED_HASH = os.environ.get(
    "EXPECTED_HASH", "41c64a0fc7c303222c2b492e82a0ea51cec6c16139bc2f0cde9ec9e9da642ff9"
)
ELIGIBLE_ONLY = os.environ.get("ELIGIBLE_ONLY", "0") == "1"


def api(method: str, path: str, body=None):
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
    try:
        with urllib.request.urlopen(req, timeout=420) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "code", None)
        raw = ""
        if hasattr(e, "read"):
            try:
                raw = e.read().decode()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                raw = ""
        raise RuntimeError(f"HTTP {code}: {raw[:500] or e}") from e


def send(sid: str, content: str) -> dict:
    t0 = time.perf_counter()
    r = api("POST", f"/lottery/chat/sessions/{sid}/messages", {"content": content})
    r["_latency_ms"] = (time.perf_counter() - t0) * 1000.0
    return r


def new_session(title: str) -> str:
    s = api("POST", "/lottery/chat/sessions", {"title": title})
    return s.get("id") or (s.get("session") or {}).get("id")


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
    return {"chars": len(t), "words": len(words), "sentences": len([s for s in re.split(r"[.!?]+", t) if s.strip()])}


def clarity_score(text: str) -> float:
    """Heuristic 0–1: prefers short clear Spanish answers without section spam."""
    t = (text or "").strip()
    if len(t) < 20:
        return 0.2
    w = len(re.findall(r"\b\w+\b", t, flags=re.UNICODE))
    bad = 0
    for marker in ("Hallazgos", "Detalle", "Recomendaciones", "números fuertes", "vecinos", "compañeros"):
        if marker.lower() in t.lower():
            bad += 1
    length_pen = 0.0 if w <= 160 else min(0.4, (w - 160) / 400)
    return max(0.0, min(1.0, 1.0 - 0.15 * bad - length_pen))


def score_case(row: dict) -> dict:
    reason = row.get("studio_guard_reason") or ""
    extras = row.get("extra_subjects") or []
    studio_pass = row.get("studio_guard_passed")
    provider = row.get("provider_used")
    eligible = provider == "huawei_modelarts" and row.get("studio_preview")
    subject_score = 1.0
    factual_score = 1.0
    hallucination = False
    if eligible:
        if extras or "extra_subjects" in reason:
            subject_score = 0.0
            hallucination = True
        if studio_pass is False:
            factual_score = 0.0
            if "count_mismatch" in reason or "invented" in reason or "unknown_date" in reason:
                hallucination = True
        elif studio_pass is True:
            factual_score = 1.0
    clarity = clarity_score(row.get("studio_preview") or row.get("legacy_preview") or "")
    return {
        "factual_score": factual_score,
        "subject_score": subject_score,
        "clarity": round(clarity, 3),
        "hallucination": hallucination,
        "eligible_shadow": bool(eligible),
    }


def extract_row(c: dict, r: dict) -> dict:
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
    row = {
        "case_id": c["id"],
        "group": c.get("group"),
        "user": c["user"],
        "setup": c.get("setup") or [],
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
        "studio_preview": studio_raw[:600],
        "studio_stats": word_stats(studio_raw),
        "legacy_preview": ans[:600],
        "same_evidence_package": (shadow or {}).get("same_evidence_package"),
        "extra_subjects": extras,
        "missing_subjects": [],
        "altered_subjects": [],
        "fallback": bool(pr.get("fallback_used")),
        "prompt_hash": None,
        "prompt_version": pr.get("prompt_semantic_version"),
        "prompt_version_id": pr.get("prompt_version_id"),
        "hash_ok": True,
    }
    ph = (shadow or {}).get("studio_prompt_hash") or pr.get("compiled_prompt_hash")
    if isinstance(pr.get("shadow_meta"), dict):
        ph = ph or pr["shadow_meta"].get("compiled_prompt_hash")
    row["prompt_hash"] = ph
    if provider == "huawei_modelarts" and studio_raw:
        row["hash_ok"] = (ph == EXPECTED_HASH) if ph else False
    row.update(score_case(row))
    return row


def main() -> None:
    cases = json.loads(SUITE.read_text())["cases"]
    if START > 0:
        cases = cases[START:]
    if LIMIT > 0:
        cases = cases[:LIMIT]
    results = []
    for c in cases:
        sid = None
        try:
            sid = new_session(f"shadow-{c['id']}")
            for u in c.get("setup") or []:
                send(sid, u)
            r = send(sid, c["user"])
            row = extract_row(c, r)
            if ELIGIBLE_ONLY and not row.get("eligible_shadow"):
                # still record but mark skipped for dual-LLM criteria
                row["skipped_dual"] = True
        except Exception as exc:  # noqa: BLE001
            row = {
                "case_id": c["id"],
                "group": c.get("group"),
                "error": str(exc)[:500],
                "factual_score": 0.0,
                "subject_score": 0.0,
                "clarity": 0.0,
                "hallucination": True,
                "fallback": True,
                "eligible_shadow": False,
            }
        if sid:
            try:
                api("DELETE", f"/lottery/chat/sessions/{sid}")
            except Exception:  # noqa: BLE001
                pass
        results.append(row)
        print(
            c["id"],
            row.get("provider_used") or "ERR",
            "guard=",
            row.get("studio_guard_passed"),
            "hall=",
            row.get("hallucination"),
            "extra=",
            row.get("extra_subjects"),
            "lat=",
            int(row.get("legacy_latency_ms") or 0),
            flush=True,
        )
        (OUT / "PARTIAL.json").write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False) + "\n")

    eligible = [x for x in results if x.get("eligible_shadow")]
    summary = {
        "n": len(results),
        "eligible_shadow": len(eligible),
        "studio_guard_pass": sum(1 for x in eligible if x.get("studio_guard_passed") is True),
        "studio_guard_fail": sum(1 for x in eligible if x.get("studio_guard_passed") is False),
        "extra_subjects_cases": sum(1 for x in results if x.get("extra_subjects")),
        "hallucinations": sum(1 for x in results if x.get("hallucination")),
        "fallback_true": sum(1 for x in results if x.get("fallback")),
        "errors": sum(1 for x in results if x.get("error")),
        "hash_mismatch": sum(1 for x in eligible if x.get("hash_ok") is False),
        "avg_factual": round(sum(x.get("factual_score") or 0 for x in eligible) / max(1, len(eligible)), 4),
        "avg_subject": round(sum(x.get("subject_score") or 0 for x in eligible) / max(1, len(eligible)), 4),
        "avg_clarity": round(sum(x.get("clarity") or 0 for x in eligible) / max(1, len(eligible)), 4),
        "avg_legacy_words": round(
            sum((x.get("legacy_stats") or {}).get("words") or 0 for x in results) / max(1, len(results)), 1
        ),
        "avg_studio_words": round(
            sum((x.get("studio_stats") or {}).get("words") or 0 for x in eligible) / max(1, len(eligible)), 1
        )
        if eligible
        else None,
        "avg_legacy_ms": round(sum(x.get("legacy_latency_ms") or 0 for x in results) / max(1, len(results)), 1),
        "avg_studio_ms": round(
            sum(x.get("studio_latency_ms") or 0 for x in eligible) / max(1, len(eligible)), 1
        )
        if eligible
        else None,
    }
    if eligible:
        lats = sorted(x.get("studio_latency_ms") or 0 for x in eligible)
        walls = sorted(x.get("legacy_latency_ms") or 0 for x in results)

        def pct(arr, p):
            if not arr:
                return None
            return arr[min(len(arr) - 1, int(p / 100 * (len(arr) - 1)))]

        summary["studio_p50_ms"] = pct(lats, 50)
        summary["studio_p95_ms"] = pct(lats, 95)
        summary["studio_p99_ms"] = pct(lats, 99)
        summary["wall_p50_ms"] = pct(walls, 50)
        summary["wall_p95_ms"] = pct(walls, 95)
        summary["wall_p99_ms"] = pct(walls, 99)

    summary["PASS"] = (
        summary["errors"] == 0
        and summary["extra_subjects_cases"] == 0
        and summary["hallucinations"] == 0
        and summary["studio_guard_fail"] == 0
        and summary["hash_mismatch"] == 0
        and summary["eligible_shadow"] > 0
        and summary["studio_guard_pass"] == summary["eligible_shadow"]
    )
    (OUT / "RESULTS.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False) + "\n"
    )
    print("SUMMARY", json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
