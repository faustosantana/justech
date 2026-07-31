#!/usr/bin/env python3
"""Directed validation for rc3.5 — E0068×10, Compare20, MissingBreakdown10 (live DEV)."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import UUID, uuid4

from app.core.security import create_access_token

BASE = os.environ.get("FORENSIC_BASE_URL", "http://127.0.0.1:8000/api/v1")
OUT = Path(os.environ.get("RC35_OUT", "/tmp/rc35_directed"))
OUT.mkdir(parents=True, exist_ok=True)
AUTH = json.loads(Path("/tmp/routing3_auth.json").read_text())
UID, TID, ROLE = AUTH["uid"], AUTH["tid"], AUTH.get("role") or "owner"
EXPECTED_HASH = os.environ.get(
    "EXPECTED_HASH", "f9cb83c80271de345fb3b50a08cc9a76b31c66666d2dcb55517bbb7059d21149"
)
E0068_Q = (
    "Compara históricamente el 61 y el 14: ¿quién aparece más en coincidencias "
    "same-day con el otro? Interpreta. No inventes subtotales de posiciones, "
    "frecuencias parciales ni desgloses que no estén explícitos en la evidencia."
)


def tok() -> str:
    return create_access_token(subject=UID, tenant_id=UUID(TID), role=ROLE)


def api(method: str, path: str, body=None, timeout: float = 600) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok()}",
            "Content-Type": "application/json",
            "X-Tenant-Id": TID,
            "X-Correlation-Id": f"rc35-{uuid4().hex[:10]}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


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


def run_one(question: str, label: str) -> dict:
    sid = None
    t0 = time.perf_counter()
    try:
        sess = api("POST", "/lottery/chat/sessions", {"title": f"rc35-{label}"}, timeout=90)
        sid = sess.get("id") or (sess.get("session") or {}).get("id")
        r = api("POST", f"/lottery/chat/sessions/{sid}/messages", {"content": question}, timeout=600)
        sh = deep_find(r, "shadow_comparison") or {}
        pr = deep_find(r, "prompt_runtime") or {}
        studio = sh.get("studio_raw") or sh.get("studio_response") or ""
        legacy = (r.get("assistant") or {}).get("content") or r.get("content") or ""
        guard_ok = sh.get("studio_guard_passed")
        reason = sh.get("studio_guard_reason")
        phash = sh.get("studio_prompt_hash") or deep_find(pr, "compiled_prompt_hash")
        unauth = bool(reason and "unauthorized_breakdown" in str(reason))
        invent = bool(
            re.search(r"(?i)94|ambos.*?primera|\d+\s+casos?\s+en\s+primera", studio or "")
        )
        winner = bool(
            re.search(r"(?i)aparece\s+m[aá]s", studio or "")
            and not re.search(r"(?i)no\s+(?:es\s+posible|se\s+puede|incluye|contiene)", studio or "")
        )
        ok = (
            guard_ok is True
            and not unauth
            and not invent
            and not winner
            and (phash == EXPECTED_HASH or phash is None)
            and "152" in (studio or "")
        )
        return {
            "label": label,
            "ok": ok,
            "studio_guard_passed": guard_ok,
            "studio_guard_reason": reason,
            "prompt_hash": phash,
            "hash_ok": phash == EXPECTED_HASH,
            "unauthorized_breakdown": unauth,
            "invented_subtotals": invent,
            "false_winner": winner,
            "studio": studio,
            "legacy_snip": (legacy or "")[:400],
            "latency_ms": (time.perf_counter() - t0) * 1000,
            "provider": deep_find(r, "provider_used"),
        }
    except Exception as e:  # noqa: BLE001
        return {"label": label, "ok": False, "error": str(e)[:400]}
    finally:
        if sid:
            try:
                api("DELETE", f"/lottery/chat/sessions/{sid}", timeout=60)
            except Exception:  # noqa: BLE001
                pass


def main():
    e0068 = [run_one(E0068_Q, f"E0068_{i+1:02d}") for i in range(10)]
    (OUT / "E0068_RUNS.json").write_text(json.dumps(e0068, indent=2, ensure_ascii=False) + "\n")

    # Compare20 — joint total only pairs (same style as dataset compare_numbers)
    pairs = [
        (61, 14), (66, 2), (68, 19), (72, 5), (73, 9), (78, 15), (81, 16), (85, 17),
        (88, 21), (91, 23), (93, 24), (95, 26), (97, 27), (99, 29), (1, 30), (2, 31),
        (5, 32), (7, 34), (9, 36), (11, 37),
    ]
    compare = []
    for i, (a, b) in enumerate(pairs):
        q = (
            f"Compara históricamente el {a:02d} y el {b:02d}: ¿quién aparece más en "
            f"coincidencias same-day con el otro? Interpreta. No inventes subtotales "
            f"de posiciones, frecuencias parciales ni desgloses que no estén explícitos "
            f"en la evidencia."
        )
        compare.append(run_one(q, f"C{i+1:02d}_{a:02d}_{b:02d}"))
        print(compare[-1]["label"], compare[-1].get("ok"), compare[-1].get("studio_guard_reason"), flush=True)
    (OUT / "COMPARE20_RUNS.json").write_text(json.dumps(compare, indent=2, ensure_ascii=False) + "\n")

    missing = []
    for i in range(10):
        a, b = pairs[i]
        q = (
            f"Dame el desglose por primera posición de las coincidencias same-day "
            f"del {a:02d} y el {b:02d}. Si no hay desglose, dilo."
        )
        row = run_one(q, f"M{i+1:02d}")
        # For missing breakdown: pass if no invented numbers / guard ok / acknowledges limit
        studio = row.get("studio") or ""
        acknowledges = bool(
            re.search(r"(?i)no\s+(?:hay|incluye|contiene|proporciona)|sin\s+desglose|no\s+se\s+puede", studio)
        )
        row["acknowledges_limit"] = acknowledges
        row["ok"] = bool(row.get("studio_guard_passed")) and not row.get("invented_subtotals") and acknowledges
        missing.append(row)
        print(row["label"], row["ok"], flush=True)
    (OUT / "MISSING10_RUNS.json").write_text(json.dumps(missing, indent=2, ensure_ascii=False) + "\n")

    summary = {
        "e0068_pass": sum(1 for r in e0068 if r.get("ok")),
        "e0068_n": len(e0068),
        "compare20_pass": sum(1 for r in compare if r.get("ok")),
        "compare20_n": len(compare),
        "missing10_pass": sum(1 for r in missing if r.get("ok")),
        "missing10_n": len(missing),
        "expected_hash": EXPECTED_HASH,
    }
    summary["PASS"] = (
        summary["e0068_pass"] == 10
        and summary["compare20_pass"] == 20
        and summary["missing10_pass"] == 10
    )
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
