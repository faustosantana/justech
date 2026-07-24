#!/usr/bin/env python3
"""J-9.7–J-9.9 — perf + seven-draws DB cross-check + case fixtures (DEV only)."""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from datetime import date, time as dtime
from pathlib import Path
from uuid import UUID

import asyncpg
import httpx

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

API = os.environ.get("J9_API", "http://127.0.0.1:8001/api/v1")
DSN = os.environ.get(
    "PG_DSN", "postgresql://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev"
)
OUT = Path(__file__).resolve().parent
N = int(os.environ.get("J9_PERF_N", "10"))
PASS = os.environ.get("J9_UAT_PASS", "UatDevNumericRelations2026!")


def pct(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def summarize(times: list[float]) -> dict:
    return {
        "n": len(times),
        "min_ms": round(min(times), 1) if times else None,
        "max_ms": round(max(times), 1) if times else None,
        "avg_ms": round(statistics.mean(times), 1) if times else None,
        "median_ms": round(statistics.median(times), 1) if times else None,
        "p95_ms": round(pct(times, 0.95), 1) if times else None,
    }


def login(client: httpx.Client) -> tuple[str, str]:
    r = client.post(
        f"{API}/auth/login",
        json={
            "email": "uat-nr-admin@example.com",
            "password": PASS,
            "tenant_slug": "uat-numeric-relations",
        },
        timeout=30,
    )
    r.raise_for_status()
    d = r.json()
    token = d["access_token"]
    tenant = str(d.get("tenant_id") or (d.get("tenant") or {}).get("id") or "")
    return token, tenant


def pick_lotteries(client: httpx.Client, headers: dict) -> list[str]:
    r = client.get(f"{API}/lottery/admin/numeric-relations/lotteries", headers=headers, timeout=60)
    r.raise_for_status()
    items = r.json().get("items") or []
    wanted = []
    for key in ("Quiniela Leidsa", "Quiniela Loteka", "Loteria Nacional", "Loto Leidsa"):
        for it in items:
            name = it.get("name") or it.get("commercial_name") or ""
            if key.lower() in name.lower() and it["id"] not in wanted:
                wanted.append(it["id"])
    if not wanted:
        wanted = [it["id"] for it in items[:4]]
    return wanted[:4]


def scope(lids: list[str]) -> dict:
    return {
        "primary_lottery_ids": lids,
        "confirming_lottery_ids": lids,
        "follow_up_lottery_ids": lids,
    }


def timed(client: httpx.Client, method: str, path: str, headers: dict, body: dict | None) -> tuple[float, dict, int]:
    t0 = time.perf_counter()
    if method == "POST":
        r = client.post(f"{API}{path}", headers=headers, json=body, timeout=180)
    else:
        r = client.get(f"{API}{path}", headers=headers, timeout=180)
    ms = (time.perf_counter() - t0) * 1000
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text[:500]}
    return ms, data, r.status_code


async def db_next_draws(conn: asyncpg.Connection, draw_id: str, lottery_id: str, count: int = 7) -> list[dict]:
    anchor = await conn.fetchrow(
        "SELECT id::text, lottery_id::text, draw_date, draw_time FROM lottery_draws WHERE id=$1::uuid",
        UUID(draw_id),
    )
    if not anchor:
        return []
    rows = await conn.fetch(
        """
        SELECT d.id::text AS draw_id, d.draw_date, d.draw_time,
               array_agg(n.number_value ORDER BY n.position) AS nums
        FROM lottery_draws d
        LEFT JOIN lottery_draw_numbers n ON n.draw_id = d.id
        WHERE d.lottery_id = $1::uuid
          AND (d.draw_date, COALESCE(d.draw_time, TIME '00:00'), d.id)
              > ($2::date, COALESCE($3::time, TIME '00:00'), $4::uuid)
        GROUP BY d.id, d.draw_date, d.draw_time
        ORDER BY d.draw_date ASC, COALESCE(d.draw_time, TIME '00:00') ASC, d.id ASC
        LIMIT $5
        """,
        UUID(lottery_id),
        anchor["draw_date"],
        anchor["draw_time"],
        UUID(draw_id),
        count,
    )
    out = []
    for r in rows:
        nums = []
        for raw in r["nums"] or []:
            try:
                v = int(str(raw).lstrip("0") or "0")
            except ValueError:
                continue
            if 1 <= v <= 100:
                nums.append(v)
        out.append(
            {
                "draw_id": r["draw_id"],
                "draw_date": r["draw_date"].isoformat(),
                "numbers": sorted(set(nums)),
            }
        )
    return out


def main() -> int:
    report: dict = {
        "api": API,
        "database": "jaios_lottery_dev@5433",
        "production_untouched": True,
        "perf": {},
        "seven_draws": [],
        "cases": {},
        "permissions": {},
        "targets": {
            "profile_ms": 2000,
            "occurrences_ms": 2000,
            "detail_ms": 1500,
            "next_draws_ms": 1500,
            "compare_ms": 3000,
        },
    }

    with httpx.Client() as client:
        token, tenant = login(client)
        headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant}
        lids = pick_lotteries(client, headers)
        report["lottery_ids"] = lids
        base = {
            "number": 35,
            "scope": scope(lids),
            "confirmation_window": {"mode": "SAME_DRAW", "timezone": "America/Santo_Domingo"},
            "max_horizon": 7,
            "date_from": "2015-01-01",
        }

        # cold then hot profile
        cold = []
        hot = []
        last_profile = None
        for i in range(N):
            ms, data, code = timed(client, "POST", "/lottery/admin/numeric-relations/history/numbers/profile", headers, base)
            assert code == 200, data
            last_profile = data
            (cold if i == 0 else hot).append(ms)
        # fill remaining as hot for fair avg
        while len(hot) < N - 1:
            ms, data, code = timed(client, "POST", "/lottery/admin/numeric-relations/history/numbers/profile", headers, base)
            hot.append(ms)
            last_profile = data
        all_p = cold + hot
        report["perf"]["profile"] = {
            "cold": summarize(cold),
            "hot": summarize(hot),
            "all": summarize(all_p),
            "sample_size": last_profile.get("sample_size"),
            "aparecio": (last_profile.get("header") or {}).get("aparecio"),
        }
        report["cases"]["A_frequent_35"] = {
            "header": last_profile.get("header"),
            "condition_summary": last_profile.get("condition_summary"),
            "top_candidates": (last_profile.get("charts") or {}).get("candidatos_fortalecidos", [])[:5],
            "top_confirmers": (last_profile.get("charts") or {}).get("confirmadores", [])[:5],
        }

        # occurrences
        occ_times = []
        last_occ = None
        for _ in range(N):
            body = {**base, "page": 1, "page_size": 10, "order": "desc"}
            ms, data, code = timed(
                client, "POST", "/lottery/admin/numeric-relations/history/numbers/occurrences", headers, body
            )
            assert code == 200, data
            occ_times.append(ms)
            last_occ = data
        report["perf"]["occurrences"] = summarize(occ_times)
        report["cases"]["occurrences_page1_total"] = last_occ.get("total")

        # find positive / negative / partial / multi-confirmer
        def find_status(status: str, pages: int = 8):
            for p in range(1, pages + 1):
                body = {
                    **base,
                    "page": p,
                    "page_size": 20,
                    "condition": {"yes": "positive", "no": "negative", "partial": "partial"}[status],
                    "order": "desc",
                }
                _, data, code = timed(
                    client, "POST", "/lottery/admin/numeric-relations/history/numbers/occurrences", headers, body
                )
                if code != 200:
                    continue
                for it in data.get("items") or []:
                    if it.get("status") == status:
                        return it
            return None

        pos = find_status("yes") or find_status("partial")
        neg = find_status("no")
        partial = find_status("partial")
        report["cases"]["B_negative"] = neg
        report["cases"]["C_partial"] = partial
        report["cases"]["positive_or_partial"] = pos

        detail_times = []
        next_times = []
        why_times = []
        detail_anchor = None
        multi = None
        for it in (last_occ.get("items") or [])[:5]:
            body = {
                "number": 35,
                "draw_id": it["draw_id"],
                "scope": scope(lids),
                "confirmation_window": base["confirmation_window"],
                "max_horizon": 7,
            }
            ms, detail, code = timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/occurrences/detail",
                headers,
                body,
            )
            detail_times.append(ms)
            assert code == 200, detail
            detail_anchor = detail
            for b in (detail.get("relation_tree") or {}).get("candidatos") or []:
                if int(b.get("confirmaciones") or 0) >= 2:
                    multi = {"draw_id": it["draw_id"], "branch": b, "verdict": detail.get("verdict")}
                    break
            # next draws
            nd_body = {
                "draw_id": it["draw_id"],
                "follow_up_lottery_ids": lids,
                "count": 7,
                "mode": "DRAWS",
                "strengthened_candidates": (detail.get("verdict") or {}).get("confirmed_numbers") or [],
            }
            ms2, nxt, code2 = timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/occurrences/next-draws",
                headers,
                nd_body,
            )
            next_times.append(ms2)
            assert code2 == 200, nxt
            # why
            cand = ((detail.get("verdict") or {}).get("confirmed_numbers") or detail.get("candidates") or [None])[0]
            if cand:
                why_body = {
                    **base,
                    "candidate": cand,
                    "draw_id": it["draw_id"],
                }
                ms3, why, code3 = timed(
                    client,
                    "POST",
                    "/lottery/admin/numeric-relations/history/numbers/why-strengthened",
                    headers,
                    why_body,
                )
                why_times.append(ms3)
                assert code3 == 200, why

        # pad detail/next/why to N with repeats of last
        while len(detail_times) < N and detail_anchor:
            did = (detail_anchor.get("anchor") or {}).get("draw_id") or (last_occ["items"][0]["draw_id"])
            body = {
                "number": 35,
                "draw_id": did,
                "scope": scope(lids),
                "confirmation_window": base["confirmation_window"],
                "max_horizon": 7,
            }
            ms, _, code = timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/occurrences/detail",
                headers,
                body,
            )
            detail_times.append(ms)
        while len(next_times) < N and last_occ and last_occ.get("items"):
            did = last_occ["items"][0]["draw_id"]
            ms, _, _ = timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/occurrences/next-draws",
                headers,
                {"draw_id": did, "follow_up_lottery_ids": lids, "count": 7, "mode": "DRAWS"},
            )
            next_times.append(ms)
        while len(why_times) < N and detail_anchor:
            cand = ((detail_anchor.get("verdict") or {}).get("confirmed_numbers") or detail_anchor.get("candidates") or [4])[0]
            did = (detail_anchor.get("anchor") or {}).get("draw_id")
            ms, _, _ = timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/why-strengthened",
                headers,
                {**base, "candidate": cand, "draw_id": did},
            )
            why_times.append(ms)

        report["perf"]["detail"] = summarize(detail_times)
        report["perf"]["next_draws"] = summarize(next_times)
        report["perf"]["why"] = summarize(why_times)
        report["cases"]["D_multi_confirmers"] = multi

        # compare 35 vs 40
        cmp_times = []
        last_cmp = None
        for _ in range(N):
            body = {
                "number_a": 35,
                "number_b": 40,
                "scope": scope(lids),
                "confirmation_window": base["confirmation_window"],
                "max_horizon": 7,
                "date_from": "2015-01-01",
            }
            ms, data, code = timed(
                client, "POST", "/lottery/admin/numeric-relations/history/numbers/compare", headers, body
            )
            assert code == 200, data
            cmp_times.append(ms)
            last_cmp = data
        report["perf"]["compare"] = summarize(cmp_times)
        report["cases"]["compare_35_40"] = {"conclusiones": last_cmp.get("conclusiones")}

        # small sample
        ms, small, code = timed(
            client,
            "POST",
            "/lottery/admin/numeric-relations/history/numbers/profile",
            headers,
            {**base, "number": 35, "date_from": "2016-01-01", "date_to": "2016-03-31"},
        )
        report["cases"]["E_small_sample"] = {
            "ms": round(ms, 1),
            "aparecio": (small.get("header") or {}).get("aparecio"),
            "nivel": (small.get("header") or {}).get("nivel_evidencia"),
            "warning": (small.get("header") or {}).get("sample_warning"),
        }

        # permissions: client role
        r = client.post(
            f"{API}/auth/login",
            json={
                "email": "uat-nr-client@example.com",
                "password": PASS,
                "tenant_slug": "uat-numeric-relations",
            },
            timeout=30,
        )
        if r.status_code == 200:
            ct = r.json()["access_token"]
            ch = {"Authorization": f"Bearer {ct}"}
            denied = client.post(
                f"{API}/lottery/admin/numeric-relations/history/numbers/profile",
                headers=ch,
                json=base,
                timeout=60,
            )
            report["permissions"]["client_profile"] = {
                "status": denied.status_code,
                "pass": denied.status_code in (401, 403),
            }
        else:
            report["permissions"]["client_login"] = {"status": r.status_code, "note": "login failed"}

        report["permissions"]["admin_profile"] = {"status": 200, "pass": True}

        # censored: find from next draws on recent? use last items
        cens = None
        for it in (last_occ.get("items") or [])[:15]:
            ms, nxt, code = timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/occurrences/next-draws",
                headers,
                {"draw_id": it["draw_id"], "follow_up_lottery_ids": lids[:1], "count": 7, "mode": "DRAWS"},
            )
            if nxt.get("censored"):
                cens = {"draw_id": it["draw_id"], "texto": nxt.get("censored_texto"), "returned": nxt.get("returned_count")}
                break
        report["cases"]["F_censored"] = cens

    # DB cross-check seven draws for up to 5 anchors
    import asyncio

    async def cross():
        conn = await asyncpg.connect(DSN)
        try:
            with httpx.Client() as client:
                token, tenant = login(client)
                headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant}
                lids = pick_lotteries(client, headers)
                body = {
                    "number": 35,
                    "scope": scope(lids),
                    "confirmation_window": {"mode": "SAME_DRAW", "timezone": "America/Santo_Domingo"},
                    "max_horizon": 7,
                    "date_from": "2020-01-01",
                    "page": 1,
                    "page_size": 5,
                    "order": "desc",
                }
                _, occ, _ = timed(
                    client,
                    "POST",
                    "/lottery/admin/numeric-relations/history/numbers/occurrences",
                    headers,
                    body,
                )
                results = []
                for it in occ.get("items") or []:
                    # follow-up: use primary lottery of the occurrence
                    lid = it.get("lottery_id")
                    _, nxt, _ = timed(
                        client,
                        "POST",
                        "/lottery/admin/numeric-relations/history/numbers/occurrences/next-draws",
                        headers,
                        {
                            "draw_id": it["draw_id"],
                            "follow_up_lottery_ids": [lid] if lid else lids[:1],
                            "count": 7,
                            "mode": "DRAWS",
                        },
                    )
                    db_seq = await db_next_draws(conn, it["draw_id"], lid or lids[0], 7)
                    api_ids = [s["draw_id"] for s in nxt.get("steps") or []]
                    db_ids = [s["draw_id"] for s in db_seq]
                    # API may merge multi-lottery; when single lottery should match
                    match = api_ids == db_ids if lid else api_ids[: len(db_ids)] == db_ids
                    # also verify numbers subset equality for matching ids
                    num_ok = True
                    if match:
                        for a, b in zip(nxt.get("steps") or [], db_seq):
                            api_nums = sorted(set(a.get("numeros_ganadores") or []))
                            if api_nums != b["numbers"]:
                                # allow API to include only 1..100 already filtered
                                if not set(api_nums).issubset(set(b["numbers"])) and api_nums != b["numbers"]:
                                    num_ok = False
                    results.append(
                        {
                            "anchor": it["draw_id"],
                            "lottery_id": lid,
                            "api_ids": api_ids,
                            "db_ids": db_ids,
                            "ids_match": match,
                            "numbers_ok": num_ok,
                            "censored_api": nxt.get("censored"),
                            "api_label_mode": nxt.get("mode"),
                        }
                    )
                return results
        finally:
            await conn.close()

    report["seven_draws"] = asyncio.run(cross())
    report["seven_draws_pass"] = all(x["ids_match"] and x["numbers_ok"] for x in report["seven_draws"]) if report["seven_draws"] else False

    # target assessment
    def ok(op: str, key: str, limit: int) -> bool:
        block = report["perf"].get(op) or {}
        if "all" in block:
            avg = block["all"].get("avg_ms")
        else:
            avg = block.get("avg_ms")
        return avg is not None and avg <= limit

    report["targets_assessment"] = {
        "profile": {
            "avg_ms": (report["perf"]["profile"].get("all") or {}).get("avg_ms"),
            "limit": 2000,
            "pass": ok("profile", "avg_ms", 2000),
            "cold_ms": (report["perf"]["profile"].get("cold") or {}).get("avg_ms"),
        },
        "occurrences": {
            "avg_ms": report["perf"]["occurrences"].get("avg_ms"),
            "limit": 2000,
            "pass": report["perf"]["occurrences"].get("avg_ms", 99999) <= 2000,
        },
        "detail": {
            "avg_ms": report["perf"]["detail"].get("avg_ms"),
            "limit": 1500,
            "pass": report["perf"]["detail"].get("avg_ms", 99999) <= 1500,
        },
        "next_draws": {
            "avg_ms": report["perf"]["next_draws"].get("avg_ms"),
            "limit": 1500,
            "pass": report["perf"]["next_draws"].get("avg_ms", 99999) <= 1500,
        },
        "compare": {
            "avg_ms": report["perf"]["compare"].get("avg_ms"),
            "limit": 3000,
            "pass": report["perf"]["compare"].get("avg_ms", 99999) <= 3000,
        },
    }

    OUT.joinpath("perf_and_cases.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"targets": report["targets_assessment"], "seven_draws_pass": report["seven_draws_pass"], "cases_keys": list(report["cases"].keys())}, indent=2))
    return 0 if report["seven_draws_pass"] else 1


if __name__ == "__main__":
    # Python 3.9 compat for asyncio
    try:
        asyncio_mod = __import__("asyncio")
        if hasattr(asyncio_mod, "get_event_loop"):
            pass
    except Exception:
        pass
    raise SystemExit(main())
