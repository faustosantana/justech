#!/usr/bin/env python3
"""Pre-freeze regressions and inventory (read-only)."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

OUT = Path("/tmp/freeze_precheck.json")


def motor() -> dict:
    from app.lottery.numeric_relations.analysis_engine import run_complete_analysis

    r = run_complete_analysis(
        {"numbers": [35, 14], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
    )
    r2 = run_complete_analysis(
        {"numbers": [39, 58], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
    )
    return {
        "35_14_primary": r.primary_signal["number"],
        "35_14_ok": r.primary_signal["number"] == 54,
        "39_58_primary": r2.primary_signal["number"],
        "39_58_ok": r2.primary_signal["number"] == 94,
    }


async def db_inventory() -> dict:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from app.config import settings
    from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    out: dict = {"default_lotteries": list(DEFAULT_ALL_HISTORY_LOTTERIES)}
    async with engine.connect() as conn:
        await conn.execute(text("SET search_path TO jaios, public"))
        out["alembic"] = (
            await conn.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar()
        out["draws"] = (await conn.execute(text("SELECT count(*) FROM lottery_draws"))).scalar()
        out["draw_numbers"] = (
            await conn.execute(text("SELECT count(*) FROM lottery_draw_numbers"))
        ).scalar()
        out["lotteries"] = (
            await conn.execute(text("SELECT count(*) FROM lottery_lotteries"))
        ).scalar()

        # Product-scope last occurrence helper
        async def last_n(number: str, limit: int = 1, lottery: str | None = None):
            variants = list(dict.fromkeys([str(int(number)), str(number).zfill(2)]))
            in_list = ",".join("'" + v + "'" for v in variants)
            if lottery and lottery.lower() == "nacional":
                lot = " AND (l.normalized_name = 'loteria nacional' OR l.name ILIKE '%nacional%')"
            else:
                ors = " OR ".join(
                    f"(l.name ILIKE '%{x}%' OR l.normalized_name ILIKE '%{x.lower()}%')"
                    for x in DEFAULT_ALL_HISTORY_LOTTERIES
                    if x not in {"Nacional Día", "Nacional Noche"}
                    or True
                )
                # Prefer exact product names to avoid Loto Leidsa false positives
                lot = """ AND (
                    l.name IN ('Gana Mas','Loteria Nacional','Quiniela Leidsa','Quiniela Loteka','Quiniela Real')
                    OR l.normalized_name IN ('gana mas','loteria nacional','leidsa','loteka','quiniela real','quiniela leidsa','quiniela loteka')
                )"""
            sql = f"""
            SELECT d.draw_date::text AS draw_date, l.name AS lottery, dn.position
            FROM lottery_draw_numbers dn
            JOIN lottery_draws d ON d.id = dn.draw_id
            JOIN lottery_lotteries l ON l.id = d.lottery_id
            WHERE (dn.number_value IN ({in_list}) OR dn.number_raw IN ({in_list}))
              {lot}
            ORDER BY d.draw_date DESC, d.draw_time DESC NULLS LAST
            LIMIT {int(limit)}
            """
            rows = (await conn.execute(text(sql))).mappings().all()
            return [dict(r) for r in rows]

        out["last_22"] = await last_n("22", 1)
        out["last3_97"] = await last_n("97", 3)
        out["last_44"] = await last_n("44", 1)
        out["last3_35_nacional_pos1"] = (
            await conn.execute(
                text(
                    """
            SELECT d.draw_date::text AS draw_date, l.name AS lottery, dn.position
            FROM lottery_draw_numbers dn
            JOIN lottery_draws d ON d.id = dn.draw_id
            JOIN lottery_lotteries l ON l.id = d.lottery_id
            WHERE (dn.number_value IN ('35','35') OR dn.number_raw IN ('35','35'))
              AND (l.normalized_name = 'loteria nacional' OR l.name ILIKE '%nacional%')
              AND dn.position = 1
            ORDER BY d.draw_date DESC
            LIMIT 3
            """
                )
            )
        ).mappings().all()
        out["last3_35_nacional_pos1"] = [dict(r) for r in out["last3_35_nacional_pos1"]]

        # same_day 55+24 count
        sd = (
            await conn.execute(
                text(
                    """
            WITH hits AS (
              SELECT d.draw_date, COALESCE(dn.number_raw, dn.number_value) AS number
              FROM lottery_draw_numbers dn
              JOIN lottery_draws d ON d.id = dn.draw_id
              JOIN lottery_lotteries l ON l.id = d.lottery_id
              WHERE (dn.number_value IN ('55','24','55','24') OR dn.number_raw IN ('55','24','55','24'))
                AND (
                    l.name IN ('Gana Mas','Loteria Nacional','Quiniela Leidsa','Quiniela Loteka','Quiniela Real')
                    OR l.normalized_name IN ('gana mas','loteria nacional','leidsa','loteka','quiniela real','quiniela leidsa','quiniela loteka')
                )
            ), days AS (
              SELECT draw_date FROM hits
              GROUP BY draw_date
              HAVING COUNT(*) FILTER (WHERE number IN ('55','55')) > 0
                 AND COUNT(*) FILTER (WHERE number IN ('24','24')) > 0
            )
            SELECT count(*)::int FROM days
            """
                )
            )
        ).scalar()
        out["same_day_55_24_core_days"] = sd

        # compare totals rough
        for n in ("54", "94"):
            tot = (
                await conn.execute(
                    text(
                        f"""
                SELECT count(*)::int FROM lottery_draw_numbers dn
                JOIN lottery_draws d ON d.id = dn.draw_id
                JOIN lottery_lotteries l ON l.id = d.lottery_id
                WHERE (dn.number_value IN ('{n}','{n}') OR dn.number_raw IN ('{n}','{n}'))
                  AND (
                    l.name IN ('Gana Mas','Loteria Nacional','Quiniela Leidsa','Quiniela Loteka','Quiniela Real')
                    OR l.normalized_name IN ('gana mas','loteria nacional','leidsa','loteka','quiniela real','quiniela leidsa','quiniela loteka')
                  )
                """
                    )
                )
            ).scalar()
            out[f"count_{n}_core"] = tot
    await engine.dispose()
    return out


def checksums() -> dict:
    files = [
        "/app/app/lottery/ai/prompts/lottery_assistant_system_v1.py",
        "/app/app/lottery/ai/prompts/lottery_analyst_system_v6.py",
        "/app/app/services/lottery_chat_service.py",
        "/app/app/lottery/ai/analyst/conversation_brain.py",
        "/app/app/lottery/ai/analyst/question_classifier.py",
        "/app/app/lottery/numeric_relations/analysis_engine/motor_v1_freeze.py",
    ]
    out = {}
    for f in files:
        p = Path(f)
        if not p.exists():
            # try alternate paths
            alt = Path(f.replace("/app/app/", "/app/"))
            p = alt if alt.exists() else p
        if p.exists():
            out[str(p)] = {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "bytes": p.stat().st_size,
            }
        else:
            out[f] = {"missing": True}
    return out


def prompt_markers() -> dict:
    from app.lottery.ai.prompts import get_active_prompt

    p = get_active_prompt()
    return {
        "active_prompt_name": getattr(p, "name", None) or getattr(p, "key", None) or str(type(p)),
        "recommended_model": getattr(p, "recommended_model", None),
        "v6_file_exists": Path("/app/app/lottery/ai/prompts/lottery_analyst_system_v6.py").exists(),
        "v5_file_exists": Path("/app/app/lottery/ai/prompts/lottery_assistant_system_v1.py").exists(),
    }


def main() -> None:
    report = {
        "motor": motor(),
        "db": asyncio.run(db_inventory()),
        "checksums": checksums(),
        "prompts": prompt_markers(),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report["motor"], indent=2))
    print("alembic", report["db"].get("alembic"))
    print("last_22", report["db"].get("last_22"))
    print("last_44", report["db"].get("last_44"))
    print("last3_97", report["db"].get("last3_97"))
    print("nacional35", report["db"].get("last3_35_nacional_pos1"))
    print("same_day", report["db"].get("same_day_55_24_core_days"))
    print("prompts", report["prompts"])
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
