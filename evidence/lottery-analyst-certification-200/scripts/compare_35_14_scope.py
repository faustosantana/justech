#!/usr/bin/env python3
"""Compare same-day 35+14: global vs official 7."""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import text

from app.db.session import AsyncSessionLocal

OFFICIAL = (
    "Nacional",
    "Nacional Día",
    "Nacional Noche",
    "Leidsa",
    "Loteka",
    "Real",
    "Gana Más",
)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        catalog = int(
            (await db.execute(text("SELECT COUNT(*) FROM lottery_lotteries"))).scalar() or 0
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
        official_total = int(
            (
                await db.execute(
                    text(
                        """
                        WITH scoped AS (
                          SELECT id FROM lottery_lotteries
                          WHERE name = ANY(:names)
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
                    {"names": list(OFFICIAL)},
                )
            ).scalar()
            or 0
        )
        external_in_global = (
            await db.execute(
                text(
                    """
                    WITH hits AS (
                      SELECT d.draw_date, n.number_value, l.name
                      FROM lottery_draw_numbers n
                      JOIN lottery_draws d ON d.id = n.draw_id
                      JOIN lottery_lotteries l ON l.id = d.lottery_id
                      WHERE n.number_value IN ('35', '14')
                    ),
                    days AS (
                      SELECT draw_date FROM hits
                      GROUP BY draw_date
                      HAVING COUNT(DISTINCT number_value) >= 2
                    )
                    SELECT DISTINCT l.name
                    FROM lottery_draws d
                    JOIN lottery_lotteries l ON l.id = d.lottery_id
                    JOIN lottery_draw_numbers n ON n.draw_id = d.id
                    WHERE d.draw_date IN (SELECT draw_date FROM days)
                      AND n.number_value IN ('35', '14')
                      AND l.name !~* '(Nacional|Leidsa|Loteka|Real|Gana)'
                    ORDER BY 1
                    LIMIT 30
                    """
                )
            )
        ).scalars().all()

        # Resolve official IDs present
        present = (
            await db.execute(
                text("SELECT name FROM lottery_lotteries WHERE name = ANY(:names) ORDER BY 1"),
                {"names": list(OFFICIAL)},
            )
        ).scalars().all()

        out = {
            "catalog_size": catalog,
            "global_total_35_14": global_total,
            "official7_total_35_14": official_total,
            "official_names_present": list(present),
            "external_names_in_global_hits": list(external_in_global),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
