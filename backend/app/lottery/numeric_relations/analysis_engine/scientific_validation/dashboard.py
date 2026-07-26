"""Dashboard metrics aggregator + HTML report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_dashboard_payload(phase2: dict[str, Any]) -> dict[str, Any]:
    socio = (
        ((phase2.get("calibration") or {}).get("full") or {}).get("perfil_socio")
        or ((phase2.get("historical") or {}))
    )
    rows = socio.get("rows") if isinstance(socio, dict) else None
    if rows is None:
        rows = (phase2.get("historical") or {}).get("rows") or []

    n = len(rows)
    exact_d1 = sum(r.get("exact_D+1", 0) for r in rows)
    exact_d3 = sum(r.get("exact_D+3", 0) for r in rows)
    exact_d7 = sum(r.get("exact_D+7", 0) for r in rows)
    by_lottery = {}
    by_pos = {}
    for r in rows:
        lot = r.get("origin_lottery") or "?"
        b = by_lottery.setdefault(lot, {"n": 0, "match": 0})
        b["n"] += 1
        b["match"] += int(r.get("methodology_match", False))
        pos = str(r.get("origin_position") or "1")
        p = by_pos.setdefault(pos, {"n": 0, "match": 0})
        p["n"] += 1
        p["match"] += int(r.get("methodology_match", False))

    rules = (phase2.get("rule_inventory") or {}).get("rules") or []
    errors = phase2.get("error_analysis") or {}
    cal = phase2.get("calibration") or {}
    bench = phase2.get("benchmark") or {}

    return {
        "title": "Scientific Validation Dashboard — NR Motor",
        "total_analyses": n or (phase2.get("historical") or {}).get("n_analyses"),
        "total_signals": n,
        "exact_D1": exact_d1,
        "exact_D3": exact_d3,
        "exact_D7": exact_d7,
        "exact_D1_D3": (phase2.get("historical") or {}).get("exact_D1_D3"),
        "exact_D1_D7": (phase2.get("historical") or {}).get("exact_D1_D7"),
        "methodology_match_rate": (phase2.get("historical") or {}).get(
            "methodology_match_rate"
        ),
        "fulfillment_by_lottery": {
            k: {
                "n": v["n"],
                "match_rate": (v["match"] / v["n"]) if v["n"] else 0,
            }
            for k, v in by_lottery.items()
        },
        "fulfillment_by_position": {
            k: {"n": v["n"], "match_rate": (v["match"] / v["n"]) if v["n"] else 0}
            for k, v in by_pos.items()
        },
        "errors": {
            "n_failures": errors.get("n_failures"),
            "failure_rate": errors.get("failure_rate"),
            "patterns": errors.get("repetitive_patterns"),
        },
        "rule_ranking": [
            {"id": r["id"], "status": r["status"], "statement": r["statement"]} for r in rules
        ],
        "most_successful_rules": [
            r for r in rules if r["status"] == "confirmada_por_evidencia"
        ],
        "least_successful_or_pending": [
            r
            for r in rules
            if r["status"] in {"hipotesis", "regla_pendiente_de_validacion", "inferida"}
        ],
        "calibration_ranking": cal.get("ranking"),
        "best_profile": cal.get("best_methodology_reproduction"),
        "benchmark_table": bench.get("blind_benchmark_table"),
        "best_variant": bench.get("best_blind_variant"),
        "production_modified": False,
        "ml_decides_fuerte": False,
    }


def write_dashboard_html(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_bench = "".join(
        f"<tr><td>{b['variant']}</td><td>{b['methodology_match_rate']}</td>"
        f"<td>{b['exact_D+1']}</td><td>{b['exact_D1_D3']}</td><td>{b['exact_D1_D7']}</td>"
        f"<td>{b['failures']}</td></tr>"
        for b in (payload.get("benchmark_table") or [])
    )
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<title>{payload.get('title')}</title>
<style>
body{{font-family:Georgia,serif;background:#f4f1ea;color:#1c2420;margin:2rem}}
h1{{font-size:1.8rem}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem}}
.card{{background:#fff;border:1px solid #d5ddd7;padding:1rem;border-radius:6px}}
table{{border-collapse:collapse;width:100%;background:#fff}} th,td{{border:1px solid #ccc;padding:.4rem;font-size:.9rem}}
.muted{{opacity:.75;font-size:.9rem}}
</style></head><body>
<h1>Dashboard — Validación Científica NR</h1>
<p class="muted">Producción no modificada · Decisión del fuerte determinística (sin ML)</p>
<div class="grid">
<div class="card"><strong>Total análisis</strong><div>{payload.get('total_analyses')}</div></div>
<div class="card"><strong>Exactos D+1</strong><div>{payload.get('exact_D1')}</div></div>
<div class="card"><strong>Exactos D+3</strong><div>{payload.get('exact_D3')}</div></div>
<div class="card"><strong>Exactos D+7</strong><div>{payload.get('exact_D7')}</div></div>
<div class="card"><strong>Match metodológico</strong><div>{payload.get('methodology_match_rate')}</div></div>
<div class="card"><strong>Mejor perfil</strong><div>{payload.get('best_profile')}</div></div>
<div class="card"><strong>Errores</strong><div>{(payload.get('errors') or {}).get('n_failures')}</div></div>
</div>
<h2>Benchmark de variantes</h2>
<table><thead><tr><th>Variante</th><th>Match</th><th>D+1</th><th>D1–D3</th><th>D1–D7</th><th>Fallos</th></tr></thead>
<tbody>{rows_bench}</tbody></table>
<h2>Patrones de error</h2>
<pre>{json.dumps((payload.get('errors') or {}).get('patterns'), indent=2, ensure_ascii=False)}</pre>
<h2>Reglas confirmadas</h2>
<ul>{''.join(f"<li><code>{r['id']}</code> — {r['statement']}</li>" for r in (payload.get('most_successful_rules') or []))}</ul>
<h2>Pendientes / hipótesis</h2>
<ul>{''.join(f"<li><code>{r['id']}</code> [{r['status']}] — {r['statement']}</li>" for r in (payload.get('least_successful_or_pending') or []))}</ul>
</body></html>"""
    path.write_text(html, encoding="utf-8")
    return path
