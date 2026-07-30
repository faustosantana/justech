#!/usr/bin/env python3
"""Subject50 + Prompt50 directed harness for Phase 3 rc3 (DEV shadow)."""
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
OUT = Path(os.environ.get("SUBJECT_OUT", "/tmp/subject50_out"))
OUT.mkdir(parents=True, exist_ok=True)
AUTH = json.loads(Path("/tmp/routing3_auth.json").read_text()) if Path("/tmp/routing3_auth.json").exists() else {
    "uid": "e520ca09-882a-4e8f-8d73-8045dc3c6245",
    "tid": "35e2edb5-23e8-403e-86cd-8535dc048720",
    "role": "owner",
}
UID, TID, ROLE = AUTH["uid"], AUTH["tid"], AUTH.get("role") or "owner"
SUITE = Path(os.environ.get("SUITE_PATH", "/tmp/SUBJECT50.json"))
LIMIT = int(os.environ.get("CASE_LIMIT", "0") or "0")  # 0 = all
START = int(os.environ.get("CASE_START", "0") or "0")
EXPECTED_HASH = os.environ.get(
    "EXPECTED_HASH", "721dc1060214b08f604dcfa27aa2b67b86c7474f42cf0c5f232712e46c770e2a"
)


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
        with urllib.request.urlopen(req, timeout=360) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "code", None)
        raw = ""
        if hasattr(e, "read"):
            try:
                raw = e.read().decode()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                raw = ""
        raise RuntimeError(f"HTTP {code}: {raw[:400] or e}") from e


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
            if key in cur:
                return cur[key]
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


def word_stats(text: str) -> dict:
    t = text or ""
    words = re.findall(r"\b\w+\b", t, flags=re.UNICODE)
    sents = [s for s in re.split(r"[.!?]+", t) if s.strip()]
    lists = len(re.findall(r"(?m)^\s*[-*•]\s+", t)) + len(re.findall(r"(?m)^\s*\d+[.)]\s+", t))
    return {
        "chars": len(t),
        "words": len(words),
        "sentences": len(sents),
        "lists": lists,
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
        shadow = deep_find({"rt": rt, "at": at, "r": r}, "shadow_comparison")
    studio_raw = (shadow or {}).get("studio_raw") or ""
    reason = (shadow or {}).get("studio_guard_reason") or ""
    extras = []
    miss = []
    altered = []
    m = re.search(r"extra_subjects:(\[[^\]]*\])", reason)
    if m:
        try:
            extras = json.loads(m.group(1).replace("'", '"'))
        except Exception:  # noqa: BLE001
            extras = [m.group(1)]
    if "missing_subjects" in reason:
        miss = [reason]
    if "altered_subjects" in reason:
        altered = [reason]
    # also scan studio text for invented subject phrasing markers
    false_date_as_subj = bool(re.search(r"\bel\s+n[uú]mero\s+20\d{2}\b", studio_raw, re.I))
    row = {
        "case_id": c["id"],
        "group": c.get("group"),
        "user": c["user"],
        "provider_used": provider,
        "legacy_latency_ms": r.get("_latency_ms"),
        "legacy_preview": ans[:400],
        "legacy_stats": word_stats(ans),
        "prompt_runtime": {
            k: pr.get(k)
            for k in (
                "prompt_runtime_mode",
                "prompt_source",
                "fallback_used",
                "compiled_prompt_hash",
                "prompt_semantic_version",
                "prompt_version_id",
            )
        },
        "studio_latency_ms": (shadow or {}).get("studio_latency_ms"),
        "studio_guard_passed": (shadow or {}).get("studio_guard_passed"),
        "studio_guard_reason": reason,
        "studio_preview": studio_raw[:500],
        "studio_stats": word_stats(studio_raw),
        "studio_input_tokens": (shadow or {}).get("studio_input_tokens"),
        "studio_output_tokens": (shadow or {}).get("studio_output_tokens"),
        "same_evidence_package": (shadow or {}).get("same_evidence_package"),
        "extra_subjects": extras,
        "missing_subjects": miss,
        "altered_subjects": altered,
        "false_date_as_subject": false_date_as_subj,
        "hash_ok": (pr.get("compiled_prompt_hash") in {None, EXPECTED_HASH})
        or ((shadow or {}).get("studio_prompt_hash") == EXPECTED_HASH),
    }
    # pass criteria for subject guard when shadow present
    if shadow:
        row["subject_pass"] = (
            bool(shadow.get("studio_guard_passed"))
            or (
                not extras
                and "extra_subjects" not in reason
                # count_mismatch alone is not a subject failure for Subject50 subject criteria —
                # but Phase 8 requires subject_guard 50/50; if guard fails for count it's still fail.
                # Strict: studio_guard_passed must be True when shadow exists.
            )
            and not extras
            and not miss
            and not altered
            and not false_date_as_subj
        )
        # Override: require studio_guard_passed True
        row["subject_pass"] = bool(shadow.get("studio_guard_passed")) and not extras and not miss and not altered
    else:
        row["subject_pass"] = None  # not eligible / no shadow
    return row


def main() -> None:
    cases = json.loads(SUITE.read_text())["cases"]
    if START > 0:
        cases = cases[START:]
    if LIMIT > 0:
        cases = cases[:LIMIT]
    results = []
    for idx, c in enumerate(cases):
        try:
            sid = new_session(f"s50-{c['id']}")
            for u in c.get("setup") or []:
                send(sid, u)
            r = send(sid, c["user"])
            row = extract_row(c, r)
        except Exception as exc:  # noqa: BLE001
            row = {
                "case_id": c["id"],
                "error": str(exc)[:400],
                "subject_pass": False,
                "extra_subjects": [],
                "missing_subjects": [],
                "altered_subjects": [],
            }
        results.append(row)
        print(
            c["id"],
            row.get("provider_used") or row.get("error", "")[:40],
            "guard=",
            row.get("studio_guard_passed"),
            "extra=",
            row.get("extra_subjects"),
            "lat=",
            int(row.get("legacy_latency_ms") or 0),
            flush=True,
        )
        # Persist partials for resume
        (OUT / "SUBJECT50_PARTIAL.json").write_text(
            json.dumps({"results": results}, indent=2, ensure_ascii=False) + "\n"
        )

    shadowed = [x for x in results if x.get("studio_preview") is not None and x.get("studio_guard_passed") is not None]
    summary = {
        "n": len(results),
        "with_shadow": len(shadowed),
        "subject_pass": sum(1 for x in results if x.get("subject_pass") is True),
        "subject_fail": sum(1 for x in results if x.get("subject_pass") is False),
        "subject_na": sum(1 for x in results if x.get("subject_pass") is None),
        "extra_subjects_cases": sum(1 for x in results if x.get("extra_subjects")),
        "missing_subjects_cases": sum(1 for x in results if x.get("missing_subjects")),
        "altered_subjects_cases": sum(1 for x in results if x.get("altered_subjects")),
        "fallback_true": sum(1 for x in results if (x.get("prompt_runtime") or {}).get("fallback_used") is True),
        "avg_legacy_words": round(
            sum((x.get("legacy_stats") or {}).get("words") or 0 for x in results) / max(1, len(results)), 1
        ),
        "avg_studio_words": round(
            sum((x.get("studio_stats") or {}).get("words") or 0 for x in shadowed) / max(1, len(shadowed)), 1
        )
        if shadowed
        else None,
        "p95_studio_words": None,
        "avg_legacy_ms": round(sum(x.get("legacy_latency_ms") or 0 for x in results) / max(1, len(results)), 1),
        "avg_studio_ms": round(
            sum(x.get("studio_latency_ms") or 0 for x in shadowed) / max(1, len(shadowed)), 1
        )
        if shadowed
        else None,
    }
    if shadowed:
        ws = sorted((x.get("studio_stats") or {}).get("words") or 0 for x in shadowed)
        summary["p95_studio_words"] = ws[int(0.95 * (len(ws) - 1))] if ws else None

    # Subject50 criterion: all shadowed cases must pass; non-shadowed local routes OK
    eligible = [x for x in results if x.get("subject_pass") is not None]
    summary["eligible"] = len(eligible)
    summary["pass_rate"] = f"{summary['subject_pass']}/{len(eligible)}" if eligible else "0/0"
    summary["PASS"] = bool(eligible) and summary["subject_pass"] == len(eligible) and summary["extra_subjects_cases"] == 0

    (OUT / "SUBJECT50_RESULTS.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False) + "\n"
    )
    print("SUMMARY", json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
