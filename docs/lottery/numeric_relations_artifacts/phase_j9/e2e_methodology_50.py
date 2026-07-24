#!/usr/bin/env python3
"""J-9.6 E2E metodológico — 50 casos contra DB DEV (solo lectura, asyncpg)."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import date, time as dtime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

import asyncpg

from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.historical.confirmation import neighbors_for_candidate
from app.lottery.numeric_relations.historical.enums import ConfirmationWindowMode
from app.lottery.numeric_relations.historical.models import (
    ConfirmationWindowConfig,
    DrawRef,
    LotteryScope,
)
from app.lottery.numeric_relations.historical.number_explorer import NumberExplorerService
from app.lottery.numeric_relations.historical.presentation import condition_verdict
from app.lottery.numeric_relations.historical.universe import InMemoryDrawUniverse

DSN = os.environ.get(
    "PG_DSN",
    "postgresql://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev",
)
OUT_DIR = Path(__file__).resolve().parent
REPORT = OUT_DIR / "e2e_50_results.json"


def _case(cid: str, **kw):
    return {"id": cid, **kw}


CASES = [
    _case("C01", number=35, year_from=2020, expect="profile"),
    _case("C02", number=40, year_from=2020, expect="profile"),
    _case("C03", number=1, year_from=2022, expect="profile"),
    _case("C04", number=100, year_from=2022, expect="profile"),
    _case("C05", number=26, year_from=2018, expect="profile"),
    _case("C06", number=58, year_from=2019, expect="profile"),
    _case("C07", number=7, year_from=2021, expect="profile"),
    _case("C08", number=77, year_from=2021, expect="profile"),
    _case("C09", number=13, year_from=2020, expect="profile"),
    _case("C10", number=34, year_from=2023, expect="profile"),
    *[
        _case(f"C{11+i:02d}", number=n, year_from=2022, expect="occurrence_sample")
        for i, n in enumerate([35, 40, 12, 55, 88, 3, 21, 66, 91, 44])
    ],
    *[
        _case(f"C{21+i:02d}", number=n, year_from=2023, expect="next_draws")
        for i, n in enumerate([35, 18, 27, 61, 4, 50, 9, 72, 33, 99])
    ],
    _case("C31", number=35, year_from=2020, expect="filter_positive"),
    _case("C32", number=35, year_from=2020, expect="filter_negative"),
    _case("C33", number=35, year_from=2020, expect="filter_partial"),
    _case("C34", number_a=35, number_b=40, year_from=2020, expect="compare"),
    _case("C35", number=35, year_from=2024, expect="why"),
    _case("C36", number=2, year_from=2024, expect="t1_t2_consistency"),
    _case("C37", number=45, year_from=2024, expect="t1_t2_consistency"),
    _case("C38", number=60, year_from=2023, expect="no_dup_confirmer"),
    _case("C39", number=15, year_from=2023, expect="strength_to_candidate"),
    _case("C40", number=80, year_from=2024, expect="censored_or_complete"),
    _case("C41", number=35, year_from=2016, year_to=2017, expect="small_sample"),
    _case("C42", number=11, year_from=2022, expect="pagination"),
    _case("C43", number=22, year_from=2022, expect="lottery_dist"),
    _case("C44", number=35, year_from=2021, expect="seven_not_calendar"),
    _case("C45", number=48, year_from=2020, expect="verdict_math"),
    _case("C46", number=5, year_from=2023, expect="occurrence_sample"),
    _case("C47", number=95, year_from=2023, expect="next_draws"),
    _case("C48", number=70, year_from=2022, expect="profile"),
    _case("C49", number=35, number_b=26, year_from=2019, expect="compare"),
    _case("C50", number=34, year_from=2020, expect="full_pipeline"),
]


def _parse_num(raw) -> int | None:
    if raw is None:
        return None
    try:
        n = int(str(raw).lstrip("0") or "0")
    except ValueError:
        return None
    if 1 <= n <= 100:
        return n
    return None


async def load_universe(conn: asyncpg.Connection, lids: list[str]) -> tuple[InMemoryDrawUniverse, dict[str, str], float]:
    t0 = time.perf_counter()
    rows = await conn.fetch(
        """
        SELECT id::text, coalesce(commercial_name, name) AS n
        FROM lottery_lotteries WHERE id = ANY($1::uuid[])
        """,
        [UUID(x) for x in lids],
    )
    names = {r["id"]: r["n"] for r in rows}

    draws = await conn.fetch(
        """
        SELECT d.id::text AS draw_id, d.lottery_id::text AS lottery_id, d.draw_date, d.draw_time
        FROM lottery_draws d
        WHERE d.lottery_id = ANY($1::uuid[])
          AND d.draw_date >= DATE '2015-01-01'
        ORDER BY d.draw_date ASC, d.id ASC
        LIMIT 25000
        """,
        [UUID(x) for x in lids],
    )
    draw_ids = [r["draw_id"] for r in draws]
    nums_by: dict[str, list[tuple[int, int]]] = {d: [] for d in draw_ids}
    if draw_ids:
        # chunk to avoid huge ANY
        chunk = 2000
        for i in range(0, len(draw_ids), chunk):
            part = draw_ids[i : i + chunk]
            nrow = await conn.fetch(
                """
                SELECT draw_id::text AS draw_id, position, number_value
                FROM lottery_draw_numbers
                WHERE draw_id = ANY($1::uuid[])
                ORDER BY draw_id, position
                """,
                [UUID(x) for x in part],
            )
            for n in nrow:
                val = _parse_num(n["number_value"])
                if val is None:
                    continue
                pos = int(n["position"] or 0)
                nums_by[n["draw_id"]].append((pos, val))

    u = InMemoryDrawUniverse()
    for d in draws:
        t = d["draw_time"]
        if t is None:
            tt = dtime(20, 0)
        elif hasattr(t, "hour"):
            tt = dtime(t.hour, t.minute, getattr(t, "second", 0) or 0)
        else:
            tt = dtime(20, 0)
        u.add(
            DrawRef(
                draw_id=d["draw_id"],
                lottery_id=d["lottery_id"],
                lottery_name=names.get(d["lottery_id"], d["lottery_id"]),
                draw_date=d["draw_date"],
                draw_time=tt,
                numbers=tuple(nums_by.get(d["draw_id"]) or ()),
            )
        )
    return u, names, round((time.perf_counter() - t0) * 1000, 1)


async def run() -> dict:
    catalog = build_catalog()
    results = []
    perf = []
    conn = await asyncpg.connect(DSN)
    try:
        lot_rows = await conn.fetch(
            "SELECT id::text, coalesce(commercial_name, name) AS n FROM lottery_lotteries ORDER BY n"
        )
        lots = {r["n"]: r["id"] for r in lot_rows}
        preferred = []
        for key in ("Quiniela Leidsa", "Quiniela Loteka", "Loteria Nacional", "Loto Leidsa"):
            for name, lid in lots.items():
                if key.lower() in name.lower() and lid not in preferred:
                    preferred.append(lid)
        lids = preferred[:4] or list(lots.values())[:3]

        universe, names, load_ms = await load_universe(conn, lids)
        scope = LotteryScope(
            primary_lottery_ids=tuple(lids),
            confirming_lottery_ids=tuple(lids),
            follow_up_lottery_ids=tuple(lids),
            lottery_names=names,
        )
        window = ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)
        svc = NumberExplorerService(universe=universe, catalog=catalog)

        for case in CASES:
            ok = True
            errors = []
            meta = {}
            t0 = time.perf_counter()
            try:
                expect = case["expect"]
                year_from = case.get("year_from", 2020)
                year_to = case.get("year_to")
                df = date(year_from, 1, 1)
                dt = date(year_to, 12, 31) if year_to else None

                if expect == "profile":
                    n = case["number"]
                    p = svc.profile(number=n, scope=scope, window=window, date_from=df, date_to=dt, max_horizon=7)
                    assert p["header"]["aparecio"] == p["condition_summary"]["total_apariciones"]
                    tot = p["condition_summary"]["total_apariciones"]
                    assert (
                        p["condition_summary"]["positivas"]
                        + p["condition_summary"]["negativas"]
                        + p["condition_summary"]["parciales"]
                        == tot
                    )
                    assert "garantía" in (p["resumen_automatico"] or "").lower()
                    meta["aparecio"] = tot

                elif expect in {"occurrence_sample", "full_pipeline"}:
                    n = case["number"]
                    occ = svc.occurrences(
                        number=n, scope=scope, window=window, date_from=df, date_to=dt, page=1, page_size=5
                    )
                    if occ["total"] == 0:
                        meta["note"] = "sin apariciones en filtros"
                    else:
                        item = occ["items"][0]
                        detail = svc.occurrence_detail(
                            number=n, draw_id=item["draw_id"], scope=scope, window=window, max_horizon=7
                        )
                        cands = catalog.get_table1_companions(n)
                        assert detail["candidates"] == cands
                        v = condition_verdict(
                            candidates=cands, combination_events=detail["combination_events"]
                        )
                        assert v["status"] == detail["verdict"]["status"]
                        for b in detail["relation_tree"]["candidatos"]:
                            assert len(b["confirmadores_encontrados"]) == len(set(b["confirmadores_encontrados"]))
                        if expect == "full_pipeline":
                            nxt = svc.next_draws(
                                draw_id=item["draw_id"],
                                follow_up_lottery_ids=list(lids),
                                count=7,
                                mode="DRAWS",
                                strengthened_candidates=detail["verdict"]["confirmed_numbers"],
                            )
                            assert nxt["mode"] == "DRAWS"
                            assert len(nxt["reproductor"]) == 8
                            meta["next"] = nxt["returned_count"]
                        meta["status"] = detail["verdict"]["status"]

                elif expect == "next_draws":
                    n = case["number"]
                    occ = svc.occurrences(
                        number=n, scope=scope, window=window, date_from=df, page=1, page_size=1, order="desc"
                    )
                    if occ["total"] == 0:
                        meta["note"] = "sin apariciones"
                    else:
                        did = occ["items"][0]["draw_id"]
                        nxt = svc.next_draws(
                            draw_id=did, follow_up_lottery_ids=list(lids), count=7, mode="DRAWS"
                        )
                        ids = [s["draw_id"] for s in nxt["steps"]]
                        assert len(ids) == len(set(ids))
                        if nxt["censored"]:
                            assert nxt["returned_count"] < 7
                        else:
                            assert nxt["returned_count"] == 7
                        meta.update({"returned": nxt["returned_count"], "censored": nxt["censored"]})

                elif expect.startswith("filter_"):
                    n = case["number"]
                    cond = expect.replace("filter_", "")
                    occ = svc.occurrences(
                        number=n, scope=scope, window=window, date_from=df, condition=cond, page_size=20
                    )
                    mapping = {"positive": "yes", "negative": "no", "partial": "partial"}
                    want = mapping[cond]
                    for it in occ["items"]:
                        assert it["status"] == want
                    meta["filtered"] = occ["total"]

                elif expect == "compare":
                    a = case.get("number_a", case.get("number"))
                    b = case["number_b"]
                    out = svc.compare_numbers(
                        number_a=a, number_b=b, scope=scope, window=window, date_from=df, max_horizon=7
                    )
                    assert any("ganador absoluto" in c.lower() for c in out["conclusiones"])
                    meta["conclusiones"] = len(out["conclusiones"])

                elif expect == "why":
                    n = case["number"]
                    occ = svc.occurrences(
                        number=n, scope=scope, window=window, date_from=df, condition="positive", page_size=1
                    )
                    if occ["total"] == 0:
                        occ = svc.occurrences(
                            number=n, scope=scope, window=window, date_from=df, condition="partial", page_size=1
                        )
                    if occ["total"] == 0:
                        meta["note"] = "sin positivos/parciales"
                    else:
                        d = svc.occurrence_detail(
                            number=n, draw_id=occ["items"][0]["draw_id"], scope=scope, window=window
                        )
                        cand = (d["verdict"]["confirmed_numbers"] or d["candidates"][:1])[0]
                        why = svc.why_strengthened(number=n, candidate=cand, analyzed=d)
                        assert why["numeros_no_modificables_por_ia"] is True
                        assert why["candidato"] == cand

                elif expect == "t1_t2_consistency":
                    n = case["number"]
                    cands = catalog.get_table1_companions(n)
                    for c in cands:
                        _code, _g, neigh = neighbors_for_candidate(catalog, c)
                        assert all(1 <= x <= 100 for x in neigh)
                    meta["candidates"] = cands

                elif expect == "no_dup_confirmer":
                    n = case["number"]
                    occ = svc.occurrences(number=n, scope=scope, window=window, date_from=df, page_size=3)
                    for it in occ["items"]:
                        d = svc.occurrence_detail(number=n, draw_id=it["draw_id"], scope=scope, window=window)
                        for b in d["relation_tree"]["candidatos"]:
                            confs = b["confirmadores_encontrados"]
                            assert len(confs) == len(set(confs))

                elif expect == "strength_to_candidate":
                    n = case["number"]
                    occ = svc.occurrences(
                        number=n, scope=scope, window=window, date_from=df, condition="partial", page_size=5
                    )
                    if occ["total"] == 0:
                        occ = svc.occurrences(
                            number=n, scope=scope, window=window, date_from=df, condition="positive", page_size=5
                        )
                    companions = set(catalog.get_table1_companions(n))
                    for it in occ["items"][:3]:
                        d = svc.occurrence_detail(number=n, draw_id=it["draw_id"], scope=scope, window=window)
                        strengthened = {
                            b["candidato"] for b in d["relation_tree"]["candidatos"] if b["confirmaciones"] > 0
                        }
                        all_confs = set()
                        for b in d["relation_tree"]["candidatos"]:
                            all_confs.update(b["confirmadores_encontrados"])
                        for conf in all_confs:
                            if conf not in companions:
                                assert conf not in strengthened

                elif expect == "censored_or_complete":
                    n = case["number"]
                    occ = svc.occurrences(
                        number=n, scope=scope, window=window, date_from=df, page_size=20, order="desc"
                    )
                    saw = False
                    for it in occ["items"][:10]:
                        nxt = svc.next_draws(
                            draw_id=it["draw_id"], follow_up_lottery_ids=list(lids), count=7, mode="DRAWS"
                        )
                        saw = True
                        if nxt["censored"]:
                            assert nxt["returned_count"] < 7
                            meta["censored_example"] = it["draw_id"]
                            break
                    if not saw:
                        meta["note"] = "sin apariciones"
                    elif "censored_example" not in meta:
                        meta["note"] = "muestra sin censura en top 10 (válido)"

                elif expect == "small_sample":
                    n = case["number"]
                    p = svc.profile(
                        number=n, scope=scope, window=window, date_from=df, date_to=dt, max_horizon=7
                    )
                    meta["sample"] = p["sample_size"]
                    meta["nivel"] = p["header"]["nivel_evidencia"]

                elif expect == "pagination":
                    n = case["number"]
                    p1 = svc.occurrences(
                        number=n, scope=scope, window=window, date_from=df, page=1, page_size=5
                    )
                    p2 = svc.occurrences(
                        number=n, scope=scope, window=window, date_from=df, page=2, page_size=5
                    )
                    ids1 = {i["draw_id"] for i in p1["items"]}
                    ids2 = {i["draw_id"] for i in p2["items"]}
                    assert ids1.isdisjoint(ids2) or p1["total"] <= 5
                    meta["total"] = p1["total"]

                elif expect == "lottery_dist":
                    n = case["number"]
                    p = svc.profile(number=n, scope=scope, window=window, date_from=df, max_horizon=7)
                    dist = p["charts"]["apariciones_por_loteria"]
                    assert sum(x["cantidad"] for x in dist) == p["header"]["aparecio"]

                elif expect == "seven_not_calendar":
                    n = case["number"]
                    occ = svc.occurrences(number=n, scope=scope, window=window, date_from=df, page_size=1)
                    if occ["total"]:
                        did = occ["items"][0]["draw_id"]
                        d_mode = svc.next_draws(
                            draw_id=did, follow_up_lottery_ids=list(lids), count=7, mode="DRAWS"
                        )
                        c_mode = svc.next_draws(
                            draw_id=did, follow_up_lottery_ids=list(lids), count=7, mode="CALENDAR_DAYS"
                        )
                        assert d_mode["mode"] != c_mode["mode"]
                        meta["draws"] = d_mode["returned_count"]
                        meta["calendar"] = c_mode["returned_count"]

                elif expect == "verdict_math":
                    n = case["number"]
                    occ = svc.occurrences(number=n, scope=scope, window=window, date_from=df, page_size=8)
                    for it in occ["items"]:
                        d = svc.occurrence_detail(
                            number=n, draw_id=it["draw_id"], scope=scope, window=window
                        )
                        v = d["verdict"]
                        assert (
                            v["candidates_confirmed"] + v["candidates_without_confirmation"]
                            == v["candidates_total"]
                        )

                else:
                    raise AssertionError(f"unknown expect {expect}")

            except Exception as exc:  # noqa: BLE001
                ok = False
                errors.append(f"{type(exc).__name__}: {exc}")

            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            perf.append(elapsed)
            results.append(
                {
                    "id": case["id"],
                    "expect": case["expect"],
                    "pass": ok,
                    "errors": errors,
                    "meta": meta,
                    "ms": elapsed,
                }
            )
    finally:
        await conn.close()

    passed = sum(1 for r in results if r["pass"])
    failed = [r for r in results if not r["pass"]]
    summary = {
        "environment": "DEV jaios_lottery_dev:5433",
        "universe_load_ms": load_ms,
        "lottery_ids": lids,
        "lottery_names": names,
        "total": len(results),
        "passed": passed,
        "failed": len(failed),
        "pass_ratio": f"{passed}/{len(results)}",
        "perf_ms": {
            "min": min(perf) if perf else None,
            "max": max(perf) if perf else None,
            "avg": round(sum(perf) / len(perf), 1) if perf else None,
        },
        "failures": failed,
        "cases": results,
        "production_untouched": True,
    }
    REPORT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


if __name__ == "__main__":
    summary = asyncio.run(run())
    print(
        json.dumps(
            {k: summary[k] for k in ("pass_ratio", "failed", "perf_ms", "universe_load_ms")},
            indent=2,
        )
    )
    if summary["failed"]:
        print("FAILURES:", json.dumps(summary["failures"], indent=2, ensure_ascii=False)[:4000])
        sys.exit(1)
    print("E2E 50/50 PASS")
