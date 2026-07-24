#!/usr/bin/env python3
"""J-10.5 — E2E hub + expediente + permissions + perf vs J-9 (DEV only)."""

from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path

import httpx

API = os.environ.get("J9_API", "http://127.0.0.1:8001/api/v1")
PASS = os.environ.get("J9_UAT_PASS", "UatDevNumericRelations2026!")
OUT = Path(__file__).resolve().parent
N = int(os.environ.get("J10_PERF_N", "10"))
CANONICAL = {
    "Quiniela Leidsa",
    "Quiniela Loteka",
    "Loteria Nacional",
    "Loto Leidsa",
    "Quiniela Real",
    "Loto Real",
    "Gana Mas",
}


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


def login(client: httpx.Client, email: str) -> tuple[str, str, int]:
    r = client.post(
        f"{API}/auth/login",
        json={"email": email, "password": PASS, "tenant_slug": "uat-numeric-relations"},
        timeout=30,
    )
    if r.status_code != 200:
        return "", "", r.status_code
    d = r.json()
    return d["access_token"], str(d.get("tenant_id") or ""), 200


def timed(client: httpx.Client, method: str, path: str, headers: dict, body=None):
    t0 = time.perf_counter()
    if method == "GET":
        r = client.get(f"{API}{path}", headers=headers, timeout=180)
    else:
        r = client.post(f"{API}{path}", headers=headers, json=body, timeout=180)
    ms = (time.perf_counter() - t0) * 1000
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text[:300]}
    return ms, data, r.status_code


def main() -> int:
    report: dict = {
        "api": API,
        "production_untouched": True,
        "checks": {},
        "cases": {},
        "perf": {},
        "permissions": {},
        "j9_baseline": {
            "profile_avg_ms": 1827.5,
            "profile_cold_ms": 2252.3,
            "compare_avg_ms": 2640.5,
        },
    }
    with httpx.Client() as client:
        health = client.get(f"{API}/health", timeout=15).json()
        report["health"] = health
        if health.get("database_target") != "jaios_lottery_dev" or not health.get("production_forbidden"):
            report["verdict"] = "NO-GO"
            report["reason"] = "health not DEV / production_forbidden missing"
            (OUT / "e2e_j10_results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
            print(json.dumps(report, indent=2))
            return 2

        tok, ten, _ = login(client, "uat-nr-admin@example.com")
        h = {"Authorization": f"Bearer {tok}", "X-Tenant-Id": ten}

        # Featured catalog
        ms, cat, code = timed(client, "GET", "/lottery/catalog?featured_only=true&page_size=20", h)
        items = cat.get("items") or []
        names = {i.get("name") for i in items}
        report["checks"]["featured_count"] = len(items)
        report["checks"]["featured_names"] = sorted(names)
        report["checks"]["featured_exact_seven"] = names == CANONICAL
        report["checks"]["no_anguila"] = not any("anguila" in (n or "").lower() for n in names)
        report["checks"]["no_haiti"] = not any("haiti" in (n or "").lower() or "haití" in (n or "").lower() for n in names)
        report["checks"]["no_miami_florida"] = not any(
            x in (n or "").lower() for n in names for x in ("miami", "florida")
        )
        report["checks"]["clickable_numbers"] = all(len(i.get("last_numbers") or []) > 0 for i in items)
        report["perf"]["catalog_featured"] = {"first_ms": round(ms, 1), "status": code}

        # Admin still has hidden lotteries
        ms_a, admin, code_a = timed(client, "GET", "/lottery/admin/lotteries?limit=100", h)
        admin_names = [x.get("name") or "" for x in (admin if isinstance(admin, list) else admin.get("items") or [])]
        if not admin_names and isinstance(admin, list):
            admin_names = [x.get("name") or "" for x in admin]
        report["checks"]["admin_has_anguila"] = any("anguila" in n.lower() for n in admin_names)
        report["checks"]["admin_lotteries_status"] = code_a
        report["perf"]["admin_lotteries_ms"] = round(ms_a, 1)

        lids = [i["id"] for i in items]
        scope = {
            "primary_lottery_ids": lids,
            "confirming_lottery_ids": lids,
            "follow_up_lottery_ids": lids,
        }
        cw = {"mode": "SAME_DRAW", "timezone": "America/Santo_Domingo"}

        # Cases via number explorer
        def profile(num: int, date_from: str | None = "2015-01-01", date_to: str | None = "2016-12-31"):
            body = {"number": num, "scope": scope, "confirmation_window": cw, "max_horizon": 7}
            if date_from:
                body["date_from"] = date_from
            if date_to:
                body["date_to"] = date_to
            return timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/profile",
                h,
                body,
            )

        def occurrences(num: int, condition: str, date_from="2015-01-01", date_to="2016-12-31"):
            body = {
                "number": num,
                "scope": scope,
                "confirmation_window": cw,
                "max_horizon": 7,
                "date_from": date_from,
                "date_to": date_to,
                "page": 1,
                "page_size": 20,
                "condition": condition,
                "order": "desc",
            }
            return timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/occurrences",
                h,
                body,
            )

        ms50, p50, c50 = profile(50)
        report["cases"]["positive_50"] = {
            "status": c50,
            "positivas": (p50.get("condition_summary") or {}).get("positivas"),
            "ms": round(ms50, 1),
        }
        ms_occ, occ_pos, _ = occurrences(50, "positive")
        yes_item = next((it for it in (occ_pos.get("items") or []) if it.get("status") == "yes"), None)
        report["cases"]["positive_occurrence"] = {
            "found": bool(yes_item),
            "estado": (yes_item or {}).get("estado"),
            "draw_id": (yes_item or {}).get("draw_id"),
            "ms": round(ms_occ, 1),
        }

        ms35, p35, c35 = profile(35)
        report["cases"]["partial_or_neg_35"] = {
            "status": c35,
            "positivas": (p35.get("condition_summary") or {}).get("positivas"),
            "parciales": (p35.get("condition_summary") or {}).get("parciales"),
            "negativas": (p35.get("condition_summary") or {}).get("negativas"),
            "ms": round(ms35, 1),
        }
        _, occ_neg, _ = occurrences(35, "negative")
        neg_item = (occ_neg.get("items") or [None])[0]
        report["cases"]["negative_occurrence"] = {
            "found": bool(neg_item),
            "estado": (neg_item or {}).get("estado"),
            "draw_id": (neg_item or {}).get("draw_id"),
        }
        _, occ_par, _ = occurrences(35, "partial")
        par_item = (occ_par.get("items") or [None])[0]
        report["cases"]["partial_occurrence"] = {
            "found": bool(par_item),
            "estado": (par_item or {}).get("estado"),
            "draw_id": (par_item or {}).get("draw_id"),
        }

        # Multi-confirmers detail
        multi = None
        for it in occ_par.get("items") or []:
            ms_d, det, cd = timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/occurrences/detail",
                h,
                {
                    "number": 35,
                    "draw_id": it["draw_id"],
                    "scope": scope,
                    "confirmation_window": cw,
                    "max_horizon": 7,
                },
            )
            for b in ((det.get("relation_tree") or {}).get("candidatos") or []):
                if int(b.get("confirmaciones") or 0) >= 2:
                    multi = {
                        "draw_id": it["draw_id"],
                        "candidato": b.get("candidato"),
                        "confirmadores": b.get("confirmadores_encontrados"),
                        "confirmaciones": b.get("confirmaciones"),
                        "detail_ms": round(ms_d, 1),
                        "status": cd,
                    }
                    break
            if multi:
                break
        report["cases"]["multi_confirmers"] = multi

        # Open case next-draws for positive
        if yes_item:
            ms_n, nxt, cn = timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/occurrences/next-draws",
                h,
                {
                    "draw_id": yes_item["draw_id"],
                    "follow_up_lottery_ids": lids,
                    "count": 7,
                    "mode": "DRAWS",
                },
            )
            report["cases"]["next_draws_positive"] = {
                "status": cn,
                "returned": nxt.get("returned_count"),
                "censored": nxt.get("censored"),
                "ms": round(ms_n, 1),
            }

        # Permissions
        ctok, cten, _ = login(client, "uat-nr-client@example.com")
        hc = {"Authorization": f"Bearer {ctok}", "X-Tenant-Id": cten}
        body35 = {
            "number": 35,
            "scope": scope,
            "confirmation_window": cw,
            "max_horizon": 7,
            "date_from": "2015-01-01",
            "date_to": "2015-01-07",
        }
        _, _, admin_st = timed(
            client, "POST", "/lottery/admin/numeric-relations/history/numbers/profile", h, body35
        )
        _, _, client_st = timed(
            client, "POST", "/lottery/admin/numeric-relations/history/numbers/profile", hc, body35
        )
        _, _, anon_st = timed(
            client, "POST", "/lottery/admin/numeric-relations/history/numbers/profile", {}, body35
        )
        _, _, cat_client = timed(client, "GET", "/lottery/catalog?featured_only=true", hc)
        report["permissions"] = {
            "admin_profile": admin_st,
            "client_profile": client_st,
            "anon_profile": anon_st,
            "client_catalog": cat_client,
            "admin_pass": admin_st == 200,
            "client_denied_or_limited": client_st in (200, 403),
            "anon_denied": anon_st in (401, 403),
        }

        # Perf 10x vs J-9 baseline (featured scope, number 35 full history)
        body_full = {
            "number": 35,
            "scope": scope,
            "confirmation_window": cw,
            "max_horizon": 7,
        }
        hub_times = []
        for i in range(N):
            ms, _, st = timed(client, "GET", "/lottery/catalog?featured_only=true&page_size=12", h)
            assert st == 200
            hub_times.append(ms)
        report["perf"]["hub_catalog"] = summarize(hub_times)

        profile_times = []
        for i in range(N):
            ms, data, st = timed(
                client,
                "POST",
                "/lottery/admin/numeric-relations/history/numbers/profile",
                h,
                body_full,
            )
            assert st == 200
            profile_times.append(ms)
            if i == 0:
                report["perf"]["profile_sample_aparecio"] = (data.get("header") or {}).get("aparecio")
        report["perf"]["profile_35"] = {
            "cold": summarize(profile_times[:1]),
            "hot": summarize(profile_times[1:]),
            "all": summarize(profile_times),
        }

        # detail + why + next + compare
        _, occ_all, _ = timed(
            client,
            "POST",
            "/lottery/admin/numeric-relations/history/numbers/occurrences",
            h,
            {**body_full, "page": 1, "page_size": 5, "condition": "all", "order": "desc"},
        )
        anchor = (occ_all.get("items") or [{}])[0]
        draw_id = anchor.get("draw_id")
        detail_times, why_times, next_times, compare_times = [], [], [], []
        if draw_id:
            for _ in range(N):
                ms, det, _ = timed(
                    client,
                    "POST",
                    "/lottery/admin/numeric-relations/history/numbers/occurrences/detail",
                    h,
                    {"number": 35, "draw_id": draw_id, "scope": scope, "confirmation_window": cw, "max_horizon": 7},
                )
                detail_times.append(ms)
                cand = None
                for b in ((det.get("relation_tree") or {}).get("candidatos") or []):
                    if int(b.get("confirmaciones") or 0) > 0:
                        cand = b.get("candidato")
                        break
                if cand is None:
                    branches = ((det.get("relation_tree") or {}).get("candidatos") or [])
                    cand = branches[0]["candidato"] if branches else 6
                ms_w, _, _ = timed(
                    client,
                    "POST",
                    "/lottery/admin/numeric-relations/history/numbers/why-strengthened",
                    h,
                    {
                        "number": 35,
                        "candidate": cand,
                        "draw_id": draw_id,
                        "scope": scope,
                        "confirmation_window": cw,
                        "max_horizon": 7,
                    },
                )
                why_times.append(ms_w)
                ms_n, _, _ = timed(
                    client,
                    "POST",
                    "/lottery/admin/numeric-relations/history/numbers/occurrences/next-draws",
                    h,
                    {"draw_id": draw_id, "follow_up_lottery_ids": lids, "count": 7, "mode": "DRAWS"},
                )
                next_times.append(ms_n)
            for _ in range(N):
                ms_c, _, _ = timed(
                    client,
                    "POST",
                    "/lottery/admin/numeric-relations/history/numbers/compare",
                    h,
                    {
                        "number_a": 35,
                        "number_b": 40,
                        "scope": scope,
                        "confirmation_window": cw,
                        "max_horizon": 7,
                    },
                )
                compare_times.append(ms_c)
        report["perf"]["detail"] = summarize(detail_times)
        report["perf"]["why"] = summarize(why_times)
        report["perf"]["next_draws"] = summarize(next_times)
        report["perf"]["compare"] = summarize(compare_times)

        # Degradation vs J-9 (featured scope may be faster; compare profile avg)
        j9 = report["j9_baseline"]["profile_avg_ms"]
        j10 = (report["perf"]["profile_35"]["all"] or {}).get("avg_ms") or 0
        deg = ((j10 - j9) / j9 * 100) if j9 else 0
        report["perf"]["vs_j9_profile_pct"] = round(deg, 1)
        report["perf"]["vs_j9_pass"] = deg <= 15

        j9c = report["j9_baseline"]["compare_avg_ms"]
        j10c = (report["perf"]["compare"] or {}).get("avg_ms") or 0
        degc = ((j10c - j9c) / j9c * 100) if j9c else 0
        report["perf"]["vs_j9_compare_pct"] = round(degc, 1)
        report["perf"]["vs_j9_compare_pass"] = degc <= 15

        # Tables still available
        ms_t, tables, ct = timed(client, "GET", "/lottery/admin/numeric-relations/tables", h)
        report["checks"]["tables_status"] = ct
        report["checks"]["table1_len"] = len(tables.get("table1") or [])
        report["checks"]["table2_len"] = len(tables.get("table2") or [])
        report["perf"]["tables_ms"] = round(ms_t, 1)

        # Verdict helpers
        fail = []
        if not report["checks"]["featured_exact_seven"]:
            fail.append("featured_not_exact_seven")
        if not report["checks"]["no_anguila"]:
            fail.append("anguila_visible")
        if not report["checks"]["admin_has_anguila"]:
            fail.append("admin_missing_hidden")
        if not report["cases"]["positive_occurrence"]["found"]:
            fail.append("no_positive_case")
        if not report["cases"]["negative_occurrence"]["found"]:
            fail.append("no_negative_case")
        if not report["permissions"]["admin_pass"]:
            fail.append("admin_perm")
        if not report["permissions"]["anon_denied"]:
            fail.append("anon_perm")
        if not report["perf"]["vs_j9_pass"]:
            fail.append("perf_profile_degraded")
        report["fail_flags"] = fail
        report["verdict"] = "GO PARA DESPLIEGUE" if not fail else "GO CONDICIONADO" if len(fail) <= 2 and "anguila_visible" not in fail and "admin_perm" not in fail else "NO-GO"

    (OUT / "e2e_j10_results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print(json.dumps({"verdict": report["verdict"], "fail": report["fail_flags"], "featured": report["checks"].get("featured_names"), "perf_vs_j9": report["perf"].get("vs_j9_profile_pct"), "profile_avg": (report["perf"].get("profile_35") or {}).get("all")}, indent=2))
    return 0 if report["verdict"] != "NO-GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
