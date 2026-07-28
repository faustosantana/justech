#!/usr/bin/env python3
"""Resolve OFFICIAL_LOTTERY_SCOPE names and count 35+14 same-day."""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.services.lottery_aliases import LotteryResolver

SCOPE = (
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
        resolver = LotteryResolver(db)
        resolved = []
        failed = []
        ids = []
        for name in SCOPE:
            try:
                lot = await resolver.resolve_or_raise(name)
                resolved.append(
                    {
                        "alias": name,
                        "db_name": lot.name,
                        "id": str(lot.id),
                        "source_id": getattr(lot, "source_id", None),
                    }
                )
                ids.append(lot.id)
            except Exception as exc:  # noqa: BLE001
                failed.append({"alias": name, "error": str(exc)})

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

        official_total = 0
        if ids:
            official_total = int(
                (
                    await db.execute(
                        text(
                            """
                            WITH hits AS (
                              SELECT d.draw_date, n.number_value
                              FROM lottery_draw_numbers n
                              JOIN lottery_draws d ON d.id = n.draw_id
                              WHERE d.lottery_id = ANY(:ids)
                                AND n.number_value IN ('35', '14')
                            )
                            SELECT COUNT(*) FROM (
                              SELECT draw_date FROM hits
                              GROUP BY draw_date
                              HAVING COUNT(DISTINCT number_value) >= 2
                            ) x
                            """
                        ),
                        {"ids": ids},
                    )
                ).scalar()
                or 0
            )

        # Also run through query service if available
        from app.services.lottery_query_service import LotteryQueryService

        svc = LotteryQueryService(db)
        data = await svc.same_day_number_coincidences(["35", "14"], lotteries=None, limit_dates=5000)
        # Check external pollution in results
        external = []
        for it in data.get("items") or []:
            for a in it.get("appearances") or []:
                lot = a.get("lottery") or ""
                if lot and not any(
                    x.lower() in lot.lower()
                    for x in (
                        "nacional",
                        "leidsa",
                        "loteka",
                        "real",
                        "gana",
                    )
                ):
                    external.append(lot)

        print(
            json.dumps(
                {
                    "resolved": resolved,
                    "failed": failed,
                    "global_total_35_14": global_total,
                    "official_resolved_ids_total": official_total,
                    "query_service_total": data.get("total"),
                    "query_service_lotteries": data.get("lotteries"),
                    "external_in_query_service": sorted(set(external))[:20],
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
