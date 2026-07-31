#!/usr/bin/env python3
"""E0068 x10 directed validation under pinned rc3.5."""
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
Q = (
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
            "X-Correlation-Id": f"e0068-{uuid4().hex[:8]}",
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


def main() -> None:
    runs = []
    for i in range(10):
        sid = None
        row: dict = {"n": i + 1}
        try:
            sess = api("POST", "/lottery/chat/sessions", {"title": f"e0068-{i+1}"}, timeout=90)
            sid = sess.get("id") or (sess.get("session") or {}).get("id")
            t0 = time.perf_counter()
            r = api(
                "POST",
                f"/lottery/chat/sessions/{sid}/messages",
                {"content": Q},
                timeout=600,
            )
            sh = deep_find(r, "shadow_comparison") or {}
            studio = sh.get("studio_raw") or ""
            reason = sh.get("studio_guard_reason")
            ph = sh.get("studio_prompt_hash")
            invent = bool(
                re.search(
                    r"(?i)\b94\b|ambos\s+(?:salieron|coincidieron)\s+en\s+primera|"
                    r"\d+\s+casos?\s+en\s+primera\s+posici",
                    studio,
                )
            )
            has_limit = bool(
                re.search(
                    r"(?i)(no\s+permite\s+determinar|no\s+es\s+posible\s+determinar|"
                    r"no\s+se\s+puede\s+(?:afirmar|determinar|responder)|"
                    r"no\s+(?:hay|incluye|contiene|proporciona)\s+(?:un\s+)?desglose|"
                    r"sin\s+desglose|solo\s+(?:se\s+)?(?:proporciona|incluye|autoriza))",
                    studio,
                )
            )
            affirms_winner = bool(
                re.search(
                    r"(?i)(el\s+n[uú]mero\s+\d{1,2}\s+aparece\s+m[aá]s|"
                    r"tiene\s+mayor\s+presencia|"
                    r"aparece\s+m[aá]s\s+en\s+coincidencias)",
                    studio,
                )
            )
            winner = affirms_winner and not has_limit
            ok = (
                sh.get("studio_guard_passed") is True
                and not invent
                and not winner
                and ph == HASH
                and "152" in studio
            )
            row.update(
                {
                    "ok": ok,
                    "guard": sh.get("studio_guard_passed"),
                    "reason": reason,
                    "hash": ph,
                    "invent": invent,
                    "winner": winner,
                    "lat": (time.perf_counter() - t0) * 1000,
                    "studio": studio,
                }
            )
        except Exception as e:  # noqa: BLE001
            row.update({"ok": False, "error": str(e)[:300]})
        finally:
            if sid:
                try:
                    api("DELETE", f"/lottery/chat/sessions/{sid}", timeout=60)
                except Exception:  # noqa: BLE001
                    pass
        runs.append(row)
        print(
            f"E0068_{i+1:02d}",
            row.get("ok"),
            row.get("reason"),
            row.get("hash"),
            int(row.get("lat") or 0),
            flush=True,
        )
    summary = {
        "pass": sum(1 for x in runs if x.get("ok")),
        "n": 10,
        "PASS": all(x.get("ok") for x in runs),
        "expected_hash": HASH,
    }
    (OUT / "E0068_RUNS.json").write_text(
        json.dumps({"summary": summary, "runs": runs}, indent=2, ensure_ascii=False) + "\n"
    )
    print("SUMMARY", summary, flush=True)


if __name__ == "__main__":
    main()
