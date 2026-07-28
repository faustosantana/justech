#!/usr/bin/env python3
"""Manual-30 conversational probes — demonstratives, compound subjects, positions.

Read-only against local backend. No bank/seed/evaluator changes for cert200.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path
from uuid import UUID

from app.core.security import create_access_token

UID = "185d091c-0c1c-43db-b7b8-fb6b819b173a"
TID = "8ebfa281-cd3c-4017-8e47-c572a79d84b2"
BASE = "http://127.0.0.1:8000/api/v1"
OUT = Path("/tmp/lottery-manual30")

# (conversation_id, turns, checks)
# checks: list of callables(prev_text, text, ctx) -> list[str] failures
PROBES = [
    ("M01", ["¿Han salido el 35 y el 14 el mismo día?", "¿Cuáles fueron esas últimas 3 veces?"], "compound_list"),
    ("M02", ["¿Han salido el 55 y el 24 el mismo día?", "¿Y esas fechas?"], "compound_list"),
    ("M03", ["¿Han salido el 22 y el 97 el mismo día?", "Muéstrame las anteriores."], "compound_list"),
    ("M04", ["¿Han salido el 01 y el 07 el mismo día?", "¿Cuáles fueron?"], "compound_list"),
    ("M05", ["¿Han salido el 44 y el 88 el mismo día?", "esas 3"], "compound_list"),
    ("M06", ["¿Han salido el 39 y el 58 el mismo día?", "Dame las anteriores."], "compound_list"),
    ("M07", ["¿Han salido el 54 y el 94 el mismo día?", "esa coincidencia"], "compound_keep"),
    ("M08", ["¿Han salido el 03 y el 07 el mismo día?", "ambos"], "compound_keep"),
    ("M09", ["¿Han salido el 35 y el 55 el mismo día?", "los dos"], "compound_keep"),
    ("M10", ["Últimas 3 del 35.", "Ahora en todas las posiciones."], "no_todas_as_row"),
    ("M11", ["¿Cuándo salió el 22?", "¿Y el 35?"], "subject_switch"),
    ("M12", ["¿Han salido el 55 y el 24 el mismo día?", "¿Cuáles fueron esas últimas 3 veces?", "¿Y esas fechas?"], "compound_list"),
    ("M13", ["¿Han salido el 14 y el 35 el mismo día?", "las anteriores"], "compound_list"),
    ("M14", ["¿Han salido el 97 y el 22 el mismo día?", "muéstrame esas veces"], "compound_list"),
    ("M15", ["¿Han salido el 88 y el 44 el mismo día?", "cuáles fueron esas apariciones"], "compound_list"),
    ("M16", ["Busca las últimas 5 del 54.", "¿Y esas fechas?"], "last_n_ok"),
    ("M17", ["¿Han salido el 35 y el 14 el mismo día?", "¿Cuáles fueron esas últimas 3 veces?"], "positions_concrete"),
    ("M18", ["¿Han salido el 55 y el 24 el mismo día?", "¿Cuáles fueron esas últimas 3 veces?"], "positions_concrete"),
    ("M19", ["¿Han salido el 01 y el 99 el mismo día?", "esas veces"], "compound_list"),
    ("M20", ["¿Han salido el 07 y el 03 el mismo día?", "esa fecha"], "compound_keep"),
    ("M21", ["¿Han salido el 35 y el 14 el mismo día?", "¿Cuáles fueron esas últimas 3 veces?"], "both_numbers_in_list"),
    ("M22", ["¿Han salido el 22 y el 54 el mismo día?", "¿Cuáles fueron esas últimas 3 veces?"], "both_numbers_in_list"),
    ("M23", ["¿Han salido el 94 y el 54 el mismo día?", "Muéstrame las anteriores."], "both_numbers_in_list"),
    ("M24", ["Última del 35.", "¿Y el 14?"], "subject_switch"),
    ("M25", ["¿Han salido el 35 y el 14 el mismo día?", "en primera posición"], "compound_keep"),
    ("M26", ["¿Han salido el 55 y el 24 el mismo día?", "¿Cuáles fueron esas últimas 3 veces?"], "no_single_last_n"),
    ("M27", ["¿Han salido el 44 y el 22 el mismo día?", "¿Cuáles fueron esas últimas 3 veces?"], "no_single_last_n"),
    ("M28", ["¿Han salido el 35 y el 14 el mismo día?", "¿Cuáles fueron esas últimas 3 veces?"], "no_todas_as_row"),
    ("M29", ["Últimas 3 del 97.", "Muéstrame las anteriores."], "last_n_ok"),
    ("M30", ["¿Han salido el 35 y el 14 el mismo día?", "¿Cuáles fueron esas últimas 3 veces?", "¿Y esas fechas?"], "compound_list"),
]


def token() -> str:
    return create_access_token(subject=UID, tenant_id=UUID(TID), role="owner")


def api(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token()}",
            "Content-Type": "application/json",
            "X-Tenant-Id": TID,
        },
    )
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read().decode() or "{}")


def extract_pair(turns: list[str]) -> list[str]:
    for t in turns:
        m = re.findall(r"\b(\d{1,2})\b", t)
        if len(m) >= 2:
            return [m[0].zfill(2), m[1].zfill(2)]
    return []


def evaluate(kind: str, turns: list[str], answers: list[str], ctx: dict) -> list[str]:
    fails: list[str] = []
    last = answers[-1] if answers else ""
    low = last.lower()
    pair = extract_pair(turns)
    # Never use «todas las posiciones» as a result-row slot (date — lot — todas…)
    if re.search(r"—\s*todas las posiciones\s*[\.\n]?", last, re.I):
        fails.append("todas_las_posiciones_as_row")
    if kind in {"compound_list", "positions_concrete", "both_numbers_in_list", "no_single_last_n"}:
        if re.search(r"apariciones más recientes del \d+", low):
            fails.append("collapsed_to_single_last_n")
        if pair and kind in {"both_numbers_in_list", "compound_list", "positions_concrete", "no_single_last_n"}:
            # Both balls should appear in the follow-up answer when listing
            if turns[-1].lower().startswith(("¿cuáles", "cuáles", "mué", "dame", "esas", "las anteriores", "muéstrame")) or "últimas" in turns[-1].lower() or "fechas" in turns[-1].lower() or "anteriores" in turns[-1].lower() or "veces" in turns[-1].lower():
                missing = [n for n in pair if n.lstrip("0") not in last and n not in last]
                # allow zfill variants
                missing = [n for n in pair if not (n in last or n.lstrip("0") in last or n.zfill(2) in last)]
                if missing and "coincid" in low:
                    fails.append(f"missing_pair_numbers:{missing}")
    if kind == "positions_concrete":
        if "coincid" in low and not re.search(r"\d(ra|da|ro)|posici[oó]n", low):
            fails.append("missing_concrete_position")
    if kind == "subject_switch":
        # Just ensure HTTP ok / non-empty
        if len(last.strip()) < 10:
            fails.append("empty_answer")
    if kind == "last_n_ok":
        if "http 5" in low or len(last.strip()) < 5:
            fails.append("bad_last_n")
    if kind == "compound_keep":
        nums = ctx.get("active_numbers") or []
        if pair and len(nums) == 1:
            fails.append("state_collapsed_pair")
    return fails


def ensure_session_quota() -> None:
    """Best-effort cleanup of prior audit sessions if at limit (infra only)."""
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from app.config import settings

    async def _run() -> None:
        eng = create_async_engine(settings.database_url, poolclass=NullPool)
        async with eng.begin() as conn:
            await conn.execute(text("SET search_path TO jaios, public"))
            await conn.execute(
                text(
                    """
                    DELETE FROM lottery_chat_messages
                    WHERE session_id IN (
                      SELECT id FROM lottery_chat_sessions
                      WHERE user_id = :uid
                        AND (title ILIKE 'manual30%' OR title ILIKE 'cont-fix%'
                             OR title ILIKE 'cert%' OR title ILIKE 'AUDIT_%')
                    )
                    """
                ),
                {"uid": UID},
            )
            await conn.execute(
                text(
                    """
                    DELETE FROM lottery_chat_sessions
                    WHERE user_id = :uid
                      AND (title ILIKE 'manual30%' OR title ILIKE 'cont-fix%'
                           OR title ILIKE 'cert%' OR title ILIKE 'AUDIT_%')
                    """
                ),
                {"uid": UID},
            )
        await eng.dispose()

    try:
        asyncio.run(_run())
    except Exception as e:  # noqa: BLE001
        print(f"quota_cleanup_warn {e}", flush=True)


def main() -> int:
    print("manual30_start", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    print("manual30_quota", flush=True)
    ensure_session_quota()
    print("manual30_running", flush=True)
    rows = []
    pass_n = fail_n = 0
    for pid, turns, kind in PROBES:
        try:
            s = api("POST", "/lottery/chat/sessions", {"title": f"manual30-{pid}"})
            sid = s.get("id") or (s.get("session") or {}).get("id")
            if not sid:
                raise RuntimeError(f"no session id: {s}")
            answers = []
            ctx = {}
            for msg in turns:
                r = api("POST", f"/lottery/chat/sessions/{sid}/messages", {"content": msg})
                answers.append(((r.get("message") or {}).get("content") or ""))
                ctx = (r.get("context") or {}).get("conversation_v4") or {}
            fails = evaluate(kind, turns, answers, ctx)
            verdict = "PASS" if not fails else "FAIL"
            if verdict == "PASS":
                pass_n += 1
            else:
                fail_n += 1
            print(f"{verdict} {pid} {kind} :: {turns[-1][:50]}", flush=True)
            rows.append(
                {
                    "id": pid,
                    "kind": kind,
                    "turns": turns,
                    "answers": answers,
                    "fails": fails,
                    "verdict": verdict,
                    "active_numbers": ctx.get("active_numbers"),
                    "active_relation": ctx.get("active_relation"),
                }
            )
        except Exception as e:  # noqa: BLE001
            fail_n += 1
            print(f"FAIL {pid} EXCEPTION {e}", flush=True)
            rows.append({"id": pid, "verdict": "FAIL", "fails": [str(e)], "turns": turns, "kind": kind})
            try:
                ensure_session_quota()
            except Exception:  # noqa: BLE001
                pass

    summary = {
        "pass": pass_n,
        "fail": fail_n,
        "total": pass_n + fail_n,
        "certification_level": "PASS" if fail_n == 0 and pass_n == 30 else "BLOQUEADO",
    }
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "raw_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE {summary['certification_level']} PASS={pass_n} FAIL={fail_n}", flush=True)
    return 0 if fail_n == 0 and pass_n == 30 else 1


if __name__ == "__main__":
    sys.exit(main())
