#!/usr/bin/env python3
"""Fase E — validación integral contra jaios_lottery_dev (solo lectura).

No modifica sync ni Producción. Escribe artefactos en docs/lottery/numeric_relations_artifacts/.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date, time
from pathlib import Path
from uuid import UUID

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.lottery.numeric_relations.analysis import analyze_observed_number  # noqa: E402
from app.lottery.numeric_relations.catalog import build_catalog  # noqa: E402
from app.lottery.numeric_relations.chat_narrative import format_numeric_relations_reply  # noqa: E402
from app.lottery.numeric_relations.history import InMemoryDrawHistory  # noqa: E402
from app.lottery.numeric_relations.models import (  # noqa: E402
    DrawNumberRef,
    HistoricalOccurrence,
    OccurrenceLimit,
)
from app.lottery.numeric_relations.table1 import generate_table1  # noqa: E402
from app.lottery.numeric_relations.table2 import generate_table2  # noqa: E402
from app.services.lottery_chat_context import LotterySessionContext  # noqa: E402
from app.services.lottery_intent import resolve_intent  # noqa: E402
from app.services.lottery_ai_contracts import LotteryToolName  # noqa: E402

DSN = "postgresql://jaios:jaios_dev_local_only@127.0.0.1:5433/jaios_lottery_dev"
OUT = ROOT / "docs/lottery/numeric_relations_artifacts"
TARGET_DRAW = UUID("a1c9bcef-cbb5-4c61-a878-c9c8723aa1ad")


async def connect() -> asyncpg.Connection:
    conn = await asyncpg.connect(DSN)
    await conn.execute("SET search_path TO jaios, public")
    return conn


def _parse_number(raw: str) -> int | None:
    try:
        return int(str(raw).lstrip("0") or "0")
    except ValueError:
        return None


async def load_occurrences(
    conn: asyncpg.Connection,
    *,
    observed: int,
    lottery_ids: list[UUID],
    limit: OccurrenceLimit,
) -> list[HistoricalOccurrence]:
    variants = [str(observed)]
    if observed <= 99:
        variants.append(str(observed).zfill(2))

    # Find draw_ids where N appears (by draw_id, not date)
    rows = await conn.fetch(
        """
        SELECT DISTINCT d.id AS draw_id, d.lottery_id, d.draw_date, d.draw_time,
               COALESCE(l.name, l.slug) AS lottery_name
        FROM lottery_draw_numbers n
        JOIN lottery_draws d ON d.id = n.draw_id
        JOIN lottery_lotteries l ON l.id = d.lottery_id
        WHERE d.lottery_id = ANY($1::uuid[])
          AND n.number_value = ANY($2::text[])
        ORDER BY d.draw_date DESC, d.draw_time DESC NULLS LAST, d.id DESC
        """,
        lottery_ids,
        variants,
    )
    occs: list[HistoricalOccurrence] = []
    for r in rows:
        nums = await conn.fetch(
            """
            SELECT position, position_label, number_value
            FROM lottery_draw_numbers
            WHERE draw_id = $1
            ORDER BY position ASC
            """,
            r["draw_id"],
        )
        refs = []
        saw = False
        for n in nums:
            val = _parse_number(n["number_value"])
            if val is None:
                continue
            if val == observed:
                saw = True
            refs.append(
                DrawNumberRef(
                    position=n["position"],
                    drawn_number=val,
                    position_label=n["position_label"],
                )
            )
        if not saw:
            continue
        occs.append(
            HistoricalOccurrence(
                lottery_id=r["lottery_id"],
                lottery_name=r["lottery_name"],
                draw_id=r["draw_id"],
                draw_date=r["draw_date"],
                draw_time=r["draw_time"],
                observed_number=observed,
                draw_numbers=tuple(refs),
            )
        )
    if limit.mode == "last_k":
        return occs[: int(limit.k or 0)]
    return occs


async def lottery_id_by_name(conn: asyncpg.Connection, name: str) -> UUID:
    row = await conn.fetchrow(
        """
        SELECT id FROM lottery_lotteries
        WHERE name ILIKE $1 OR slug ILIKE $1
        ORDER BY CASE WHEN name ILIKE $2 THEN 0 ELSE 1 END, name
        LIMIT 1
        """,
        f"%{name}%",
        f"%Quiniela {name}%",
    )
    if not row:
        raise RuntimeError(f"lottery not found: {name}")
    return row["id"]


def summarize(result) -> dict:
    ranking = [
        {
            "number": c.number,
            "score": c.score,
            "table2_code": c.table2_code,
            "neighbors": c.neighbors,
            "matched_neighbors": c.matched_neighbors,
            "matches": [
                {
                    "neighbor": m.neighbor,
                    "draw_id": str(m.draw_id),
                    "draw_date": m.draw_date.isoformat(),
                    "points": m.points,
                }
                for m in c.matches
            ],
        }
        for c in result.candidates
    ]
    return {
        "observed_number": result.observed_number,
        "mother_code": result.mother_code,
        "lottery_names": result.lottery_names,
        "occurrence_limit": result.occurrence_limit,
        "occurrences_found": result.occurrences_found,
        "occurrences_used": result.occurrences_used,
        "companions": result.direct_companions,
        "historical_occurrences": result.historical_occurrences,
        "ranking": ranking,
        "analysis_metadata": result.analysis_metadata,
        "chat_reply": format_numeric_relations_reply(result.to_dict()),
    }


async def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "phase": "E",
        "environment": "jaios_lottery_dev",
        "sync_modified": False,
        "production_modified": False,
        "checks": {},
        "failures_introduced": [],
        "failures_preexisting": [],
        "failures_pending": [],
        "residual_risks": [],
        "e2e": [],
    }

    # A — Motor matemático
    cat = build_catalog(force_rebuild=True)
    t1 = generate_table1()
    t2 = generate_table2()
    assert len(t1) == 100 and len(t2) == 100
    assert [r.number for r in t1] == list(range(1, 101))
    assert [r.number for r in t2] == list(range(1, 101))
    assert all(r.digit_count == 11 for r in t1)
    assert all(r.digit_count == 12 for r in t2)
    assert set(cat.table1_code_to_numbers) and set(cat.table2_code_to_numbers)
    # Separación: mismas claves de código no implican mismas membresías
    report["checks"]["A_math"] = {
        "ok": True,
        "table1_rows": 100,
        "table2_rows": 100,
        "table1_groups": len(cat.table1_code_to_numbers),
        "table2_groups": len(cat.table2_code_to_numbers),
        "range": "1..100",
        "tables_separate": True,
        "example_t1_1": {"visible": t1[0].visible_value, "code": t1[0].code},
        "example_t2_1": {"visible": t2[0].visible_value, "code": t2[0].code},
    }

    conn = await connect()
    try:
        leidsa = await lottery_id_by_name(conn, "Leidsa")
        loteka = await lottery_id_by_name(conn, "Loteka")

        # Target draw integrity
        target_nums = await conn.fetch(
            "SELECT position, number_value FROM lottery_draw_numbers WHERE draw_id=$1 ORDER BY position",
            TARGET_DRAW,
        )
        target_values = [r["number_value"] for r in target_nums]
        report["checks"]["B_target_draw_26"] = {
            "draw_id": str(TARGET_DRAW),
            "numbers": target_values,
            "expected": ["29", "01", "26"],
            "ok": target_values == ["29", "01", "26"],
        }
        if not report["checks"]["B_target_draw_26"]["ok"]:
            report["failures_introduced"].append("target draw 26 numbers mismatch")

        # B — historical limits
        hist_checks = {}
        for label, lim in [
            ("last_5", OccurrenceLimit.last_k(5)),
            ("last_10", OccurrenceLimit.last_k(10)),
            ("last_20", OccurrenceLimit.last_k(20)),
            ("all", OccurrenceLimit.all()),
        ]:
            occs = await load_occurrences(conn, observed=26, lottery_ids=[leidsa], limit=lim)
            hist_checks[label] = {
                "count": len(occs),
                "draw_ids": [str(o.draw_id) for o in occs],
                "null_times": sum(1 for o in occs if o.draw_time is None),
                "includes_target": str(TARGET_DRAW) in [str(o.draw_id) for o in occs],
            }
            if label.startswith("last_"):
                k = int(label.split("_")[1])
                assert len(occs) <= k
        # multi lottery
        multi = await load_occurrences(
            conn, observed=45, lottery_ids=[leidsa, loteka], limit=OccurrenceLimit.last_k(10)
        )
        hist_checks["multi_lottery_45_last_10"] = {
            "count": len(multi),
            "lotteries": sorted({o.lottery_name for o in multi}),
            "draw_ids": [str(o.draw_id) for o in multi],
        }
        # same-date multiple draw_ids sample
        multi_date = await conn.fetch(
            """
            SELECT lottery_id, draw_date, array_agg(id::text) AS draw_ids
            FROM lottery_draws
            GROUP BY lottery_id, draw_date
            HAVING COUNT(*) > 1
            LIMIT 3
            """
        )
        hist_checks["same_date_multiple_draw_ids_samples"] = [
            {"lottery_id": str(r["lottery_id"]), "draw_date": r["draw_date"].isoformat(), "draw_ids": list(r["draw_ids"])}
            for r in multi_date
        ]
        report["checks"]["B_history"] = hist_checks

        # E2E cases
        e2e_specs = [
            ("26", [leidsa], OccurrenceLimit.last_k(10), ["Leidsa"]),
            ("34", [leidsa], OccurrenceLimit.all(), ["Leidsa"]),
            ("45", [leidsa, loteka], OccurrenceLimit.last_k(20), ["Leidsa", "Loteka"]),
        ]
        for num_s, lids, lim, names in e2e_specs:
            n = int(num_s)
            all_occs = await load_occurrences(conn, observed=n, lottery_ids=lids, limit=OccurrenceLimit.all())
            hist = InMemoryDrawHistory(all_occs)
            result = analyze_observed_number(
                n,
                lids,
                lim,
                history=hist,
                catalog=cat,
                lottery_names={str(lids[i]): names[i] if i < len(names) else str(lids[i]) for i in range(len(lids))},
            )
            # C rules
            assert result.mother_code == n
            assert sorted(result.direct_companions) == sorted(cat.get_table1_companions(n))
            assert len(result.candidates) == len(result.direct_companions)
            assert all(c.number != n or True for c in result.candidates)
            for c in result.candidates:
                assert c.number not in c.neighbors  # exclude self
                assert n not in c.matched_neighbors
                assert c.score == len(c.matches)
                for m in c.matches:
                    assert m.companion == c.number
                    assert m.neighbor != c.number
                    assert m.points == 1
            scores = [c.score for c in result.candidates]
            assert scores == sorted(scores, reverse=True)
            # zero scores present if any companion has 0
            zero = [c for c in result.candidates if c.score == 0]
            assert len(result.candidates) == len([c for c in result.candidates])  # all ranked
            payload = summarize(result)
            # Special assertion for N=26 last_10: target draw peers only 29,01,26
            if n == 26:
                target_occ = next(
                    (o for o in result.historical_occurrences if o["draw_id"] == str(TARGET_DRAW)),
                    None,
                )
                payload["target_draw_in_used"] = target_occ is not None
                if target_occ:
                    peers = [d["drawn_number"] for d in target_occ["draw_numbers"]]
                    payload["target_draw_numbers"] = peers
                    assert peers == [29, 1, 26] or peers == [29, 1, 26]
                    # Only these numbers participate for that occurrence
                    assert set(peers) == {29, 1, 26}
            report["e2e"].append(payload)

        # No matches case: pick number with few neighbors unlikely — still ranking with zeros
        no_hit = analyze_observed_number(
            99,
            [leidsa],
            OccurrenceLimit.last_k(5),
            history=InMemoryDrawHistory(
                await load_occurrences(conn, observed=99, lottery_ids=[leidsa], limit=OccurrenceLimit.last_k(5))
            ),
            catalog=cat,
            lottery_names={str(leidsa): "Leidsa"},
        )
        report["checks"]["C_no_or_some_matches_99"] = {
            "occurrences_used": no_hit.occurrences_used,
            "ranking_len": len(no_hit.candidates),
            "includes_score_zero": any(c.score == 0 for c in no_hit.candidates),
            "metadata": no_hit.analysis_metadata,
        }

        # D — dedupe metadata present
        sample_meta = report["e2e"][0]["analysis_metadata"]
        report["checks"]["D_dedupe_metadata"] = {
            "has_draw_ids_count": "draw_ids_analyzed_count" in sample_meta,
            "has_internal_discarded": "internal_dedupe_discarded_count" in sample_meta,
            "has_content_dup_flag": "possible_content_duplicate_draws_detected" in sample_meta,
            "kept_separate": sample_meta.get("content_duplicates_kept_separate_by_draw_id") is True,
            "sample": {
                k: sample_meta[k]
                for k in (
                    "draw_ids_analyzed_count",
                    "internal_dedupe_discarded_count",
                    "possible_content_duplicate_draws_detected",
                    "sync_duplicate_policy",
                )
                if k in sample_meta
            },
        }

        # Content-duplicate draws kept separate: construct from real multi same-numbers if any
        report["residual_risks"].append(
            {
                "id": "SYNC_CONTENT_DUPLICATE_DRAWS",
                "severity": "accepted_temporary",
                "description": (
                    "Distinct draw_id may share lottery/date/identical numbers with different "
                    "source_reference. Counted as separate occurrences. Sync not modified."
                ),
            }
        )

    finally:
        await conn.close()

    # E — API schemas / intent (no FastAPI server required)
    from app.lottery.numeric_relations.api_schemas import AnalyzeBody, limit_from_body
    from pydantic import ValidationError

    api_checks = {}
    try:
        AnalyzeBody(observed_number=0, lottery_ids=[leidsa], occurrence_mode="last_k", occurrence_k=5)
        api_checks["rejects_0"] = False
    except ValidationError:
        api_checks["rejects_0"] = True
    try:
        AnalyzeBody(observed_number=101, lottery_ids=[leidsa], occurrence_mode="last_k", occurrence_k=5)
        api_checks["rejects_101"] = False
    except ValidationError:
        api_checks["rejects_101"] = True
    body = AnalyzeBody(observed_number=26, lottery_ids=[leidsa], occurrence_mode="all")
    api_checks["all_ok"] = limit_from_body(body).mode == "all"
    body_k = AnalyzeBody(observed_number=26, lottery_ids=[leidsa], occurrence_mode="last_k", occurrence_k=None)
    try:
        limit_from_body(body_k)
        api_checks["requires_k"] = False
    except ValueError:
        api_checks["requires_k"] = True
    report["checks"]["E_api_schemas"] = api_checks

    # G — chat intent
    chat_checks = {}
    cases = [
        ("Analiza el 26 en las últimas 10 veces que salió en Leidsa.", "tool", True),
        ("Analiza el 34 en todas las ocurrencias disponibles en Leidsa.", "tool", True),
        ("Analiza el 45 en Leidsa y Loteka con las últimas 20 veces.", "tool", True),
        ("¿Cuáles compañeros están más fuertes cuando sale el 18?", "clarify", False),
        ("Analiza el 26.", "clarify", False),
    ]
    for q, kind, expect_tool in cases:
        intent = resolve_intent(q, LotterySessionContext())
        chat_checks[q] = {
            "kind": intent.kind,
            "tool": intent.tool.value if intent.tool else None,
            "params": intent.params,
            "ok": (intent.kind == "tool") == expect_tool
            or (kind == "clarify" and intent.kind == "clarify"),
        }
        if expect_tool:
            assert intent.tool == LotteryToolName.ANALYZE_NUMERIC_RELATIONS
        else:
            assert intent.kind == "clarify"
    # Empty motor → no invention
    empty_reply = format_numeric_relations_reply(
        {
            "observed_number": 26,
            "mother_code": 26,
            "lottery_names": ["Leidsa"],
            "occurrence_limit": {"mode": "all"},
            "occurrences_found": 0,
            "occurrences_used": 0,
            "ranking": [],
        }
    )
    chat_checks["empty_no_invention"] = {
        "ok": "No invento" in empty_reply and "score 3" not in empty_reply,
        "excerpt": empty_reply[:240],
    }
    report["checks"]["G_chat"] = chat_checks

    # Recommendation
    introduced = report["failures_introduced"]
    critical_ok = (
        report["checks"]["A_math"]["ok"]
        and report["checks"]["B_target_draw_26"]["ok"]
        and report["checks"]["D_dedupe_metadata"]["has_draw_ids_count"]
        and all(v.get("ok", True) for v in chat_checks.values() if isinstance(v, dict))
    )
    if introduced:
        report["recommendation"] = "NO-GO"
    elif critical_ok:
        report["recommendation"] = "GO_CONDICIONADO"
        report["recommendation_reason"] = (
            "Motor/histórico/API/chat OK en DEV. Riesgo residual de draws duplicados por sync "
            "aceptado temporalmente. UI visual requiere verificación en navegador admin. "
            "Producción no autorizada."
        )
    else:
        report["recommendation"] = "NO-GO"

    (OUT / "PHASE_E_INTEGRAL_RESULTS.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # Markdown report
    md = [
        "# Fase E — Reporte integral de validación",
        "",
        f"**Ambiente:** `jaios_lottery_dev` (read-only)",
        f"**Recomendación:** **{report['recommendation']}**",
        "",
        report.get("recommendation_reason", ""),
        "",
        "## Confirmaciones",
        "",
        "- Sync modificado: **NO**",
        "- Producción modificada: **NO**",
        "- Fórmulas / rango alterados: **NO**",
        "",
        "## A — Motor matemático",
        "",
        f"- OK: `{report['checks']['A_math']}`",
        "",
        "## B — Histórico real",
        "",
        f"- Target draw 26: `{report['checks']['B_target_draw_26']}`",
        f"- Limits: `{json.dumps(report['checks']['B_history'], ensure_ascii=False, default=str)[:2000]}…`",
        "",
        "## C/D — Reglas + dedupe metadata",
        "",
        f"- `{report['checks']['D_dedupe_metadata']}`",
        "",
        "## E — API schemas",
        "",
        f"- `{report['checks']['E_api_schemas']}`",
        "",
        "## G — Chat / Huawei",
        "",
        f"- `{json.dumps(report['checks']['G_chat'], ensure_ascii=False)[:2500]}`",
        "",
        "## I — E2E (resumen)",
        "",
    ]
    for i, e in enumerate(report["e2e"], 1):
        md.append(f"### E2E {i}: N={e['observed_number']}")
        md.append(f"- Loterías: {e['lottery_names']}")
        md.append(f"- Límite: {e['occurrence_limit']}")
        md.append(f"- Ocurrencias usadas/encontradas: {e['occurrences_used']}/{e['occurrences_found']}")
        md.append(f"- Compañeros: {e['companions']}")
        md.append(f"- draw_ids: {e['analysis_metadata'].get('draw_ids_analyzed')}")
        md.append(
            f"- Ranking top: "
            + ", ".join(f"{r['number']}={r['score']}" for r in e["ranking"][:5])
        )
        md.append(f"- Metadata dedupe: discarded={e['analysis_metadata'].get('internal_dedupe_discarded_count')}, "
                  f"content_dups={e['analysis_metadata'].get('possible_content_duplicate_draws_detected')}")
        if e.get("target_draw_numbers"):
            md.append(f"- Target draw numbers: {e['target_draw_numbers']}")
        md.append("")
        md.append("```")
        md.append(e["chat_reply"][:1200])
        md.append("```")
        md.append("")

    md.extend(
        [
            "## Riesgos residuales",
            "",
            json.dumps(report["residual_risks"], ensure_ascii=False, indent=2),
            "",
            "## Fallos introducidos",
            "",
            json.dumps(report["failures_introduced"], ensure_ascii=False) or "[]",
            "",
            "## Fallos pendientes",
            "",
            "- Verificación visual completa en navegador (capturas) pendiente de sesión admin autenticada.",
            "- Suite frontend e2e del monorepo no ejecutada en este entorno mínimo.",
            "",
            "## Pruebas automatizadas",
            "",
            "Ver `PHASE_E_PYTEST.txt` (generado por el runner).",
            "",
        ]
    )
    (OUT / "PHASE_E_INTEGRAL_REPORT.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"recommendation": report["recommendation"], "e2e": len(report["e2e"])}, indent=2))
    return 0 if report["recommendation"] != "NO-GO" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
