#!/usr/bin/env python3
"""DEV-only incremental sync for Validation Lab C5 (2026-07-22 .. 2026-07-23).

HARD CONSTRAINTS:
- Only writes to jaios_lottery_dev @ 127.0.0.1:5433
- Never touches Production
- Incremental, idempotent, auditable
- Does not modify NR motor / tables
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import asyncpg

DEV_DSN = "postgresql://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev"
ALLOWED_DB = "jaios_lottery_dev"
ALLOWED_PORT = 5433
BASE_URL = "https://api.elboletoganador.com/api"
USER_AGENT = "JAIOS-ValidationLab-C5/0.1 (+dev-only; incremental)"
FROM_D = date(2026, 7, 22)
TO_D = date(2026, 7, 23)
EVIDENCE = Path(__file__).resolve().parents[2] / "docs/lottery/validation/evidence"
DELAY = 2.6


def _assert_dev_dsn(dsn: str) -> None:
    low = dsn.lower()
    if "5433" not in low or ALLOWED_DB not in low:
        raise SystemExit(f"REFUSED: not DEV DSN ({dsn})")
    if "jaios.justech" in low or "production" in low:
        raise SystemExit(f"REFUSED: looks like production ({dsn})")


def _fetch(source_id: int, d: date) -> list[dict]:
    url = f"{BASE_URL}/sorteos/buscar/historial?id={source_id}&fecha={d.isoformat()}"
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    items = (
        payload
        if isinstance(payload, list)
        else payload.get("historial") or payload.get("data") or []
    )
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        dd = str(item.get("fecha_sorteo") or "")[:10]
        if dd != d.isoformat():
            continue
        out.append(item)
    time.sleep(DELAY)
    return out


def _parse_numbers(item: dict) -> list[str]:
    raw = item.get("premios") or ""
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.replace(",", "-").split("-") if p.strip()]
    elif isinstance(raw, list):
        parts = [str(x).strip() for x in raw]
    else:
        parts = []
    nums = []
    for p in parts:
        if p.isdigit():
            nums.append(str(int(p)))  # store without forcing zfill; keep int form as existing rows
        else:
            nums.append(p)
    return nums


def _hash(lottery_id: str, draw_date: str, numbers: list[str], source_ref: str) -> str:
    material = f"{lottery_id}|{draw_date}|{','.join(numbers)}|{source_ref}"
    return hashlib.sha256(material.encode()).hexdigest()


async def main() -> int:
    _assert_dev_dsn(DEV_DSN)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    conn = await asyncpg.connect(DEV_DSN)
    try:
        dbname = await conn.fetchval("select current_database()")
        # Docker maps host 5433 → container 5432; trust DSN host port + database name.
        if dbname != ALLOWED_DB:
            raise SystemExit(f"REFUSED: connected to database {dbname}")
        port = ALLOWED_PORT

        before = int(await conn.fetchval("select count(*) from lottery_draws"))
        featured = await conn.fetch(
            "select id::text, name, source_id from lottery_lotteries where is_featured=true order by name"
        )
        if len(featured) != 7:
            raise SystemExit(f"FEATURED_SEVEN broken: {len(featured)}")
        uuid_set = {r["id"] for r in featured}
        expected = {
            "43250709-ee65-476f-91f6-cb8438f49d65",
            "0118037f-8f8b-4a82-899c-42cd50b6e194",
            "1624b6f2-88c6-42b5-a597-bf9c0f98a6b5",
            "1c488641-adb6-4790-89e7-879d361da7cc",
            "523875dc-c7f4-4883-b0f6-b440397e3aeb",
            "b9f2c5a2-bc3e-4382-9b6d-3cee16db00fd",
            "205c58d2-cfcf-44e6-894d-97358b3d540b",
        }
        if uuid_set != expected:
            raise SystemExit(f"FEATURED UUID mismatch: {uuid_set ^ expected}")

        src_map = {int(r["source_id"]): dict(r) for r in featured}
        report = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "database": dbname,
            "port": int(port),
            "from_date": FROM_D.isoformat(),
            "to_date": TO_D.isoformat(),
            "draws_before": before,
            "fetched": [],
            "inserted": [],
            "skipped_existing": [],
            "errors": [],
            "production_touched": False,
        }

        dates = [FROM_D, TO_D]
        for sid, meta in sorted(src_map.items()):
            for d in dates:
                try:
                    items = _fetch(sid, d)
                except Exception as exc:
                    report["errors"].append({"source_id": sid, "date": d.isoformat(), "error": str(exc)})
                    continue
                for item in items:
                    nums = _parse_numbers(item)
                    source_ref = str(item.get("id") or item.get("numero_sorteo") or "")
                    row = {
                        "lottery_uuid": meta["id"],
                        "lottery_name": meta["name"],
                        "source_id": sid,
                        "draw_date": d.isoformat(),
                        "source_reference": source_ref,
                        "numbers": nums,
                        "hora": item.get("hora"),
                        "raw": item,
                    }
                    report["fetched"].append(
                        {k: row[k] for k in row if k != "raw"}
                    )
                    exists = await conn.fetchval(
                        """
                        select id::text from lottery_draws
                        where lottery_id=$1::uuid and draw_date=$2::date
                          and source_reference=$3
                        limit 1
                        """,
                        meta["id"],
                        d,
                        source_ref,
                    )
                    if exists:
                        report["skipped_existing"].append(
                            {"draw_id": exists, "source_reference": source_ref, "lottery": meta["name"]}
                        )
                        continue
                    # also skip if same lottery+date already present (idempotent natural key)
                    exists2 = await conn.fetchval(
                        """
                        select id::text from lottery_draws
                        where lottery_id=$1::uuid and draw_date=$2::date
                        limit 1
                        """,
                        meta["id"],
                        d,
                    )
                    if exists2:
                        report["skipped_existing"].append(
                            {
                                "draw_id": exists2,
                                "reason": "lottery_date_exists",
                                "lottery": meta["name"],
                                "date": d.isoformat(),
                            }
                        )
                        continue

                    draw_id = uuid.uuid4()
                    ch = _hash(meta["id"], d.isoformat(), nums, source_ref)
                    async with conn.transaction():
                        await conn.execute(
                            """
                            insert into lottery_draws (
                              id, lottery_id, draw_date, draw_time, game_name,
                              source_reference, source_url, content_hash, raw_payload, scraped_at,
                              created_at, updated_at
                            ) values (
                              $1::uuid, $2::uuid, $3::date, null, 'quiniela',
                              $4, $5, $6, $7::jsonb, now(), now(), now()
                            )
                            """,
                            str(draw_id),
                            meta["id"],
                            d,
                            source_ref,
                            f"{BASE_URL}/sorteos/buscar/historial?id={sid}&fecha={d.isoformat()}",
                            ch,
                            json.dumps(item),
                        )
                        for i, n in enumerate(nums, start=1):
                            labels = {1: "1ro", 2: "2do", 3: "3ro"}
                            await conn.execute(
                                """
                                insert into lottery_draw_numbers (
                                  id, draw_id, position, position_label, number_value, number_raw, number_type, created_at
                                ) values ($1::uuid, $2::uuid, $3, $4, $5, $6, 'principal', now())
                                """,
                                str(uuid.uuid4()),
                                str(draw_id),
                                i,
                                labels.get(i, f"posición {i}"),
                                str(int(n)) if str(n).isdigit() else str(n),
                                str(n),
                            )
                        await conn.execute(
                            """
                            update lottery_lotteries
                            set draw_count = coalesce(draw_count,0) + 1,
                                last_draw_date = greatest(coalesce(last_draw_date, $2::date), $2::date),
                                updated_at = now()
                            where id=$1::uuid
                            """,
                            meta["id"],
                            d,
                        )
                    report["inserted"].append(
                        {
                            "draw_id": str(draw_id),
                            "lottery_uuid": meta["id"],
                            "lottery_name": meta["name"],
                            "source_id": sid,
                            "draw_date": d.isoformat(),
                            "source_reference": source_ref,
                            "numbers": nums,
                            "content_hash": ch,
                        }
                    )

        after = int(await conn.fetchval("select count(*) from lottery_draws"))
        report["draws_after"] = after
        report["rows_added"] = after - before
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["featured_count"] = 7
        report["rollback_delete_draw_ids"] = [x["draw_id"] for x in report["inserted"]]

        # C5 probe after sync
        c5 = {}
        for name, d in (("New York 2:30", FROM_D), ("Loteria Nacional", FROM_D), ("Gana Mas", TO_D)):
            r = await conn.fetchrow(
                """
                select l.id::text as lottery_uuid, l.name, d.id::text as draw_id, d.draw_date,
                       d.source_reference, array_agg(dn.number_value order by dn.position) as numbers
                from lottery_draws d
                join lottery_lotteries l on l.id=d.lottery_id
                join lottery_draw_numbers dn on dn.draw_id=d.id
                where l.name=$1 and d.draw_date=$2::date
                group by l.id, l.name, d.id, d.draw_date, d.source_reference
                """,
                name,
                d,
            )
            c5[f"{name}:{d.isoformat()}"] = dict(r) if r else None
        report["c5_probe"] = c5

        out = EVIDENCE / "c5_dev_sync_report.json"
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(json.dumps({k: report[k] for k in (
            "draws_before","draws_after","rows_added","inserted","skipped_existing","errors","c5_probe"
        )}, indent=2, ensure_ascii=False, default=str))
        print("wrote", out)
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
