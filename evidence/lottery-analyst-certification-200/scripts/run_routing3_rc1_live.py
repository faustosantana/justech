#!/usr/bin/env python3
"""RC1 live forensic cases on DEV :8022 / in-container :8000."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from uuid import UUID

sys.path.insert(0, "/app")
from app.core.security import create_access_token

BASE = os.environ.get("FORENSIC_BASE_URL", "http://127.0.0.1:8000/api/v1")
OUT = Path(os.environ.get("RC1_LIVE_OUT", "/tmp/RC1_LIVE.json"))
auth = json.loads(Path("/tmp/routing3_auth.json").read_text()) if Path("/tmp/routing3_auth.json").exists() else {
    "uid": "e520ca09-882a-4e8f-8d73-8045dc3c6245",
    "tid": "35e2edb5-23e8-403e-86cd-8535dc048720",
    "role": "owner",
}


def api(method, path, body=None):
    tok = create_access_token(subject=auth["uid"], tenant_id=UUID(auth["tid"]), role=auth["role"])
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "X-Tenant-Id": auth["tid"],
        },
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def new_session(title):
    s = api("POST", "/lottery/chat/sessions", {"title": title})
    return s["id"]


def send(sid, content):
    r = api("POST", f"/lottery/chat/sessions/{sid}/messages", {"content": content})
    msg = r.get("message") or {}
    ctx = (r.get("context") or {}).get("conversation_v4") or {}
    text = msg.get("content") or ""
    corr = (r.get("forensic") or {}).get("correlation_id") or r.get("correlation_id")
    return {
        "content": content,
        "answer": text,
        "correlation_id": corr,
        "intent": r.get("intent"),
        "structured": (msg.get("structured_content") or {}).get("type")
        if isinstance(msg.get("structured_content"), dict)
        else None,
        "tool_payload": msg.get("tool_payload"),
        "active_numbers": ctx.get("active_numbers"),
        "active_relation": ctx.get("active_relation"),
        "active_asset_id": ctx.get("active_asset_id"),
        "pending_slots": ctx.get("pending_slots"),
        "pending_intent": ctx.get("pending_intent"),
        "has_hallazgos": bool(re.search(r"Hallazgos|Interpretaci", text)),
        "raw": r,
    }


def chk(name, ok, detail=""):
    return {"name": name, "pass": bool(ok), "detail": str(detail)[:300]}


def main():
    results = {"cases": {}, "checks": []}

    # 1) Gana Más filter with rows
    sid = new_session("rc1-gana-mas")
    t1 = send(sid, "¿Han coincidido el 50 y el 90 el mismo día?")
    t2 = send(sid, "Solo Gana Más.")
    results["cases"]["gana_mas"] = [t1, t2]
    results["checks"].append(
        chk(
            "gana_mas_filter_rows",
            t2.get("structured") == "investigation_workspace_table"
            and "0 fila" not in (t2["answer"] or "")
            and ("Gana" in t2["answer"] or "fila" in t2["answer"]),
            t2["answer"][:160],
        )
    )
    results["checks"].append(chk("gana_mas_corr", bool(t2.get("correlation_id")), t2.get("correlation_id")))

    # 2) Ahora analiza el 35
    sid = new_session("rc1-analiza-35")
    send(sid, "¿Han coincidido el 50 y el 90 el mismo día?")
    t = send(sid, "Ahora analiza el 35.")
    results["cases"]["analiza_35"] = [t]
    results["checks"].append(
        chk(
            "analiza_35_not_soft",
            "Pude mantener el contexto" not in (t["answer"] or "")
            and ("35" in (t["answer"] or "") or t.get("active_numbers") == ["35"]),
            f"nums={t.get('active_numbers')} ans={t['answer'][:160]}",
        )
    )
    results["checks"].append(
        chk("analiza_35_subjects", t.get("active_numbers") == ["35"], t.get("active_numbers"))
    )

    # 3) Pending subjects clarification
    sid = new_session("rc1-pending-subjects")
    a = send(sid, "Analiza coincidencias.")
    b = send(sid, "50 y 90.")
    results["cases"]["pending_subjects"] = [a, b]
    results["checks"].append(
        chk(
            "pending_ask",
            a.get("pending_intent") == "same_day_coincidence"
            or "?" in (a["answer"] or "")
            and "número" in (a["answer"] or "").lower(),
            a["answer"][:120],
        )
    )
    results["checks"].append(
        chk(
            "pending_match_50_90",
            (b.get("active_numbers") or [])[:2] == ["50", "90"]
            or ("50" in b["answer"] and "90" in b["answer"]),
            f"nums={b.get('active_numbers')} pending={b.get('pending_slots')} ans={b['answer'][:120]}",
        )
    )

    # 4) Pending lottery
    sid = new_session("rc1-pending-lottery")
    # Force last-occurrence clarify style: incomplete ask then number then lottery
    x = send(sid, "¿Cuándo salió?")
    y = send(sid, "54")
    # If still needs lottery:
    z = send(sid, "Gana Más.")
    results["cases"]["pending_lottery"] = [x, y, z]
    results["checks"].append(
        chk(
            "pending_lottery_not_social",
            "Con gusto" not in (z["answer"] or "") and "Excelente" not in (z["answer"] or ""),
            z["answer"][:120],
        )
    )

    # 5) Contaminated social
    sid = new_session("rc1-social-sticky")
    send(sid, "¿Han coincidido el 50 y el 90 el mismo día?")
    s1 = send(sid, "Todo bien, ¿y tú?")
    results["cases"]["social_sticky"] = [s1]
    results["checks"].append(
        chk(
            "social_no_leak",
            not s1["has_hallazgos"] and "50" not in s1["answer"] and "90" not in s1["answer"],
            s1["answer"][:100],
        )
    )

    # 6) show_dates
    sid = new_session("rc1-show-dates")
    send(sid, "¿Han coincidido el 50 y el 90 el mismo día?")
    d = send(sid, "Muéstrame las fechas.")
    results["cases"]["show_dates"] = [d]
    results["checks"].append(
        chk(
            "show_dates",
            d.get("structured") == "investigation_workspace_table" and "Fechas" in (d["answer"] or ""),
            d["answer"][:120],
        )
    )

    failed = [c for c in results["checks"] if not c["pass"]]
    results["status"] = "PASS" if not failed else "FAIL"
    results["passed"] = sum(1 for c in results["checks"] if c["pass"])
    results["failed"] = len(failed)
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": results["status"], "passed": results["passed"], "failed": results["failed"], "out": str(OUT)}, indent=2))
    for f in failed:
        print("FAIL", f)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
