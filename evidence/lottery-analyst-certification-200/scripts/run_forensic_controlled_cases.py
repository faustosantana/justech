#!/usr/bin/env python3
"""Run controlled forensic cases A/B/C against a local chat API (DEV).

Requires:
  LOTTERY_FORENSIC_TRACE_ENABLED=true on the API
  BASE_URL, and either SMOKE_EMAIL/SMOKE_PASSWORD or JWT via create_access_token + existing user

Does NOT modify production. Does NOT change agent behavior beyond capturing traces.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3] if len(Path(__file__).resolve().parents) > 3 else Path("/app")
if (ROOT / "backend").exists():
    sys.path.insert(0, str(ROOT / "backend"))
elif Path("/app").exists():
    sys.path.insert(0, "/app")
    ROOT = Path("/app")

BASE = os.environ.get("FORENSIC_BASE_URL", "http://127.0.0.1:8022/api/v1")
OUT = Path(os.environ.get("FORENSIC_OUT", str(ROOT / "artifacts" / "forensics" / "controlled_runs")))
OUT.mkdir(parents=True, exist_ok=True)


def _login() -> tuple[str, str]:
    email = os.environ.get("SMOKE_EMAIL") or os.environ.get("FORENSIC_EMAIL")
    password = os.environ.get("SMOKE_PASSWORD") or os.environ.get("FORENSIC_PASSWORD")
    if email and password:
        req = urllib.request.Request(
            BASE.replace("/api/v1", "") + "/api/v1/auth/login"
            if BASE.endswith("/api/v1")
            else BASE + "/auth/login",
            data=json.dumps({"email": email, "password": password}).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        # try standard path
        for url in (
            f"{BASE}/auth/login",
            f"{BASE.rsplit('/api/v1', 1)[0]}/api/v1/auth/login",
        ):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps({"email": email, "password": password}).encode(),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read().decode())
                tok = data.get("access_token") or data.get("token")
                tid = str(data.get("tenant_id") or os.environ.get("FORENSIC_TENANT_ID") or "")
                if tok:
                    return tok, tid
            except Exception:
                continue
    # fallback: mint token (user must exist in DB)
    from app.core.security import create_access_token

    uid = os.environ.get("FORENSIC_USER_ID", "185d091c-0c1c-43db-b7b8-fb6b819b173a")
    tid = os.environ.get("FORENSIC_TENANT_ID", "8ebfa281-cd3c-4017-8e47-c572a79d84b2")
    return create_access_token(subject=uid, tenant_id=UUID(tid), role="owner"), tid


def api(method: str, path: str, body: dict | None, token: str, tenant: str):
    data = None if body is None else json.dumps(body).encode()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if tenant:
        headers["X-Tenant-Id"] = tenant
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_error": raw[:800]}


def run_case(name: str, turns: list[str], token: str, tenant: str) -> dict:
    st, sess = api("POST", "/lottery/chat/sessions", {"title": f"forensic-{name}"}, token, tenant)
    if st >= 400:
        return {"case": name, "ok": False, "error": sess, "http": st}
    sid = sess["id"]
    rows = []
    for i, msg in enumerate(turns, 1):
        st, r = api("POST", f"/lottery/chat/sessions/{sid}/messages", {"content": msg}, token, tenant)
        m = r.get("message") or {}
        forensic = r.get("forensic") or {}
        rows.append(
            {
                "turn": i,
                "user": msg,
                "http": st,
                "assistant_preview": (m.get("content") or "")[:400],
                "structured_type": ((m.get("structured_content") or {}) or {}).get("type"),
                "correlation_id": forensic.get("correlation_id"),
                "artifact_dir": forensic.get("artifact_dir"),
                "intent": r.get("intent"),
            }
        )
    path = OUT / f"{name}.json"
    path.write_text(json.dumps({"case": name, "session_id": sid, "turns": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"case": name, "ok": True, "session_id": sid, "turns": rows, "report": str(path)}


def main() -> int:
    token, tenant = _login()
    cases = {
        "A_greeting": ["Hola", "Todo bien, ¿y tú?"],
        "B_ops": [
            "¿Han coincidido el 50 y el 90 el mismo día?",
            "Muéstrame las fechas.",
            "Desglosa por posición.",
            "Solo Gana Más.",
            "Ordénalo desde la fecha más reciente.",
        ],
        "C_topic_switch": [
            "¿Han coincidido el 50 y el 90?",
            "Ahora analiza el 35.",
        ],
    }
    summary = []
    for name, turns in cases.items():
        print("===", name, "===")
        res = run_case(name, turns, token, tenant)
        summary.append(res)
        print(json.dumps({k: res.get(k) for k in ("case", "ok", "session_id", "error", "http")}, ensure_ascii=False))
        for t in res.get("turns") or []:
            print(
                f"  T{t['turn']} cid={t.get('correlation_id')} type={t.get('structured_type')} "
                f"preview={t.get('assistant_preview', '')[:120]!r}"
            )
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("OUT", OUT)
    return 0 if all(s.get("ok") for s in summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
