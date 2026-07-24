#!/usr/bin/env python3
"""I-7 production smoke — Control Center + NR + chat + permissions. No secrets printed."""
from __future__ import annotations

import asyncio
import json
from uuid import UUID

import httpx
from sqlalchemy import select, text

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User


def ok(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"{status} {name}" + (f" — {detail}" if detail else ""))


async def main() -> None:
    async with AsyncSessionLocal() as db:
        admin = (
            await db.execute(select(User).where(User.is_superadmin == True).limit(1))  # noqa: E712
        ).scalar_one()
        user = (
            await db.execute(
                select(User).where(User.is_superadmin == False, User.is_active == True).limit(1)  # noqa: E712
            )
        ).scalar_one_or_none()
        tenant = (await db.execute(text("SELECT id::text FROM tenants LIMIT 1"))).scalar_one()
        draws = (await db.execute(text("SELECT count(*) FROM jaios.lottery_draws"))).scalar_one()
        alembic = (
            await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        ).scalar_one()
        active_prompts = (
            await db.execute(
                text(
                    "SELECT id::text FROM jaios.lottery_ai_prompt_versions "
                    "WHERE status='active' ORDER BY updated_at DESC NULLS LAST LIMIT 1"
                )
            )
        ).scalar_one_or_none()

    admin_token = create_access_token(subject=str(admin.id), tenant_id=UUID(tenant), role="owner")
    headers = {"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": tenant}
    base = "http://127.0.0.1:8000/api/v1"

    print(f"META alembic={alembic} draws={draws} active_prompt={active_prompts}")

    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.get(f"{base}/health")
        ok("health", r.status_code == 200, str(r.status_code))

        r = await client.get(f"{base}/lottery/admin/numeric-relations/tables", headers=headers)
        tables = r.json() if r.status_code == 200 else {}
        t1 = tables.get("table1") or []
        t2 = tables.get("table2") or []
        n1 = next((x for x in t1 if x.get("number") == 1), None)
        n2 = next((x for x in t2 if x.get("number") == 1), None)
        ok("tables", r.status_code == 200 and len(t1) == 100 and len(t2) == 100, f"code={r.status_code}")
        ok(
            "table1_n1",
            bool(n1)
            and "1 ÷ 1220" in str(n1.get("formula"))
            and str(n1.get("visible_value", "")).startswith("0.0008196721")
            and n1.get("digits_without_point") == "00008196721"
            and int(n1.get("code")) == 34,
            str(n1.get("formula") if n1 else None),
        )
        ok(
            "table2_n1",
            bool(n2)
            and "1220" in str(n2.get("formula"))
            and n2.get("digits_without_point") == "122000000000"
            and int(n2.get("code")) == 5,
            str(n2.get("formula") if n2 else None),
        )

        r = await client.get(f"{base}/lottery/admin/numeric-relations/groups", headers=headers)
        groups = r.json() if r.status_code == 200 else {}
        g1 = groups.get("table1_groups") or {}
        g2 = groups.get("table2_groups") or {}
        ok("groups_34_53", r.status_code == 200 and "34" in g1 and "53" in g2)

        r = await client.get(f"{base}/lottery/admin/numeric-relations/lotteries", headers=headers)
        lots = (r.json() or {}).get("items") or []
        leidsa = next((x for x in lots if "leidsa" in x.get("name", "").lower()), None)
        loteka = next((x for x in lots if "loteka" in x.get("name", "").lower()), None)
        ok("lotteries", bool(leidsa and loteka), f"n={len(lots)}")

        r = await client.post(
            f"{base}/lottery/admin/numeric-relations/analyze",
            headers=headers,
            json={
                "observed_number": 26,
                "lottery_ids": [leidsa["id"]],
                "occurrence_mode": "last_k",
                "occurrence_k": 10,
            },
        )
        a26 = r.json() if r.status_code == 200 else {}
        comps = set(a26.get("direct_companions") or [])
        ok("relaciones_26", r.status_code == 200 and 27 in comps and 38 in comps, f"comps={sorted(comps)[:6]}")
        ok("llm_false", (a26.get("metadata") or {}).get("llm_calculates") is False)

        r = await client.get(f"{base}/lottery/admin/predictions/motors", headers=headers)
        motors = (r.json() or {}).get("items") or []
        nr = next((m for m in motors if m.get("key") == "numeric_relations"), None)
        freq = next((m for m in motors if m.get("key") == "frequencies"), None)
        ok("motors_nr", bool(nr and nr.get("implemented") is True))
        ok("motors_stub", bool(freq and freq.get("implemented") is False))

        r = await client.patch(
            f"{base}/lottery/admin/predictions/motors/frequencies",
            headers=headers,
            json={"enabled": True},
        )
        ok("stub_blocked", r.status_code == 400, f"code={r.status_code}")

        r = await client.post(
            f"{base}/lottery/admin/predictions/numeric-relations/run",
            headers=headers,
            json={"observed_number": 34, "lottery_ids": [leidsa["id"]], "occurrence_mode": "all"},
        )
        pred = r.json() if r.status_code == 200 else {}
        ok("prediction_34", r.status_code == 200 and isinstance(pred.get("ranking"), list))
        ok("prediction_no_guarantee", pred.get("guarantees_outcome") is False)

        r = await client.post(
            f"{base}/lottery/admin/numeric-relations/analyze",
            headers=headers,
            json={
                "observed_number": 45,
                "lottery_ids": [leidsa["id"], loteka["id"]],
                "occurrence_mode": "last_k",
                "occurrence_k": 10,
            },
        )
        multi = r.json() if r.status_code == 200 else {}
        ok("multi_45", r.status_code == 200 and len(multi.get("lottery_ids") or []) == 2)

        r = await client.get(f"{base}/lottery/admin/ai/prompt-studio/schema", headers=headers)
        schema = r.json() if r.status_code == 200 else {}
        ok("prompt_schema", r.status_code == 200 and any(b.get("key") == "identidad" for b in schema.get("blocks") or []))

        r = await client.get(f"{base}/lottery/admin/ai/prompts", headers=headers)
        prompts = r.json() if r.status_code == 200 else {}
        active = [i for i in (prompts.get("items") or []) if i.get("status") == "active"]
        ok("prompts_list", r.status_code == 200 and len(active) >= 1, f"active={len(active)}")
        if active:
            pid = active[0]["id"]
            r = await client.get(f"{base}/lottery/admin/ai/prompts/{pid}/compiled", headers=headers)
            compiled = r.json() if r.status_code == 200 else {}
            body = ((compiled.get("compiled") or {}).get("body")) or ""
            ok("prompt_compiled", r.status_code == 200 and len(body) > 0)

        # chat minimal
        r = await client.post(f"{base}/lottery/chat/sessions", headers=headers, json={"title": "i7-smoke"})
        ok("chat_session", r.status_code in (200, 201), f"code={r.status_code}")
        if r.status_code in (200, 201):
            sid = r.json().get("id")
            r = await client.post(
                f"{base}/lottery/chat/sessions/{sid}/messages",
                headers=headers,
                json={"content": "Analiza el 26 en Leidsa usando las últimas 10"},
            )
            ok("chat_message", r.status_code == 200, f"code={r.status_code}")
            # I-8 chat matrix (valid / missing / multi / absolute / stub motor)
            chat_cases = [
                ("chat_missing", "Analiza el 26"),
                ("chat_multi", "Analiza el 45 en Leidsa y Loteka usando las últimas 10"),
                ("chat_absolute", "El 34 va a salir mañana seguro"),
                ("chat_stub_motor", "Usa el motor de frecuencias para predecir el 10"),
            ]
            for label, msg in chat_cases:
                rr = await client.post(
                    f"{base}/lottery/chat/sessions/{sid}/messages",
                    headers=headers,
                    json={"content": msg},
                )
                ok(label, rr.status_code == 200, f"code={rr.status_code}")

        # permissions (backend 403 — not menu-only)
        if user:
            utok = create_access_token(subject=str(user.id), tenant_id=UUID(tenant), role="usuario")
            uh = {"Authorization": f"Bearer {utok}", "X-Tenant-ID": tenant}
            denied = []
            for label, path, method, body in [
                ("tables", f"{base}/lottery/admin/numeric-relations/tables", "GET", None),
                ("compiled", f"{base}/lottery/admin/ai/prompts/{active[0]['id']}/compiled" if active else f"{base}/lottery/admin/ai/prompts", "GET", None),
                ("prompts", f"{base}/lottery/admin/ai/prompts", "GET", None),
                ("schema", f"{base}/lottery/admin/ai/prompt-studio/schema", "GET", None),
                ("benchmark", f"{base}/lottery/admin/ai/control-center/benchmark/run", "POST", {}),
                ("export_json", f"{base}/lottery/admin/numeric-relations/export?table=table1&format=json", "GET", None),
            ]:
                if method == "GET":
                    rr = await client.get(path, headers=uh)
                else:
                    rr = await client.post(path, headers=uh, json=body or {})
                denied.append((label, rr.status_code))
            ok(
                "permisos_403",
                all(c in (401, 403) for _, c in denied),
                str(denied),
            )
        else:
            ok("permisos_403", False, "no non-admin user")

        # openapi presence (root app path — NOT under /api/v1)
        r = await client.get("http://127.0.0.1:8000/openapi.json")
        paths = (r.json() or {}).get("paths") or {}
        ok(
            "openapi_cc",
            r.status_code == 200
            and any("/lottery/admin/predictions/" in p for p in paths)
            and any("prompt-studio" in p for p in paths)
            and any("numeric-relations" in p for p in paths),
            f"code={r.status_code} paths={len(paths)}",
        )

    # post draws invariant
    async with AsyncSessionLocal() as db:
        draws2 = (await db.execute(text("SELECT count(*) FROM jaios.lottery_draws"))).scalar_one()
        active2 = (
            await db.execute(
                text(
                    "SELECT id::text FROM jaios.lottery_ai_prompt_versions "
                    "WHERE status='active' ORDER BY updated_at DESC NULLS LAST LIMIT 1"
                )
            )
        ).scalar_one_or_none()
    ok("draws_unchanged", draws2 == draws, f"{draws}->{draws2}")
    ok("active_prompt_unchanged", active2 == active_prompts, f"{active_prompts}->{active2}")


if __name__ == "__main__":
    asyncio.run(main())
