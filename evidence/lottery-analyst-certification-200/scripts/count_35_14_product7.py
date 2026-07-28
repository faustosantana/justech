#!/usr/bin/env python3
"""Count 35+14 on product seven DB names."""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import text

from app.db.session import AsyncSessionLocal

DB_NAMES = (
    "Gana Mas",
    "Loteria Nacional",
    "New York 10:30",
    "New York 2:30",
    "Quiniela Leidsa",
    "Quiniela Loteka",
    "Quiniela Real",
)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        present = (
            await db.execute(
                text("SELECT name FROM lottery_lotteries WHERE name = ANY(:n) ORDER BY 1"),
                {"n": list(DB_NAMES)},
            )
        ).scalars().all()
        official = int(
            (
                await db.execute(
                    text(
                        """
                        WITH scoped AS (
                          SELECT id FROM lottery_lotteries WHERE name = ANY(:n)
                        ),
                        hits AS (
                          SELECT d.draw_date, n.number_value
                          FROM lottery_draw_numbers n
                          JOIN lottery_draws d ON d.id = n.draw_id
                          WHERE d.lottery_id IN (SELECT id FROM scoped)
                            AND n.number_value IN ('35', '14')
                        )
                        SELECT COUNT(*) FROM (
                          SELECT draw_date FROM hits
                          GROUP BY draw_date
                          HAVING COUNT(DISTINCT number_value) >= 2
                        ) x
                        """
                    ),
                    {"n": list(DB_NAMES)},
                )
            ).scalar()
            or 0
        )
        global_total = int(
            (
                await db.execute(
                    text(
                        """
                        WITH hits AS (
                          SELECT d.draw_date, n.number_value
                          FROM lottery_draw_numbers n
                          JOIN lottery_draws d ON d.id = n.draw_id
                          WHERE n.number_value IN ('35', '14')
                        )
                        SELECT COUNT(*) FROM (
                          SELECT draw_date FROM hits
                          GROUP BY draw_date
                          HAVING COUNT(DISTINCT number_value) >= 2
                        ) x
                        """
                    )
                )
            ).scalar()
            or 0
        )
        print(
            json.dumps(
                {
                    "present": list(present),
                    "global_total_35_14": global_total,
                    "official7_total_35_14": official,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
