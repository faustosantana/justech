#!/usr/bin/env python3
"""Autonomous Lottery Analyst conversation audit — production API only. NO code changes."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID
from xml.sax.saxutils import escape

OUT = Path("/tmp/lottery_analyst_conversation_audit_20260727.json")
USER_ID = "185d091c-0c1c-43db-b7b8-fb6b819b173a"
TENANT_ID = "8ebfa281-cd3c-4017-8e47-c572a79d84b2"
BASE = "http://127.0.0.1:8000/api/v1"


def token() -> str:
    from app.core.security import create_access_token

    return create_access_token(
        subject=USER_ID,
        tenant_id=UUID(TENANT_ID),
        role="owner",
    )


def api(method: str, path: str, body: dict | None = None, tok: str | None = None, timeout: int = 180) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok or token()}",
            "Content-Type": "application/json",
            "X-Tenant-Id": TENANT_ID,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {path}: {err[:800]}") from e


def create_session(title: str, tok: str) -> str:
    s = api("POST", "/lottery/chat/sessions", {"title": title}, tok=tok)
    return str(s["id"])


def send(session_id: str, content: str, tok: str) -> dict:
    t0 = time.perf_counter()
    try:
        resp = api(
            "POST",
            f"/lottery/chat/sessions/{session_id}/messages",
            {"content": content},
            tok=tok,
            timeout=240,
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        resp["_client_latency_ms"] = elapsed
        return resp
    except Exception as e:
        return {
            "error": str(e),
            "_client_latency_ms": int((time.perf_counter() - t0) * 1000),
            "message": {"content": f"[ERROR] {e}"},
            "active_context": {},
            "context": {},
        }


def repo_query(sql: str) -> list[dict]:
    import asyncio
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from app.config import settings

    async def _run():
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SET search_path TO jaios, public"))
                result = await conn.execute(text(sql))
                cols = list(result.keys())
                return [dict(zip(cols, row)) for row in result.fetchall()]
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def serialize_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        item = {}
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                item[k] = v.isoformat()
            else:
                item[k] = v
        out.append(item)
    return out


def _num_variants(number: str) -> list[str]:
    assert re.fullmatch(r"\d{1,2}", str(number)), number
    n = str(int(number))
    z = n.zfill(2)
    return list(dict.fromkeys([n, z, number]))


def last_n_number(number: str, limit: int = 1, lottery_ilike: str | None = None, position: int | None = None) -> list[dict]:
    variants = _num_variants(number)
    assert 1 <= limit <= 50
    in_list = ",".join("'" + v.replace("'", "") + "'" for v in variants)
    lot_clause = ""
    if lottery_ilike:
        if lottery_ilike.lower() == "nacional":
            lot_clause = " AND (l.normalized_name = 'loteria nacional' OR l.name ILIKE '%nacional%')"
        else:
            safe = lottery_ilike.replace("'", "")
            lot_clause = f" AND (l.name ILIKE '%{safe}%' OR l.normalized_name ILIKE '%{safe.lower()}%')"
    pos_clause = f" AND dn.position = {int(position)}" if position is not None else ""
    sql = f"""
    SELECT d.draw_date::text AS draw_date,
           COALESCE(d.draw_time::text,'') AS draw_time,
           l.name AS lottery,
           l.normalized_name,
           dn.position,
           COALESCE(dn.number_raw, dn.number_value) AS number
    FROM lottery_draw_numbers dn
    JOIN lottery_draws d ON d.id = dn.draw_id
    JOIN lottery_lotteries l ON l.id = d.lottery_id
    WHERE (dn.number_value IN ({in_list}) OR dn.number_raw IN ({in_list}))
      {lot_clause}
      {pos_clause}
    ORDER BY d.draw_date DESC, d.draw_time DESC NULLS LAST, dn.position ASC
    LIMIT {limit}
    """
    return serialize_rows(repo_query(sql))


def same_day_pair(a: str, b: str, lottery_ilike: str | None = None, position: int | None = None) -> list[dict]:
    av = _num_variants(a)
    bv = _num_variants(b)
    allv = ",".join("'" + v + "'" for v in dict.fromkeys(av + bv))
    a_in = ",".join("'" + v + "'" for v in av)
    b_in = ",".join("'" + v + "'" for v in bv)
    lot_clause = ""
    if lottery_ilike and lottery_ilike.lower() == "nacional":
        lot_clause = " AND (l.normalized_name = 'loteria nacional' OR l.name ILIKE '%nacional%')"
    pos_clause = f" AND dn.position = {int(position)}" if position is not None else ""
    sql = f"""
    WITH hits AS (
      SELECT d.draw_date,
             l.name AS lottery,
             l.normalized_name,
             dn.position,
             COALESCE(dn.number_raw, dn.number_value) AS number,
             d.id AS draw_id
      FROM lottery_draw_numbers dn
      JOIN lottery_draws d ON d.id = dn.draw_id
      JOIN lottery_lotteries l ON l.id = d.lottery_id
      WHERE (dn.number_value IN ({allv}) OR dn.number_raw IN ({allv}))
        {lot_clause}
        {pos_clause}
    ),
    days AS (
      SELECT draw_date
      FROM hits
      GROUP BY draw_date
      HAVING COUNT(*) FILTER (WHERE number IN ({a_in})) > 0
         AND COUNT(*) FILTER (WHERE number IN ({b_in})) > 0
    )
    SELECT h.draw_date::text AS draw_date, h.lottery, h.position, h.number
    FROM hits h
    JOIN days d ON d.draw_date = h.draw_date
    ORDER BY h.draw_date DESC, h.lottery, h.position
    LIMIT 200
    """
    return serialize_rows(repo_query(sql))


def compare_freq(n1: str, n2: str, year: int | None = None, position: int | None = None) -> dict:
    y = f" AND EXTRACT(YEAR FROM d.draw_date) = {int(year)}" if year else ""
    p = f" AND dn.position = {int(position)}" if position is not None else ""

    def one(n: str) -> dict:
        variants = _num_variants(n)
        in_list = ",".join("'" + v + "'" for v in variants)
        rows = repo_query(
            f"""
            SELECT COUNT(*)::int AS total,
                   COUNT(*) FILTER (WHERE dn.position = 1)::int AS first_pos,
                   MAX(d.draw_date)::text AS last_date
            FROM lottery_draw_numbers dn
            JOIN lottery_draws d ON d.id = dn.draw_id
            WHERE (dn.number_value IN ({in_list}) OR dn.number_raw IN ({in_list}))
              {y}{p}
            """
        )
        return serialize_rows(rows)[0] if rows else {"total": 0, "first_pos": 0, "last_date": None}

    return {n1: one(n1), n2: one(n2)}


def turn_record(block: str, turn: int, question: str, session_id: str, resp: dict, repo: Any, expected: dict) -> dict:
    msg = resp.get("message") or {}
    content = msg.get("content") if isinstance(msg, dict) else None
    return {
        "block": block,
        "turn": turn,
        "session_id": session_id,
        "request_id": resp.get("user_message_id") or (msg.get("id") if isinstance(msg, dict) else None),
        "assistant_message_id": msg.get("id") if isinstance(msg, dict) else None,
        "question": question,
        "response": content,
        "latency_ms": resp.get("latency_ms") or resp.get("_client_latency_ms"),
        "client_latency_ms": resp.get("_client_latency_ms"),
        "active_context": resp.get("active_context"),
        "context": resp.get("context"),
        "research": resp.get("research"),
        "research_trace": resp.get("research_trace"),
        "research_audit": resp.get("research_audit"),
        "suggestions": resp.get("suggestions"),
        "structured_content": msg.get("structured_content") if isinstance(msg, dict) else None,
        "tool_trace": msg.get("tool_trace") if isinstance(msg, dict) else None,
        "synthesis_fallback": resp.get("synthesis_fallback"),
        "error": resp.get("error"),
        "repo_truth": repo,
        "expected": expected,
    }


def run_block(name: str, turns: list[tuple[str, dict]], tok: str, report: dict) -> str:
    sid = create_session(f"AUDIT_{name}_{int(time.time())}", tok)
    report["conversation_ids"][name] = sid
    print(f"\n=== {name} session={sid} ===", flush=True)
    for i, (q, meta) in enumerate(turns, 1):
        print(f"  T{i}: {q[:80]}", flush=True)
        resp = send(sid, q, tok)
        repo = meta.get("repo")
        if callable(repo):
            try:
                repo = repo()
            except Exception as e:
                repo = {"repo_error": str(e)}
        rec = turn_record(name, i, q, sid, resp, repo, meta.get("expected", {}))
        report["turns"].append(rec)
        # incremental save
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        preview = (rec["response"] or "")[:160].replace("\n", " ")
        print(f"     -> {preview}", flush=True)
        time.sleep(0.4)
    return sid


def main() -> None:
    tok = token()
    report: dict[str, Any] = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoint": BASE + "/lottery/chat/sessions/{id}/messages",
        "env": "production jaios.justech.do via backend localhost",
        "image": "lottery-ia-ux-v2.4.3",
        "user": "admin@justech.do",
        "conversation_ids": {},
        "repo_baselines": {},
        "turns": [],
        "block_g_cases": {},
    }

    # --- Repository baselines ---
    print("Querying repository baselines...", flush=True)
    report["repo_baselines"] = {
        "last_22": last_n_number("22", 1),
        "last_35": last_n_number("35", 1),
        "last_97": last_n_number("97", 1),
        "last3_97": last_n_number("97", 3),
        "last5_97": last_n_number("97", 5),
        "last4_35": last_n_number("35", 4),
        "last_35_nacional_pos1": last_n_number("35", 1, lottery_ilike="nacional", position=1),
        "last3_35_nacional_pos1": last_n_number("35", 3, lottery_ilike="nacional", position=1),
        "last3_35_nacional_allpos": last_n_number("35", 3, lottery_ilike="nacional", position=None),
        "last_44": last_n_number("44", 1),
        "last4_44": last_n_number("44", 4),
        "pair_55_24_sample": same_day_pair("55", "24")[:30],
        "pair_55_24_nacional": same_day_pair("55", "24", lottery_ilike="nacional")[:30],
        "compare_54_94": compare_freq("54", "94"),
        "compare_54_94_2026": compare_freq("54", "94", year=2026),
        "compare_54_94_2026_pos1": compare_freq("54", "94", year=2026, position=1),
        "last5_54": last_n_number("54", 5),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # Block G case selection from repo
    print("Selecting Block G cases...", flush=True)
    # zero: 35 + Nacional + position that never happened? try rare pair
    zero_rows = same_day_pair("01", "99", lottery_ilike="nacional", position=1)
    # if not zero, try another
    if zero_rows:
        zero_probe = last_n_number("00", 1, lottery_ilike="nacional", position=1)
    else:
        zero_probe = []
    # number with results outside first only recently — find number that has pos>1 but check last in pos1
    outside_first = serialize_rows(
        repo_query(
            """
            SELECT dn.number_value AS number,
                   COUNT(*) FILTER (WHERE dn.position = 1) AS c1,
                   COUNT(*) FILTER (WHERE dn.position <> 1) AS c_other,
                   MAX(d.draw_date) FILTER (WHERE dn.position <> 1)::text AS last_other
            FROM lottery_draw_numbers dn
            JOIN lottery_draws d ON d.id = dn.draw_id
            WHERE dn.number_value ~ '^[0-9]{2}$'
            GROUP BY 1
            HAVING COUNT(*) FILTER (WHERE dn.position = 1) = 0
               AND COUNT(*) FILTER (WHERE dn.position <> 1) BETWEEN 1 AND 20
            ORDER BY c_other ASC
            LIMIT 5
            """
        )
    )
    small_sample = serialize_rows(
        repo_query(
            """
            SELECT dn.number_value AS number,
                   COUNT(*)::int AS total,
                   MAX(d.draw_date)::text AS last_date
            FROM lottery_draw_numbers dn
            JOIN lottery_draws d ON d.id = dn.draw_id
            JOIN lottery_lotteries l ON l.id = d.lottery_id
            WHERE (l.normalized_name = 'loteria nacional' OR l.name ILIKE '%nacional%')
              AND dn.position = 1
              AND EXTRACT(YEAR FROM d.draw_date) = 2026
            GROUP BY 1
            HAVING COUNT(*) BETWEEN 1 AND 3
            ORDER BY total ASC, number
            LIMIT 5
            """
        )
    )
    multi_lot = last_n_number("35", 10)
    report["block_g_cases"] = {
        "zero_pair_01_99_nacional_pos1_count": len(zero_rows),
        "zero_probe_00": zero_probe,
        "outside_first_only": outside_first,
        "small_sample_nacional_2026_pos1": small_sample,
        "multi_lottery_35": multi_lot,
    }

    # ========== BLOCK A ==========
    last5_97 = report["repo_baselines"]["last5_97"]
    run_block(
        "A",
        [
            ("Hola, ¿cómo estás?", {"expected": {"no_investigation": True}, "repo": None}),
            (
                "¿Cuándo fue la última vez que salió el 22?",
                {"expected": {"number": "22", "intent": "last_occurrence"}, "repo": lambda: last_n_number("22", 1)},
            ),
            (
                "¿Cuándo fue la última vez que salió el 35?",
                {"expected": {"number": "35"}, "repo": lambda: last_n_number("35", 1)},
            ),
            (
                "¿Y el 97 cuándo fue la última vez que salió?",
                {"expected": {"number": "97"}, "repo": lambda: last_n_number("97", 1)},
            ),
            (
                "¿Y las últimas 3 veces?",
                {"expected": {"number": "97", "limit": 3, "intent": "last_n_occurrences"}, "repo": lambda: last_n_number("97", 3)},
            ),
            (
                "Dame las dos anteriores a esas.",
                {
                    "expected": {"number": "97", "previous_2": True},
                    "repo": lambda: last_n_number("97", 5)[3:5] if len(last_n_number("97", 5)) >= 5 else last_n_number("97", 5),
                },
            ),
            (
                "Ahora las últimas 4 del 35.",
                {"expected": {"number": "35", "limit": 4}, "repo": lambda: last_n_number("35", 4)},
            ),
        ],
        tok,
        report,
    )

    # ========== BLOCK B ==========
    run_block(
        "B",
        [
            (
                "¿Cuándo salió por última vez el 35 en Nacional y en primera posición?",
                {
                    "expected": {"number": "35", "lottery": "nacional", "position": 1},
                    "repo": lambda: last_n_number("35", 1, lottery_ilike="nacional", position=1),
                },
            ),
            (
                "¿Y las últimas 3?",
                {
                    "expected": {"number": "35", "lottery": "nacional", "position": 1, "limit": 3},
                    "repo": lambda: last_n_number("35", 3, lottery_ilike="nacional", position=1),
                },
            ),
            (
                "Ahora en todas las posiciones.",
                {
                    "expected": {"number": "35", "lottery": "nacional", "position": None},
                    "repo": lambda: last_n_number("35", 3, lottery_ilike="nacional"),
                },
            ),
            (
                "Ahora en todas las loterías.",
                {
                    "expected": {"number": "35", "lottery": None},
                    "repo": lambda: last_n_number("35", 3),
                },
            ),
            (
                "¿Cuál fue la más reciente?",
                {"expected": {"number": "35", "limit": 1}, "repo": lambda: last_n_number("35", 1)},
            ),
        ],
        tok,
        report,
    )

    # ========== BLOCK C ==========
    run_block(
        "C",
        [
            (
                "¿Han salido el 55 y el 24 el mismo día?",
                {"expected": {"pair": ["55", "24"], "relation": "same_day"}, "repo": lambda: {"count_days": len({r['draw_date'] for r in same_day_pair('55','24')}), "sample": same_day_pair('55','24')[:20]}},
            ),
            (
                "¿Y en Nacional?",
                {"expected": {"pair": ["55", "24"], "lottery": "nacional"}, "repo": lambda: {"count_days": len({r['draw_date'] for r in same_day_pair('55','24', lottery_ilike='nacional')}), "sample": same_day_pair('55','24', lottery_ilike='nacional')[:20]}},
            ),
            (
                "¿Y en primera posición?",
                {"expected": {"pair": ["55", "24"], "lottery": "nacional", "position": 1}, "repo": lambda: {"sample": same_day_pair('55','24', lottery_ilike='nacional', position=1)[:20]}},
            ),
            (
                "Ahora vuelve a todas las posiciones.",
                {"expected": {"pair": ["55", "24"], "lottery": "nacional", "position": None}, "repo": lambda: {"sample": same_day_pair('55','24', lottery_ilike='nacional')[:20]}},
            ),
            (
                "¿Cuándo salió por última vez el 97?",
                {"expected": {"number": "97", "no_pair": True}, "repo": lambda: last_n_number("97", 1)},
            ),
            (
                "¿Y las últimas 3?",
                {"expected": {"number": "97", "limit": 3, "no_pair": True}, "repo": lambda: last_n_number("97", 3)},
            ),
        ],
        tok,
        report,
    )

    # ========== BLOCK D ==========
    run_block(
        "D",
        [
            (
                "Compara el 54 con el 94 en todo el histórico.",
                {"expected": {"numbers": ["54", "94"]}, "repo": lambda: compare_freq("54", "94")},
            ),
            (
                "¿Y solo en 2026?",
                {"expected": {"numbers": ["54", "94"], "year": 2026}, "repo": lambda: compare_freq("54", "94", year=2026)},
            ),
            (
                "Ahora solo en primera posición.",
                {"expected": {"numbers": ["54", "94"], "year": 2026, "position": 1}, "repo": lambda: compare_freq("54", "94", year=2026, position=1)},
            ),
            (
                "¿Cuál de los dos salió más recientemente?",
                {"expected": {"compare_last": True}, "repo": lambda: compare_freq("54", "94", year=2026, position=1)},
            ),
        ],
        tok,
        report,
    )

    # ========== BLOCK E ==========
    run_block(
        "E",
        [
            (
                "Busca las últimas 5 apariciones del 54.",
                {"expected": {"number": "54", "limit": 5}, "repo": lambda: last_n_number("54", 5)},
            ),
            (
                "¿Qué pasó en los tres días siguientes a cada una?",
                {"expected": {"after_window": True, "base": "54"}, "repo": None},
            ),
            (
                "¿Y en la misma lotería solamente?",
                {"expected": {"same_lottery": True}, "repo": None},
            ),
            (
                "Ahora compáralo con cualquier lotería.",
                {"expected": {"compare_scopes": True}, "repo": None},
            ),
        ],
        tok,
        report,
    )

    # ========== BLOCK F ==========
    run_block(
        "F",
        [
            ("¿Cuándo salió?", {"expected": {"clarify_number_only": True}, "repo": None}),
            (
                "El 44.",
                {"expected": {"number": "44", "complete_pending": True}, "repo": lambda: last_n_number("44", 1)},
            ),
            (
                "¿Y las otras tres?",
                {"expected": {"number": "44", "additional": 3}, "repo": lambda: last_n_number("44", 4)},
            ),
        ],
        tok,
        report,
    )

    # ========== BLOCK G ==========
    g_num_outside = (outside_first[0]["number"] if outside_first else "88")
    g_small = (small_sample[0]["number"] if small_sample else "54")
    g_turns = [
        (
            "¿Han salido el 01 y el 99 el mismo día en Nacional y en primera posición?",
            {
                "expected": {"zero_or_rare": True},
                "repo": lambda: {"rows": same_day_pair("01", "99", lottery_ilike="nacional", position=1)},
            },
        ),
        (
            f"¿Cuándo salió por última vez el {g_num_outside} en primera posición?",
            {
                "expected": {"outside_first_probe": g_num_outside},
                "repo": lambda: {
                    "pos1": last_n_number(str(int(g_num_outside)), 3, position=1) if str(g_num_outside).isdigit() else [],
                    "any": last_n_number(str(int(g_num_outside)) if str(g_num_outside).lstrip("0") or "0" else g_num_outside, 5),
                },
            },
        ),
        (
            f"¿Cuántas veces salió el {g_small} en Nacional en primera posición en 2026?",
            {
                "expected": {"small_sample": g_small},
                "repo": lambda: compare_freq(str(int(g_small)), str(int(g_small)), year=2026, position=1)
                if False
                else {
                    "rows": last_n_number(str(int(g_small)), 10, lottery_ilike="nacional", position=1),
                    "note": "filter year in evaluation",
                },
            },
        ),
        (
            "¿Cuándo salió por última vez el 35?",
            {"expected": {"multi_lottery": "35"}, "repo": lambda: last_n_number("35", 5)},
        ),
    ]
    # fix g_num for last_n - ensure 2 digit
    def _norm(n: str) -> str:
        n = str(n).strip()
        if n.isdigit():
            return str(int(n)) if int(n) < 10 else n.zfill(2) if len(n) == 1 else n
        return n

    g_num_outside = _norm(g_num_outside)
    g_small = _norm(g_small)
    g_turns[1] = (
        f"¿Cuándo salió por última vez el {g_num_outside} en primera posición?",
        {
            "expected": {"outside_first_probe": g_num_outside},
            "repo": lambda n=g_num_outside: {
                "pos1": last_n_number(n, 3, position=1),
                "any": last_n_number(n, 5),
            },
        },
    )
    g_turns[2] = (
        f"¿Cuántas veces salió el {g_small} en Nacional en primera posición en 2026?",
        {
            "expected": {"small_sample": g_small},
            "repo": lambda n=g_small: {
                "all_nacional_pos1": last_n_number(n, 50, lottery_ilike="nacional", position=1),
            },
        },
    )
    report["block_g_cases"]["chosen_outside_first"] = g_num_outside
    report["block_g_cases"]["chosen_small"] = g_small
    run_block("G", g_turns, tok, report)

    # ========== BLOCK H ==========
    # New conversation with a seed factual turn then naturality probes
    h_turns = [
        (
            "¿Cuándo fue la última vez que salió el 22?",
            {"expected": {"seed": True}, "repo": lambda: last_n_number("22", 1)},
        ),
        ("Gracias.", {"expected": {"natural": True}, "repo": None}),
        ("Perfecto.", {"expected": {"natural": True}, "repo": None}),
        ("No, me refiero al 97.", {"expected": {"correct_to_97": True}, "repo": lambda: last_n_number("97", 1)}),
        ("Eso no fue lo que pregunté.", {"expected": {"acknowledge": True}, "repo": None}),
        ("Revísalo otra vez.", {"expected": {"reverify_97": True}, "repo": lambda: last_n_number("97", 1)}),
        ("¿Estás seguro?", {"expected": {"confirm": True}, "repo": lambda: last_n_number("97", 1)}),
        ("Explícamelo más simple.", {"expected": {"simplify": True}, "repo": None}),
        ("Dame solo la respuesta.", {"expected": {"brief": True}, "repo": None}),
        ("Hazme un análisis más profundo.", {"expected": {"deeper": True}, "repo": None}),
        ("¿Qué te llama la atención de eso?", {"expected": {"interpret": True}, "repo": None}),
    ]
    run_block("H", h_turns, tok, report)

    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report["total_turns"] = len(report["turns"])
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nDONE turns={report['total_turns']} -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
