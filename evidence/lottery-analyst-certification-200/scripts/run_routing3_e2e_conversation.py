#!/usr/bin/env python3
"""E2E Conversational Routing 3.0 — mandatory 50+90 conversation via chat API."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from uuid import UUID

from app.core.security import create_access_token

UID = "185d091c-0c1c-43db-b7b8-fb6b819b173a"
TID = "8ebfa281-cd3c-4017-8e47-c572a79d84b2"
BASE = "http://127.0.0.1:8000/api/v1"

NARR = [
    "Dentro de las 7 loterías",
    "No significa necesariamente",
    "La cifra es histórica",
    "Conviene revisar",
    "Puedo mostrarte",
]

TURNS = [
    "Han salido juntos el 50 y el 90",
    "Desglosar por posición",
    "Ver fechas",
    "Solo Nacional",
    "Ordenar por fecha",
    "Mostrar primeras 20",
    "Exportar Excel",
]


def token() -> str:
    return create_access_token(subject=UID, tenant_id=UUID(TID), role="owner")


def api(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token()}",
            "Content-Type": "application/json",
            "X-Tenant-Id": TID,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(err)
        except Exception:
            return e.code, {"_error": err[:800]}


def main() -> int:
    st, sess = api("POST", "/lottery/chat/sessions", {"title": "routing3-50-90"})
    if st >= 400:
        print("SESSION_FAIL", st, sess)
        return 1
    sid = sess["id"]
    print("session", sid)
    fails: list[str] = []
    prev = None
    for i, msg in enumerate(TURNS, 1):
        st, r = api("POST", f"/lottery/chat/sessions/{sid}/messages", {"content": msg})
        m = r.get("message") or {}
        text = m.get("content") or ""
        sc = m.get("structured_content") or {}
        typ = sc.get("type")
        # Diagnostics may live in different envelopes
        diag = r.get("diagnostics") or r.get("runtime_trace") or {}
        hermes = (
            (diag.get("hermes_decision") if isinstance(diag, dict) else None)
            or r.get("hermes_decision")
            or (m.get("tool_trace") if isinstance(m.get("tool_trace"), dict) else {})
            or {}
        )
        if isinstance(hermes, list):
            hermes = {}
        print(
            f"{i}. http={st} type={typ} turn={hermes.get('turn_type')} "
            f"reason={hermes.get('reason_code')} preview={text[:140]!r}"
        )
        if st >= 500:
            fails.append(f"step{i}: http {st}")
        if i == 1:
            if typ in {
                "investigation_workspace_table",
                "investigation_workspace_export",
            }:
                fails.append("step1: unexpected workspace on first research turn")
            prev = text
            continue
        if typ not in {
            "investigation_workspace_table",
            "investigation_workspace_export",
        }:
            fails.append(f"step{i}: structured_type={typ} expected workspace")
        for n in NARR:
            if n in text:
                fails.append(f"step{i}: narrative marker {n!r}")
        if prev and text.strip() == prev.strip() and len(text) > 80:
            fails.append(f"step{i}: exact repeat of prior paragraph")
        prev = text

    print("FAILS", fails)
    if fails:
        print("FAIL")
        return 1
    print("PASS e2e_routing3_conversation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
