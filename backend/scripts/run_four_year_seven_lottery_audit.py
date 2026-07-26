#!/usr/bin/env python3
"""Run four-year FEATURED_SEVEN historical audit (DEV read-only)."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.lottery.numeric_relations.catalog import build_catalog  # noqa: E402
from app.lottery.numeric_relations.four_year_audit import (  # noqa: E402
    PREFERRED_FROM,
    PREFERRED_TO,
    aggregate_audit,
    build_day_case,
    coverage_table,
    decide_verdicts,
    new_audit_id,
    pick_ten_explained,
)
from app.lottery.numeric_relations.historical_manual_audit import (  # noqa: E402
    SEED_DEFAULT,
)
from app.lottery.numeric_relations.historical_audit_runner import (  # noqa: E402
    DEFAULT_DEV_DSN,
    first_obs_for_date,
    load_featured_draws,
)
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION  # noqa: E402

OUT_DOCS = REPO / "docs/lottery/four_year_audit"
OUT_ART = REPO / "artifacts/four_year_audit"
EVIDENCE = OUT_DOCS / "evidence"


async def main() -> int:
    OUT_DOCS.mkdir(parents=True, exist_ok=True)
    OUT_ART.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    audit_id = new_audit_id()
    cat = build_catalog()
    if "jaios_lottery_dev" not in DEFAULT_DEV_DSN:
        raise SystemExit("production_forbidden: DEV DSN required")

    conn = await asyncpg.connect(DEFAULT_DEV_DSN)
    try:
        featured_rows = await conn.fetch(
            """
            select id::text as id, name, source_id,
                   coalesce(draw_times::text, '') as draw_times
            from lottery_lotteries
            where is_featured = true
            order by display_order, name
            """
        )
        featured = [dict(r) for r in featured_rows]
        draw_count_all = int(await conn.fetchval("select count(*) from lottery_draws"))
        min_max = await conn.fetchrow(
            """
            select min(d.draw_date) as dmin, max(d.draw_date) as dmax
            from lottery_draws d
            join lottery_lotteries l on l.id = d.lottery_id
            where l.is_featured = true
            """
        )
        draws = await load_featured_draws(conn)
    finally:
        await conn.close()

    if len(featured) != 7:
        raise SystemExit(f"FEATURED_SEVEN broken: {len(featured)}")

    dmin = min_max["dmin"]
    dmax = min_max["dmax"]
    date_from = max(PREFERRED_FROM, dmin) if dmin else PREFERRED_FROM
    date_to = min(PREFERRED_TO, dmax) if dmax else PREFERRED_TO

    by_date: dict[date, list[dict]] = defaultdict(list)
    draws_f = []
    for dr in draws:
        dd = dr["draw_date"]
        if dd < date_from or dd > date_to:
            continue
        by_date[dd].append(dr)
        draws_f.append(dr)

    days = []
    for d in sorted(by_date.keys()):
        obs = first_obs_for_date(by_date[d], d)
        if len(obs) < 2:
            continue
        days.append(
            build_day_case(
                case_date=d,
                observations=obs,
                catalog=cat,
                all_draws_sorted=draws_f,
                by_date=by_date,
            )
        )

    cov = coverage_table(by_date, date_from=date_from, date_to=date_to)
    agg = aggregate_audit(days, by_date=by_date, catalog=cat, seed=SEED_DEFAULT)
    explained = pick_ten_explained(days, seed=SEED_DEFAULT)
    verdicts = decide_verdicts(agg)

    summary = {
        "audit_id": audit_id,
        "trace_id": audit_id,
        "production_forbidden": True,
        "motor_modified": False,
        "tables_modified": False,
        "methodology_version": METHODOLOGY_VERSION,
        "seed": SEED_DEFAULT,
        "preferred_range": {
            "from": PREFERRED_FROM.isoformat(),
            "to": PREFERRED_TO.isoformat(),
        },
        "actual_range": {
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "db_min_featured": dmin.isoformat() if dmin else None,
            "db_max_featured": dmax.isoformat() if dmax else None,
        },
        "featured_seven": {
            "count": len(featured),
            "lotteries": featured,
        },
        "draw_count_all_db": draw_count_all,
        "featured_draws_in_range": len(draws_f),
        "dates_with_draws": len(by_date),
        "dates_analyzed_ge2_obs": len(days),
        "coverage_by_year": cov,
        "aggregates": {
            k: agg[k]
            for k in (
                "total_days",
                "days_with_fuerte",
                "days_multi_fuerte",
                "days_sin_fuerte",
                "total_strengthened_instances",
                "level_counts",
                "window_metrics",
                "confirmation_level_metrics",
                "yearly",
                "baselines_w3",
                "walk_forward",
                "relations_count",
            )
        },
        "top_relations_by_sample": agg["top_relations_by_sample"],
        "top_relations_by_lift_min_sample": agg["top_relations_by_lift_min_sample"],
        "worst_relations_min_sample": agg["worst_relations_min_sample"],
        "deceptive_relations": agg["deceptive_relations"],
        "lottery_pairs_top": agg["lottery_pairs"][:20],
        "explained_cases": explained,
        "verdicts": verdicts,
    }

    # Persist
    (EVIDENCE / "statistics.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (OUT_ART / "statistics.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (OUT_ART / "cases.json").write_text(
        json.dumps(explained, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    # number profiles CSV
    with (OUT_ART / "number_profiles.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "number",
                "table1_code",
                "table2_code",
                "times_observed",
                "times_strengthened",
                "w3_hits_when_strengthened",
                "hit_rate_w3",
                "lift_vs_base_freq",
                "security_level",
            ],
        )
        w.writeheader()
        for row in agg["number_profiles"]:
            w.writerow({k: row.get(k) for k in w.fieldnames})

    with (OUT_ART / "relationships.csv").open("w", newline="", encoding="utf-8") as f:
        fields = [
            "relation",
            "generator",
            "candidate",
            "n_confirmers",
            "activations",
            "w3_hits",
            "hit_rate_w3",
            "lift_vs_base_freq_random_one",
            "security_level",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in agg["all_relations"]:
            w.writerow({k: row.get(k) for k in fields})

    with (OUT_ART / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["audit_id", audit_id])
        w.writerow(["dates_analyzed", len(days)])
        w.writerow(["days_with_fuerte", agg["days_with_fuerte"]])
        w.writerow(["w3_hit_rate", agg["baselines_w3"]["official_t1_x_t2"]["hit_rate"]])
        w.writerow(
            ["lift_vs_random_same_k", agg["baselines_w3"]["lift_official_vs_random_same_k"]]
        )
        w.writerow(["veredicto_estadistico", verdicts["veredicto_estadistico"]])
        w.writerow(["decision_j11a", "|".join(verdicts["decision_j11a"])])

    # HTML executive
    b = agg["baselines_w3"]
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<title>Auditoría 4 años — FEATURED_SEVEN</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;line-height:1.5;color:#111}}
h1,h2{{letter-spacing:-0.02em}} .card{{border:1px solid #ddd;border-radius:12px;padding:1rem 1.25rem;margin:1rem 0}}
.muted{{color:#555}} table{{border-collapse:collapse;width:100%}} th,td{{border-bottom:1px solid #eee;padding:.4rem .5rem;text-align:left}}
.badge{{display:inline-block;background:#eef;padding:.15rem .5rem;border-radius:999px;font-size:.85rem}}
.warn{{background:#fff7ed;border-color:#fdba74}}
</style></head><body>
<h1>Auditoría histórica de 4 años</h1>
<p class="muted">Metodología {METHODOLOGY_VERSION} · Solo lectura · FEATURED_SEVEN = 7 · Producción no modificada</p>
<div class="card warn"><strong>Aviso:</strong> frecuencias históricas e intervalos. No es garantía predictiva.</div>
<div class="card">
<h2>Resumen ejecutivo</h2>
<p><span class="badge">Veredicto matemático: {verdicts['veredicto_matematico']}</span>
<span class="badge">Veredicto estadístico: {verdicts['veredicto_estadistico']}</span></p>
<ul>
<li>Rango real: {date_from} → {date_to}</li>
<li>Fechas analizadas (≥2 observados): {len(days)}</li>
<li>Días con fuerte oficial: {agg['days_with_fuerte']}</li>
<li>Ventana principal W3 (día siguiente): hit rate {b['official_t1_x_t2']['hit_rate']}
  ({b['official_t1_x_t2']['hits']}/{b['official_t1_x_t2']['denominator']}),
  IC95 {b['official_t1_x_t2']['wilson_ci_95']}</li>
<li>Lift vs random same-k: {b['lift_official_vs_random_same_k']}</li>
<li>Lift vs random one: {b['lift_official_vs_random_one']}</li>
<li>Decisión J-11A: {', '.join(verdicts['decision_j11a'])}</li>
</ul>
</div>
<div class="card">
<h2>¿Qué significa?</h2>
<p>Se midió si los candidatos fortalecidos por Tabla&nbsp;1×Tabla&nbsp;2 aparecen al día siguiente
con más frecuencia que una selección aleatoria con la misma cantidad de candidatos.
Un lift cercano a 1 indica que no hay ventaja clara frente al azar controlado.</p>
</div>
<div class="card">
<h2>Cobertura por año (aprox.)</h2>
<table><tr><th>Año</th><th>Desde</th><th>Hasta</th><th>Sorteos</th><th>Cobertura%</th></tr>
{''.join(f"<tr><td>{r['year']}</td><td>{r['date_from']}</td><td>{r['date_to']}</td><td>{r['draws_available']}</td><td>{r['coverage_pct_approx']}</td></tr>" for r in cov)}
</table>
</div>
<div class="card">
<h2>Walk-forward</h2>
<table><tr><th>Train</th><th>Test</th><th>In-sample</th><th>OOS</th><th>Δ pp</th></tr>
{''.join(f"<tr><td>{w['train_years']}</td><td>{w['test_year']}</td><td>{w['in_sample_w3']['hit_rate']}</td><td>{w['out_of_sample_w3']['hit_rate']}</td><td>{w['degradation_pp']}</td></tr>" for w in agg['walk_forward'])}
</table>
</div>
<p class="muted">audit_id / trace_id: {audit_id}</p>
</body></html>"""
    (OUT_ART / "executive_report.html").write_text(html, encoding="utf-8")

    # PDF attempt
    pdf_note = "PDF no generado: dependencia weasyprint/reportlab no forzada en este entorno. HTML completo disponible."
    try:
        # Prefer writing a tiny note file rather than failing the audit
        (OUT_ART / "executive_report.pdf.README.txt").write_text(pdf_note + "\n", encoding="utf-8")
    except Exception:
        pass

    print(
        json.dumps(
            {
                "audit_id": audit_id,
                "range": [date_from.isoformat(), date_to.isoformat()],
                "featured": len(featured),
                "days": len(days),
                "days_with_fuerte": agg["days_with_fuerte"],
                "w3": b["official_t1_x_t2"],
                "lift_same_k": b["lift_official_vs_random_same_k"],
                "verdicts": verdicts,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
