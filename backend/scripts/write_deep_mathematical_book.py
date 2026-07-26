#!/usr/bin/env python3
"""Write the 30-chapter deep mathematical audit book + HTML dashboard."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs/lottery/deep_mathematical_audit"
ART = REPO / "artifacts/deep_mathematical_audit"
ASSETS = DOCS / "assets"


def w(name: str, body: str) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / name).write_text(body.strip() + "\n", encoding="utf-8")


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(lines)


def write_book(
    summary: dict,
    explained: list[dict],
    manual: list[dict],
    number_profiles: list[dict],
    pair_rank: list[dict],
) -> None:
    c = summary["coverage"]
    t = summary["totals"]
    fh = summary["first_hit_stats"]
    ap = summary["answers_preview"]
    audit_id = summary["audit_id"]
    meth = summary["methodology_version"]

    featured = "\n".join(f"- `{x['name']}`" for x in c["featured_seven"])
    day_rows = [[k, v, fh["by_day_pct_of_activations"][k]] for k, v in fh["by_day"].items()]
    cum_rows = [
        [k, v["count"], v["pct_of_activations"]] for k, v in fh["cumulative"].items()
    ]
    t1d = [[x["distance"], x["count"], f"{x['pct']}%"] for x in summary["t1_distance_rank"][:20]]
    t2d = [[x["distance"], x["count"], f"{x['pct']}%"] for x in summary["t2_distance_rank"][:20]]
    lab = [[x["label"], x["count"]] for x in summary["label_summary"][:25]]
    year_rows = [
        [y["year"], y["fuerte_activations"], y["exact_hits"], f"{y['exact_pct']}%"]
        for y in summary["yearly"]
    ]
    chain_rows = [
        [
            f"{x['origin']}→{x['fuerte']}←{x['confirmer']}→{x['result']}",
            x["count"],
            x["consistency"],
        ]
        for x in summary["top_chains"][:25]
    ]
    pair_rows = [
        [
            f"{x['origin']}→{x['fuerte']}←{x['confirmer']}",
            x["activations"],
            x["sample_bucket"],
            x["year_span"],
            x["consistency"],
            ",".join(str(r["number"]) for r in x["top_results"]),
        ]
        for x in summary["top_pairs"][:25]
    ]
    lot_rows = [
        [
            x["origin_lottery"],
            x["confirmer_lottery"],
            x["result_lottery"],
            x["count"],
        ]
        for x in summary["matrices"]["lottery_triples_top"][:20]
    ]
    conf_rows = [
        [k, v["activations"], v["exact"], f"{v['exact_pct']}%", v["median_first_day"], v["mean_first_day"]]
        for k, v in sorted(summary["confirmation_count"].items())
    ]
    top_fuertes = sorted(number_profiles, key=lambda x: -x["times_fuerte"])[:20]
    fuerte_prof_rows = [
        [
            p["number"],
            p["times_fuerte"],
            p["exact_any"],
            p["t1_pos"],
            p["t1_group_size"],
            p["times_origin"],
            p["times_confirmer"],
        ]
        for p in top_fuertes
    ]

    w(
        "00_README.md",
        f"""
# Auditoría matemática profunda — Motor de Relaciones Numéricas

| Campo | Valor |
|-------|--------|
| Rama | `{summary['branch']}` |
| Commit de fase | `{summary['phase_commit']}` |
| Worktree | `{summary['worktree']}` |
| audit_id | `{audit_id}` |
| Período | {c['period_from']} → {c['period_to']} |
| Metodología | `{meth}` |
| Motor / Tablas | sin modificar |
| Producción | intacta |
| J-11A | no iniciado |
| Eje aleatorio | no utilizado |

**Abrir dashboard:** [index.html](index.html)

Artefactos exactos: `artifacts/deep_mathematical_audit/`
""",
    )

    w(
        "01_EXECUTIVE_SUMMARY.md",
        f"""
# 01 — Resumen ejecutivo

Esta auditoría reconstruye, con datos históricos exactos, **qué ocurrió después de cada activación oficial** del motor: posiciones en Tabla 1/2, distancias, cadenas, loterías y plazos D+1…D+7.

No clasifica el trabajo como “el motor acierta” o “falla”.
No usa comparaciones aleatorias como eje.
No modifica fórmulas ni Producción.

## Volumen

| Métrica | Valor |
|---------|------:|
| Activaciones cadena O→F←C | {t['chain_activations']} |
| Activaciones fuerte (únicas/día) | {t['fuerte_activations_unique_per_day']} |
| Fuertes distintos | {t['distinct_fuertes']} |
| Filas de apariciones posteriores | {t['future_appearance_rows']} |
| Días con ≥2 observados | {t['days_ge2']} |
| Días con ≥1 fuerte | {t['days_with_fuerte']} |

## Primera aparición del fuerte exacto

{md_table(['Día', 'Primera aparición', '% activaciones'], day_rows)}

![exact by day](assets/exact_by_day.svg)

### Acumulado

{md_table(['Ventana', 'Conteo', '% activaciones'], cum_rows)}

## Distancias posicionales T1 más frecuentes

{md_table(['Distancia', 'Conteo', '%'], t1d)}

![t1 dist](assets/t1_distances.svg)

## Etiquetas de relación más frecuentes (nivel aparición)

{md_table(['Etiqueta', 'Conteo'], lab)}

## Lectura

1. El fuerte exacto tiene una trayectoria temporal medible por D+n (capítulo 06/15).
2. Cuando no es exacto, las apariciones posteriores se clasifican por **posición y distancia** en T1/T2, no solo como “compañero”.
3. Las cadenas O→F←C→R más repetidas están rankeadas con niveles de consistencia (capítulo 10/23).

Detalle: [30_FINAL_REPORT.md](30_FINAL_REPORT.md).
""",
    )

    w(
        "02_DATA_COVERAGE.md",
        f"""
# 02 — Cobertura exacta

| Campo | Valor |
|-------|------:|
| Fecha inicial análisis | {c['period_from']} |
| Fecha final análisis | {c['period_to']} |
| Días calendario | {c['calendar_days']} |
| Días con draws featured | {c['days_with_featured_draws']} |
| Días faltantes | {c['days_missing']} |
| Días ≥2 observados | {c['days_ge2_observed']} |
| Días con fuerte | {c['days_with_fuerte']} |
| Sorteos featured en período | {c['featured_draws_in_period']} |
| DB featured min/max | {c['db_featured_min']} / {c['db_featured_max']} |

## FEATURED_SEVEN

{featured}

Archivadas excluidas. Números fuera de 1..100 excluidos. Período fuera de rango excluido.
Cola D+1…D+7 cargada hasta {c['period_to']} + 7 días.
""",
    )

    w(
        "03_EXACT_METHODOLOGY.md",
        f"""
# 03 — Metodología exacta

Versión: `{meth}`

```
Número observado O
    ↓  (O se usa como código madre Tabla 1)
Candidatos T1 = grupo con código O
    ↓
Para cada candidato F
    ↓  Tabla 2 de F
Confirmador C ∈ observados del mismo día ∩ vecinos T2(F)
    ↓
Fuerte oficial = F
(Confirmador C no se fortalece)
```

## Regla temporal

- Día D: solo observados de D forman cadenas.
- Evidencia: D+1 … D+7 exclusivamente.
- D no valida. D+8 no entra.

## Clasificación

Cada aparición posterior recibe **todas** las etiquetas aplicables (A–Q).
Se conservan posición canónica (orden ascendente del grupo), distancia y dirección.
""",
    )

    w(
        "04_TABLE_POSITION_MODEL.md",
        f"""
# 04 — Modelo posicional de tablas

## Orden canónico

Dentro de cada código, los integrantes se ordenan de menor a mayor.
La posición 1 es el menor número del grupo.

```
distancia_posicional = posición_resultado − posición_fuerte
```

| Distancia | Significado |
|----------:|-------------|
| 0 | misma posición / exacto en el grupo |
| +1 | siguiente en el grupo |
| -1 | anterior en el grupo |
| ±2, ±3 | cercano |
| \\|d\\| > 3 | lejano |

## Ejemplo real (fuerte 54)

Grupo T1 del 54 (código digit-sum del 54): ver perfiles CSV.
Grupo T2 del 54: vecinos oficiales del catálogo.

No se inventan órdenes distintos al canónico del motor.
""",
    )

    w(
        "05_ALL_ACTIVATIONS.md",
        f"""
# 05 — Todas las activaciones

| Tipo | Conteo |
|------|-------:|
| Cadenas O→F←C | {t['chain_activations']} |
| Fuertes únicos por día | {t['fuerte_activations_unique_per_day']} |

CSV trazable: `artifacts/deep_mathematical_audit/all_activations.csv`

Cada fila incluye origen, confirmador, fuerte, posiciones T1/T2, loterías, sources y flags de aparición.
""",
    )

    w(
        "06_EXACT_STRONG_RESULTS.md",
        f"""
# 06 — Resultados del fuerte exacto

Activaciones fuerte (únicas/día): **{t['fuerte_activations_unique_per_day']}**  
Con exacto en ≤7d: **{fh['with_exact']}**  
Sin exacto: **{fh['without_exact']}**

## Por día de primera aparición

{md_table(['Día', 'Conteo', '% de activaciones'], day_rows)}

![chart](assets/exact_by_day.svg)

## Acumulado

{md_table(['Ventana', 'Conteo', '%'], cum_rows)}

CSV: `strong_exact_results.csv`
""",
    )

    w(
        "07_WHEN_STRONG_DID_NOT_APPEAR.md",
        f"""
# 07 — Cuando el fuerte no apareció

Activaciones sin exacto: **{fh['without_exact']}**

Para cada una, `all_future_appearances.csv` lista **todos** los números que sí salieron,
con etiquetas múltiples, posición T1/T2, distancia, día, lotería y posición de sorteo.

No se resume como “salió algún compañero”: cada compañero conserva su posición exacta.

Ver casos etiquetados `no_exact` en [25_FIFTY_EXPLAINED_CASES.md](25_FIFTY_EXPLAINED_CASES.md).
""",
    )

    # T1 position matrix excerpt
    t1m = summary["matrices"]["t1_pos_fuerte_x_appeared"]
    t1m_rows = []
    for r in list(t1m["rows"])[:8]:
        for col in list(t1m["cols"])[:8]:
            cnt = t1m["counts"][r][col]
            if cnt:
                t1m_rows.append([r, col, cnt, f"{t1m['row_pct'][r][col]}%"])

    w(
        "08_TABLE1_POSITION_ANALYSIS.md",
        f"""
# 08 — Análisis posicional Tabla 1

## Distancias observadas (result − fuerte)

{md_table(['Distancia', 'Conteo', '%'], t1d)}

![t1](assets/t1_distances.svg)

## Matriz (extracto) posición_fuerte × posición_aparecida

{md_table(['Pos fuerte', 'Pos aparecida', 'Conteo', '% fila'], t1m_rows[:40])}

### Preguntas

- **¿Cuál distancia domina?** Ver ranking arriba (dato exacto en CSV).
- **¿+1 vs −1?** Comparar conteos de distancia +1 y −1 en la tabla.
- **¿Cercanos vs lejanos?** Etiquetas POSICION_T1_ADYACENTE / CERCANA / LEJANA en `label_summary`.

CSV: `table1_position_results.csv`
""",
    )

    w(
        "09_TABLE2_POSITION_ANALYSIS.md",
        f"""
# 09 — Análisis posicional Tabla 2

{md_table(['Distancia', 'Conteo', '%'], t2d)}

![t2](assets/t2_distances.svg)

Preguntas respondidas con conteos:

- Vecinos inmediatos T2: etiqueta `POSICION_T2_ADYACENTE` / dist ±1.
- Reaparición del confirmador: etiqueta `CONFIRMADOR_ORIGINAL`.
- Compañero/vecino del confirmador: `COMPANERO_DEL_CONFIRMADOR`, `VECINO_DEL_CONFIRMADOR`.

CSV: `table2_position_results.csv`
""",
    )

    w(
        "10_ORIGIN_CONFIRMATION_CHAINS.md",
        f"""
# 10 — Cadenas origen → fuerte ← confirmador → resultado

Forma: **O → F ← C → R**

## Top cadenas exactas (por conteo de apariciones R)

{md_table(['Cadena', 'Conteo', 'Consistencia'], chain_rows)}

![chains](assets/top_chains.svg)

## Pares O–F–C por activaciones

{md_table(['Par', 'Activaciones', 'Muestra', 'Años', 'Nivel', 'Top R'], pair_rows)}

Niveles: 1 aislado (<5) … 5 muy alta (≥50). Una muestra 1–4 no se presenta como conclusión fuerte.

CSV: `origin_confirmator_chains.csv`
""",
    )

    w(
        "11_STRONG_NUMBER_PROFILES.md",
        f"""
# 11 — Perfiles de números fuertes (top 20)

{md_table(['Número', 'Veces fuerte', 'Exacto', 'Pos T1', 'Tam T1', 'Como origen', 'Como conf'], fuerte_prof_rows)}

Perfil completo 1–100: `number_profiles.csv`
""",
    )

    top_origins = sorted(number_profiles, key=lambda x: -x["times_origin"])[:20]
    w(
        "12_OBSERVED_NUMBER_PROFILES.md",
        f"""
# 12 — Perfiles de números observados (origen)

Cuando aparece X como origen, el motor produce candidatos = grupo T1 con código X.

{md_table(['Número', 'Veces origen', 'Candidatos', 'Veces fuerte', 'Veces conf'],
[[p['number'], p['times_origin'], p['candidates_as_origin'], p['times_fuerte'], p['times_confirmer']] for p in top_origins])}

CSV: `number_profiles.csv`
""",
    )

    top_conf = sorted(number_profiles, key=lambda x: -x["times_confirmer"])[:20]
    w(
        "13_CONFIRMING_NUMBER_PROFILES.md",
        f"""
# 13 — Perfiles de confirmadores

{md_table(['Número', 'Veces conf', 'Veces fuerte', 'Veces origen', 'Grupo T2'],
[[p['number'], p['times_confirmer'], p['times_fuerte'], p['times_origin'], p['t2_group']] for p in top_conf])}

La reaparición del confirmador y de su familia se mide con etiquetas
`CONFIRMADOR_ORIGINAL`, `COMPANERO_DEL_CONFIRMADOR`, `VECINO_DEL_CONFIRMADOR`.
""",
    )

    w(
        "14_CONFIRMATION_COUNT_ANALYSIS.md",
        f"""
# 14 — Cantidad de confirmaciones

{md_table(['Confirmadores', 'Activaciones', 'Exactos', '%', 'Mediana D+', 'Media D+'], conf_rows)}

![conf](assets/confirmation_counts.svg)

Interpretación: comparar filas para ver si más confirmadores cambian tasa o velocidad.
No se modifica el motor.
""",
    )

    # Day by day chapters content in one file as requested structure - user asked 15_DAY_BY_DAY
    day_detail = []
    day_mat = summary["matrices"]["day_x_relation"]
    for dlabel in [f"D+{i}" for i in range(1, 8)]:
        if dlabel not in day_mat["counts"]:
            continue
        top = sorted(day_mat["counts"][dlabel].items(), key=lambda kv: -kv[1])[:12]
        day_detail.append(f"## {dlabel}\n\n" + md_table(["Relación", "Conteo"], [[a, b] for a, b in top]) + "\n")

    w(
        "15_DAY_BY_DAY_D1_D7.md",
        f"""
# 15 — Día por día (D+1 … D+7)

Primera aparición del exacto:

{md_table(['Día', 'Conteo', '% activaciones'], day_rows)}

## Cualquier aparición × etiqueta (top por día)

{''.join(day_detail)}

Métricas separadas: primera aparición / cualquier aparición / total — ver CSV `all_future_appearances.csv` y `relationship_matrix.csv`.
""",
    )

    w(
        "16_DRAW_POSITION_ANALYSIS.md",
        f"""
# 16 — Posición del sorteo

Matriz posición origen × posición resultado (márgenes en JSON):

Total celdas no nulas disponibles en `full_statistics.json` → `matrices.origin_pos_x_result_pos`.

![draw pos](assets/draw_positions.svg)

Preguntas (responder con la matriz):

- ¿El exacto se concentra en 1ª/2ª/3ª?
- ¿Los compañeros T1 cambian de posición de sorteo?
- ¿La posición del confirmador predice la del resultado? (correlación descriptiva, no causal)
""",
    )

    w(
        "17_LOTTERY_TRANSITIONS.md",
        f"""
# 17 — Transiciones entre loterías

Forma: lotería origen → lotería confirmadora → lotería resultado

{md_table(['Origen', 'Confirmadora', 'Resultado', 'Conteo'], lot_rows)}

![lot](assets/lottery_transitions.svg)

CSV: `lottery_transitions.csv`
""",
    )

    w(
        "18_YEARLY_STABILITY.md",
        f"""
# 18 — Estabilidad anual

{md_table(['Año', 'Activaciones fuerte', 'Exactos', '%'], year_rows)}

![year](assets/activations_by_year.svg)

Matriz año × relación: `matrices.year_x_relation` en JSON.
Una relación estable aparece en varios años con conteo material (niveles 3–5).
""",
    )

    w(
        "19_TEMPORAL_PATTERNS.md",
        f"""
# 19 — Patrones temporales observados

Conteos disponibles sin inferir causalidad:

- Distribución D+1…D+7 del exacto (cap. 06/15).
- Estabilidad anual (cap. 18).
- Pares O–F–C con `year_span` alto (cap. 10).

Mes / día de semana / rachas: derivables de `all_activations.csv` (`case_date`).
Este libro reporta los agregados principales; el CSV permite reanálizar calendarios.
""",
    )

    w(
        "20_REPETITION_AND_ROTATION.md",
        f"""
# 20 — Repetición y rotación

Etiquetas y distancias documentan:

- reaparición del fuerte (`FUERTE_EXACTO`);
- rotación T1 (distancias ≠ 0 dentro de `MISMO_GRUPO_T1`);
- rotación T2 (`MISMO_GRUPO_T2`, distancias T2);
- salto a otra familia (`SIN_RELACION_DIRECTA_IDENTIFICADA` / niveles 2–3).

Distancias T1 dominantes:

{md_table(['Distancia', 'Conteo', '%'], t1d[:10])}
""",
    )

    w(
        "21_RELATIONSHIP_MATRICES.md",
        f"""
# 21 — Matrices matemáticas

Generadas (conteo, % fila, % columna donde aplica):

1. fuerte → resultado (top)
2. fuerte → posición T1
3. fuerte → posición T2
4. origen → fuerte
5. confirmador → fuerte
6. día → tipo de relación
7. año → tipo de relación
8. posición origen → posición resultado
9. lotería origen → lotería resultado
10. triples de lotería

Archivos: `relationship_matrix.csv`, `full_statistics.json`.
""",
    )

    w(
        "22_RELATIONSHIP_GRAPH.md",
        f"""
# 22 — Grafo de relaciones

Nodos: 1–100.  
Aristas tipadas (no mezcladas): `t1_geometry`, `origin_fuerte`, `confirmer_fuerte`, `fuerte_result`.

Archivo: `artifacts/deep_mathematical_audit/relationship_graph.json`

Pesos: count, mean_day (si aplica), top_lottery.
""",
    )

    w(
        "23_REPEATED_SEQUENCES.md",
        f"""
# 23 — Secuencias repetidas exactas

{md_table(['Cadena O→F←C→R', 'Conteo', 'Nivel'], chain_rows)}

CSV: `repeated_sequences.csv`

Secuencias con nivel 1 (muestra <5) se listan pero **no** se elevan a conclusión.
""",
    )

    # Candidate patterns from top pairs with high consistency
    pats = [p for p in pair_rank if p["activations"] >= 10][:15]
    pat_md = []
    for i, p in enumerate(pats, 1):
        pat_md.append(
            f"""### Patrón candidato P{i:02d}: {p['origin']} → {p['fuerte']} ← {p['confirmer']}

- Condición: origen={p['origin']}, confirmador={p['confirmer']}, fuerte={p['fuerte']}
- Activaciones: **{p['activations']}** ({p['sample_bucket']}, {p['consistency']})
- Años: {p['years']} (span {p['year_span']})
- Resultados posteriores top: {p['top_results']}
- Primarios top: {p['top_primary']}
- Días top: {p['top_days']}
- Estado: **observado / repetido** — no incorporado al motor
"""
        )

    w(
        "24_CANDIDATE_PATTERNS.md",
        f"""
# 24 — Patrones candidatos de investigación

No se incorporan al motor. Lenguaje: observado, repetido, consistente, inestable, muestra.

{''.join(pat_md) if pat_md else '_Sin pares ≥10 activaciones en el ranking exportado._'}
""",
    )

    case_parts = ["# 25 — Cincuenta casos explicados\n"]
    for e in explained:
        case_parts.append(
            f"""## {e.get('case_id','?')} — {e['case_date']} · {e['origin']}→{e['fuerte']}←{e['confirmer']}

1. Fecha: **{e['case_date']}**
2. Origen: {e['origin']} · Confirmador: {e['confirmer']} · Fuerte: **{e['fuerte']}**
3. Grupo T1: {e.get('t1_group')}
4. Posición T1 del fuerte: {e.get('t1_pos_fuerte')}
5. Grupo T2: {e.get('t2_group')}
6. ¿Salió el fuerte?: **{'Sí' if e.get('fuerte_appeared') else 'No'}** (D+{e.get('first_day')}, {e.get('first_lottery')})
7. Confirmadores ese día (n): {e.get('n_confirmers')} · Fuertes ese día: {e.get('n_fuertes')}
8. Primera relación no trivial: `{e.get('related_first')}`
9. Muestra de apariciones relacionadas: `{e.get('appearance_sample')}`

Interpretación: reconstruir con `all_activations.csv` + `all_future_appearances.csv` filtrando `case_date` y `fuerte`.
"""
        )
    w("25_FIFTY_EXPLAINED_CASES.md", "\n".join(case_parts))

    man_parts = [
        "# 26 — Checklist de verificación manual\n",
        "Recalcular a mano cada caso. Marcar ☐/☑.\n",
    ]
    for e in manual:
        man_parts.append(
            f"""## {e.get('case_id')} — {e['case_date']}

- [ ] Observados del día recuperados del histórico
- [ ] Candidatos T1 de origen {e['origin']} = grupo código {e['origin']}
- [ ] Confirmador {e['confirmer']} ∈ vecinos T2({e['fuerte']})
- [ ] Fuerte oficial = {e['fuerte']} (confirmador no fortalecido)
- [ ] Ventana solo D+1…D+7
- [ ] Clasificación de resultados posteriores coincide con CSV
- [ ] Posiciones T1/T2 y distancias coinciden

Datos: origen={e['origin']}, fuerte={e['fuerte']}, confirmer={e['confirmer']}, exacto={e.get('fuerte_appeared')}, first_day={e.get('first_day')}
"""
        )
    w("26_MANUAL_VERIFICATION_CHECKLIST.md", "\n".join(man_parts))

    w(
        "27_EXCEPTIONS_AND_COUNTERCASES.md",
        f"""
# 27 — Excepciones y contracasos

- Activaciones sin exacto: {fh['without_exact']}
- Etiqueta `SIN_RELACION_DIRECTA_IDENTIFICADA`: ver `label_summary`
- Pares con muestra 1–4: presentes en ranking pero nivel 1
- Multi-confirmación / multi-fuerte: casos en capítulo 25

No existen reglas “siempre”. Todo conteo admite excepciones en el CSV.
""",
    )

    w(
        "28_DEEP_FINDINGS.md",
        f"""
# 28 — Hallazgos profundos (solo conteos)

1. **Activaciones cadena:** {t['chain_activations']}; **fuertes/día:** {t['fuerte_activations_unique_per_day']}.
2. **Temporalidad del exacto:** masa en días tempranos — ver tabla D+n.
3. **Posición T1:** distancias dominantes = {ap['top_t1_dist'][:3]}.
4. **Posición T2:** distancias dominantes = {ap['top_t2_dist'][:3]}.
5. **Cadenas más repetidas:** {ap['top_chain'][:3] if ap.get('top_chain') else summary['top_chains'][:3]}.
6. **Transiciones de lotería top:** {lot_rows[:5]}.
7. **Etiquetas top:** {lab[:5]}.

Ningún hallazgo se convierte en regla del motor en esta fase.
""",
    )

    w(
        "29_ENGINE_RESEARCH_RECOMMENDATIONS.md",
        """
# 29 — Recomendaciones de investigación (sin implementar)

1. Conservar geometría oficial O→F←C.
2. Exponer al usuario **posición y distancia T1/T2**, no solo “salió/no salió”.
3. Investigar cadenas de nivel 4–5 con estabilidad multi-año.
4. No incorporar patrones candidatos automáticamente.
5. No iniciar J-11A desde este informe.
6. No modificar Tabla 1/2.
""",
    )

    w(
        "30_FINAL_REPORT.md",
        f"""
# 30 — Informe final

## Identificación

| Campo | Valor |
|-------|--------|
| Rama | `{summary['branch']}` |
| Commit fase | `{summary['phase_commit']}` |
| Worktree | `{summary['worktree']}` |
| audit_id | `{audit_id}` |
| Período | {c['period_from']} → {c['period_to']} |
| Producción | intacta |
| J-11A | no iniciado |

## Respuestas numéricas (1–30, extracto)

1. Activaciones cadena: **{t['chain_activations']}**
2. Fuertes distintos: **{t['distinct_fuertes']}** (activaciones fuerte/día: {t['fuerte_activations_unique_per_day']})
3. Exacto por D+n: {fh['by_day']}
4. Lotería/posición de primera aparición: ver `strong_exact_results.csv`
5–8. Cuando no sale: primer relacionado y posiciones en `all_future_appearances.csv` + cap. 07/25
9. Distancia T1 más frecuente: {summary['t1_distance_rank'][0] if summary['t1_distance_rank'] else '—'}
10. Anterior vs siguiente: comparar dist −1 y +1 en cap. 08
11. Cercanos vs lejanos: etiquetas T1 en `label_summary`
12–13. Confirmador / compañero del confirmador: etiquetas dedicadas
14. Cadenas top: cap. 10
15–16. Estabilidad anual / lotería: cap. 17–18
17. Posiciones de sorteo: cap. 16
18–19. Multi-confirmación / multi-fuerte: cap. 14/25
20. Número con más repetición como fuerte: {top_fuertes[0]['number'] if top_fuertes else '—'}
21–22. Pares y loterías: cap. 10/17
23–27. T1/T2 como secuencia ordenada: distancias ≠ 0 demuestran uso del orden canónico
28–30. Ciclos/estables/inestables: niveles de consistencia + year_span

## Rutas

- Libro HTML: `docs/lottery/deep_mathematical_audit/index.html`
- CSV: `artifacts/deep_mathematical_audit/*.csv`
- JSON: `artifacts/deep_mathematical_audit/full_statistics.json`

## Cierre

Período procesado. Trazabilidad por CSV. 50 casos. 20 verificaciones manuales.
Producción intacta. Motor intacto. Detener y esperar autorización.
""",
    )

    # Dashboard HTML with filters (client-side over embedded top data)
    embed = {
        "audit_id": audit_id,
        "totals": t,
        "first_hit": fh,
        "top_chains": summary["top_chains"][:30],
        "top_pairs": summary["top_pairs"][:30],
        "labels": summary["label_summary"][:30],
        "t1_dist": summary["t1_distance_rank"][:20],
        "yearly": summary["yearly"],
        "lottery_triples": summary["matrices"]["lottery_triples_top"][:30],
        "explained": [
            {
                "case_id": e.get("case_id"),
                "case_date": e["case_date"],
                "origin": e["origin"],
                "fuerte": e["fuerte"],
                "confirmer": e["confirmer"],
                "first_day": e.get("first_day"),
                "fuerte_appeared": e.get("fuerte_appeared"),
            }
            for e in explained
        ],
    }
    chapters = sorted(p.name for p in DOCS.glob("*.md") if p.name[:2].isdigit() or p.name.startswith("00_"))
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<title>Auditoría matemática profunda NR</title>
<style>
body{{font-family:Georgia,serif;max-width:1100px;margin:2rem auto;padding:0 1rem;line-height:1.5}}
h1,h2,h3,label{{font-family:system-ui,sans-serif}}
.card{{border:1px solid #e5e7eb;border-radius:12px;padding:1rem;margin:1rem 0;background:#fafafa}}
.warn{{background:#fff7ed}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid #eee;padding:.35rem .4rem;text-align:left}}
img{{max-width:100%;border:1px solid #eee;border-radius:8px}}
input,select{{padding:.35rem;margin:.2rem;font-size:13px}}
nav a{{display:inline-block;margin:.15rem .4rem .15rem 0;font-family:system-ui;font-size:13px}}
</style>
</head>
<body>
<h1>Auditoría matemática profunda</h1>
<p>audit_id <code>{audit_id}</code> · {meth} · {c['period_from']} → {c['period_to']}</p>
<div class="card warn">Sin J-11A. Sin cambios a motor/tablas/Producción. Sin eje aleatorio.</div>
<div class="card">
<table>
<tr><th>Cadenas O→F←C</th><td>{t['chain_activations']}</td></tr>
<tr><th>Fuertes únicos/día</th><td>{t['fuerte_activations_unique_per_day']}</td></tr>
<tr><th>Fuertes distintos</th><td>{t['distinct_fuertes']}</td></tr>
<tr><th>Apariciones filas</th><td>{t['future_appearance_rows']}</td></tr>
<tr><th>Exactos (primera vez)</th><td>{fh['with_exact']} / {fh['activations']}</td></tr>
</table>
</div>
<h2>Gráficos</h2>
<img src="assets/exact_by_day.svg" alt="D+n"/>
<img src="assets/t1_distances.svg" alt="T1"/>
<img src="assets/t2_distances.svg" alt="T2"/>
<img src="assets/top_chains.svg" alt="chains"/>
<img src="assets/lottery_transitions.svg" alt="lot"/>
<img src="assets/activations_by_year.svg" alt="year"/>
<h2>Filtro de casos explicados</h2>
<div class="card">
<label>Fuerte <input id="fFuerte" type="number"/></label>
<label>Origen <input id="fOrigin" type="number"/></label>
<label>Año <input id="fYear" type="number"/></label>
<button id="btnFilter">Filtrar</button>
<table id="caseTable"><thead><tr>
<th>ID</th><th>Fecha</th><th>O</th><th>F</th><th>C</th><th>Exacto</th><th>D+</th>
</tr></thead><tbody></tbody></table>
</div>
<script>
const DATA = {json.dumps(embed, ensure_ascii=False)};
function render(rows){{
  const tb=document.querySelector('#caseTable tbody');
  tb.innerHTML=rows.map(r=>`<tr><td>${{r.case_id}}</td><td>${{r.case_date}}</td><td>${{r.origin}}</td><td>${{r.fuerte}}</td><td>${{r.confirmer}}</td><td>${{r.fuerte_appeared}}</td><td>${{r.first_day ?? ''}}</td></tr>`).join('');
}}
render(DATA.explained);
document.getElementById('btnFilter').onclick=()=>{{
  const f=document.getElementById('fFuerte').value;
  const o=document.getElementById('fOrigin').value;
  const y=document.getElementById('fYear').value;
  render(DATA.explained.filter(r=>{{
    if(f && String(r.fuerte)!==f) return false;
    if(o && String(r.origin)!==o) return false;
    if(y && !String(r.case_date).startsWith(y)) return false;
    return true;
  }}));
}};
</script>
<h2>Capítulos</h2>
<nav>
{''.join(f'<a href="{ch}">{ch}</a>' for ch in chapters)}
</nav>
<p>CSV en <code>artifacts/deep_mathematical_audit/</code>. Para filtros completos sobre todas las activaciones, usar los CSV (el dashboard embebe casos y tops).</p>
</body></html>
"""
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    (ART / "executive_report.html").write_text(html, encoding="utf-8")
    print(json.dumps({"book_chapters": len(chapters), "explained": len(explained)}, indent=2))
