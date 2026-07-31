#!/usr/bin/env python3
"""Compare20 + MissingBreakdown10 for rc3.5 (DEV shadow)."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path
from uuid import UUID, uuid4

from app.core.security import create_access_token

BASE = os.environ.get("FORENSIC_BASE_URL", "http://127.0.0.1:8000/api/v1")
OUT = Path(os.environ.get("RC35_OUT", "/tmp/rc35_directed"))
OUT.mkdir(parents=True, exist_ok=True)
AUTH = json.loads(Path("/tmp/routing3_auth.json").read_text())
UID, TID, ROLE = AUTH["uid"], AUTH["tid"], AUTH.get("role") or "owner"
HASH = os.environ.get(
    "EXPECTED_HASH", "f9cb83c80271de345fb3b50a08cc9a76b31c66666d2dcb55517bbb7059d21149"
)
PAIRS = [
    (61, 14), (66, 2), (68, 19), (72, 5), (73, 9), (78, 15), (81, 16), (85, 17),
    (88, 21), (91, 23), (93, 24), (95, 26), (97, 27), (99, 29), (1, 30), (2, 31),
    (5, 32), (7, 34), (9, 36), (11, 37),
]


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
            "X-Correlation-Id": f"rc35-{uuid4().hex[:8]}",
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


def score_studio(studio: str, guard, ph: str | None, *, require_total: bool = False) -> dict:
    invent = bool(
        re.search(
            r"(?i)\d+\s+casos?\s+en\s+primera\s+posici|ambos\s+(?:salieron|coincidieron)\s+en\s+primera",
            studio or "",
        )
    )
    has_limit = bool(
        re.search(
            r"(?i)(no\s+permite\s+determinar|no\s+es\s+posible|no\s+se\s+puede|"
            r"no\s+(?:hay|incluye|contiene|proporciona)|sin\s+desglose|solo\s+(?:se\s+)?(?:proporciona|incluye|autoriza|cuenta))",
            studio or "",
        )
    )
    affirms_winner = bool(
        re.search(
            r"(?i)(el\s+n[uú]mero\s+\d{1,2}\s+aparece\s+m[aá]s|tiene\s+mayor\s+presencia)",
            studio or "",
        )
    )
    winner = affirms_winner and not has_limit
    ok = guard is True and not invent and not winner and ph == HASH
    if require_total:
        ok = ok and bool(re.search(r"\b\d{2,5}\b", studio or ""))
    return {
        "ok": ok,
        "invent": invent,
        "winner": winner,
        "has_limit": has_limit,
        "guard": guard,
        "hash": ph,
    }


def run_one(question: str, label: str, *, require_total: bool = False) -> dict:
    sid = None
    row = {"label": label}
    try:
        sess = api("POST", "/lottery/chat/sessions", {"title": label}, timeout=90)
        sid = sess.get("id") or (sess.get("session") or {}).get("id")
        t0 = time.perf_counter()
        r = api(
            "POST",
            f"/lottery/chat/sessions/{sid}/messages",
            {"content": question},
            timeout=600,
        )
        sh = deep_find(r, "shadow_comparison") or {}
        studio = sh.get("studio_raw") or ""
        sc = score_studio(
            studio,
            sh.get("studio_guard_passed"),
            sh.get("studio_prompt_hash"),
            require_total=require_total,
        )
        row.update(sc)
        row["studio"] = studio
        row["reason"] = sh.get("studio_guard_reason")
        row["lat"] = (time.perf_counter() - t0) * 1000
    except Exception as e:  # noqa: BLE001
        row.update({"ok": False, "error": str(e)[:300]})
    finally:
        if sid:
            try:
                api("DELETE", f"/lottery/chat/sessions/{sid}", timeout=60)
            except Exception:  # noqa: BLE001
                pass
    print(label, row.get("ok"), row.get("reason"), int(row.get("lat") or 0), flush=True)
    return row


def main() -> None:
    compare = []
    for i, (a, b) in enumerate(PAIRS):
        q = (
            f"Compara históricamente el {a:02d} y el {b:02d}: ¿quién aparece más en "
            f"coincidencias same-day con el otro? Interpreta. No inventes subtotales "
            f"de posiciones, frecuencias parciales ni desgloses que no estén explícitos "
            f"en la evidencia."
        )
        compare.append(run_one(q, f"C{i+1:02d}_{a:02d}_{b:02d}", require_total=True))
    (OUT / "COMPARE20_RUNS.json").write_text(
        json.dumps(compare, indent=2, ensure_ascii=False) + "\n"
    )

    missing = []
    for i, (a, b) in enumerate(PAIRS[:10]):
        q = (
            f"Dame el desglose por primera posición de las coincidencias same-day "
            f"del {a:02d} y el {b:02d}. Si no hay desglose, dilo."
        )
        row = run_one(q, f"M{i+1:02d}")
        row["ok"] = bool(row.get("ok")) and bool(row.get("has_limit")) and not row.get("invent")
        missing.append(row)
    (OUT / "MISSING10_RUNS.json").write_text(
        json.dumps(missing, indent=2, ensure_ascii=False) + "\n"
    )

    summary = {
        "compare20_pass": sum(1 for r in compare if r.get("ok")),
        "compare20_n": len(compare),
        "missing10_pass": sum(1 for r in missing if r.get("ok")),
        "missing10_n": len(missing),
        "expected_hash": HASH,
    }
    summary["PASS"] = summary["compare20_pass"] == 20 and summary["missing10_pass"] == 10
    (OUT / "COMPARE_MISSING_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", summary, flush=True)


if __name__ == "__main__":
    main()
