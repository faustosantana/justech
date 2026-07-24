#!/usr/bin/env python3
"""J-10F DEV-only: fija el universo activo definitivo (7 loterías).

Fuente de verdad operativa: is_featured == true
Conjunto aprobado (IDs estables DEV + nombres canónicos DB):

  Loteria Nacional, Quiniela Leidsa, Quiniela Loteka, Gana Mas,
  Quiniela Real, New York 2:30, New York 10:30

No borra registros. No modifica sorteos. Idempotente.
Aborta si no está en jaios_lottery_dev.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# IDs estables verificados en jaios_lottery_dev (2026-07-24 audit)
FINAL_FEATURED: tuple[tuple[str, str], ...] = (
    ("0118037f-8f8b-4a82-899c-42cd50b6e194", "Loteria Nacional"),
    ("523875dc-c7f4-4883-b0f6-b440397e3aeb", "Quiniela Leidsa"),
    ("b9f2c5a2-bc3e-4382-9b6d-3cee16db00fd", "Quiniela Loteka"),
    ("43250709-ee65-476f-91f6-cb8438f49d65", "Gana Mas"),
    ("205c58d2-cfcf-44e6-894d-97358b3d540b", "Quiniela Real"),
    ("1c488641-adb6-4790-89e7-879d361da7cc", "New York 2:30"),
    ("1624b6f2-88c6-42b5-a597-bf9c0f98a6b5", "New York 10:30"),
)

FORBIDDEN_AS_FEATURED_NAMES = ("Loto Leidsa", "Loto Real")

DSN_DEFAULT = "postgresql://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev"


def _abort(msg: str, code: int = 2) -> None:
    print(f"ABORT: {msg}", file=sys.stderr)
    raise SystemExit(code)


async def _connect(dsn: str):
    try:
        import asyncpg
    except ImportError:
        # fallback via docker exec is not used here; require asyncpg in venv
        _abort("asyncpg no instalado; use: pip install asyncpg")
    if "jaios_lottery_dev" not in dsn:
        _abort("DSN must target jaios_lottery_dev")
    if any(x in dsn.lower() for x in ("prod", "production", "5432/jaios")):
        _abort("DSN looks like production — refusing")
    conn = await asyncpg.connect(dsn)
    db = await conn.fetchval("SELECT current_database()")
    if db != "jaios_lottery_dev":
        await conn.close()
        _abort(f"connected to {db}, expected jaios_lottery_dev")
    return conn


async def audit(conn) -> dict:
    wanted_ids = {i for i, _ in FINAL_FEATURED}
    wanted_names = {n for _, n in FINAL_FEATURED}
    rows = await conn.fetch(
        """
        SELECT id::text AS id, name, is_featured, draw_count,
               last_draw_date::text AS last_draw_date, country, timezone
        FROM lottery_lotteries
        WHERE COALESCE(is_aggregate, false) = false
        ORDER BY name
        """
    )
    by_id = {r["id"]: dict(r) for r in rows}
    plan = []
    missing = []
    name_mismatch = []
    for lid, expected_name in FINAL_FEATURED:
        row = by_id.get(lid)
        if not row:
            missing.append({"id": lid, "expected_name": expected_name})
            continue
        if row["name"] != expected_name:
            name_mismatch.append(
                {"id": lid, "expected_name": expected_name, "actual_name": row["name"]}
            )
        plan.append(
            {
                "id": lid,
                "name": row["name"],
                "is_featured_before": bool(row["is_featured"]),
                "is_featured_after": True,
                "draw_count": row["draw_count"],
                "last_draw_date": row["last_draw_date"],
                "country": row["country"],
                "timezone": row["timezone"],
            }
        )
    deactivate = []
    for r in rows:
        if r["id"] not in wanted_ids and r["is_featured"]:
            deactivate.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "is_featured_before": True,
                    "is_featured_after": False,
                    "draw_count": r["draw_count"],
                }
            )
    featured_now = sorted(r["name"] for r in rows if r["is_featured"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": "jaios_lottery_dev",
        "wanted_ids": sorted(wanted_ids),
        "wanted_names": sorted(wanted_names),
        "featured_before": featured_now,
        "activate_or_keep": plan,
        "deactivate": deactivate,
        "missing": missing,
        "name_mismatch": name_mismatch,
        "forbidden_still_featured_risk": [
            r["name"] for r in rows if r["name"] in FORBIDDEN_AS_FEATURED_NAMES and r["is_featured"]
        ],
    }


async def apply(conn, evidence: dict) -> dict:
    if evidence["missing"] or evidence["name_mismatch"]:
        _abort(f"identity ambiguity: {evidence['missing']} {evidence['name_mismatch']}")
    wanted_ids = [i for i, _ in FINAL_FEATURED]
    async with conn.transaction():
        await conn.execute("UPDATE lottery_lotteries SET is_featured = false")
        for lid in wanted_ids:
            n = await conn.fetchval(
                "UPDATE lottery_lotteries SET is_featured = true WHERE id = $1::uuid RETURNING name",
                lid,
            )
            if not n:
                _abort(f"failed to feature {lid}")
    after = await conn.fetch(
        "SELECT id::text AS id, name FROM lottery_lotteries WHERE is_featured = true ORDER BY name"
    )
    names = [r["name"] for r in after]
    if len(after) != 7:
        _abort(f"expected 7 featured, got {len(after)}: {names}")
    for forbidden in FORBIDDEN_AS_FEATURED_NAMES:
        if forbidden in names:
            _abort(f"{forbidden} still featured")
    expected = sorted(n for _, n in FINAL_FEATURED)
    if sorted(names) != expected:
        _abort(f"name set mismatch: got {sorted(names)} expected {expected}")
    return {
        "featured_after": [{"id": r["id"], "name": r["name"]} for r in after],
        "count": len(after),
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    parser.add_argument("--dsn", default=os.environ.get("PG_DSN", DSN_DEFAULT))
    parser.add_argument(
        "--evidence-dir",
        default="docs/lottery/numeric_relations_artifacts/phase_j10_final_scope",
    )
    args = parser.parse_args()
    out_dir = Path(args.evidence_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = await _connect(args.dsn)
    try:
        evidence = await audit(conn)
        dry_path = out_dir / "01_featured_audit_before.json"
        dry_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({"dry_run": True, "wrote": str(dry_path), **{k: evidence[k] for k in (
            "featured_before", "deactivate", "missing", "name_mismatch", "forbidden_still_featured_risk"
        )}}, indent=2, ensure_ascii=False))
        if evidence["missing"] or evidence["name_mismatch"]:
            _abort("resolve identity ambiguity before apply")
        if not args.apply:
            print("OK dry-run (no writes)")
            return 0
        result = await apply(conn, evidence)
        after_path = out_dir / "02_featured_after.json"
        payload = {**evidence, "apply_result": result}
        after_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({"applied": True, "wrote": str(after_path), **result}, indent=2, ensure_ascii=False))
        print("OK j10f_set_final_featured_lotteries_dev")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
