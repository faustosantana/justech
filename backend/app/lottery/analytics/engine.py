"""Lottery Analytics Engine — descriptive statistics from real DB data only.

No predictions. Hot/cold = historical descriptors with explicit definitions.
"""

from __future__ import annotations

import math
import statistics
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lottery import LotteryDraw, LotteryDrawNumber, LotteryLottery


class LotteryAnalyticsEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _lottery(self, lottery_id: uuid.UUID) -> LotteryLottery | None:
        return await self.db.get(LotteryLottery, lottery_id)

    async def frequencies(
        self,
        lottery_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        filters = [LotteryDraw.lottery_id == lottery_id]
        if from_date:
            filters.append(LotteryDraw.draw_date >= from_date)
        if to_date:
            filters.append(LotteryDraw.draw_date <= to_date)
        rows = (
            await self.db.execute(
                select(LotteryDrawNumber.number_value, func.count().label("cnt"))
                .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
                .where(and_(*filters))
                .group_by(LotteryDrawNumber.number_value)
                .order_by(func.count().desc())
                .limit(limit)
            )
        ).all()
        total = sum(int(c) for _, c in rows) or 1
        items = [
            {
                "number": n,
                "absolute": int(c),
                "relative": round(int(c) / total, 6),
            }
            for n, c in rows
        ]
        lot = await self._lottery(lottery_id)
        return {
            "lottery": lot.name if lot else str(lottery_id),
            "from_date": from_date.isoformat() if from_date else None,
            "to_date": to_date.isoformat() if to_date else None,
            "sample_size": total,
            "items": items,
            "definition": "Frecuencia absoluta/relativa sobre números observados en el período; no es probabilidad predictiva.",
            "confidence": "high" if total >= 100 else "medium" if total >= 20 else "low",
        }

    async def position_distribution(
        self,
        lottery_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Any]:
        filters = [LotteryDraw.lottery_id == lottery_id]
        if from_date:
            filters.append(LotteryDraw.draw_date >= from_date)
        if to_date:
            filters.append(LotteryDraw.draw_date <= to_date)
        rows = (
            await self.db.execute(
                select(
                    LotteryDrawNumber.position,
                    LotteryDrawNumber.number_value,
                    func.count().label("cnt"),
                )
                .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
                .where(and_(*filters))
                .group_by(LotteryDrawNumber.position, LotteryDrawNumber.number_value)
                .order_by(LotteryDrawNumber.position.asc(), func.count().desc())
            )
        ).all()
        by_pos: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for pos, num, cnt in rows:
            by_pos[int(pos)].append({"number": num, "count": int(cnt)})
        return {
            "lottery_id": str(lottery_id),
            "by_position": {str(k): v[:20] for k, v in sorted(by_pos.items())},
            "definition": "Distribución histórica por posición de bolilla; descriptiva.",
        }

    async def intervals(
        self,
        lottery_id: uuid.UUID,
        number: str,
        *,
        limit: int = 500,
    ) -> dict[str, Any]:
        rows = (
            await self.db.execute(
                select(LotteryDraw.draw_date)
                .join(LotteryDrawNumber, LotteryDrawNumber.draw_id == LotteryDraw.id)
                .where(
                    LotteryDraw.lottery_id == lottery_id,
                    LotteryDrawNumber.number_value == number,
                )
                .order_by(LotteryDraw.draw_date.asc())
                .limit(limit)
            )
        ).scalars().all()
        if len(rows) < 2:
            return {
                "number": number,
                "occurrences": len(rows),
                "intervals_days": [],
                "mean": None,
                "stdev": None,
                "definition": "Intervalos entre apariciones consecutivas del número (días).",
            }
        gaps = [(rows[i] - rows[i - 1]).days for i in range(1, len(rows))]
        return {
            "number": number,
            "occurrences": len(rows),
            "intervals_days": gaps[-50:],
            "mean": round(statistics.mean(gaps), 3),
            "stdev": round(statistics.pstdev(gaps), 3) if len(gaps) > 1 else 0.0,
            "min": min(gaps),
            "max": max(gaps),
            "last_seen": rows[-1].isoformat(),
            "definition": "Estadística descriptiva de intervalos históricos; no predice la próxima aparición.",
        }

    async def hot_cold(
        self,
        lottery_id: uuid.UUID,
        *,
        window_draws: int = 30,
        cold_days_threshold: int = 30,
        focus: str = "both",
    ) -> dict[str, Any]:
        """Hot = top relative frequency in last N draws.

        Cold (interval / atrasado) = longest days since last appearance.
        Cold (frequency) = lowest frequency inside the same window.
        Definitions are mutually explicit — never mixed without saying which metric.
        """
        definitions = {
            "hot": (
                f"Caliente: alta frecuencia relativa dentro de los últimos {window_draws} sorteos "
                "(conteo de apariciones / total de números extraídos en la muestra)."
            ),
            "cold_frequency": (
                f"Frío por frecuencia: baja frecuencia relativa en los últimos {window_draws} sorteos."
            ),
            "cold_interval": (
                f"Frío/atrasado por intervalo: muchos días sin aparecer respecto al último sorteo "
                f"conocido (umbral ≥{cold_days_threshold} días)."
            ),
            "disclaimer": (
                "Análisis histórico descriptivo. No es predicción ni recomendación de apuestas."
            ),
        }
        if focus == "definition":
            return {
                "window_draws": 0,
                "as_of": None,
                "hot": [],
                "cold": [],
                "cold_by_frequency": [],
                "focus": "definition",
                "metric_used": "definition",
                "definitions": definitions,
                "definition": (
                    f"{definitions['hot']} {definitions['cold_frequency']} "
                    f"{definitions['cold_interval']} {definitions['disclaimer']}"
                ),
            }

        recent = (
            await self.db.execute(
                select(LotteryDraw.id, LotteryDraw.draw_date)
                .where(LotteryDraw.lottery_id == lottery_id)
                .order_by(LotteryDraw.draw_date.desc())
                .limit(window_draws)
            )
        ).all()
        if not recent:
            return {
                "hot": [],
                "cold": [],
                "cold_by_frequency": [],
                "window_draws": 0,
                "focus": focus,
                "definitions": definitions,
                "definition": definitions["disclaimer"],
            }
        draw_ids = [r[0] for r in recent]
        last_date = recent[0][1]
        nums = (
            await self.db.execute(
                select(LotteryDrawNumber.number_value).where(LotteryDrawNumber.draw_id.in_(draw_ids))
            )
        ).scalars().all()
        total = max(1, len(nums))
        counts = Counter(nums)
        hot = [
            {
                "number": n,
                "count": c,
                "relative_frequency_pct": round(100.0 * c / total, 2),
            }
            for n, c in counts.most_common(10)
        ]
        cold_freq = [
            {
                "number": n,
                "count": c,
                "relative_frequency_pct": round(100.0 * c / total, 2),
            }
            for n, c in sorted(counts.items(), key=lambda kv: (kv[1], kv[0]))[:10]
        ]

        last_occ = (
            await self.db.execute(
                select(LotteryDrawNumber.number_value, func.max(LotteryDraw.draw_date))
                .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
                .where(LotteryDraw.lottery_id == lottery_id)
                .group_by(LotteryDrawNumber.number_value)
            )
        ).all()
        cold_interval = []
        for n, d in last_occ:
            gap = (last_date - d).days if d else None
            if gap is not None and gap >= cold_days_threshold:
                cold_interval.append({"number": n, "days_since": gap, "last_seen": d.isoformat()})
        cold_interval.sort(key=lambda x: x["days_since"], reverse=True)

        metric = {
            "hot": "relative_frequency",
            "cold_frequency": "relative_frequency",
            "cold_interval": "days_since_last_appearance",
            "both": "hot=relative_frequency; cold=days_since_last_appearance",
        }.get(focus, "relative_frequency")

        def_bits = [definitions["disclaimer"]]
        if focus in ("hot", "both"):
            def_bits.insert(0, definitions["hot"])
        if focus in ("cold_frequency",):
            def_bits.insert(0, definitions["cold_frequency"])
        if focus in ("cold_interval", "both"):
            def_bits.insert(0, definitions["cold_interval"])

        return {
            "window_draws": len(recent),
            "sample_numbers": total,
            "as_of": last_date.isoformat(),
            "hot": hot if focus in ("hot", "both") else [],
            "cold": cold_interval[:15] if focus in ("cold_interval", "both") else [],
            "cold_by_frequency": cold_freq if focus in ("cold_frequency", "both") else [],
            "focus": focus,
            "metric_used": metric,
            "definitions": definitions,
            "definition": " ".join(def_bits),
        }

    async def coverage(self, lottery_id: uuid.UUID | None = None) -> dict[str, Any]:
        if lottery_id:
            lot = await self._lottery(lottery_id)
            cnt = int(
                (
                    await self.db.execute(
                        select(func.count()).select_from(LotteryDraw).where(LotteryDraw.lottery_id == lottery_id)
                    )
                ).scalar_one()
            )
            mn = (
                await self.db.execute(
                    select(func.min(LotteryDraw.draw_date), func.max(LotteryDraw.draw_date)).where(
                        LotteryDraw.lottery_id == lottery_id
                    )
                )
            ).one()
            return {
                "lottery": lot.name if lot else str(lottery_id),
                "draw_count": cnt,
                "metadata_draw_count": lot.draw_count if lot else None,
                "first_draw_date": mn[0].isoformat() if mn[0] else None,
                "last_draw_date": mn[1].isoformat() if mn[1] else None,
                "metadata_last_draw_date": lot.last_draw_date.isoformat() if lot and lot.last_draw_date else None,
                "metadata_drift": bool(
                    lot
                    and (
                        lot.draw_count != cnt
                        or (lot.last_draw_date and mn[1] and lot.last_draw_date != mn[1])
                    )
                ),
            }
        rows = (
            await self.db.execute(
                select(
                    LotteryLottery.source_id,
                    LotteryLottery.name,
                    LotteryLottery.draw_count,
                    LotteryLottery.last_draw_date,
                    func.count(LotteryDraw.id),
                    func.max(LotteryDraw.draw_date),
                )
                .outerjoin(LotteryDraw, LotteryDraw.lottery_id == LotteryLottery.id)
                .where(LotteryLottery.is_aggregate.is_(False))
                .group_by(
                    LotteryLottery.id,
                    LotteryLottery.source_id,
                    LotteryLottery.name,
                    LotteryLottery.draw_count,
                    LotteryLottery.last_draw_date,
                )
                .order_by(func.count(LotteryDraw.id).desc())
            )
        ).all()
        items = []
        for sid, name, meta_cnt, meta_last, live_cnt, live_last in rows:
            items.append(
                {
                    "source_id": sid,
                    "name": name,
                    "draw_count": int(live_cnt),
                    "metadata_draw_count": meta_cnt,
                    "last_draw_date": live_last.isoformat() if live_last else None,
                    "metadata_last_draw_date": meta_last.isoformat() if meta_last else None,
                    "metadata_drift": bool(
                        meta_cnt != int(live_cnt)
                        or (meta_last and live_last and meta_last != live_last)
                    ),
                }
            )
        return {
            "lotteries": len(items),
            "items": items,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def data_quality(self, lottery_id: uuid.UUID) -> dict[str, Any]:
        cov = await self.coverage(lottery_id)
        # duplicate source_reference check
        dupes = (
            await self.db.execute(
                select(LotteryDraw.source_reference, func.count())
                .where(
                    LotteryDraw.lottery_id == lottery_id,
                    LotteryDraw.source_reference.is_not(None),
                )
                .group_by(LotteryDraw.source_reference)
                .having(func.count() > 1)
                .limit(20)
            )
        ).all()
        empty_nums = 0
        draw_ids = (
            await self.db.execute(select(LotteryDraw.id).where(LotteryDraw.lottery_id == lottery_id))
        ).scalars().all()
        if draw_ids:
            numbered = set(
                (
                    await self.db.execute(
                        select(LotteryDrawNumber.draw_id)
                        .where(LotteryDrawNumber.draw_id.in_(draw_ids))
                        .distinct()
                    )
                ).scalars().all()
            )
            empty_nums = len(draw_ids) - len(numbered)
        zero = empty_nums
        return {
            **cov,
            "duplicate_source_references": [{"ref": r, "count": int(c)} for r, c in dupes],
            "draws_without_numbers": zero,
            "issues": (
                (["metadata_drift"] if cov.get("metadata_drift") else [])
                + (["duplicate_source_references"] if dupes else [])
                + (["draws_without_numbers"] if zero else [])
            ),
        }

    async def anomalies(self, lottery_id: uuid.UUID) -> dict[str, Any]:
        quality = await self.data_quality(lottery_id)
        lot = await self._lottery(lottery_id)
        anomalies = []
        if lot and lot.last_draw_date and lot.last_draw_date.year >= 2090:
            anomalies.append(
                {
                    "code": "future_metadata_date",
                    "severity": "high",
                    "detail": f"last_draw_date metadata={lot.last_draw_date.isoformat()}",
                }
            )
        if quality.get("metadata_drift"):
            anomalies.append({"code": "metadata_drift", "severity": "medium", "detail": quality})
        for d in quality.get("duplicate_source_references") or []:
            anomalies.append({"code": "duplicate_external_id", "severity": "medium", "detail": d})
        if quality.get("draws_without_numbers"):
            anomalies.append(
                {
                    "code": "missing_numbers",
                    "severity": "high",
                    "detail": {"count": quality["draws_without_numbers"]},
                }
            )
        return {"lottery_id": str(lottery_id), "anomalies": anomalies, "count": len(anomalies)}

    async def coincidences(
        self,
        lottery_ids: list[uuid.UUID],
        *,
        on_date: date | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Any]:
        """Numbers that co-appeared across lotteries on the same calendar date."""
        if len(lottery_ids) < 2:
            return {"matches": [], "error": "need_at_least_two_lotteries"}
        filters = [LotteryDraw.lottery_id.in_(lottery_ids)]
        if on_date:
            filters.append(LotteryDraw.draw_date == on_date)
        if from_date:
            filters.append(LotteryDraw.draw_date >= from_date)
        if to_date:
            filters.append(LotteryDraw.draw_date <= to_date)
        rows = (
            await self.db.execute(
                select(
                    LotteryDraw.draw_date,
                    LotteryDraw.lottery_id,
                    LotteryDrawNumber.number_value,
                )
                .join(LotteryDrawNumber, LotteryDrawNumber.draw_id == LotteryDraw.id)
                .where(and_(*filters))
            )
        ).all()
        by_date: dict[date, dict[uuid.UUID, set[str]]] = defaultdict(lambda: defaultdict(set))
        for d, lid, num in rows:
            by_date[d][lid].add(num)
        matches = []
        for d, per_lot in sorted(by_date.items(), reverse=True):
            if len(per_lot) < 2:
                continue
            sets = list(per_lot.values())
            common = set.intersection(*sets) if sets else set()
            if common:
                matches.append(
                    {
                        "date": d.isoformat(),
                        "shared_numbers": sorted(common),
                        "lotteries": [str(x) for x in per_lot.keys()],
                    }
                )
        return {
            "matches": matches[:50],
            "definition": "Coincidencia = mismos números publicados el mismo día en ≥2 loterías del conjunto.",
        }
