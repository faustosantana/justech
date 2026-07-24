#!/usr/bin/env python3
"""J-10S E2E + fair/real perf checks (DEV only)."""
from __future__ import annotations

import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8001/api/v1"
OUT = Path(__file__).resolve().parent


def req(method: str, path: str, body=None, token=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(r, timeout=180) as resp:
            payload = json.loads(resp.read().decode())
            return resp.status, (time.perf_counter() - t0) * 1000, payload
    except urllib.error.HTTPError as e:
        raw = e.read().decode()[:400]
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw}
        return e.code, (time.perf_counter() - t0) * 1000, payload


def summarize(times: list[float]):
    if not times:
        return {}
    s = sorted(times)
    return {
        "n": len(times),
        "min_ms": round(min(times), 1),
        "max_ms": round(max(times), 1),
        "avg_ms": round(statistics.mean(times), 1),
        "median_ms": round(statistics.median(times), 1),
        "p95_ms": round(s[int(0.95 * (len(s) - 1))], 1),
    }


def main():
    report: dict = {
        "api": API,
        "production_untouched": True,
        "checks": {},
        "cases": {},
        "permissions": {},
        "perf": {},
        "fail_flags": [],
        "verdict": "GO PARA DESPLIEGUE",
    }

    st, ms, tok = req(
        "POST",
        "/auth/login",
        {
            "email": "uat-nr-admin@example.com",
            "password": "UatDevNumericRelations2026!",
            "tenant_slug": "uat-numeric-relations",
        },
    )
    token = tok.get("access_token") or tok.get("token")
    assert st == 200 and token, tok

    st, _, health = req("GET", "/health", token=token)
    # health path may be /api/v1/health already via API prefix
    st, _, health = req("GET", "/../health".replace("/../", "/") ) if False else (200, 0, {})
    with urllib.request.urlopen("http://127.0.0.1:8001/api/v1/health", timeout=10) as r:
        health = json.loads(r.read().decode())
    report["health"] = health
    if health.get("database_target") != "jaios_lottery_dev" or not health.get("production_forbidden"):
        report["fail_flags"].append("production_risk")
        report["verdict"] = "NO-GO"

    st, _, admin_lots = req("GET", "/lottery/admin/lotteries", token=token)
    items = admin_lots if isinstance(admin_lots, list) else (admin_lots.get("items") or [])
    featured = [x for x in items if x.get("is_featured")]
    names = sorted(x["name"] for x in featured)
    expected = sorted(
        [
            "Gana Mas",
            "Loteria Nacional",
            "Loto Leidsa",
            "Loto Real",
            "Quiniela Leidsa",
            "Quiniela Loteka",
            "Quiniela Real",
        ]
    )
    report["checks"]["featured_names"] = names
    report["checks"]["featured_exact_seven"] = names == expected
    report["checks"]["no_anguila"] = not any("Anguila" in n for n in names)
    if not report["checks"]["featured_exact_seven"]:
        report["fail_flags"].append("featured_mismatch")

    lids = [x["id"] for x in featured]
    fair_names = ["Quiniela Leidsa", "Quiniela Loteka", "Loteria Nacional", "Quiniela Real"]
    by = {x["name"]: x["id"] for x in items}
    fair_ids = [by[n] for n in fair_names]

    def scope(ids):
        return {
            "primary_lottery_ids": ids,
            "confirming_lottery_ids": ids,
            "follow_up_lottery_ids": ids,
        }

    cw = {"mode": "SAME_DRAW", "timezone": "America/Santo_Domingo"}

    def profile(num, ids, **extra):
        body = {
            "number": num,
            "scope": scope(ids),
            "confirmation_window": cw,
            "max_horizon": 7,
            **extra,
        }
        return req("POST", "/lottery/admin/numeric-relations/history/numbers/profile", body, token)

    def occ(num, ids, condition):
        body = {
            "number": num,
            "scope": scope(ids),
            "confirmation_window": cw,
            "max_horizon": 7,
            "page": 1,
            "page_size": 20,
            "condition": condition,
            "order": "desc",
        }
        return req("POST", "/lottery/admin/numeric-relations/history/numbers/occurrences", body, token)

    # Cases
    st, ms, p50 = profile(50, lids)
    report["cases"]["positive_50"] = {
        "status": st,
        "positivas": (p50.get("condition_summary") or {}).get("positivas"),
        "senales": len((p50.get("charts") or {}).get("senales") or []),
        "ms": round(ms, 1),
    }
    st, _, opos = occ(50, lids, "positive")
    pos_item = (opos.get("items") or [None])[0]
    report["cases"]["positive_occurrence"] = {
        "found": bool(pos_item),
        "estado": (pos_item or {}).get("estado"),
        "draw_id": (pos_item or {}).get("draw_id"),
    }

    st, ms, p35 = profile(35, lids)
    report["cases"]["partial_or_neg_35"] = {
        "status": st,
        "positivas": (p35.get("condition_summary") or {}).get("positivas"),
        "parciales": (p35.get("condition_summary") or {}).get("parciales"),
        "negativas": (p35.get("condition_summary") or {}).get("negativas"),
        "ms": round(ms, 1),
    }
    st, _, oneg = occ(35, lids, "negative")
    neg = (oneg.get("items") or [None])[0]
    report["cases"]["negative_occurrence"] = {
        "found": bool(neg),
        "estado": (neg or {}).get("estado"),
        "draw_id": (neg or {}).get("draw_id"),
    }
    st, _, opar = occ(35, lids, "partial")
    par = (opar.get("items") or [None])[0]
    report["cases"]["partial_occurrence"] = {
        "found": bool(par),
        "estado": (par or {}).get("estado"),
        "draw_id": (par or {}).get("draw_id"),
    }

    # multi confirmers from known draw if partial exists
    multi = None
    for item in (opar.get("items") or [])[:10]:
        st, _, det = req(
            "POST",
            "/lottery/admin/numeric-relations/history/numbers/occurrences/detail",
            {
                "number": 35,
                "draw_id": item["draw_id"],
                "scope": scope(lids),
                "confirmation_window": cw,
                "max_horizon": 7,
            },
            token,
        )
        if st != 200:
            continue
        for b in ((det.get("relation_tree") or {}).get("candidatos") or []):
            confs = b.get("confirmadores_encontrados") or []
            if len(confs) >= 2:
                multi = {
                    "draw_id": item["draw_id"],
                    "candidato": b.get("candidato"),
                    "confirmadores": confs,
                    "confirmaciones": b.get("confirmaciones"),
                    "estado": item.get("estado"),
                }
                break
        if multi:
            break
    report["cases"]["multi_confirmers"] = multi

    # tables
    st, ms, tables = req("GET", "/lottery/admin/numeric-relations/tables", token=token)
    report["checks"]["tables_status"] = st
    report["checks"]["table1_len"] = len(tables.get("table1") or [])
    report["checks"]["table2_len"] = len(tables.get("table2") or [])

    # permissions
    st_c, _, client_tok = req(
        "POST",
        "/auth/login",
        {
            "email": "uat-nr-client@example.com",
            "password": "UatDevNumericRelations2026!",
            "tenant_slug": "uat-numeric-relations",
        },
    )
    ct = (client_tok.get("access_token") or client_tok.get("token")) if st_c == 200 else None
    body35 = {"number": 35, "scope": scope(fair_ids), "confirmation_window": cw, "max_horizon": 7}
    admin_st, _, _ = req("POST", "/lottery/admin/numeric-relations/history/numbers/profile", body35, token)
    client_st, _, _ = req("POST", "/lottery/admin/numeric-relations/history/numbers/profile", body35, ct) if ct else (403, 0, {})
    anon_st, _, _ = req("POST", "/lottery/admin/numeric-relations/history/numbers/profile", body35, None)
    report["permissions"] = {
        "admin_profile": admin_st,
        "client_profile": client_st,
        "anon_profile": anon_st,
        "admin_pass": admin_st == 200,
        "client_denied_or_limited": client_st in (401, 403),
        "anon_denied": anon_st in (401, 403),
    }
    if not all(
        [
            report["permissions"]["admin_pass"],
            report["permissions"]["client_denied_or_limited"],
            report["permissions"]["anon_denied"],
        ]
    ):
        report["fail_flags"].append("permissions")
        report["verdict"] = "NO-GO"

    # Perf A fair J-9 scope
    fair_times = []
    for i in range(10):
        st, ms, p = profile(35, fair_ids)
        fair_times.append(ms)
        if i == 0:
            report["perf"]["fair_aparecio"] = (p.get("header") or {}).get("aparecio")
    fair = summarize(fair_times)
    fair["cold_ms"] = round(fair_times[0], 1)
    fair["hot"] = summarize(fair_times[1:])
    j9 = 1827.5
    fair["j9_baseline_avg"] = j9
    fair["delta_pct"] = round((fair["avg_ms"] - j9) / j9 * 100, 1)
    fair["pass_within_15pct"] = fair["delta_pct"] <= 15
    report["perf"]["fair_j9_scope"] = fair
    if not fair["pass_within_15pct"]:
        report["fail_flags"].append("perf_fair_degraded")

    # Perf B featured-7 experience
    feat_times = []
    for _ in range(5):
        st, ms, _ = profile(35, lids)
        feat_times.append(ms)
    report["perf"]["featured7_profile_35"] = summarize(feat_times)

    hub_times = []
    for _ in range(10):
        st, ms, _ = req("GET", "/lottery/admin/lotteries", token=token)
        hub_times.append(ms)
    report["perf"]["admin_lotteries"] = summarize(hub_times)

    t_times = []
    for _ in range(10):
        st, ms, _ = req("GET", "/lottery/admin/numeric-relations/tables", token=token)
        t_times.append(ms)
    report["perf"]["tables"] = summarize(t_times)

    # Gate functional
    if not report["cases"]["positive_occurrence"].get("found"):
        report["fail_flags"].append("missing_positive")
    if not report["cases"]["negative_occurrence"].get("found"):
        report["fail_flags"].append("missing_negative")
    if not report["cases"]["partial_occurrence"].get("found"):
        report["fail_flags"].append("missing_partial")

    if report["fail_flags"]:
        if report["verdict"] != "NO-GO":
            report["verdict"] = "GO CONDICIONADO" if all(
                f.startswith("perf_") or f.startswith("minor_") for f in report["fail_flags"]
            ) else ("NO-GO" if any(f in ("permissions", "production_risk", "featured_mismatch") for f in report["fail_flags"]) else "GO CONDICIONADO")

    if not report["fail_flags"]:
        report["verdict"] = "GO PARA DESPLIEGUE"

    path = OUT / "e2e_j10s_results.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"verdict": report["verdict"], "fail": report["fail_flags"], "fair_delta": fair.get("delta_pct"), "featured": names}, indent=2))


if __name__ == "__main__":
    main()
