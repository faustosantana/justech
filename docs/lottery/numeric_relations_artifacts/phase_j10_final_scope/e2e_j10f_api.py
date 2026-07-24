#!/usr/bin/env python3
"""J-10F — Validación API: universo final, exclusiones, permisos, perfiles."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

import httpx

API = "http://127.0.0.1:8001/api/v1"
PASS = "UatDevNumericRelations2026!"
OUT = Path("docs/lottery/numeric_relations_artifacts/phase_j10_final_scope")
EXPECTED = {
    "Loteria Nacional",
    "Quiniela Leidsa",
    "Quiniela Loteka",
    "Gana Mas",
    "Quiniela Real",
    "New York 2:30",
    "New York 10:30",
}
FORBIDDEN = {"Loto Leidsa", "Loto Real", "Anguila", "Haiti", "Miami"}
FINAL_IDS = [
    "0118037f-8f8b-4a82-899c-42cd50b6e194",
    "523875dc-c7f4-4883-b0f6-b440397e3aeb",
    "b9f2c5a2-bc3e-4382-9b6d-3cee16db00fd",
    "43250709-ee65-476f-91f6-cb8438f49d65",
    "205c58d2-cfcf-44e6-894d-97358b3d540b",
    "1c488641-adb6-4790-89e7-879d361da7cc",
    "1624b6f2-88c6-42b5-a597-bf9c0f98a6b5",
]


def login(client: httpx.Client, email: str) -> tuple[str, str]:
    r = client.post(
        f"{API}/auth/login",
        json={"email": email, "password": PASS, "tenant_slug": "uat-numeric-relations"},
    )
    r.raise_for_status()
    data = r.json()
    return data["access_token"], str(data.get("tenant_id") or data.get("tenant", {}).get("id") or "")


def auth_headers(token: str, tenant: str) -> dict[str, str]:
    h = {"Authorization": f"Bearer {token}"}
    if tenant:
        h["X-Tenant-Id"] = tenant
    return h


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict = {"checks": [], "perf": {}, "profiles": {}}
    ok = True

    def check(name: str, cond: bool, detail=None):
        nonlocal ok
        if isinstance(detail, set):
            detail = sorted(detail)
        results["checks"].append({"name": name, "pass": bool(cond), "detail": detail})
        if not cond:
            ok = False
            print("FAIL", name, detail)
        else:
            print("PASS", name)

    with httpx.Client(timeout=120.0) as client:
        health = client.get(f"{API}/health").json()
        check("production_forbidden", health.get("production_forbidden") is True, health)
        check("db_dev", health.get("database_target") == "jaios_lottery_dev", health)

        tok, ten = login(client, "uat-nr-admin@example.com")
        h = auth_headers(tok, ten)

        # Catalog featured
        cat = client.get(f"{API}/lottery/catalog", params={"featured_only": True, "page_size": 50}, headers=h)
        check("catalog_featured_200", cat.status_code == 200, cat.status_code)
        items = (cat.json() or {}).get("items") or []
        names = {i.get("name") for i in items}
        check("featured_count_7", len(items) == 7, len(items))
        check("featured_names_exact", names == EXPECTED, sorted(names))
        for bad in ("Loto Leidsa", "Loto Real"):
            check(f"no_{bad.replace(' ', '_')}", bad not in names, names)

        # NR lotteries active
        nr = client.get(f"{API}/lottery/admin/numeric-relations/lotteries", params={"scope": "active"}, headers=h)
        check("nr_lotteries_active_200", nr.status_code == 200, nr.status_code)
        nr_items = (nr.json() or {}).get("items") or []
        nr_names = {i.get("name") for i in nr_items}
        check("nr_active_count_7", len(nr_items) == 7, len(nr_items))
        check("nr_active_names", nr_names == EXPECTED, sorted(nr_names))
        check("nr_no_anguila", not any("Anguila" in n for n in nr_names), nr_names)
        check("nr_no_haiti", not any("Haiti" in n for n in nr_names), nr_names)
        check("nr_no_miami", not any("Miami" in n for n in nr_names), nr_names)

        archived = client.get(
            f"{API}/lottery/admin/numeric-relations/lotteries", params={"scope": "archived"}, headers=h
        )
        arch_items = (archived.json() or {}).get("items") or []
        arch_names = {i.get("name") for i in arch_items}
        check("archived_has_loto_leidsa", "Loto Leidsa" in arch_names, sorted(arch_names)[:20])
        check("archived_has_loto_real", "Loto Real" in arch_names)
        check("archived_not_empty", len(arch_items) > 0, len(arch_items))

        # Reject / ignore non-active id in analyze
        loto_leidsa = "e76951f3-c120-4787-aeae-2225187fd769"
        body_bad = {"observed_number": 35, "lottery_ids": [loto_leidsa]}
        an = client.post(f"{API}/lottery/admin/numeric-relations/analyze", json=body_bad, headers=h)
        # should 400 (no active left) or 200 with ignored — policy raises if empty
        check(
            "analyze_rejects_only_archived",
            an.status_code in (400, 422) or (
                an.status_code == 200 and (an.json().get("metadata") or {}).get("ignored_non_active_count", 0) >= 1
            ),
            {"status": an.status_code, "body": an.text[:300]},
        )

        scope = {
            "primary_lottery_ids": FINAL_IDS,
            "confirming_lottery_ids": FINAL_IDS,
            "follow_up_lottery_ids": FINAL_IDS,
        }
        window = {"mode": "SAME_DRAW", "timezone": "America/Santo_Domingo"}

        def profile(n: int):
            t0 = time.perf_counter()
            r = client.post(
                f"{API}/lottery/admin/numeric-relations/history/numbers/profile",
                json={"number": n, "scope": scope, "confirmation_window": window, "max_horizon": 7},
                headers=h,
            )
            ms = (time.perf_counter() - t0) * 1000
            return r, ms

        for n in (50, 35, 86):
            times = []
            last = None
            for i in range(3):
                r, ms = profile(n)
                times.append(ms)
                last = r
            check(f"profile_{n}_200", last is not None and last.status_code == 200, last.status_code if last else None)
            data = last.json() if last and last.status_code == 200 else {}
            meta = data.get("analysis_scope_meta") or {}
            check(f"profile_{n}_scope", meta.get("analysis_scope") == "FEATURED_SEVEN", meta)
            check(f"profile_{n}_count7", meta.get("active_lottery_count") == 7, meta.get("active_lottery_count"))
            # ensure no archived lottery names in charts
            lot_chart = (data.get("charts") or {}).get("apariciones_por_loteria") or []
            lot_names = {x.get("loteria") for x in lot_chart}
            check(
                f"profile_{n}_no_loto_leidsa_chart",
                "Loto Leidsa" not in lot_names,
                sorted(list(lot_names)),
            )
            results["profiles"][str(n)] = {
                "header": data.get("header"),
                "condition_summary": data.get("condition_summary"),
                "active_lottery_names": meta.get("active_lottery_names"),
                "scope_set_hash": meta.get("scope_set_hash"),
                "sample_size": data.get("sample_size"),
                "evaluable_events": data.get("evaluable_events"),
                "perf_ms": times,
            }
            results["perf"][f"profile_{n}"] = {
                "avg": round(statistics.mean(times), 1),
                "median": round(statistics.median(times), 1),
                "p95": round(sorted(times)[max(0, int(0.95 * (len(times) - 1)))], 1),
                "samples": [round(x, 1) for x in times],
            }

        # Permissions
        ctok, cten = login(client, "uat-nr-client@example.com")
        ch = auth_headers(ctok, cten)
        denied = client.get(f"{API}/lottery/admin/numeric-relations/lotteries", headers=ch)
        check("client_403_or_401", denied.status_code in (401, 403), denied.status_code)
        anon = client.get(f"{API}/lottery/admin/numeric-relations/lotteries")
        check("anon_401", anon.status_code in (401, 403), anon.status_code)

        # Tables still return formulas internally
        tables = client.get(f"{API}/lottery/admin/numeric-relations/tables", headers=h)
        check("tables_200", tables.status_code == 200)
        t1 = (tables.json() or {}).get("table1") or []
        check("table1_has_formula_internal", bool(t1 and t1[0].get("formula")), t1[0] if t1 else None)

    results["verdict_partial"] = "PASS" if ok else "FAIL"
    (OUT / "04_api_validation.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    print("wrote", OUT / "04_api_validation.json", "ok=", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
