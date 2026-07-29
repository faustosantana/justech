#!/usr/bin/env python3
"""Live DEV validation — Conversational Routing 3.0 cases 1–7 on :8022."""

from __future__ import annotations

import json
import os
import re
import sys
import time
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
else:
    sys.path.insert(0, str(ROOT))

BASE = os.environ.get("FORENSIC_BASE_URL", "http://127.0.0.1:8022/api/v1")
OUT = Path(
    os.environ.get(
        "ROUTING3_LIVE_OUT",
        str(
            ROOT
            / "evidence"
            / "lottery-investigation-workspace-mvp-20260728"
            / "routing3"
            / "LIVE_CASES.json"
        ),
    )
)
OUT.parent.mkdir(parents=True, exist_ok=True)


def _token() -> tuple[str, str]:
    from app.core.security import create_access_token

    auth_path = Path("/tmp/routing3_auth.json")
    if auth_path.exists():
        data = json.loads(auth_path.read_text())
        uid = data["uid"]
        tid = data["tid"]
        role = data.get("role") or "owner"
    else:
        uid = os.environ.get("FORENSIC_USER_ID", "e520ca09-882a-4e8f-8d73-8045dc3c6245")
        tid = os.environ.get("FORENSIC_TENANT_ID", "35e2edb5-23e8-403e-86cd-8535dc048720")
        role = os.environ.get("FORENSIC_ROLE", "owner")
    return create_access_token(subject=uid, tenant_id=UUID(tid), role=role), tid


def api(method: str, path: str, body: dict | None, token: str, tenant: str) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Tenant-Id": tenant,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            payload = json.loads(r.read().decode())
            payload["_http_status"] = r.status
            return payload
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:2000]}
        payload["_http_status"] = e.code
        return payload


def new_session(token: str, tenant: str, title: str) -> str:
    s = api("POST", "/lottery/chat/sessions", {"title": title}, token, tenant)
    sid = s.get("id") or (s.get("session") or {}).get("id")
    assert sid, s
    return str(sid)


def send(token: str, tenant: str, sid: str, content: str) -> dict:
    r = api("POST", f"/lottery/chat/sessions/{sid}/messages", {"content": content}, token, tenant)
    msg = r.get("message") or {}
    ctx = (r.get("context") or {}).get("conversation_v4") or {}
    inv = ctx.get("active_investigation") or {}
    assets = ctx.get("investigation_assets") or ctx.get("assets") or {}
    active_asset_id = ctx.get("active_asset_id") or (
        list(assets.keys())[0] if isinstance(assets, dict) and assets else None
    )
    hd = r.get("hermes_decision") or ((r.get("context") or {}).get("agent_trace") or {}).get(
        "hermes_decision"
    )
    if isinstance(hd, dict) is False:
        hd = {}
    tp = msg.get("tool_payload") or {}
    text = msg.get("content") or ""
    structured = msg.get("structured_content")
    forensic = r.get("forensic") or {}
    corr = (
        forensic.get("correlation_id")
        or r.get("correlation_id")
        or (tp.get("correlation_id") if isinstance(tp, dict) else None)
    )
    return {
        "content": content,
        "http": r.get("_http_status"),
        "answer": text,
        "intent": r.get("intent") or tp.get("routing_intent"),
        "provider_used": r.get("provider_used")
        or tp.get("provider_used")
        or ((r.get("runtime_trace") or {}).get("provider_used")),
        "routing_reason_code": r.get("routing_reason_code") or tp.get("reason_code"),
        "correlation_id": corr,
        "forensic": forensic,
        "hermes_decision": hd,
        "tool_payload": tp,
        "structured_type": (structured or {}).get("type") if isinstance(structured, dict) else None,
        "active_numbers": ctx.get("active_numbers"),
        "active_relation": ctx.get("active_relation"),
        "active_asset_id": active_asset_id,
        "investigation_subjects": inv.get("subjects"),
        "pending_slots": ctx.get("pending_slots"),
        "pending_intent": ctx.get("pending_intent"),
        "has_hallazgos": bool(re.search(r"Hallazgos|Interpretaci[oó]n|\bDetalle\b", text)),
        "mentions_50_90": bool(re.search(r"\b50\b|\b90\b", text)),
        "raw_keys": sorted(r.keys()),
    }


def chk(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "pass": bool(ok), "detail": detail[:400]}


def main() -> int:
    token, tenant = _token()
    results: dict = {"cases": {}, "checks": [], "base": BASE, "ts": time.time()}

    # ---- CASE 1 ----
    sid = new_session(token, tenant, "routing3-c1-clean")
    t1 = send(token, tenant, sid, "Hola")
    t2 = send(token, tenant, sid, "Todo bien, ¿y tú?")
    results["cases"]["1"] = {"session": sid, "turns": [t1, t2]}
    for i, t in enumerate([t1, t2], 1):
        results["checks"].append(
            chk(
                f"C1.T{i}_social",
                (t.get("intent") == "social_chitchat" or t.get("provider_used") == "social_template")
                and not t["has_hallazgos"]
                and not t["mentions_50_90"]
                and t["http"] < 500,
                f"intent={t.get('intent')} provider={t.get('provider_used')} ans={t['answer'][:80]!r}",
            )
        )

    # ---- CASE 2 ----
    sid = new_session(token, tenant, "routing3-c2-sticky")
    t1 = send(token, tenant, sid, "¿Han coincidido el 50 y el 90 el mismo día?")
    t2 = send(token, tenant, sid, "Hola")
    t3 = send(token, tenant, sid, "Todo bien, ¿y tú?")
    results["cases"]["2"] = {"session": sid, "turns": [t1, t2, t3]}
    results["checks"].append(
        chk(
            "C2.T1_research",
            t1["http"] < 500 and ("50" in t1["answer"] or "90" in t1["answer"] or t1.get("active_numbers")),
            t1["answer"][:120],
        )
    )
    for i, t in enumerate([t2, t3], 2):
        results["checks"].append(
            chk(
                f"C2.T{i}_social_clean",
                (t.get("intent") == "social_chitchat" or t.get("provider_used") == "social_template")
                and not t["has_hallazgos"]
                and not t["mentions_50_90"],
                f"intent={t.get('intent')} ans={t['answer'][:100]!r} sticky={t.get('active_numbers')}",
            )
        )

    # ---- CASE 3 ----
    sid = new_session(token, tenant, "routing3-c3-return")
    t1 = send(token, tenant, sid, "¿Han coincidido el 50 y el 90 el mismo día?")
    t2 = send(token, tenant, sid, "Gracias.")
    t3 = send(token, tenant, sid, "Muéstrame las fechas.")
    results["cases"]["3"] = {"session": sid, "turns": [t1, t2, t3]}
    results["checks"].append(
        chk(
            "C3.T2_social",
            t2.get("intent") == "social_chitchat" or t2.get("provider_used") == "social_template",
            f"{t2.get('intent')} {t2['answer'][:60]!r}",
        )
    )
    wa = ((t3.get("tool_payload") or {}).get("workspace_action") or {})
    if isinstance(wa, dict) is False:
        wa = {}
    hd = t3.get("hermes_decision") or {}
    results["checks"].append(
        chk(
            "C3.T3_show_dates",
            (
                wa.get("action") == "show_dates"
                or (hd.get("workspace_action") or {}).get("action") == "show_dates"
                or hd.get("requested_attribute") == "show_dates"
                or t3.get("structured_type") == "investigation_workspace_table"
            )
            and not re.search(r"Dentro de las 7 loter[ií]as", t3["answer"] or ""),
            f"wa={wa} structured={t3.get('structured_type')} ans={t3['answer'][:100]!r}",
        )
    )

    # ---- CASE 4 ----
    sid = new_session(token, tenant, "routing3-c4-ops")
    turns4 = []
    phrases = [
        "¿Han coincidido el 50 y el 90 el mismo día?",
        "Muéstrame las fechas.",
        "Desglosa por posición.",
        "Solo Gana Más.",
        "Ordénalo desde la fecha más reciente.",
    ]
    for p in phrases:
        turns4.append(send(token, tenant, sid, p))
    results["cases"]["4"] = {"session": sid, "turns": turns4}
    expect_actions = [None, "show_dates", "sort_results", "filter_results", "sort_results"]
    for i, (t, exp) in enumerate(zip(turns4, expect_actions)):
        if i == 0:
            results["checks"].append(
                chk("C4.T1_research", t["http"] < 500 and len(t["answer"]) > 20, t["answer"][:80])
            )
            continue
        wa = ((t.get("tool_payload") or {}).get("workspace_action") or {})
        hd = t.get("hermes_decision") or {}
        act = wa.get("action") or (hd.get("workspace_action") or {}).get("action") or hd.get(
            "requested_attribute"
        )
        results["checks"].append(
            chk(
                f"C4.T{i+1}_{exp}",
                act == exp or t.get("structured_type") in {
                    "investigation_workspace_table",
                    "investigation_workspace_export",
                },
                f"got={act} structured={t.get('structured_type')} ans={t['answer'][:80]!r}",
            )
        )

    # ---- CASE 5 ----
    sid = new_session(token, tenant, "routing3-c5-topic")
    t1 = send(token, tenant, sid, "¿Han coincidido el 50 y el 90?")
    t2 = send(token, tenant, sid, "Ahora analiza el 35.")
    results["cases"]["5"] = {"session": sid, "turns": [t1, t2]}
    nums = t2.get("active_numbers") or t2.get("investigation_subjects") or []
    results["checks"].append(
        chk(
            "C5.T2_new_topic_35",
            "35" in str(nums) or "35" in (t2["answer"] or ""),
            f"nums={nums} ans={t2['answer'][:120]!r}",
        )
    )

    # ---- CASE 6 ----
    # Force clarification: incomplete last-occurrence ask
    sid = new_session(token, tenant, "routing3-c6-clarify")
    t1 = send(token, tenant, sid, "¿Cuándo salió?")  # likely asks for number
    # If system asks lottery after number:
    t_mid = send(token, tenant, sid, "54")
    # Try to get lottery clarification — if not pending, craft via state is hard over HTTP.
    # Alternative: message that triggers lottery slot
    t2 = send(token, tenant, sid, "Gana Más.")
    results["cases"]["6"] = {"session": sid, "turns": [t1, t_mid, t2]}
    # Soft pass: Gana Más does not become social_chitchat; preferably continues research
    results["checks"].append(
        chk(
            "C6_gana_mas_not_social",
            t2.get("intent") != "social_chitchat",
            f"intent={t2.get('intent')} pending={t2.get('pending_slots')} ans={t2['answer'][:100]!r}",
        )
    )

    # ---- CASE 7 ----
    phrases7 = [
        "Gracias",
        "Perfecto",
        "Excelente",
        "Muy bien",
        "Qué bueno",
        "Buenos días",
        "Buenas tardes",
        "Buenas noches",
        "¿Cómo estás?",
    ]
    turns7 = []
    for p in phrases7:
        sid = new_session(token, tenant, f"routing3-c7-{p[:12]}")
        turns7.append(send(token, tenant, sid, p))
    results["cases"]["7"] = {"turns": turns7}
    for t in turns7:
        results["checks"].append(
            chk(
                f"C7_{t['content']}",
                (t.get("intent") == "social_chitchat" or t.get("provider_used") == "social_template")
                and not t["has_hallazgos"],
                f"intent={t.get('intent')} provider={t.get('provider_used')} ans={t['answer'][:60]!r}",
            )
        )

    failed = [c for c in results["checks"] if not c["pass"]]
    results["status"] = "PASS" if not failed else "FAIL"
    results["passed"] = sum(1 for c in results["checks"] if c["pass"])
    results["failed"] = len(failed)
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": results["status"], "passed": results["passed"], "failed": results["failed"], "out": str(OUT)}, indent=2))
    for f in failed:
        print("FAIL", f)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
