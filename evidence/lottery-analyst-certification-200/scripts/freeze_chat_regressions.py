#!/usr/bin/env python3
"""Mandatory conversational regressions before freeze (read-only)."""
from __future__ import annotations

import json
import re
import urllib.request
from uuid import UUID

from app.core.security import create_access_token

UID = "185d091c-0c1c-43db-b7b8-fb6b819b173a"
TID = "8ebfa281-cd3c-4017-8e47-c572a79d84b2"
BASE = "http://127.0.0.1:8000/api/v1"
OUT = "/tmp/freeze_chat_regressions.json"


def tok() -> str:
    return create_access_token(subject=UID, tenant_id=UUID(TID), role="owner")


def api(method: str, path: str, body: dict | None = None, timeout: int = 240) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok()}",
            "Content-Type": "application/json",
            "X-Tenant-Id": TID,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode() or "{}")


def send(sid: str, content: str) -> dict:
    return api("POST", f"/lottery/chat/sessions/{sid}/messages", {"content": content})


def text(r: dict) -> str:
    return ((r.get("message") or {}).get("content")) or ""


def items(r: dict) -> list:
    sc = r.get("structured_content") or {}
    data = sc.get("data") if isinstance(sc, dict) else {}
    its = (data or {}).get("items")
    if its:
        return its
    research = r.get("research") or sc.get("research") if isinstance(sc, dict) else {}
    for ev in (research or {}).get("evidence") or []:
        sm = ev.get("summary") or {}
        if sm.get("items"):
            return sm["items"]
    return []


def main() -> None:
    results = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append({"name": name, "ok": ok, "detail": detail[:500]})
        print(("PASS" if ok else "FAIL"), name, detail[:160])

    # 1) last 22
    s = api("POST", "/lottery/chat/sessions", {"title": "freeze-reg-22"})["id"]
    r = send(s, "¿Cuándo fue la última vez que salió el 22?")
    t = text(r)
    check("last_22", "2026-07-20" in t and "Gana" in t and "22" in t, t)

    # 2) last3 97
    s = api("POST", "/lottery/chat/sessions", {"title": "freeze-reg-97"})["id"]
    send(s, "¿Cuándo salió por última vez el 97?")
    r = send(s, "¿Y las últimas 3?")
    t = text(r)
    it = items(r)
    dates = [x.get("date") for x in it] if it else re.findall(r"20\d{2}-\d{2}-\d{2}", t)
    check("last3_97", "97" in t and len(dates) >= 2, f"dates={dates} text={t[:200]}")

    # 3) Nacional inherit
    s = api("POST", "/lottery/chat/sessions", {"title": "freeze-reg-nac"})["id"]
    send(s, "¿Cuándo salió por última vez el 35 en Nacional y en primera posición?")
    r = send(s, "¿Y las últimas 3?")
    it = items(r)
    lots = [x.get("lottery") for x in it]
    check(
        "nacional_inherit",
        bool(it) and all("Nacional" in str(x) for x in lots) and "Leidsa" not in str(lots),
        f"lots={lots}",
    )

    # 4) last 44
    s = api("POST", "/lottery/chat/sessions", {"title": "freeze-reg-44"})["id"]
    send(s, "¿Cuándo salió?")
    r = send(s, "El 44.")
    t = text(r)
    check("last_44", "44" in t and "2026-07-20" in t and "Leidsa" in t, t)

    # 5) correction 97
    s = api("POST", "/lottery/chat/sessions", {"title": "freeze-reg-corr"})["id"]
    send(s, "¿Cuándo fue la última vez que salió el 22?")
    r = send(s, "No, me refiero al 97.")
    t = text(r)
    check("correction_97", "97" in t and "2026-07-18" in t and "22" not in t.split("97")[0][-40:], t)

    # 6) same_day
    s = api("POST", "/lottery/chat/sessions", {"title": "freeze-reg-sd"})["id"]
    r = send(s, "¿Han salido el 55 y el 24 el mismo día?")
    t = text(r)
    check(
        "same_day_55_24",
        ("55" in t and "24" in t)
        and ("coinciden" in t.lower() or "mismo día" in t.lower() or re.search(r"\b([1-9]\d{0,2}|200)\b", t))
        and "no encontr" not in t.lower()[:80],
        t,
    )

    # 7) compare 54 vs 94
    s = api("POST", "/lottery/chat/sessions", {"title": "freeze-reg-cmp"})["id"]
    r = send(s, "Compara el 54 con el 94 en todo el histórico.")
    t = text(r)
    check("compare_54_94", "54" in t and "94" in t and len(t) > 40, t)

    blocked = any(not x["ok"] for x in results)
    payload = {"blocked": blocked, "results": results}
    open(OUT, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2))
    print("BLOCKED" if blocked else "OK", "->", OUT)


if __name__ == "__main__":
    main()
