#!/usr/bin/env python3
"""J-10 DEV-only: marca las 7 loterías canónicas como destacadas.

No toca Producción. Aborta si DATABASE_URL no apunta a jaios_lottery_dev.
"""

from __future__ import annotations

import asyncio
import os
import sys

import asyncpg

CANONICAL_SEVEN = (
    "Quiniela Leidsa",
    "Quiniela Loteka",
    "Loteria Nacional",
    "Loto Leidsa",
    "Quiniela Real",
    "Loto Real",
    "Gana Mas",
)

DSN = os.environ.get(
    "PG_DSN",
    "postgresql://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev",
)


async def main() -> int:
    if "jaios_lottery_dev" not in DSN:
        print("ABORT: DSN must target jaios_lottery_dev", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(DSN)
    try:
        db = await conn.fetchval("SELECT current_database()")
        if db != "jaios_lottery_dev":
            print(f"ABORT: connected to {db}", file=sys.stderr)
            return 2
        # Clear previous featured flags then set canonical seven
        await conn.execute("UPDATE lottery_lotteries SET is_featured = false")
        missing = []
        for name in CANONICAL_SEVEN:
            n = await conn.fetchval(
                "UPDATE lottery_lotteries SET is_featured = true WHERE name = $1 RETURNING name",
                name,
            )
            if not n:
                missing.append(name)
        rows = await conn.fetch(
            "SELECT name FROM lottery_lotteries WHERE is_featured = true ORDER BY name"
        )
        print("featured:", [r["name"] for r in rows])
        if missing:
            print("MISSING:", missing, file=sys.stderr)
            return 1
        if len(rows) != 7:
            print(f"WARN: expected 7 featured, got {len(rows)}", file=sys.stderr)
            return 1
        print("OK j10_seed_featured_dev")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
