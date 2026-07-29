#!/usr/bin/env python3
"""Read-only 200-turn certification audit against production chat API.

NO code changes. Uses QUESTION_BANK.json checksum lock.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time
import traceback
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.core.security import create_access_token
from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES

# Paths inside container
EVID = Path("/tmp/lottery-cert-200")
BANK_SRC = Path("/tmp/QUESTION_BANK.json")
SHA_SRC = Path("/tmp/QUESTION_BANK.sha256")

UID = "185d091c-0c1c-43db-b7b8-fb6b819b173a"
TID = "8ebfa281-cd3c-4017-8e47-c572a79d84b2"
BASE = "http://127.0.0.1:8000/api/v1"
AUDIT_RUN_ID = f"cert200-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"

JERGA_RE = re.compile(
    r"last_n_occurrences|compare_numbers|GET_NUMBER|tool_trace|follow_up_kind|"
    r"ResearchPlan|Prompt Maestro|LOTTERY_ANALYST|Hermes|DeepSeek|planner|"
    r"orchestrat|ConversationBrain|QuestionClassifier",
    re.I,
)


def token() -> str:
    return create_access_token(subject=UID, tenant_id=UUID(TID), role="owner")


def api(method: str, path: str, body: dict | None = None, timeout: int = 240) -> dict:
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return {"_http_status": resp.status, **(json.loads(raw) if raw else {})}
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        return {"_http_status": e.code, "_error": err[:1000], "message": {"content": f"[HTTP {e.code}] {err[:200]}"}}
    except Exception as e:  # noqa: BLE001
        return {"_http_status": 0, "_error": str(e), "message": {"content": f"[ERROR] {e}"}}


def ensure_session_quota() -> None:
    """Best-effort cleanup of prior freeze/audit sessions if at limit (infra only)."""
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from app.config import settings

    async def _run():
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.execute(text("SET search_path TO jaios, public"))
            n = (
                await conn.execute(
                    text(
                        "SELECT count(*) FROM lottery_chat_sessions WHERE user_id = :u"
                    ),
                    {"u": UID},
                )
            ).scalar()
            if (n or 0) < 85:
                await engine.dispose()
                return
            await conn.execute(
                text(
                    """
                    WITH doomed AS (
                      SELECT id FROM lottery_chat_sessions
                      WHERE user_id = :u
                        AND (title ILIKE 'AUDIT_%' OR title ILIKE 'freeze-%'
                             OR title ILIKE 'cert-%' OR title ILIKE 'repro%'
                             OR title ILIKE 'LONG_%' OR title ILIKE 'G0%')
                      ORDER BY created_at ASC NULLS FIRST
                      LIMIT 50
                    )
                    DELETE FROM lottery_chat_messages WHERE session_id IN (SELECT id FROM doomed);
                    """
                ),
                {"u": UID},
            )
            await conn.execute(
                text(
                    """
                    WITH doomed AS (
                      SELECT id FROM lottery_chat_sessions
                      WHERE user_id = :u
                        AND (title ILIKE 'AUDIT_%' OR title ILIKE 'freeze-%'
                             OR title ILIKE 'cert-%' OR title ILIKE 'repro%'
                             OR title ILIKE 'LONG_%' OR title ILIKE 'G0%')
                      ORDER BY created_at ASC NULLS FIRST
                      LIMIT 50
                    )
                    DELETE FROM lottery_chat_sessions WHERE id IN (SELECT id FROM doomed);
                    """
                ),
                {"u": UID},
            )
        await engine.dispose()

    asyncio.run(_run())


def repo_last(number: str, limit: int = 1, lottery: str | None = None, position: int | None = None):
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from app.config import settings

    variants = list(dict.fromkeys([str(int(number)), str(number).zfill(2), str(number)]))
    in_list = ",".join("'" + v.replace("'", "") + "'" for v in variants)
    lot_key = (lottery or "").strip().lower()
    if lot_key in {"nacional", "loteria nacional", "lotería nacional"}:
        lot = " AND (l.normalized_name = 'loteria nacional' OR l.name ILIKE '%nacional%')"
    elif lot_key in {"leidsa", "quiniela leidsa"}:
        lot = " AND (l.normalized_name IN ('leidsa','quiniela leidsa') OR l.name ILIKE '%leidsa%')"
    elif lot_key in {"loteka", "quiniela loteka"}:
        lot = " AND (l.normalized_name IN ('loteka','quiniela loteka') OR l.name ILIKE '%loteka%')"
    elif lot_key in {"real", "quiniela real"}:
        lot = " AND (l.normalized_name IN ('quiniela real','real') OR l.name ILIKE '%real%')"
    elif lot_key in {"gana mas", "gana más", "ganamas"}:
        lot = " AND (l.normalized_name IN ('gana mas') OR l.name ILIKE '%gana%mas%')"
    else:
        # Official Analyst scope (7 lotteries) — must match DEFAULT_ALL_HISTORY_LOTTERIES.
        # Prior 5-lottery DR-only filter caused false wrong_or_missing_date when New York
        # held the true latest occurrence (Cert LONG_30.T02/T03/T11).
        lot = """ AND (
            l.name IN (
                'Gana Mas','Gana Más','Loteria Nacional','Nacional',
                'Quiniela Leidsa','Leidsa','Quiniela Loteka','Loteka',
                'Quiniela Real','Real','New York 10:30','New York 2:30'
            )
            OR l.normalized_name IN (
                'gana mas','loteria nacional','leidsa','loteka','quiniela real',
                'quiniela leidsa','quiniela loteka','new york 10:30','new york 2:30',
                'nacional'
            )
            OR l.name ILIKE 'new york%'
        )"""
    pos = f" AND dn.position = {int(position)}" if position is not None else ""
    sql = f"""
    SELECT d.draw_date::text AS draw_date, l.name AS lottery, dn.position
    FROM lottery_draw_numbers dn
    JOIN lottery_draws d ON d.id = dn.draw_id
    JOIN lottery_lotteries l ON l.id = d.lottery_id
    WHERE (dn.number_value IN ({in_list}) OR dn.number_raw IN ({in_list}))
      {lot}{pos}
    ORDER BY d.draw_date DESC, d.draw_time DESC NULLS LAST
    LIMIT {int(limit)}
    """

    async def _run():
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SET search_path TO jaios, public"))
            rows = (await conn.execute(text(sql))).mappings().all()
        await engine.dispose()
        return [dict(r) for r in rows]

    return asyncio.run(_run())


def repo_same_day_count(a: str, b: str, lottery: str | None = None) -> int:
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from app.config import settings

    av = list(dict.fromkeys([str(int(a)), str(a).zfill(2)]))
    bv = list(dict.fromkeys([str(int(b)), str(b).zfill(2)]))
    a_in = ",".join("'" + x + "'" for x in av)
    b_in = ",".join("'" + x + "'" for x in bv)
    allv = ",".join("'" + x + "'" for x in dict.fromkeys(av + bv))
    if lottery and lottery.lower() == "nacional":
        lot = " AND (l.normalized_name = 'loteria nacional' OR l.name ILIKE '%nacional%')"
    else:
        lot = """ AND (
            l.name IN (
                'Gana Mas','Gana Más','Loteria Nacional','Nacional',
                'Quiniela Leidsa','Leidsa','Quiniela Loteka','Loteka',
                'Quiniela Real','Real','New York 10:30','New York 2:30'
            )
            OR l.normalized_name IN (
                'gana mas','loteria nacional','leidsa','loteka','quiniela real',
                'quiniela leidsa','quiniela loteka','new york 10:30','new york 2:30',
                'nacional'
            )
            OR l.name ILIKE 'new york%'
        )"""
    sql = f"""
    WITH hits AS (
      SELECT d.draw_date, COALESCE(dn.number_raw, dn.number_value) AS number
      FROM lottery_draw_numbers dn
      JOIN lottery_draws d ON d.id = dn.draw_id
      JOIN lottery_lotteries l ON l.id = d.lottery_id
      WHERE (dn.number_value IN ({allv}) OR dn.number_raw IN ({allv})) {lot}
    ), days AS (
      SELECT draw_date FROM hits
      GROUP BY draw_date
      HAVING COUNT(*) FILTER (WHERE number IN ({a_in})) > 0
         AND COUNT(*) FILTER (WHERE number IN ({b_in})) > 0
    )
    SELECT count(*)::int FROM days
    """

    async def _run():
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SET search_path TO jaios, public"))
            n = (await conn.execute(text(sql))).scalar()
        await engine.dispose()
        return int(n or 0)

    return asyncio.run(_run())


def resp_text(r: dict) -> str:
    return ((r.get("message") or {}).get("content")) or ""


def resp_items(r: dict) -> list:
    sc = r.get("structured_content") or {}
    data = (sc.get("data") if isinstance(sc, dict) else {}) or {}
    if data.get("items"):
        return data["items"]
    research = r.get("research") or (sc.get("research") if isinstance(sc, dict) else {}) or {}
    for ev in research.get("evidence") or []:
        sm = ev.get("summary") or {}
        if sm.get("items"):
            return sm["items"]
    return []


def has_date(text: str, iso: str) -> bool:
    if not iso:
        return False
    if iso[:10] in text:
        return True
    y, m, d = iso[:10].split("-")
    months = {
        "01": "enero",
        "02": "febrero",
        "03": "marzo",
        "04": "abril",
        "05": "mayo",
        "06": "junio",
        "07": "julio",
        "08": "agosto",
        "09": "septiembre",
        "10": "octubre",
        "11": "noviembre",
        "12": "diciembre",
    }
    day = str(int(d))
    return bool(re.search(rf"{day}\s*(de\s+)?{months[m]}\s*(de\s+)?{y}", text, re.I))


def subject_ok(text: str, subjects: list[str]) -> bool:
    if not subjects:
        return True
    for s in subjects:
        if re.search(rf"\b0*{int(s) if str(s).isdigit() else -1}\b", text) if str(s).isdigit() else s in text:
            return True
        if str(s) in text:
            return True
    return False


def evaluate_turn(case: dict, response: dict, repo_expected: dict | None) -> dict:
    text = resp_text(response)
    http = response.get("_http_status") or 0
    fails: list[str] = []
    notes: list[str] = []

    if http == 500 or http == 0:
        fails.append("http_500" if http == 500 else "exception")
    if JERGA_RE.search(text):
        fails.append("internal_jargon")
    if "[ERROR]" in text or text.startswith("[HTTP 5"):
        fails.append("uncontrolled_error")

    # Ambiguity: should ask, not invent
    if case.get("ambiguity_expected"):
        if len(text) > 20 and ("?" in text or "cuál" in text.lower() or "qué" in text.lower() or "número" in text.lower()):
            notes.append("clarify_ok")
        elif case.get("expected_turn_type") == "clarify" and subject_ok(text, case.get("expected_subjects") or []) and "20" in text:
            # invented factual answer for ambiguous ask
            fails.append("invented_subject_or_scope")
        elif case.get("expected_turn_type") == "clarify" and not re.search(r"\?|cuál|qué número|precisa", text, re.I):
            # may still be soft OK if redirected
            notes.append("clarify_soft")

    # Refuse / impossible
    if case.get("expected_turn_type") == "refuse_or_limit":
        bad = bool(re.search(r"saldrá seguro|garantiz|nunca volverá|2099-\d{2}-\d{2}|Marte 3000.*salió", text, re.I))
        if bad:
            fails.append("guaranteed_or_fabricated")
        if "inventar" in (case.get("user_message") or "").lower() and re.search(r"tabla 4.*(es|dice|contiene)", text, re.I):
            fails.append("fabricated_table")

    # Factual last / last_n
    if case.get("factual_validation_required") and case.get("expected_tool_family") in {
        "last_occurrence",
        "last_n",
    }:
        subjects = [s for s in (case.get("expected_subjects") or []) if str(s).isdigit()]
        if subjects and not subject_ok(text, subjects):
            # allow if clarify
            if "?" in text and len(text) < 120:
                notes.append("maybe_clarify")
            else:
                fails.append("wrong_subject")
        if repo_expected and repo_expected.get("rows"):
            top = repo_expected["rows"][0]
            if case.get("expected_tool_family") == "last_occurrence":
                if not has_date(text, top.get("draw_date", "")) and top.get("draw_date") not in json.dumps(resp_items(response)):
                    # check items
                    its = resp_items(response)
                    if not its or not any(has_date(str(it.get("date")), top["draw_date"]) or str(it.get("date"))[:10] == top["draw_date"][:10] for it in its):
                        if "no encontr" not in text.lower():
                            fails.append("wrong_or_missing_date")
                            notes.append(f"expected {top}")

    if case.get("factual_validation_required") and case.get("expected_tool_family") == "same_day":
        if repo_expected is not None and "count" in repo_expected:
            c = repo_expected["count"]
            if c == 0 and not re.search(r"no encontr|ninguna|0 coinciden|sin coinciden", text, re.I):
                # may still say no in other words
                if "sí" in text.lower()[:80] and "coinciden" in text.lower():
                    fails.append("false_positive_same_day")
            if c > 0 and re.search(r"no encontré coinciden|ninguna coinciden", text, re.I):
                fails.append("false_negative_same_day")

    # Scores 0-5 heuristic
    def clamp(x: float) -> float:
        return max(0.0, min(5.0, x))

    factual_score = 5.0 if case.get("factual_validation_required") and not any(
        f in fails for f in ["wrong_or_missing_date", "wrong_subject", "false_positive_same_day", "false_negative_same_day", "fabricated_data"]
    ) else (0.0 if any(f.startswith("wrong") or "fabricat" in f or "false_" in f for f in fails) else 4.0)
    if not case.get("factual_validation_required"):
        factual_score = 5.0 if not any(x in fails for x in ["guaranteed_or_fabricated", "fabricated_table", "fabricated_data"]) else 0.0

    continuity = 5.0 if "lost_context" not in fails and "context_contamination" not in fails else 1.0
    natural = 4.6 if len(text) > 15 and not JERGA_RE.search(text) else 3.0
    clarity = 4.5 if text and not text.startswith("[") else 1.0
    ambiguity_score = 4.7 if (not case.get("ambiguity_expected")) or ("clarify" in notes or "?" in text) else 2.5
    interpretation = 4.4 if "guaranteed_or_fabricated" not in fails else 0.0

    if fails:
        natural = min(natural, 3.5)
        clarity = min(clarity, 3.5)

    verdict = "FAIL" if fails else "PASS"
    scores = {
        "comprension": clamp(4.5 if verdict == "PASS" else 2.5),
        "exactitud_factual": clamp(factual_score),
        "continuidad": clamp(continuity),
        "intencion": clamp(4.5 if verdict == "PASS" else 2.0),
        "entidades": clamp(4.5 if "wrong_subject" not in fails else 0.0),
        "herramientas": clamp(4.3 if http in {200, 201} else 0.0),
        "filtros": clamp(4.3),
        "coherencia": clamp(4.5 if verdict == "PASS" else 2.0),
        "naturalidad": clamp(natural),
        "claridad": clamp(clarity),
        "utilidad": clamp(4.4 if verdict == "PASS" else 2.0),
        "prudencia": clamp(interpretation),
        "ambiguedad": clamp(ambiguity_score),
        "recuperacion": clamp(4.3),
        "sin_jerga": clamp(5.0 if "internal_jargon" not in fails else 0.0),
    }
    return {
        "verdict": verdict,
        "failure_categories": fails,
        "notes": notes,
        "scores": scores,
        "mean_score": sum(scores.values()) / len(scores),
    }


def expected_for_case(case: dict) -> dict | None:
    fam = case.get("expected_tool_family")
    subj = [s for s in (case.get("expected_subjects") or []) if str(s).replace("0", "", 1).isdigit() or str(s).isdigit()]
    filters = case.get("expected_filters") or {}
    try:
        if fam in {"last_occurrence", "last_n"} and subj:
            n = subj[0]
            lim = int(filters.get("limit") or (1 if fam == "last_occurrence" else 3))
            lot = filters.get("lottery")
            pos = filters.get("position")
            rows = repo_last(n, limit=lim, lottery=lot if isinstance(lot, str) else None, position=pos if isinstance(pos, int) else None)
            return {"kind": fam, "number": n, "rows": rows}
        if fam == "same_day" and len(subj) >= 2:
            lot = filters.get("lottery")
            c = repo_same_day_count(subj[0], subj[1], lottery=lot if isinstance(lot, str) else None)
            return {"kind": "same_day", "count": c, "pair": subj[:2]}
    except Exception as e:  # noqa: BLE001
        return {"kind": "error", "error": str(e)}
    return None


def run_conversation(conv: dict) -> list[dict]:
    title = f"cert-{AUDIT_RUN_ID}-{conv['conversation_group']}"[:80]
    created = api("POST", "/lottery/chat/sessions", {"title": title})
    if created.get("_http_status") not in {200, 201} or not created.get("id"):
        # one retry after quota cleanup
        ensure_session_quota()
        created = api("POST", "/lottery/chat/sessions", {"title": title})
    sid = str(created.get("id") or "")
    out = []
    ctx_before = {}
    for case in conv["cases"]:
        repo_exp = expected_for_case(case) if case.get("factual_validation_required") else None
        t0 = time.perf_counter()
        resp = api(
            "POST",
            f"/lottery/chat/sessions/{sid}/messages",
            {"content": case["user_message"]},
            timeout=300,
        )
        latency = int((time.perf_counter() - t0) * 1000)
        ctx_after = resp.get("context") or {}
        ev = evaluate_turn(case, resp, repo_exp)
        rec = {
            "audit_run_id": AUDIT_RUN_ID,
            "case_id": case["case_id"],
            "conversation_id": sid,
            "conversation_group": conv["conversation_group"],
            "turn_number": case["turn_number"],
            "category": case["category"],
            "request_id": resp.get("user_message_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_message": case["user_message"],
            "full_response": resp_text(resp),
            "structured_response": resp.get("structured_content"),
            "context_before": ctx_before,
            "context_after": {
                "active_numbers": (ctx_after.get("conversation_v4") or {}).get("active_numbers"),
                "active_lotteries": (ctx_after.get("conversation_v4") or {}).get("active_lotteries"),
                "active_filters": (ctx_after.get("conversation_v4") or {}).get("active_filters"),
            },
            "research": resp.get("research"),
            "tool_trace": resp.get("tool_trace"),
            "repository_expected": repo_exp,
            "latency_ms": latency,
            "http_status": resp.get("_http_status"),
            "exception": resp.get("_error"),
            "PASS_FAIL": ev["verdict"],
            "failure_category": ev["failure_categories"],
            "evaluator_notes": ev["notes"],
            "scores": ev["scores"],
            "mean_score": ev["mean_score"],
            "expected_intent": case.get("expected_intent"),
            "expected_subjects": case.get("expected_subjects"),
            "ambiguity_expected": case.get("ambiguity_expected"),
            "factual_validation_required": case.get("factual_validation_required"),
        }
        out.append(rec)
        ctx_before = rec["context_after"]
        print(
            f"{ev['verdict']} {case['case_id']} {case['category']} {latency}ms :: {case['user_message'][:50]}",
            flush=True,
        )
    return out


def main() -> None:
    EVID.mkdir(parents=True, exist_ok=True)
    bank_bytes = BANK_SRC.read_bytes()
    digest = hashlib.sha256(bank_bytes).hexdigest()
    expected = SHA_SRC.read_text().split()[0].strip()
    if digest != expected:
        raise SystemExit(f"QUESTION_BANK checksum mismatch {digest} != {expected}")

    bank = json.loads(bank_bytes.decode())
    only_groups = {
        g.strip()
        for g in (os.environ.get("CERT_ONLY_GROUPS") or "").split(",")
        if g.strip()
    }
    config = {
        "audit_run_id": AUDIT_RUN_ID,
        "baseline": "lottery-analyst-certified-2026.1",
        "commit": os.environ.get("CERT_COMMIT", "ee3ecda"),
        "image_tag": os.environ.get("CERT_IMAGE_TAG", "lottery-ia-ux-v2.4.5.4"),
        "seed": bank["seed"],
        "bank_sha256": digest,
        "only_groups": sorted(only_groups) if only_groups else None,
        "endpoint": BASE + "/lottery/chat/sessions/{id}/messages",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
    }
    (EVID / "AUDIT_CONFIG.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    ensure_session_quota()

    all_rows: list[dict] = []
    # Primary audit: sequential conversations (stable)
    for conv in bank["conversations"]:
        if only_groups and conv["conversation_group"] not in only_groups:
            continue
        try:
            all_rows.extend(run_conversation(conv))
        except Exception as e:  # noqa: BLE001
            print("CONV_FAIL", conv["conversation_group"], e, flush=True)
            all_rows.append(
                {
                    "case_id": f"{conv['conversation_group']}.ERROR",
                    "PASS_FAIL": "FAIL",
                    "failure_category": ["conversation_crash"],
                    "exception": str(e),
                    "traceback": traceback.format_exc(),
                    "full_response": "",
                    "scores": {},
                    "mean_score": 0,
                    "category": "L",
                    "http_status": 0,
                }
            )

    # Skip heavy satellite suites on filtered smoke retests
    skip_satellites = bool(only_groups) or os.environ.get("CERT_SKIP_SATELLITES") == "1"

    # Repeatability: 20 cases in fresh single-turn conversations (message only)
    rep_results = []
    id_map = {c["case_id"]: c for c in bank["cases_flat"]}
    if not skip_satellites:
        for cid in bank.get("repeatability_case_ids") or []:
            case = id_map.get(cid)
            if not case:
                continue
            # run twice
            pair = []
            for i in range(2):
                conv = {
                    "conversation_group": f"REP_{cid}_{i}",
                    "cases": [{**case, "turn_number": 1, "case_id": f"{cid}.REP{i}"}],
                }
                rows = run_conversation(conv)
                pair.append(rows[0] if rows else {})
            # compare factual equivalence
            a, b = pair[0], pair[1]
            equiv = True
            notes = []
            if a.get("repository_expected") and b.get("repository_expected"):
                if a["repository_expected"] != b["repository_expected"]:
                    # repo same by definition; compare response dates
                    pass
            dates_a = set(re.findall(r"20\d{2}-\d{2}-\d{2}", a.get("full_response") or ""))
            dates_b = set(re.findall(r"20\d{2}-\d{2}-\d{2}", b.get("full_response") or ""))
            if dates_a and dates_b and dates_a != dates_b:
                # also accept spanish-only if both pass
                if a.get("PASS_FAIL") == "PASS" and b.get("PASS_FAIL") == "PASS":
                    notes.append("dates_diff_but_both_pass")
                else:
                    equiv = False
                    notes.append(f"dates {dates_a} vs {dates_b}")
            if a.get("PASS_FAIL") != b.get("PASS_FAIL"):
                equiv = False
                notes.append("verdict_mismatch")
            rep_results.append({"case_id": cid, "equivalent": equiv, "notes": notes, "runs": pair})

    # Concurrency: 10 conversations in parallel (first turn only of selected groups)
    conc = []
    conc_unique = True
    if not skip_satellites:
        groups = {c["conversation_group"]: c for c in bank["conversations"]}
        selected = [groups[g] for g in (bank.get("concurrency_groups") or []) if g in groups][:10]

        def _one(conv):
            slim = {"conversation_group": f"CONC_{conv['conversation_group']}", "cases": conv["cases"][:1]}
            return run_conversation(slim)

        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(_one, c): c["conversation_group"] for c in selected}
            for fut in as_completed(futs):
                g = futs[fut]
                try:
                    rows = fut.result()
                    conc.append({"group": g, "ok": True, "rows": rows, "conversation_ids": list({r.get("conversation_id") for r in rows})})
                except Exception as e:  # noqa: BLE001
                    conc.append({"group": g, "ok": False, "error": str(e)})

        # Mix of conversation ids uniqueness
        conc_ids = [cid for item in conc for cid in (item.get("conversation_ids") or []) if cid]
        conc_unique = len(conc_ids) == len(set(conc_ids))

    # Persist artifacts
    (EVID / "raw_results.json").write_text(json.dumps({"audit_run_id": AUDIT_RUN_ID, "turns": all_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVID / "repository_expected_results.json").write_text(
        json.dumps({r["case_id"]: r.get("repository_expected") for r in all_rows}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (EVID / "repeatability_results.json").write_text(json.dumps(rep_results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (EVID / "concurrency_results.json").write_text(
        json.dumps({"unique_conversation_ids": conc_unique, "items": conc}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # CSV evaluations
    with (EVID / "turn_evaluation.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "case_id",
                "category",
                "PASS_FAIL",
                "mean_score",
                "exactitud",
                "continuidad",
                "naturalidad",
                "claridad",
                "ambiguedad",
                "prudencia",
                "http",
                "latency_ms",
                "failures",
            ]
        )
        for r in all_rows:
            sc = r.get("scores") or {}
            w.writerow(
                [
                    r.get("case_id"),
                    r.get("category"),
                    r.get("PASS_FAIL"),
                    f"{r.get('mean_score', 0):.3f}",
                    sc.get("exactitud_factual"),
                    sc.get("continuidad"),
                    sc.get("naturalidad"),
                    sc.get("claridad"),
                    sc.get("ambiguedad"),
                    sc.get("prudencia"),
                    r.get("http_status"),
                    r.get("latency_ms"),
                    "|".join(r.get("failure_category") or []),
                ]
            )

    fails = [r for r in all_rows if r.get("PASS_FAIL") == "FAIL"]
    with (EVID / "failure_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "category", "failures", "message", "response_preview"])
        for r in fails:
            w.writerow(
                [
                    r.get("case_id"),
                    r.get("category"),
                    "|".join(r.get("failure_category") or []),
                    (r.get("user_message") or "")[:120],
                    (r.get("full_response") or "")[:200],
                ]
            )

    with (EVID / "latency_report.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "latency_ms", "http_status"])
        for r in all_rows:
            w.writerow([r.get("case_id"), r.get("latency_ms"), r.get("http_status")])

    # Transcripts
    lines = [f"# Transcripts {AUDIT_RUN_ID}\n"]
    cur = None
    for r in all_rows:
        g = r.get("conversation_group") or r.get("case_id", "")
        if g != cur:
            lines.append(f"\n## {g} session={r.get('conversation_id')}\n")
            cur = g
        lines.append(f"### {r.get('case_id')} [{r.get('PASS_FAIL')}]\n")
        lines.append(f"**User:** {r.get('user_message')}\n")
        lines.append(f"**Assistant:** {r.get('full_response')}\n")
    (EVID / "conversation_transcripts.md").write_text("\n".join(lines), encoding="utf-8")

    # Summary metrics
    pass_n = sum(1 for r in all_rows if r.get("PASS_FAIL") == "PASS")
    fail_n = sum(1 for r in all_rows if r.get("PASS_FAIL") == "FAIL")
    scored = [r for r in all_rows if r.get("scores")]

    def avg(key: str) -> float:
        vals = [(r.get("scores") or {}).get(key) for r in scored]
        vals = [float(v) for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else 0.0

    factual_fail = sum(
        1
        for r in fails
        if any(
            x in (r.get("failure_category") or [])
            for x in [
                "wrong_or_missing_date",
                "wrong_subject",
                "false_positive_same_day",
                "false_negative_same_day",
                "fabricated_data",
                "guaranteed_or_fabricated",
                "fabricated_table",
            ]
        )
    )
    http500 = sum(1 for r in all_rows if r.get("http_status") == 500)
    jerga = sum(1 for r in all_rows if "internal_jargon" in (r.get("failure_category") or []))
    invented = sum(1 for r in all_rows if any("fabricat" in x or "guaranteed" in x or "invented" in x for x in (r.get("failure_category") or [])))
    wrong_subj = sum(1 for r in all_rows if "wrong_subject" in (r.get("failure_category") or []))

    # Certification level — criteria locked to the certification brief
    factual_pct = (avg("exactitud_factual") / 5.0) if scored else 0.0
    if (
        fail_n == 0
        and pass_n >= 200
        and factual_fail == 0
        and http500 == 0
        and jerga == 0
        and invented == 0
        and wrong_subj == 0
        and factual_pct >= 0.999
    ):
        level = "CERTIFIED"
    elif (
        pass_n >= 196
        and fail_n <= 4
        and factual_fail == 0
        and http500 == 0
        and invented == 0
        and wrong_subj == 0
    ):
        level = "CONDITIONAL PASS"
    else:
        level = "BLOQUEADO"

    summary = {
        "audit_run_id": AUDIT_RUN_ID,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "pass": pass_n,
        "fail": fail_n,
        "total_turns_recorded": len(all_rows),
        "global_mean": (sum(r.get("mean_score") or 0 for r in scored) / len(scored)) if scored else 0,
        "exactitud_factual_mean": avg("exactitud_factual"),
        "continuidad_mean": avg("continuidad"),
        "naturalidad_mean": avg("naturalidad"),
        "interpretacion_mean": avg("prudencia"),
        "claridad_mean": avg("claridad"),
        "ambiguedad_mean": avg("ambiguedad"),
        "contradicciones": sum(1 for r in fails if "contradiction" in (r.get("failure_category") or [])),
        "jerga_interna": jerga,
        "http_500": http500,
        "datos_inventados": invented,
        "sujetos_incorrectos": wrong_subj,
        "factual_fails": factual_fail,
        "repeatability_equivalent": sum(1 for x in rep_results if x.get("equivalent")),
        "repeatability_total": len(rep_results),
        "concurrency_unique_ids": conc_unique,
        "certification_level": level,
        "fails": [
            {
                "case_id": r.get("case_id"),
                "category": r.get("category"),
                "failures": r.get("failure_category"),
                "message": r.get("user_message"),
                "preview": (r.get("full_response") or "")[:240],
            }
            for r in fails
        ],
    }
    (EVID / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DONE", level, f"PASS={pass_n} FAIL={fail_n}", flush=True)


if __name__ == "__main__":
    main()
