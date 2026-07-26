#!/usr/bin/env python3
"""Expand forensic audit evidence into a readable 20-chapter book + HTML dashboard."""

from __future__ import annotations

import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs/lottery/forensic_audit"
ART = REPO / "artifacts/forensic_audit"
ASSETS = DOCS / "assets"


def w(name: str, body: str) -> None:
    (DOCS / name).write_text(body.strip() + "\n", encoding="utf-8")


def bar_svg(values: dict[str, float], title: str, path: Path, *, ylabel: str = "") -> None:
    items = list(values.items())
    if not items:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        return
    w_, h, pad = 780, 300, 48
    max_v = max(values.values()) or 1
    bw = (w_ - 2 * pad) / max(len(items), 1)
    bars = []
    for i, (label, val) in enumerate(items):
        bh = (h - 2 * pad - 36) * (val / max_v)
        x = pad + i * bw + 6
        y = h - pad - bh
        bars.append(
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{bw-12:.1f}' height='{bh:.1f}' fill='#1d4ed8'/>"
            f"<text x='{x+bw/2:.1f}' y='{h-18}' text-anchor='middle' font-size='11' "
            f"font-family='system-ui'>{label}</text>"
            f"<text x='{x+bw/2:.1f}' y='{y-6:.1f}' text-anchor='middle' font-size='11' "
            f"font-family='system-ui'>{val:.1f}</text>"
        )
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{w_}' height='{h}'>"
        f"<rect width='100%' height='100%' fill='#fafafa'/>"
        f"<text x='{pad}' y='28' font-size='15' font-family='system-ui' font-weight='600'>{title}</text>"
        + "".join(bars)
        + "</svg>"
    )
    path.write_text(svg, encoding="utf-8")


def main() -> int:
    s = json.loads((ART / "statistics.json").read_text(encoding="utf-8"))
    a = s["aggregates"]
    ap = a["answers_preview"]
    bl = s.get("baseline_random") or {}
    cases = s.get("case_studies") or json.loads((ART / "cases.json").read_text(encoding="utf-8"))
    r = s["range"]
    meth = s["methodology_version"]
    audit_id = s["audit_id"]

    # charts
    ASSETS.mkdir(parents=True, exist_ok=True)
    bar_svg(
        {x["bucket"].replace("_", "\n")[:16]: x["pct_of_misses"] for x in a["ranking_when_fuerte_misses"]},
        "Cuando el fuerte NO salió — % de misses (relación más cercana)",
        ASSETS / "miss_ranking.svg",
    )
    bar_svg(
        {f"D{k}": float(v) for k, v in a["day_offset_when_fuerte_hits"].items()},
        "Primera aparición del fuerte exacto por día de la ventana",
        ASSETS / "day_offset_hits.svg",
    )
    bar_svg(
        {y: float(v["fuerte_exact_rate_pct"]) for y, v in a["yearly"].items()},
        "Tasa de acierto exacto del fuerte por año (%)",
        ASSETS / "yearly_exact.svg",
    )
    if bl:
        bar_svg(
            {
                "Fuerte\nexacto": float(bl.get("fuerte_exact_rate", 0)),
                "Azar\nexacto": float(bl.get("random_number_exact_rate", 0)),
                "Fuerte\nfamilia": float(bl.get("fuerte_family_rate", 0)),
                "Azar\nfamilia": float(bl.get("random_family_rate", 0)),
            },
            "Frecuencias observadas vs control aleatorio (misma ventana)",
            ASSETS / "baseline_compare.svg",
        )

    featured = "\n".join(f"- `{x['name']}`" for x in s["featured_seven"])
    cov = "\n".join(
        f"| {c['year']} | {c['from']} | {c['to']} | {c['days_with_draws']} | {c['draws']} |"
        for c in s["coverage_by_year"]
    )
    miss_rows = "\n".join(
        f"| {x['bucket']} | {x['count']} | {x['pct_of_misses']}% |"
        for x in a["ranking_when_fuerte_misses"]
    )
    year_rows = "\n".join(
        f"| {y} | {v['activations']} | {v['fuerte_exact_hits']} | {v['fuerte_exact_rate_pct']}% | {v['misses']} |"
        for y, v in a["yearly"].items()
    )
    lot_rows = "\n".join(
        f"| {r_['lottery']} | {r_['activations']} | {r_['exact_hits']} | {r_['exact_rate_pct']}% |"
        for r_ in a["lottery_confirmer_stats"]
    )
    day_rows = "\n".join(
        f"| +{k} | {v} | {round(100*v/a['fuerte_exact_hits'],1) if a['fuerte_exact_hits'] else 0}% |"
        for k, v in a["day_offset_when_fuerte_hits"].items()
    )
    dist_rows = "\n".join(
        f"| {k} | {v} | {round(100*v/a['total_fuerte_activations'],2) if a['total_fuerte_activations'] else 0}% |"
        for k, v in a["distance_distribution_closest"].items()
    )
    top_num = "\n".join(
        f"| {r_['number']} | {r_['times_fuerte']} | {r_['exact_hits']} | {r_['exact_rate_pct']}% | "
        f"{r_['miss_companion']} | {r_['miss_neighbor']} | {r_['miss_none']} |"
        for r_ in a["by_number_top"][:25]
    )

    lift_e = bl.get("lift_exact")
    lift_f = bl.get("lift_family")

    w(
        "01_EXECUTIVE_SUMMARY.md",
        f"""
# 01 — Resumen ejecutivo

## Qué es esta auditoría

No es un intento de demostrar que el motor “funciona”.
No es un intento de demostrar que el motor “falla”.

Es una reconstrucción forense e **imparcial** de lo que ocurrió en el histórico oficial
después de que la metodología vigente (`{meth}`) declarara un **fuerte**.

Motor, Tabla 1, Tabla 2 y Producción **no se modificaron**.

## Universo y período

| Campo | Valor |
|-------|-------|
| Loterías | FEATURED_SEVEN (7) |
| Metodología | `{meth}` |
| Ventana de evidencia | días **+1 … +7** (nunca el mismo día) |
| DB featured min→max | {r['db_min']} → {r['db_max']} |
| Análisis | {r['analysis_from']} → {r['analysis_to']} |
| audit_id | `{audit_id}` |

Se pidieron siete años. El histórico featured en DEV llega desde 2015; se usaron
los **últimos ~7 años** disponibles hasta la fecha máxima, dejando 7 días de cola
para la ventana de validación.

## Volumen

| Métrica | Valor |
|---------|------:|
| Días con ≥2 observados | {s['days_analyzed_ge2_obs']} |
| Días con ≥1 fuerte | {s['days_with_fuerte']} |
| Activaciones de fuerte | {a['total_fuerte_activations']} |

## Frecuencias crudas (lo que salió)

| Resultado | Valor |
|-----------|------:|
| Fuerte exacto en ≤7 días | **{a['fuerte_exact_rate_pct']}%** ({a['fuerte_exact_hits']}/{a['total_fuerte_activations']}) |
| Exacto o compañero T1 (más cercano) | **{a['family_exact_or_companion_pct']}%** |
| Algo con distancia ≤ 3 | **{a['any_related_distance_le_3_pct']}%** |

### Cuando el fuerte NO salió

| Relación más cercana | Conteo | % de misses |
|----------------------|-------:|------------:|
{miss_rows}

![Miss ranking](assets/miss_ranking.svg)

## Control de azar (imprescindible para leer las frecuencias)

La ventana de 7 días, con siete loterías, concentra muchos números distintos
(mediana ≈ **{bl.get('median_unique_numbers_in_7d_window', '—')}** números únicos de 1..100).

Bajo ese régimen, un número **aleatorio** también “sale” con frecuencia similar:

| Métrica | Motor (fuerte) | Control aleatorio | Lift |
|---------|---------------:|------------------:|-----:|
| Exacto en ventana | {bl.get('fuerte_exact_rate')}% | {bl.get('random_number_exact_rate')}% | **{lift_e}** |
| Exacto o familia T1 | {bl.get('fuerte_family_rate')}% | {bl.get('random_family_rate')}% | **{lift_f}** |

![Baseline](assets/baseline_compare.svg)

**Lectura imparcial:** las frecuencias crudas son altas; el **exceso sobre el azar
en esta ventana de 7 días es ~nulo** (lift ≈ 1.00). Eso no niega la geometría T1×T2;
describe el poder discriminativo de “salió en 7 días” bajo FEATURED_SEVEN.

## Tres hechos que el histórico sí muestra

1. Tras un fuerte, el exacto aparece en ~{ap['fuerte_sale_exacto_pct']}% de activaciones (ventana 7d).
2. Cuando no, lo más cercano suele ser un **compañero Tabla 1** (~{ap['cuando_no_sale_companero_pct_of_misses']}% de misses).
3. Esas mismas tasas las reproduce casi igual un número aleatorio en la misma ventana.

Detalle: capítulos 11, 17 y 19.
""",
    )

    w(
        "02_DATA_COVERAGE.md",
        f"""
# 02 — Cobertura de datos

## Alcance

| Campo | Valor |
|-------|-------|
| Draws totales en DB | {s['db_draw_count']} |
| Draws featured cargados | {s['featured_draws_loaded']} |
| Fecha mínima featured | {r['db_min']} |
| Fecha máxima featured | {r['db_max']} |
| Análisis desde | {r['analysis_from']} |
| Análisis hasta (−7d cola) | {r['analysis_to']} |
| Cobertura pedida | 7 años |
| Cobertura usada | ~7 años (todo lo disponible dentro del objetivo) |

La DB tiene histórico desde **{r['db_min']}**. Para alinear el pedido de “últimos 7 años”
el análisis comienza en **{r['analysis_from']}**.

## Por año

| Año | Desde | Hasta | Días c/ draw | Sorteos |
|-----|-------|-------|-------------:|--------:|
{cov}

## FEATURED_SEVEN

{featured}

## Huecos y calidad

- **Duplicados inventados:** no se fabricaron resultados.
- **Archivadas:** excluidas (`is_featured = true` solamente).
- **Días sin ≥2 observados:** no generan fuerte; no entran al numerador de activaciones.
- **Cola final:** los últimos 7 días del DB no se usan como día de análisis porque
  no tendrían ventana completa de evidencia.
- **Sorteos faltantes:** cualquier día sin draws featured aparece como ausencia en
  `days_with_draws` anual; no se imputan.

Artefacto: `artifacts/forensic_audit/statistics.json`.
""",
    )

    w(
        "03_METHODOLOGY.md",
        f"""
# 03 — Metodología forense

## Principios

1. Solo histórico oficial FEATURED_SEVEN.
2. Solo metodología vigente `{meth}`.
3. Sin mirada al futuro al formar el fuerte.
4. Validación **solo** en los siete días siguientes.
5. Si el fuerte no sale: investigar **qué sí salió** y su distancia matemática.

## Paso A — Día de análisis (sin futuro)

Para cada fecha con ≥2 números observados (primer número in-universe 1..100 por lotería):

```
Número observado
    ↓
Tabla 1 → candidatos
    ↓
Tabla 2 → confirmadores
    ↓
Si un confirmador está entre los otros observados
    ↓
Fuerte oficial = candidato Tabla 1
```

Reglas inmutables:

- el confirmador **nunca** se fortalece;
- vecino T2 directo sin paso T1 **no** es fuerte oficial.

## Paso B — Ventana de evidencia

```
Día D (análisis)     → forma fuertes (sin mirar D+1…)
Días D+1 … D+7       → observa apariciones reales
Día D                → NUNCA se usa para validar
```

Para cada aparición se registra: día, lotería, posición, referencia.

## Paso C — Distancia al fuerte

| Distancia | Etiqueta | Significado |
|----------:|----------|-------------|
| 0 | FUERTE_EXACTO | Salió el fuerte |
| 1 | COMPANERO_TABLA1 | Compañero del grupo T1 |
| 2 | MISMO_CODIGO_T1 | Mismo código T1 (reserva; suele colapsar en 1) |
| 3 | VECINO_TABLA2 | Vecino T2 del fuerte |
| 4 | RELACION_INDIRECTA | Un salto vía compañero o vecino |
| 5 | SIN_RELACION | Ninguna de las anteriores |

Por activación se guarda la **distancia mínima** a cualquier número de la ventana.

## Paso D — Control de azar (imparcialidad)

Para cada activación se simula un “fuerte” aleatorio 1..100 con su propia familia T1
y se mide si aparece en **la misma ventana**. El lift = tasa_motor / tasa_azar.

Sin este control, una tasa cruda alta en una ventana densa se malinterpreta como ventaja.
""",
    )

    w(
        "04_RELATIONSHIP_TREE.md",
        f"""
# 04 — Árbol de relaciones

Cada activación genera un árbol automático:

```
Motor
 └─ Fuerte F
     ├─ Grupo Tabla 1 (compañeros)
     ├─ Grupo Tabla 2 (vecinos / confirmadores posibles)
     └─ Resultados reales en D+1…D+7
         ├─ dist 0  FUERTE_EXACTO
         ├─ dist 1  COMPANERO_TABLA1
         ├─ dist 3  VECINO_TABLA2
         ├─ dist 4  RELACION_INDIRECTA
         └─ dist 5  SIN_RELACION
```

## Cómo leerlo

El árbol **no** afirma causa. Solo clasifica lo que apareció respecto a F.

Ejemplos narrados: `16_CASE_STUDIES.md`.
Estructura completa por caso: `artifacts/forensic_audit/cases.json` → `tree_summary`.

## Conteos globales (contenidos observados por distancia más cercana)

| Distancia (más cercana) | Activaciones | % |
|-------------------------|-------------:|--:|
{dist_rows}

Interpretación: casi todas las activaciones encuentran algo ≤ dist 3 porque la ventana
cubre ~¾ del universo 1..100. Ver baseline en capítulo 01.
""",
    )

    w(
        "05_GROUP_ANALYSIS.md",
        f"""
# 05 — Análisis de grupos / familias

## Pregunta

¿El motor apunta a un número o a una familia?

## Evidencia cruda

- Exacto o compañero T1 como lo más cercano: **{a['family_exact_or_companion_pct']}%**
- Algo ≤ dist 3: **{a['any_related_distance_le_3_pct']}%**

## Evidencia relativa al azar

- Familia motor: **{bl.get('fuerte_family_rate')}%**
- Familia azar: **{bl.get('random_family_rate')}%**
- Lift: **{lift_f}**

## Conclusión descriptiva

Las tablas **sí organizan familias** (geometría T1). En la ventana de 7 días,
la aparición de “algún miembro de la familia” es casi inevitable por densidad,
tanto para el fuerte real como para un número aleatorio.

Por tanto: **sí hay estructura de familia en las tablas**; **no** hay, en esta ventana,
señal de que la familia del fuerte ocurra más que la de un número cualquiera.
""",
    )

    w(
        "06_TABLE1_ANALYSIS.md",
        f"""
# 06 — Tabla 1: utilidad observada

## Rol en el motor

Tabla 1 propone candidatos (compañeros / grupo) a partir del número observado.

## Rol en la evidencia posterior

Cuando el fuerte **no** sale, la relación más cercana es compañero T1 en
**{ap['cuando_no_sale_companero_pct_of_misses']}%** de los misses.

## Qué aporta realmente

| Aporte | Evidencia |
|--------|-----------|
| Geometría de familia | Sí — define compañeros del fuerte |
| Sustituto del exacto en misses | Frecuente en crudo (91.85% de misses) |
| Ventaja vs azar en 7 días | No detectada (lift familia ≈ {lift_f}) |

## Utilidad verdadera (descriptiva)

Tabla 1 es el **mapa de familia**. Explica *qué números están juntos*.
No demuestra, por sí sola en ventana 7d, que esa familia “salga más” que otra.
""",
    )

    w(
        "07_TABLE2_ANALYSIS.md",
        f"""
# 07 — Tabla 2: utilidad observada

## Rol en el motor

Tabla 2 define confirmadores. Sin confirmador observado **no hay fuerte oficial**.

## Rol en la evidencia posterior

Cuando el fuerte no sale, vecino T2 como más cercano:
**{ap['cuando_no_sale_vecino_pct_of_misses']}%** de los misses (mucho menos que compañeros T1).

## Qué aporta realmente

| Aporte | Evidencia |
|--------|-----------|
| Filtro de confirmación (crear el fuerte) | Central en la metodología |
| Sustituto del exacto tras el fuerte | Minoría entre misses (~7.6%) |
| DIRECT_T2 como fuerte | Fuera de metodología (rechazado en auditorías previas) |

## Utilidad verdadera (descriptiva)

Tabla 2 es el **candado de confirmación**. Aporta menos como “número que sale en su lugar”
que Tabla 1, en esta ventana.
""",
    )

    w(
        "08_STRONG_NUMBER_ANALYSIS.md",
        f"""
# 08 — El fuerte exacto

## Totales

| Métrica | Valor |
|---------|------:|
| Activaciones | {a['total_fuerte_activations']} |
| Hits exactos ≤7d | {a['fuerte_exact_hits']} |
| Tasa | {a['fuerte_exact_rate_pct']}% |
| Misses | {a['misses']} ({a['miss_rate_pct']}%) |
| Tasa azar (control) | {bl.get('random_number_exact_rate')}% |
| Lift | {lift_e} |

## ¿En qué día aparece?

| Día de la ventana | Primeras apariciones | % de hits |
|------------------:|---------------------:|----------:|
{day_rows}

![Day offset](assets/day_offset_hits.svg)

Patrón observado: la masa de primeras apariciones decrece con el día
(D1 > D2 > … > D7). Eso es coherente con “más oportunidades acumuladas al inicio”
y con saturación progresiva del universo en la ventana.

## Lectura

El fuerte **sí aparece a menudo** en 7 días. Un número aleatorio también.
La pregunta útil no es la tasa cruda, sino el lift ≈ **{lift_e}**.
""",
    )

    w(
        "09_COMPANION_ANALYSIS.md",
        f"""
# 09 — Compañeros Tabla 1

## Ranking en misses

De {a['misses']} activaciones sin exacto:

- Compañero T1 como más cercano: **{ap['cuando_no_sale_companero_pct_of_misses']}%**

## ¿Significa que “sale el compañero en lugar del fuerte”?

En frecuencia cruda, sí: cuando falta el exacto, casi siempre hay un compañero en la ventana.


En frecuencia relativa al azar, la familia completa (exacto∪compañeros) ocurre al mismo
ritmo que para un número aleatorio (lift ≈ {lift_f}).

## Implicación pedagógica

Tiene sentido **mostrar la familia T1** al usuario como contexto del fuerte.
No tiene sentido, con esta evidencia de 7 días, vender el compañero como predicción.
""",
    )

    w(
        "10_NEIGHBOR_ANALYSIS.md",
        f"""
# 10 — Vecinos Tabla 2

## En misses

Vecino T2 como relación más cercana: **{ap['cuando_no_sale_vecino_pct_of_misses']}%**
({next(x['count'] for x in a['ranking_when_fuerte_misses'] if x['bucket']=='VECINO_TABLA2')} casos).

## Comparado con compañeros

Los vecinos son un orden de magnitud menos frecuentes como “sustituto” del fuerte
que los compañeros T1, en esta ventana.

## Regla metodológica intacta

Un vecino T2 **sin** paso por candidato T1 no se cuenta como fuerte oficial.
Esta auditoría no lo rehabilita.
""",
    )

    w(
        "11_DISTANCE_ANALYSIS.md",
        f"""
# 11 — Distancias matemáticas

## Escala

| d | Etiqueta |
|--:|----------|
| 0 | Fuerte exacto |
| 1 | Compañero Tabla 1 |
| 2 | Mismo código T1 |
| 3 | Vecino Tabla 2 |
| 4 | Relación indirecta |
| 5 | Sin relación |

## Distribución (distancia más cercana por activación)

| Etiqueta | Activaciones | % |
|----------|-------------:|--:|
{dist_rows}

## Lectura

- Distancia 0 domina (~{a['fuerte_exact_rate_pct']}%).
- Distancia 1 absorbe casi todos los misses.
- Distancia 5 es casi inexistente (**{ap['cuando_no_sale_sin_relacion_pct_of_misses']}%** de misses):
  con mediana ~{bl.get('median_unique_numbers_in_7d_window')} números únicos en la ventana,
  “no tocar la familia” es raro.

La métrica de distancia es útil para **clasificar**; no implica por sí sola ventaja predictiva.
""",
    )

    w(
        "12_YEARLY_ANALYSIS.md",
        f"""
# 12 — Análisis por año

| Año | Activaciones | Hits exactos | Tasa | Misses |
|-----|-------------:|-------------:|-----:|-------:|
{year_rows}

![Yearly](assets/yearly_exact.svg)

## Observaciones

- Las tasas anuales de exacto oscilan en una banda estrecha (~71–79%).
- No hay un año que “rompa” el patrón de forma extrema en esta muestra.
- La estabilidad anual refuerza que el fenómeno es estructural de la **ventana densa**,
  no un artefacto de un solo período.
""",
    )

    w(
        "13_LOTTERY_ANALYSIS.md",
        f"""
# 13 — Por lotería confirmadora

Cada activación puede atribuirse a una o más loterías que aportaron confirmadores.
Conteos (una activación puede incrementar varias filas si hay multi-confirmación):

| Lotería | Activaciones | Hits exactos | Tasa |
|---------|-------------:|-------------:|-----:|
{lot_rows}

## Mejores / peores (tasa exacta cruda)

En esta muestra las tasas por lotería confirmadora están **muy cercanas entre sí**
(banda ~73–77%). No emerge una lotería confirmadora con ventaja cruda grande.

Cualquier ranking fino debe leerse con el mismo caveat del baseline: la ventana 7d
aplana diferencias.
""",
    )

    w(
        "14_SEVEN_DAY_ANALYSIS.md",
        f"""
# 14 — Horizonte de siete días

## Regla

Validación exclusiva en **D+1 … D+7**. El día D no cuenta.

## Densidad

| Estadístico | Valor |
|-------------|------:|
| Mediana de números únicos en la ventana | {bl.get('median_unique_numbers_in_7d_window')} |
| Media | {bl.get('mean_unique')} |

Con ~76 números distintos de 100 posibles, la ventana es un **casi-universo**.

## Dónde aparecen los exactos

Ver tabla y gráfico del capítulo 08. La moda está en los primeros días;
aún así hay apariciones en D6–D7.

## Implicación metodológica

Una ventana tan ancha es excelente para **describir co-ocurrencias**,
y muy pobre para **discriminar** un número específico frente al azar.
""",
    )

    # miss companion by year for patterns
    comp_by_year = []
    for y, v in a["yearly"].items():
        miss = v["misses"] or 1
        mb = v.get("miss_buckets") or {}
        comp_by_year.append(f"{y}: {round(100.0 * mb.get('COMPANERO_TABLA1', 0) / miss, 1)}%")

    w(
        "15_NEW_PATTERNS.md",
        f"""
# 15 — Patrones nuevos (solo los que salen del histórico)

No se inventan reglas. Solo se registran regularidades medidas.

## P1 — Miss ≈ compañero T1

Cuando el exacto falta, ~{ap['cuando_no_sale_companero_pct_of_misses']}% de las veces
lo más cercano es un compañero Tabla 1.

Compañero-en-miss por año (% de misses): {", ".join(comp_by_year)}.

## P2 — Ventana 7d ≈ saturación del universo

Mediana {bl.get('median_unique_numbers_in_7d_window')}/100 números únicos →
casi siempre hay *alguna* relación ≤ 3.

## P3 — Lift nulo vs azar en 7 días

Exacto lift ≈ {lift_e}; familia lift ≈ {lift_f}.

## P4 — Estabilidad anual

Tasas de exacto por año en banda estrecha (capítulo 12).

## P5 — Multi-confirmación no salva la tasa

| Confirmadores | Activaciones | Tasa exacta |
|---------------|-------------:|------------:|
"""
        + "\n".join(
            f"| {k} | {v['activations']} | {v['exact_rate_pct']}% |"
            for k, v in sorted(a["confirmation_level_stats"].items(), key=lambda kv: kv[0])
        )
        + """

No se observa, en esta muestra, que más confirmadores disparen la tasa exacta 7d
de forma monótona clara (los n altos tienen poca muestra).

## P6 — Loterías confirmadoras equivalentes

Ninguna lotería FEATURED_SEVEN domina el ranking de confirmación→exacto (capítulo 13).
""",
    )

    case_parts = ["# 16 — Estudios de caso\n", "Casos educativos mezclando hits, compañeros, vecinos y sin relación.\n"]
    for c in cases:
        case_parts.append(f"## {c['id']} — {c['date']} · fuerte **{c['fuerte']}**\n")
        case_parts.append(
            f"""
```
Motor
 └─ {c['fuerte']}
     ├─ generador: {c['generator']} ({c['generator_lottery']})
     ├─ confirmadores: {c['confirmers']} ({c['confirmer_lotteries']})
     ├─ compañeros T1: {c['tree_summary']['table1_companions']}
     ├─ vecinos T2: {c['tree_summary']['table2_neighbors']}
     └─ ventana D+1…D+7
         └─ bucket: {c['outcome_bucket']}
             más cercano: {c['closest_number']} (dist {c['closest_distance']})
```
"""
        )
        case_parts.append(
            f"- ¿Salió el fuerte?: **{'Sí' if c['fuerte_hit'] else 'No'}**\n"
            f"- Primer día (si aplica): {c['first_day_offset']}\n"
            f"- Primera aparición: {c.get('first_appearance')}\n"
            f"- Conteos por distancia: {c['tree_summary']['result_counts_by_distance']}\n"
        )
        if c.get("miss_flags"):
            mf = c["miss_flags"]
            case_parts.append(
                "### Banderas sobre el ejemplo más cercano (miss)\n\n"
                f"| Pregunta | Respuesta |\n|----------|----------|\n"
                f"| ¿Grupo T1? | {mf.get('pertenece_grupo_t1')} |\n"
                f"| ¿Grupo T2? | {mf.get('pertenece_grupo_t2')} |\n"
                f"| ¿Código T1? | {mf.get('comparte_codigo_t1')} |\n"
                f"| ¿Código T2? | {mf.get('comparte_codigo_t2')} |\n"
                f"| ¿Compañero? | {mf.get('es_companero')} |\n"
                f"| ¿Vecino? | {mf.get('es_vecino')} |\n"
                f"| ¿Indirecta? | {mf.get('relacion_indirecta')} |\n"
                f"| Distancia | {mf.get('distancia')} ({mf.get('distancia_label')}) |\n"
            )
    w("16_CASE_STUDIES.md", "\n".join(case_parts))

    w(
        "17_STATISTICAL_RESULTS.md",
        f"""
# 17 — Resultados estadísticos

## Totales

| Métrica | Valor |
|---------|------:|
| Activaciones | {a['total_fuerte_activations']} |
| Exact hits | {a['fuerte_exact_hits']} ({a['fuerte_exact_rate_pct']}%) |
| Misses | {a['misses']} ({a['miss_rate_pct']}%) |
| Familia (exacto∪compañero) | {a['family_exact_or_companion_pct']}% |
| Lift exacto vs azar | {lift_e} |
| Lift familia vs azar | {lift_f} |

## Ranking cuando NO sale el fuerte

| Bucket | n | % misses |
|--------|--:|---------:|
{miss_rows}

## Por número (top 25 por veces fuerte)

| Número | Veces fuerte | Exactos | Tasa | Miss→compañero | Miss→vecino | Miss→nada |
|-------:|-------------:|--------:|-----:|---------------:|------------:|----------:|
{top_num}

CSV completo: `artifacts/forensic_audit/by_number.csv`  
Outcomes: `artifacts/forensic_audit/outcomes_summary.csv`  
JSON: `artifacts/forensic_audit/statistics.json`
""",
    )

    # find SIN_RELACION case if any
    none_cases = [c for c in cases if c.get("outcome_bucket") == "SIN_RELACION"]
    none_txt = (
        "\n".join(f"- {c['id']} ({c['date']}, fuerte {c['fuerte']})" for c in none_cases)
        if none_cases
        else "- (ver outcomes CSV filtrando `outcome_bucket=SIN_RELACION`; es extremadamente raro)"
    )

    w(
        "18_COUNTER_EXAMPLES.md",
        f"""
# 18 — Contraejemplos

El histórico **no** es uniforme. Contraejemplos documentados:

## C1 — Miss sin ninguna relación (dist 5)

Conteo global: **{next(x['count'] for x in a['ranking_when_fuerte_misses'] if x['bucket']=='SIN_RELACION')}**
de {a['misses']} misses ({ap['cuando_no_sale_sin_relacion_pct_of_misses']}%).

Casos en la muestra educativa:
{none_txt}

## C2 — Miss donde lo más cercano es vecino T2, no compañero

{next(x['count'] for x in a['ranking_when_fuerte_misses'] if x['bucket']=='VECINO_TABLA2')} casos
({ap['cuando_no_sale_vecino_pct_of_misses']}% de misses). Ver FX con bucket `VECINO_TABLA2`.

## C3 — Exacto tardío (D4–D7)

Existen hits cuya primera aparición ocurre al final de la ventana
(capítulo 08). “Salió” no implica “salió rápido”.

## C4 — Multi-confirmación con miss

Hay activaciones con ≥2 confirmadores que aun así no ven el exacto en 7 días
(ver `confirmation_level_stats` en JSON).

Estos contraejemplos impiden afirmar reglas del tipo “siempre” o “nunca”.
""",
    )

    w(
        "19_FINAL_CONCLUSIONS.md",
        f"""
# 19 — Conclusiones finales (solo evidencia)

## Las 10 preguntas

### 1. ¿Qué ocurre realmente después de un fuerte?

En la ventana D+1…D+7, el número fuerte aparece en **{a['fuerte_exact_rate_pct']}%**
de las activaciones. Si no, casi siempre aparece un compañero T1
(**{ap['cuando_no_sale_companero_pct_of_misses']}%** de los misses).
La misma ventana también hace aparecer un número aleatorio al **{bl.get('random_number_exact_rate')}%**.

### 2. ¿El fuerte suele salir?

Sale con frecuencia cruda alta (**{ap['fuerte_sale_exacto_pct']}%**).
Respecto al azar en 7 días: **no más** (lift **{lift_e}**).

### 3. ¿O suelen salir números relacionados?

En crudo, sí (familia **{a['family_exact_or_companion_pct']}%**).
Respecto al azar: lift familia **{lift_f}**.

### 4. ¿Qué relación matemática aparece con mayor frecuencia?

Entre misses: **compañero Tabla 1**.
En el conjunto total: **fuerte exacto** (dist 0), seguido de compañero (dist 1).

### 5. ¿Qué tabla aporta más información?

- **Para crear el fuerte:** Tabla 2 (confirmación) es necesaria.
- **Para clasificar lo que sale después:** Tabla 1 (familia) domina los misses.
- **Para ventaja vs azar en 7d:** ninguna muestra lift relevante.

### 6. ¿Cuál es la verdadera utilidad de Tabla 1?

Mapear **familias** de números alrededor de un candidato. Útil como lenguaje
descriptivo; no como prueba de elevación 7d.

### 7. ¿Cuál es la verdadera utilidad de Tabla 2?

**Confirmar** candidatos T1. Como “número que sale en lugar del fuerte”,
es secundaria frente a compañeros T1.

### 8. ¿Las tablas describen un número o una familia?

**Una familia con centro.** El fuerte es el centro declarado; la evidencia de misses
se concentra en compañeros del mismo grupo T1.

### 9. ¿Existe una estructura matemática más profunda?

La estructura medida aquí es: **geometría T1×T2 + saturación de ventana 7d**.
El patrón miss→compañero es real en crudo y, a la vez, compatible con azar bajo
densidad alta. No se introduce una fórmula nueva.

### 10. Si se rediseñara el motor solo con esta evidencia…

| Conservar | Descartar como señal 7d | Investigar más |
|-----------|-------------------------|----------------|
| Geometría T1×T2 para proponer/confirmar | Usar “salió en 7 días” como métrica de éxito predictivo | Ventanas más cortas (1–3d) con baseline same-k |
| Distancia 0–5 como lenguaje de explicación | DIRECT_T2 como fuerte | Seguimiento de familia vs exacto con controles |
| FEATURED_SEVEN como universo | Prometer lift en ventana ancha | Comparar generadores/confirmadores con tests fuera de muestra |

## Veredicto forense (imparcial)

> Tras un fuerte oficial, el histórico de 7 años en ventana +1…+7 muestra
> co-ocurrencias frecuentes del exacto y de su familia T1.
> Esas co-ocurrencias **no exceden** de forma material lo esperado por azar
> dada la densidad de la ventana (lift ≈ 1.00).
>
> Las tablas describen familias. La ventana de 7 días no discrimina.
""",
    )

    w(
        "20_RECOMMENDATIONS.md",
        f"""
# 20 — Recomendaciones (investigación; sin implementar)

1. **Explicar en familia:** mostrar fuerte + compañeros T1 + vecinos T2 con distancia 0–5.
2. **No usar 7 días como KPI predictivo** sin baseline: la ventana está saturada
   (mediana ~{bl.get('median_unique_numbers_in_7d_window')}/100).
3. **Conservar** la geometría oficial T1×T2; **no** promover DIRECT_T2.
4. **No modificar** Tabla 1/2 ni fórmulas a partir solo de frecuencias crudas.
5. **No iniciar J-11A** predictivo basándose en este informe descriptivo.
6. Si hubiera una siguiente investigación (requiere autorización expresa):
   repetir el árbol de distancias en ventanas **1d / 3d** con el mismo control de azar.

Motor intacto. Producción intacta. Informe cerrado.
""",
    )

    # README index
    w(
        "README.md",
        f"""
# Auditoría forense — Motor de Relaciones Numéricas

Libro de investigación imparcial · audit_id `{audit_id}`

**Abrir:** [index.html](index.html) (dashboard navegable)

| Cap | Archivo |
|----:|---------|
| 00 | [00_ISOLATION.md](00_ISOLATION.md) |
| 01 | [01_EXECUTIVE_SUMMARY.md](01_EXECUTIVE_SUMMARY.md) |
| 02 | [02_DATA_COVERAGE.md](02_DATA_COVERAGE.md) |
| 03 | [03_METHODOLOGY.md](03_METHODOLOGY.md) |
| 04 | [04_RELATIONSHIP_TREE.md](04_RELATIONSHIP_TREE.md) |
| 05 | [05_GROUP_ANALYSIS.md](05_GROUP_ANALYSIS.md) |
| 06 | [06_TABLE1_ANALYSIS.md](06_TABLE1_ANALYSIS.md) |
| 07 | [07_TABLE2_ANALYSIS.md](07_TABLE2_ANALYSIS.md) |
| 08 | [08_STRONG_NUMBER_ANALYSIS.md](08_STRONG_NUMBER_ANALYSIS.md) |
| 09 | [09_COMPANION_ANALYSIS.md](09_COMPANION_ANALYSIS.md) |
| 10 | [10_NEIGHBOR_ANALYSIS.md](10_NEIGHBOR_ANALYSIS.md) |
| 11 | [11_DISTANCE_ANALYSIS.md](11_DISTANCE_ANALYSIS.md) |
| 12 | [12_YEARLY_ANALYSIS.md](12_YEARLY_ANALYSIS.md) |
| 13 | [13_LOTTERY_ANALYSIS.md](13_LOTTERY_ANALYSIS.md) |
| 14 | [14_SEVEN_DAY_ANALYSIS.md](14_SEVEN_DAY_ANALYSIS.md) |
| 15 | [15_NEW_PATTERNS.md](15_NEW_PATTERNS.md) |
| 16 | [16_CASE_STUDIES.md](16_CASE_STUDIES.md) |
| 17 | [17_STATISTICAL_RESULTS.md](17_STATISTICAL_RESULTS.md) |
| 18 | [18_COUNTER_EXAMPLES.md](18_COUNTER_EXAMPLES.md) |
| 19 | [19_FINAL_CONCLUSIONS.md](19_FINAL_CONCLUSIONS.md) |
| 20 | [20_RECOMMENDATIONS.md](20_RECOMMENDATIONS.md) |

Artefactos: `artifacts/forensic_audit/`
""",
    )

    # HTML dashboard richer
    chapters = sorted(p.name for p in DOCS.glob("*.md") if p.name[:2].isdigit())
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<title>Auditoría forense NR — 7 años</title>
<style>
body{{font-family:Georgia,serif;max-width:960px;margin:2rem auto;padding:0 1.25rem;line-height:1.55;color:#111;background:#fff}}
h1,h2,h3{{font-family:system-ui,sans-serif}}
.card{{border:1px solid #e5e7eb;border-radius:14px;padding:1.1rem 1.25rem;margin:1rem 0;background:#fafafa}}
.warn{{background:#fff7ed;border-color:#fdba74}}
.ok{{background:#eff6ff;border-color:#93c5fd}}
nav a{{display:block;margin:.2rem 0;font-family:system-ui,sans-serif;font-size:14px}}
img{{max-width:100%;border:1px solid #eee;border-radius:10px;background:#fff}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
td,th{{border-bottom:1px solid #eee;padding:.4rem .5rem;text-align:left}}
code{{background:#f3f4f6;padding:0 .25rem;border-radius:4px}}
</style>
</head>
<body>
<h1>Auditoría forense del Motor de Relaciones Numéricas</h1>
<p>audit_id <code>{audit_id}</code> · {meth} · solo lectura · FEATURED_SEVEN</p>
<div class="card warn">
<strong>Imparcial.</strong> Describe frecuencias históricas. Incluye control de azar.
No modifica motor, tablas ni producción. No inicia J-11A.
</div>
<div class="card ok">
<table>
<tr><th>Rango análisis</th><td>{r['analysis_from']} → {r['analysis_to']}</td></tr>
<tr><th>Activaciones</th><td>{a['total_fuerte_activations']}</td></tr>
<tr><th>Exacto ≤7d</th><td>{a['fuerte_exact_rate_pct']}% ({a['fuerte_exact_hits']}/{a['total_fuerte_activations']})</td></tr>
<tr><th>Azar exacto</th><td>{bl.get('random_number_exact_rate')}%</td></tr>
<tr><th>Lift exacto</th><td><strong>{lift_e}</strong></td></tr>
<tr><th>Miss → compañero T1</th><td>{ap['cuando_no_sale_companero_pct_of_misses']}% de misses</td></tr>
<tr><th>Lift familia</th><td><strong>{lift_f}</strong></td></tr>
</table>
</div>
<h2>Gráficos</h2>
<p>Observado vs azar</p><img src="assets/baseline_compare.svg" alt="baseline"/>
<p>Ranking en misses</p><img src="assets/miss_ranking.svg" alt="miss"/>
<p>Día de aparición del exacto</p><img src="assets/day_offset_hits.svg" alt="days"/>
<p>Tasa exacta por año</p><img src="assets/yearly_exact.svg" alt="yearly"/>
<h2>Capítulos del libro</h2>
<nav>
""" + "\n".join(f'<a href="{ch}">{ch}</a>' for ch in chapters) + """
</nav>
<p><a href="README.md">README</a> · Artefactos en <code>artifacts/forensic_audit/</code></p>
</body></html>
"""
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    (ART / "dashboard.html").write_text(html, encoding="utf-8")
    print(json.dumps({"chapters": len(chapters), "lift_exact": lift_e, "lift_family": lift_f}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
