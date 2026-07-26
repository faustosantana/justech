#!/usr/bin/env python3
"""Write dynamics/topology/manual-rules book + HTML + simple PDF."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs/lottery/dynamics_topology_manual_audit"
ART = REPO / "artifacts/dynamics_topology_manual_audit"


def w(name: str, body: str) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / name).write_text(body.strip() + "\n", encoding="utf-8")


def md_table(headers, rows) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(lines)


def write_pdf(findings: dict) -> None:
    """Minimal PDF without external deps (PDF 1.4 text objects)."""
    lines = [
        "AUDITORIA DINAMICA / TOPOLOGIA / REGLAS MANUALES (PRE-J11A)",
        f"audit_id: {findings['audit_id']}",
        f"rama: {findings['branch']}",
        "Motor/Tablas/Produccion: intactos. J-11A: no iniciado.",
        "",
        "CASOS MANUALES:",
    ]
    for m in findings["manual_cases"]:
        lines.append(
            f"- {m['case_id']}: manual={m['manual']} official={m['official']} "
            f"→ {m['classification']} ({m['certainty']})"
        )
        lines.append(f"  {m['evidence'][:200]}")
    lines += [
        "",
        f"35→54←14 activaciones: {findings['hist_35_54_14']['activations']} "
        f"exact={findings['hist_35_54_14']['exact_rate_pct']}%",
        f"39→94←58 activaciones: {findings['hist_39_94_58']['activations']}",
        f"39→94←84 activaciones: {findings['hist_39_94_84']['activations']}",
        "",
        f"Misses 552 con compañero T1: {findings['misses']['with_t1_companion']}",
        f"Tasa -1: {findings['sequences']['rate_-1']}%",
        findings["minus_one_role"]["interpretation"][:300],
        "",
        "NO incorporar DIRECT_T2 ni desempates al motor sin autorizacion.",
        "Ver libro HTML completo en docs/lottery/dynamics_topology_manual_audit/index.html",
    ]

    # Build simple PDF
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    y = 750
    content = ["BT", "/F1 9 Tf", "50 770 Td", f"({esc(lines[0])}) Tj"]
    for line in lines[1:]:
        content.append("0 -12 Td")
        content.append(f"({esc(line[:110])}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")

    objs = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objs.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objs.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode() + stream + b"\nendstream\nendobj\n"
    )
    objs.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    )
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "DYNAMICS_TOPOLOGY_MANUAL_AUDIT_EXECUTIVE_REPORT.pdf").write_bytes(out)


def write_book(findings, manual_repros, m5_84, profiles, hist_m4, hist_58, hist_84) -> None:
    audit_id = findings["audit_id"]

    class_rows = [
        [m["case_id"], m["manual_fuerte"], m["official_fuertes"], m["classification"], m["certainty"]]
        for m in manual_repros
    ]

    w(
        "00_README.md",
        f"""
# Auditoría de dinámica, topología y reglas manuales

| Campo | Valor |
|-------|--------|
| Rama | `{findings['branch']}` |
| Base | `{findings['base_commit']}` |
| audit_id | `{audit_id}` |
| Motor/Tablas/Producción | intactos |
| J-11A | no iniciado |

[index.html](index.html) · PDF: `artifacts/dynamics_topology_manual_audit/DYNAMICS_TOPOLOGY_MANUAL_AUDIT_EXECUTIVE_REPORT.pdf`
""",
    )

    w(
        "01_EXECUTIVE_SUMMARY.md",
        f"""
# 01 — Resumen ejecutivo

Esta fase reconstruye el método del socio frente al motor oficial y describe
cómo se mueven las familias T1 después de cada fuerte.

## Casos manuales

{md_table(['Caso', 'Manual', 'Oficial', 'Clase', 'Certeza'], class_rows)}

## Hallazgos clave

1. **M1 / M4** se reproducen como fuerte oficial único.
2. **M3** es oficial entre varios (35 y 22); el socio eligió 35 (más confirmadores).
3. **M2 (75)** es **VECINO_T2_DIRECTO** — no incorporar.
4. **M5**: tanto `39+58→94` como `39+84→94` son oficiales; 58 y 84 comparten grupo T2 con 94.
5. Dinámica −1: tasa {findings['sequences']['rate_-1']}% · {findings['minus_one_role']['interpretation']}
6. Misses: {findings['misses']['count']} con compañero T1 en {findings['misses']['with_t1_companion']}.

No se inicia J-11A. No se modifica el motor.
""",
    )

    w(
        "02_SCOPE_AND_DATA.md",
        f"""
# 02 — Alcance y datos

- Período / histórico: artefactos de la auditoría profunda (`artifacts/deep_mathematical_audit/`).
- Metodología: `{findings['methodology_version']}`.
- Sin azar. Sin cambios a tablas. FEATURED_SEVEN.
- Activaciones fuertes únicas/día usadas para dinámica: 2222 (heredadas).
""",
    )

    w(
        "03_MANUAL_CASES_TRANSCRIPTION.md",
        """
# 03 — Transcripción de casos manuales

## M1
Observados: 41, 41, 70 → fuerte manual **29**

## M2
Observados: 41, 62 → fuerte manual **75**

## M3
Observados: 49, 44, 70 → fuerte manual **35** (motor también 22)

## M4
Observados: 35, 14 → fuerte **54**
WhatsApp:
- 23-jun-2026: Nacional 35 + Loteka 14 → 54 al día siguiente
- 22-jul-2026: NY Día 35 + Nacional 14 → 54 en Gana Más 23-jul-2026

## M5
Manuscrito: 39 + 58 → 94  
Auditoría previa: 39 → 94 ← 84  
Ambos pares se verifican por separado (no se corrige 58 automáticamente).
""",
    )

    m_blocks = []
    for m in manual_repros:
        m_blocks.append(
            f"""### {m['case_id']}

- Observados: {m['observed']}
- Manual: **{m['manual_fuerte']}**
- Oficial: {m['official_fuertes']}
- Clase: `{m['classification']}` ({m['certainty']})
- Evidencia: {m['evidence']}
"""
        )
        if m.get("m3_tiebreak"):
            m_blocks.append(
                f"- Desempate: {m['m3_tiebreak']['hypothesis_note']}\n"
                f"- Comparación: `{m['m3_tiebreak']['comparison']}`\n"
            )
        if m.get("m5_alternate_84"):
            m_blocks.append(f"- Alterno 39+84: `{m['m5_alternate_84']}`\n")

    w(
        "04_MANUAL_CASES_REPRODUCTION.md",
        f"""
# 04 — Reproducción exacta

{''.join(m_blocks)}

### M5b 39+84

- Oficial: {m5_84['official_fuertes']}
- Clase: {m5_84['classification']}

JSON: `manual_case_reproductions.json`
""",
    )

    w(
        "05_RULE_CLASSIFICATION.md",
        f"""
# 05 — Clasificación de reglas

{md_table(['Caso', 'Clase', 'Certeza'], [[m['case_id'], m['classification'], m['certainty']] for m in manual_repros])}

CSV: `rule_classifications.csv`
""",
    )

    w(
        "06_MULTIPLE_STRONG_TIEBREAK.md",
        f"""
# 06 — Desempate con múltiples fuertes

Días con ≥2 fuertes: **{findings['multi_strong_days']}**

## Hipótesis (no incorporada)

**Más confirmadores** — en M3 coincide (35 tiene 2, 22 tiene 1).

Evaluación descriptiva en días multi-fuerte:
tasa exacta del fuerte con más confirmadores =
{findings['tie_break_candidates'][0].get('max_confirmers_exact_rate_pct')}%.

Contraejemplos: ver `tie_break_eval.json` / `multiple_strong_cases.csv`.
No se declara regla del motor.
""",
    )

    w(
        "07_DIRECT_T2_SIGNALS.md",
        f"""
# 07 — Señales T2 directas

## M2: 41 + 62 → 75 manual

- 75 ∈ vecinos T2 de **62** (grupo T2 `[62, 75]`).
- 75 ∉ vecinos T2 de 41.
- Motor oficial: **ningún fuerte**.
- Clase: `VECINO_T2_DIRECTO`.

**No incorporar** al motor. Mantener como señal experimental separada.

{findings['direct_t2']}
""",
    )

    flags = findings["sequences"]["flags"]
    w(
        "08_FAMILY_DYNAMICS.md",
        f"""
# 08 — Dinámica de familias

Secuencias observadas (conteos de activaciones donde el orden temporal se cumple):

{md_table(['Secuencia', 'Conteo'], [[k, flags.get(k, 0)] for k in ['F→-1','F→+1','F→-2','F→+2','F→-1→-2','F→+1→+2','F→-1→F']])}

![sequences](assets/sequences.svg)

CSV: `family_dynamics.csv`
""",
    )

    w(
        "09_REAL_FAMILY_CENTERS.md",
        """
# 09 — Centros reales de familia

Para cada código T1 se calculan:

- centro geométrico (mediana del grupo ordenado);
- centro por activaciones como fuerte;
- centro por apariciones posteriores;
- centro por conexiones totales.

Ejemplo grupo del 42 (`5 10 42`): ver `family_centers.csv` filtrando `t1_code` del 42.

No se convierte aún en regla.
""",
    )

    w(
        "10_POSITION_MINUS_ONE.md",
        f"""
# 10 — Posición −1

Tasa (oportunidad→aparición): **{findings['sequences']['rate_-1']}%**
({findings['sequences']['hit_-1']} / {findings['sequences']['opp_-1']})

## ¿Qué es −1?

{findings['minus_one_role']['interpretation']}

Top fuertes productores de −1: {findings['minus_one_role']['producers_top'][:10]}

Top números que ocupan −1: {findings['minus_one_role']['numbers_top'][:10]}

![minus1](assets/minus1_producers.svg)
![net](assets/minus_one_network.svg)
""",
    )

    w(
        "11_POSITION_PLUS_ONE.md",
        f"""
# 11 — Posición +1

Secuencia F→+1: {flags.get('F→+1', 0)} activaciones con orden temporal fuerte antes que +1.

Red: ![plus1](assets/plus_one_network.svg)
""",
    )

    w(
        "12_POSITION_MINUS_TWO_PLUS_TWO.md",
        f"""
# 12 — Posiciones −2 y +2

- F→−2: {flags.get('F→-2', 0)}
- F→+2: {flags.get('F→+2', 0)}
- F→−1→−2: {flags.get('F→-1→-2', 0)}
- F→+1→+2: {flags.get('F→+1→+2', 0)}
""",
    )

    w(
        "13_MISSES_552.md",
        f"""
# 13 — Misses (552)

| Métrica | Valor |
|---------|------:|
| Misses | {findings['misses']['count']} |
| Con compañero T1 | {findings['misses']['with_t1_companion']} |
| Sustitutos T1 top | {findings['misses']['top_substitutes'][:10]} |
| Distancias T1 top | {findings['misses']['top_t1_dist'][:8]} |

CSV: `misses_552_detailed.csv`
""",
    )

    w(
        "14_CYCLES_AND_MEMORY.md",
        f"""
# 14 — Ciclos y memoria

Top ciclos A→B→A (fuerte → otro → fuerte otra vez en la ventana):

{md_table(['Ciclo', 'Conteo'], findings['cycles_top'][:15])}

![cycles](assets/cycles_network.svg)

CSV: `cycles.csv`
""",
    )

    w(
        "15_PATHS_AND_TRANSITIONS.md",
        """
# 15 — Caminos y transiciones

Top fuerte→resultado en `paths.csv` y `relationship_graph.json`.

Mapas: `assets/global_network.svg`, `D1_network.svg`, `D2_network.svg`, `D3_network.svg`.
""",
    )

    # Compact profiles chapter — top + pointer
    top = sorted(profiles, key=lambda p: -int(p.get("times_fuerte") or 0))[:25]
    w(
        "16_NUMBER_PROFILES_1_100.md",
        f"""
# 16 — Perfiles 1–100

CSV completo: `number_profiles.csv` (100 filas).

## Top 25 por veces fuerte

{md_table(['N', 'Pos T1', '-1', '+1', 'Fuerte', 'Exacto', 'Origen', 'Conf', 'prod -1'],
[[p['number'], p['t1_pos'], p['num_-1'], p['num_+1'], p['times_fuerte'], p['exact_any'], p['times_origin'], p['times_confirmer'], p['produced_-1_count']] for p in top])}

Página por número: usar el CSV / JSON; el dashboard permite filtrar.
""",
    )

    w(
        "17_MANUAL_RULE_CANDIDATES.md",
        f"""
# 17 — Reglas manuales candidatas (no incorporadas)

{md_table(['Regla', 'Notas'], [[c['rule'], c.get('description') or c.get('note','')] for c in findings['tie_break_candidates']])}

Adicional observada:

- **DIRECT_T2** (M2): socio eleva vecino T2 — evidencia geométrica sí; predictiva no evaluada aquí; **no incorporar**.
- **Confirmador T2 alternativo** (M5): 58 y 84 son intercambiables como confirmadores de 94.
""",
    )

    w(
        "18_EXCEPTIONS.md",
        f"""
# 18 — Excepciones

- M2 no es fuerte oficial.
- M3 tiene dos oficiales; la elección manual no es la única geometría.
- M5 manuscrito usa 58; histórico también usa 84 — ambos válidos.
- Secuencia F→−1→−2 es rara (~4.8% en auditoría previa).
- Días multi-fuerte: {findings['multi_strong_days']} — desempate no uniforme.
""",
    )

    w(
        "19_FINDINGS.md",
        f"""
# 19 — Hallazgos

1. Motor reproduce M1 y M4 sin ambigüedad.
2. M3 muestra necesidad de lenguaje de desempate (candidato: más confirmadores).
3. M2 es regla T2 directa del socio, fuera del motor.
4. M5 no es error de transcripción obligatorio: 58 y 84 confirman 94.
5. −1 es el desplazamiento T1 más frecuente; rol mixto destino/puente.
6. Ciclos A→B→A existen y están listados.
7. Dossier 35→54←14: {hist_m4['activations']} activaciones, exact {hist_m4['exact_rate_pct']}%.
""",
    )

    w(
        "20_FINAL_RECOMMENDATIONS.md",
        """
# 20 — Recomendaciones finales

1. Conservar geometría oficial T1×T2.
2. Exponer familia y posiciones (−1/+1/…) al usuario.
3. No incorporar DIRECT_T2.
4. Investigar desempate por confirmadores solo como hipótesis.
5. Documentar que 58 y 84 son confirmadores T2 equivalentes de 94.
6. **No iniciar J-11A** sin autorización expresa.
""",
    )

    w(
        "21_FINAL_REPORT.md",
        f"""
# 21 — Informe final

| Campo | Valor |
|-------|--------|
| Rama | `{findings['branch']}` |
| audit_id | `{audit_id}` |
| M1 | {manual_repros[0]['classification']} |
| M2 | {manual_repros[1]['classification']} |
| M3 | {manual_repros[2]['classification']} |
| M4 | {manual_repros[3]['classification']} |
| M5 | {manual_repros[4]['classification']} |
| 35→54←14 act | {hist_m4['activations']} |
| 39→94←58 act | {hist_58['activations']} |
| 39→94←84 act | {hist_84['activations']} |
| Producción | intacta |
| J-11A | no iniciado |

Libro: `index.html`  
PDF: `artifacts/dynamics_topology_manual_audit/DYNAMICS_TOPOLOGY_MANUAL_AUDIT_EXECUTIVE_REPORT.pdf`
""",
    )

    # HTML index
    chapters = sorted(p.name for p in DOCS.glob("*.md"))
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<title>Dinámica · Topología · Reglas manuales</title>
<style>
body{{font-family:Georgia,serif;max-width:1050px;margin:2rem auto;padding:0 1rem;line-height:1.5}}
h1,h2,nav{{font-family:system-ui,sans-serif}}
.card{{border:1px solid #e5e7eb;border-radius:12px;padding:1rem;margin:1rem 0;background:#fafafa}}
.warn{{background:#fff7ed}}
img{{max-width:100%;border:1px solid #eee;border-radius:8px;margin:.5rem 0}}
nav a{{display:inline-block;margin:.2rem .4rem 0 0;font-size:13px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
td,th{{border-bottom:1px solid #eee;padding:.35rem;text-align:left}}
</style></head><body>
<h1>Dinámica, topología y reglas manuales</h1>
<p>audit_id <code>{audit_id}</code> · PRE-J11A · solo lectura</p>
<div class="card warn">Motor/Tablas/Producción intactos. DIRECT_T2 y desempates <strong>no</strong> incorporados.</div>
<div class="card">
<table>
<tr><th>M1</th><td>{manual_repros[0]['classification']}</td></tr>
<tr><th>M2</th><td>{manual_repros[1]['classification']}</td></tr>
<tr><th>M3</th><td>{manual_repros[2]['classification']}</td></tr>
<tr><th>M4</th><td>{manual_repros[3]['classification']}</td></tr>
<tr><th>M5</th><td>{manual_repros[4]['classification']}</td></tr>
<tr><th>35→54←14</th><td>{hist_m4['activations']} act · exact {hist_m4['exact_rate_pct']}%</td></tr>
<tr><th>39→94←58 / ←84</th><td>{hist_58['activations']} / {hist_84['activations']}</td></tr>
</table>
</div>
<h2>Mapas</h2>
<img src="assets/sequences.svg"/>
<img src="assets/minus_one_network.svg"/>
<img src="assets/plus_one_network.svg"/>
<img src="assets/global_network.svg"/>
<img src="assets/cycles_network.svg"/>
<img src="assets/D1_network.svg"/>
<h2>Capítulos</h2>
<nav>{''.join(f'<a href="{c}">{c}</a>' for c in chapters)}</nav>
</body></html>"""
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    (ART / "executive_report.html").write_text(html, encoding="utf-8")
    write_pdf(findings)
    print(json.dumps({"chapters": len(chapters), "pdf": True}, indent=2))
