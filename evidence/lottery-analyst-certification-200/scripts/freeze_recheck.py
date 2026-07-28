#!/usr/bin/env python3
"""Pre-freeze / freeze integrity re-check (read-only)."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from uuid import UUID

from app.core.security import create_access_token
from app.lottery.numeric_relations.analysis_engine import run_complete_analysis

UID = "185d091c-0c1c-43db-b7b8-fb6b819b173a"
TID = "8ebfa281-cd3c-4017-8e47-c572a79d84b2"
BASE = "http://127.0.0.1:8000/api/v1"
OUT = Path("/tmp/freeze_recheck.json")


def tok() -> str:
    return create_access_token(subject=UID, tenant_id=UUID(TID), role="owner")


def api(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok()}",
            "Content-Type": "application/json",
            "X-Tenant-Id": TID,
        },
    )
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read().decode())


def chat(turns: list[str]) -> list[str]:
    s = api("POST", "/lottery/chat/sessions", {"title": "freeze-recheck"})
    sid = s["id"]
    out = []
    for q in turns:
        r = api("POST", f"/lottery/chat/sessions/{sid}/messages", {"content": q})
        out.append((r.get("message") or {}).get("content") or "")
    return out


def main() -> None:
    results = []

    r = run_complete_analysis(
        {"numbers": [35, 14], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
    )
    r2 = run_complete_analysis(
        {"numbers": [39, 58], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
    )
    results.append(
        {
            "name": "motor_35_14",
            "ok": int(r.primary_signal["number"]) == 54,
            "detail": r.primary_signal["number"],
        }
    )
    results.append(
        {
            "name": "motor_39_58",
            "ok": int(r2.primary_signal["number"]) == 94,
            "detail": r2.primary_signal["number"],
        }
    )

    # last 22
    t = chat(["¿Cuándo fue la última vez que salió el 22?"])[0]
    results.append(
        {
            "name": "last_22",
            "ok": "2026-07-20" in t and "Gana" in t,
            "detail": t[:240],
        }
    )

    # last3 97
    t = chat(
        [
            "¿Cuándo fue la última vez que salió el 97?",
            "¿Y las últimas 3 veces?",
        ]
    )[1]
    dates = re.findall(r"20\d{2}-\d{2}-\d{2}", t)
    results.append(
        {
            "name": "last3_97",
            "ok": "97" in t and len(dates) >= 3,
            "detail": f"dates={dates[:5]} text={t[:240]}",
        }
    )

    # nacional inherit
    replies = chat(
        [
            "¿Cuándo salió por última vez el 35 en Nacional y en primera posición?",
            "¿Y las últimas 3?",
        ]
    )
    t = replies[1]
    after = t.split("Apariciones:")[-1] if "Apariciones:" in t else t
    leak = any(x in after for x in ["Leidsa", "Loteka", "Real", "Gana"])
    nac = after.count("Nacional")
    results.append(
        {
            "name": "nacional_inherit",
            "ok": (not leak) and nac >= 2 and "35" in t,
            "detail": t[:300],
        }
    )

    # last 44 — factual Leidsa 2026-07-20 (footer lottery label may be sticky; not a date fail)
    t = chat(["¿Cuándo salió?", "El 44."])[1]
    results.append(
        {
            "name": "last_44",
            "ok": "44" in t and "2026-07-20" in t and "Leidsa" in t,
            "detail": t[:300],
        }
    )

    # correction 97
    t = chat(
        [
            "¿Cuándo fue la última vez que salió el 22?",
            "No, me refiero al 97.",
        ]
    )[1]
    results.append(
        {
            "name": "correction_97",
            "ok": "97" in t and "2026-07-18" in t and "22" not in re.sub(r"2026-07-20|20 de julio", "", t),
            "detail": t[:300],
        }
    )

    # same day
    t = chat(["¿Han salido el 55 y el 24 el mismo día?"])[0]
    results.append(
        {
            "name": "same_day_55_24",
            "ok": "55" in t and "24" in t and "no encontr" not in t.lower()[:80],
            "detail": t[:240],
        }
    )

    # compare
    t = chat(["Compara el 54 con el 94 en todo el histórico."])[0]
    results.append(
        {
            "name": "compare_54_94",
            "ok": "54" in t and "94" in t and len(t) > 40,
            "detail": t[:240],
        }
    )

    blocked = not all(x["ok"] for x in results)
    report = {"blocked": blocked, "results": results}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("BLOCKED" if blocked else "OK_TO_FREEZE")


if __name__ == "__main__":
    main()
