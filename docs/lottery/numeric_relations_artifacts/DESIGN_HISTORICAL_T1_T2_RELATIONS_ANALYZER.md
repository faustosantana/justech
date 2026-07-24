# Diseño — Analizador Histórico de Relaciones Tabla 1 ↔ Tabla 2

**Estado:** BORRADOR PARA APROBACIÓN — no implementar en Producción hasta GO explícito.  
**Fecha:** 2026-07-24  
**Alcance único:** metodología oficial de relaciones entre Tabla 1, Tabla 2 e histórico de sorteos.  
**Fuera de alcance:** Winning Engine genérico, dashboards ejecutivos genéricos, motores predictivos independientes, consenso sin esta lógica, licitaciones, nuevas fórmulas, estadísticas desconectadas de T1/T2.

---

## 1. Confirmación de la lógica entendida

### 1.1 Fuente de verdad (inmutable)

| Tabla | Rol | Fórmula | Código | Universo |
|-------|-----|---------|--------|----------|
| **Tabla 1** | Código madre + candidatos (compañeros) | `N ÷ 1220` | suma de dígitos literales (11) | 1..100 |
| **Tabla 2** | Confirmadores (vecinos) del candidato T1 | `1220 ÷ N` | suma de dígitos literales (12) | 1..100 |

**No se modifica:** fórmulas, códigos, rango, grupos, metodología matemática.

### 1.2 Regla principal (fortalecimiento)

Cuando sale un **número observado N**:

1. Usar **N como código madre de Tabla 1** (regla R4 del ADR vigente: no “el código calculado de N”, sino **N = mother_code**).
2. Candidatos = todos los números que comparten ese código en Tabla 1.
3. Para **cada** candidato C:
   - código Tabla 2 de C;
   - grupo Tabla 2 de ese código;
   - excluir C del grupo (`exclude_self`);
   - comparar vecinos T2 contra números del/los sorteo(s) analizados (excluyendo N).
4. Si aparece un vecino V de Tabla 2 → **fortalece a C** (+1 por cada confirmador distinto válido).  
   **No** fortalece a V.  
   V solo entra al ranking como candidato si V es **también** compañero T1 del mismo mother_code.

### 1.3 Múltiples confirmadores

No detenerse en la primera coincidencia. Si C tiene vecinos `{6,7,8,9,10,11}` y aparecen `{6,9,11}` → score bruto de C = **3**, con **tres** registros individuales.

### 1.4 Ejemplo pedagógico vs datos reales

El ejemplo del alcance (observado 34 → candidatos 1..5; candidato 4 ↔ confirmador 6) es **ilustrativo**.  
En catálogo real, el grupo de código T1 = 34 es el conjunto calculado (p. ej. `1, 17, 33, 49, 76`). La lógica es la misma; los integrantes salen del catálogo oficial, no de listas inventadas.

### 1.5 Lo que ya hace el motor vs lo que pide este alcance

| Capacidad | Motor v1.0.0 actual | Este alcance |
|-----------|---------------------|--------------|
| T1/T2, códigos, grupos | Sí | Mantener |
| Ancla = ocurrencias reales de N | Sí | Mantener |
| Fortalecer candidatos T1 por confirmadores T2 | Sí (+1/match, same-draw) | Mantener regla |
| Ranking + trazas por draw_id | Sí | Mantener / enriquecer |
| Seguimiento **posterior** (próx. 1/2/3/5/10 sorteos) | **No** | **Nuevo** |
| Ciclos, tasas, rachas, combinaciones | **No** | **Nuevo** |
| Matriz candidato×confirmador | **No** | **Nuevo** |
| Lotería principal vs confirmadoras + ventanas | Parcial (lista plana de loterías) | **Extender** |
| IA responde con tools (sin inventar números) | Tool analyze actual | **Ampliar tools** |

---

## 2. Diagrama exacto del flujo

```
                    ┌─────────────────────────┐
                    │  Entrada                │
                    │  N observado            │
                    │  lotería principal      │
                    │  loterías confirmadoras │
                    │  ventana ocurrencias    │
                    │  ventana posterior K    │
                    └───────────┬─────────────┘
                                │
                                ▼
              ┌─────────────────────────────────┐
              │ 1. Catálogo T1/T2 (solo lectura)│
              │    mother_code = N              │
              │    candidatos = group_T1(N)     │
              └───────────┬─────────────────────┘
                          │
                          ▼
              ┌─────────────────────────────────┐
              │ 2. Histórico ancla              │
              │    draws donde drawn_number = N │
              │    en lotería(s) principal(es)  │
              │    identidad = draw_id          │
              └───────────┬─────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
 ┌──────────────────────┐    ┌──────────────────────────┐
 │ 3. Condición actual  │    │ 4. Condiciones históricas│
 │ (por cada ancla)     │    │ (todas las anclas en     │
 │                      │    │  rango de fechas/años)   │
 │ Para cada candidato C│    │                          │
 │  vecinos_T2(C)       │    │ Emite RelationalEvent    │
 │  ∩ números del set   │    │ por (ancla, C, Vs)       │
 │  confirmador(es)     │    └────────────┬─────────────┘
 │  score = |Vs|        │                 │
 └──────────┬───────────┘                 ▼
            │                ┌──────────────────────────┐
            │                │ 5. Análisis posterior    │
            │                │    ¿C salió en +1,+2,+3, │
            │                │    +5,+10 sorteos de la  │
            │                │    lotería de seguimiento│
            │                │    (por draw_id ordenado)│
            │                └────────────┬─────────────┘
            │                             │
            └──────────────┬──────────────┘
                           ▼
              ┌─────────────────────────────────┐
              │ 6. Agregados                    │
              │  ranking actual                 │
              │  frecuencias / tasas / ciclos   │
              │  matriz combinaciones           │
              │  trazas completas               │
              └───────────┬─────────────────────┘
                          ▼
              ┌─────────────────────────────────┐
              │ 7. Presentación / Tools IA      │
              │  UI + APIs + tool results       │
              │  LLM interpreta, NO calcula     │
              └─────────────────────────────────┘
```

**Identidad de sorteo:** siempre `draw_id`. La fecha ordena o define ventanas; **nunca** fusiona dos sorteos distintos.

---

## 3. Modelo de evento histórico

### 3.1 `RelationalConditionEvent` (evento atómico)

Una **condición relacional** ocurre cuando, en el contexto de un sorteo ancla donde salió N, un candidato T1 C recibe **al menos un** confirmador T2.

```text
RelationalConditionEvent
  event_id                  # estable: hash(observed_draw_id, candidate, sorted(confirmers), scope)
  observed_number           # N
  observed_draw_id          # ancla
  observed_lottery_id
  observed_lottery_name
  observed_datetime         # date+time del ancla (ordenación)
  mother_code               # = N
  table1_candidates         # lista completa group_T1(N)
  candidate                 # C evaluado (T1)
  candidate_table2_code
  candidate_table2_group    # lista completa
  confirmers[]              # lista de ConfirmingHit (puede ser 1..n)
  score_raw                 # len(confirmers) o sum(points) con dedupe
  scope                     # primary/confirming lottery config usada
```

### 3.2 `ConfirmingHit` (confirmador individual)

```text
ConfirmingHit
  confirmer_number          # V (Tabla 2)
  confirmer_lottery_id
  confirmer_lottery_name
  confirmer_draw_id         # puede = observed_draw_id (same-draw) o draw de lotería confirmadora
  confirmer_datetime
  confirmer_position        # si aplica
  relation_mode             # same_draw | same_date | same_session | time_window | cross_lottery
  points                    # 1 (regla actual)
  dedupe_key
```

### 3.3 `PosteriorOutcome` (seguimiento del candidato)

```text
PosteriorOutcome
  follow_lottery_id         # lotería donde se busca a C (default: principal)
  windows                   # {1: bool, 2: bool, 3: bool, 5: bool, 10: bool}
  first_hit_offset          # sorteos hasta primera aparición de C (null si no en ventana máx.)
  first_hit_draw_id
  first_hit_datetime
  draws_examined[]          # draw_ids ordenados posteriores al ancla
```

### 3.4 Persistencia propuesta

- **Fase 1 (recomendada):** cálculo on-demand / materialización en job + tablas de hechos (sin tocar `lottery_draws`).
- **No mutar** histórico de sorteos.
- Tablas nuevas sugeridas (nombres tentativos):
  - `jaios.nr_condition_events`
  - `jaios.nr_confirming_hits`
  - `jaios.nr_posterior_outcomes`
  - `jaios.nr_combination_stats` (agregado refrescaable)

---

## 4. Definición de condición relacional

**Condición relacional** = tripleta operativa:

```text
(observed_number N, candidate C ∈ group_T1(N), confirmers V ⊆ neighbors_T2(C))
```

con evidencia anclada a `observed_draw_id` y a los `confirmer_draw_id` de cada V.

Variantes de conteo (configurables, documentadas en metadata):

| Variante | Cuenta como 1 condición cuando… |
|----------|----------------------------------|
| `event_per_anchor_candidate` | Ancla + C con ≥1 confirmer (score = #confirmers) |
| `event_per_confirmer` | Cada (N, C, V) es una fila atómica |
| `event_per_confirmer_set` | Ancla + C + frozenset(Vs) (combinaciones) |

**Default propuesto para estadísticas de patrón:** `event_per_confirmer` (responde “¿cuántas veces el 4 fue fortalecido porque apareció el 7?”).  
**Default para ranking actual:** score = #confirmers en el set analizado (como motor actual).

---

## 5. Definición de ciclo

**Ciclo** = número de sorteos **posteriores al ancla**, en la lotería de seguimiento, hasta que el **candidato C** vuelve a aparecer como `drawn_number`.

- Unidad: **sorteos** (secuencia por `draw_id` ordenado por datetime de esa lotería), no días calendario.
- Si C no aparece dentro de la ventana máxima configurada (p. ej. 10): ciclo = `null` / censurado; **no** inventar.
- Agregados sobre ciclos observados (solo no nulos):
  - mínimo, máximo, promedio, mediana;
  - distribución por offset {1,2,3,5,10};
  - última ocurrencia (datetime del ancla más reciente con hit);
  - racha actual (anclas recientes sin hit posterior, si se define política).

---

## 6. Definición de tasa histórica

**No** llamar “probabilidad de ganar”.

Términos oficiales:

| Término | Definición |
|---------|------------|
| **Frecuencia histórica** | Nº de veces que ocurrió la condición en el filtro |
| **Tasa de repetición / respuesta histórica** | `hits_en_ventana / condiciones` para una ventana (p. ej. “apareció C dentro de 3 sorteos”) |
| **Ciclo observado** | ver §5 |
| **Fuerza relacional** | score bruto de confirmadores en el análisis actual (o promedio histórico de score) |
| **Soporte histórico** | tamaño de muestra (n condiciones); si n &lt; umbral → advertencia |

Ejemplo:

```text
condiciones = 26
hits_next_1 = 11  → tasa_respuesta_1 = 11/26
hits_within_3 = 19 → tasa_respuesta_3 = 19/26
ciclo_promedio (solo hits) = 2.1 sorteos
```

Advertencia obligatoria si muestra pequeña, p. ej. n &lt; 10 (umbral configurable, default 10):

> “Muestra insuficiente: esta condición solo se ha observado 3 veces.”

---

## 7. APIs necesarias

### 7.1 Ya existen (reutilizar, no reemplazar)

| Método | Path | Uso |
|--------|------|-----|
| GET | `/lottery/admin/numeric-relations/tables` | A/B tablas |
| GET | `/lottery/admin/numeric-relations/groups` | compañeros / grupos |
| GET | `/lottery/admin/numeric-relations/numbers/{n}` | detalle |
| POST | `/lottery/admin/numeric-relations/analyze` | analizador **actual** (fortalecimiento same-scope) |
| POST | `/lottery/admin/predictions/numeric-relations/run` | presentación ranking (sin garantía) |

### 7.2 Nuevas (propuestas — aprobar antes de implementar)

Prefijo: `/lottery/admin/numeric-relations/history/` (o `/stats/`).

| # | Método | Path | Descripción |
|---|--------|------|-------------|
| H1 | POST | `/history/conditions/search` | Buscar condiciones con filtros (años, N, C, V, loterías, min_support) |
| H2 | GET | `/history/conditions/{event_id}` | Detalle de un evento + posterior |
| H3 | POST | `/history/posterior/summary` | Agregados de respuesta para (N[, C[, V]]) y ventanas 1/2/3/5/10 |
| H4 | POST | `/history/combinations/matrix` | Matriz C × V (counts, tasas, ciclo promedio) |
| H5 | POST | `/history/combinations/top` | Top pares / sets de confirmadores |
| H6 | POST | `/history/patterns/{observed}/{candidate}/{confirmer}` | Detalle de patrón (fechas, loterías, draw_ids, posteriores, tendencia anual) |
| H7 | POST | `/analyze/v2` *(opcional)* | Extiende analyze actual con `primary_lottery_id`, `confirming_lottery_ids`, `relation_mode`, `posterior_windows` sin romper v1 |

**Compatibilidad:** mantener `/analyze` v1 intacto hasta migración explícita.

### 7.3 Tools IA (nuevas / extensión)

| Tool | Propósito |
|------|-----------|
| `lottery_analyze_numeric_relations` | Ya existe — análisis actual |
| `lottery_nr_history_conditions` | H1 |
| `lottery_nr_posterior_summary` | H3 |
| `lottery_nr_combination_matrix` | H4 |
| `lottery_nr_pattern_detail` | H6 |

Regla: la IA **solo** narra resultados de tools. Prohibido inventar scores, ciclos, draw_ids, códigos, tasas.

---

## 8. Consultas SQL / servicios de dominio propuestos

### 8.1 Servicios (Python, dominio)

```text
numeric_relations/
  analysis.py              # (existente) analyze actual
  posterior.py             # NUEVO: secuencia de draws posteriores + hit C
  conditions.py            # NUEVO: emisión de RelationalConditionEvent
  aggregates.py            # NUEVO: tasas, ciclos, matrices
  combination_stats.py     # NUEVO: top pairs/sets
  db_history.py            # (existente) ocurrencias de N
  db_draw_sequence.py      # NUEVO: draws ordenados por lottery_id después de draw_id
```

### 8.2 SQL conceptual (no fusionar por fecha)

**Ocurrencias ancla de N:**

```sql
SELECT d.id AS draw_id, d.lottery_id, d.draw_date, d.draw_time
FROM jaios.lottery_draws d
JOIN jaios.lottery_draw_numbers n ON n.draw_id = d.id
WHERE n.drawn_number = :observed
  AND d.lottery_id = ANY(:primary_lottery_ids)
  AND d.draw_date BETWEEN :from AND :to
ORDER BY d.draw_date, d.draw_time, d.id;
```

**Números del mismo draw (confirmadores same-draw):**

```sql
SELECT drawn_number, position
FROM jaios.lottery_draw_numbers
WHERE draw_id = :anchor_draw_id
  AND drawn_number BETWEEN 1 AND 100
  AND drawn_number <> :observed;
```

**Próximos K sorteos de la lotería de seguimiento (por draw_id / datetime, no por fecha sola):**

```sql
SELECT d.id
FROM jaios.lottery_draws d
WHERE d.lottery_id = :follow_lottery_id
  AND (d.draw_date, COALESCE(d.draw_time, TIME '00:00'), d.id)
      > (:anchor_date, COALESCE(:anchor_time, TIME '00:00'), :anchor_draw_id)
ORDER BY d.draw_date, d.draw_time NULLS FIRST, d.id
LIMIT :k;
```

**¿Apareció C en esos draws?**

```sql
SELECT d.id
FROM jaios.lottery_draws d
JOIN jaios.lottery_draw_numbers n ON n.draw_id = d.id
WHERE d.id = ANY(:posterior_draw_ids)
  AND n.drawn_number = :candidate
ORDER BY ...;
```

Confirmadores cross-lottery (Leidsa ancla / Loteka confirmadora): resolver set de draws confirmadores por `relation_mode` (same_date / session / time_window) **sin** colapsar múltiples draws en uno.

---

## 9. Diseño de pantallas

Reutilizar Control Center. **No** crear dashboard ejecutivo genérico.

| Pantalla | Ruta propuesta | Contenido |
|----------|----------------|-----------|
| **A. Tabla 1** | (existe) `.../motor/table1` | número, fórmula, código, compañeros |
| **B. Tabla 2** | (existe) `.../motor/table2` | número, fórmula, código, confirmadores/vecinos |
| **C. Analizador actual** | (existe) `.../motor/relaciones` | Extender inputs: lotería principal, confirmadoras, ventana posterior. Salida: candidatos T1, confirmadores, score, ranking, evidencia draw_id |
| **D. Analizador histórico** | **NUEVA** `.../motor/historico` | Filtros año/N/C/V/loterías/ventana/min_reps → condiciones, tasas, ciclos, ranking, evidencia |
| **E. Matriz combinaciones** | **NUEVA** `.../motor/combinaciones` | filas=C, columnas=V, celdas=count/tasa/ciclo |
| **F. Detalle de patrón** | **NUEVA** `.../motor/patron/[n]/[c]/[v]` | fechas, loterías, draw_ids, posterior, ciclo, tendencia anual |
| Auditoría | (existe) enriquecer copy | Enlazar a H2/H6 |

Predicciones run: sigue siendo **presentación del ranking histórico**; no nuevo motor. Puede mostrar panel “respuesta histórica” cuando H3 esté disponible.

---

## 10. Casos de prueba (ejemplos reales / anclados al motor)

Usar catálogo y histórico reales; no inventar códigos.

| ID | Caso | Esperado |
|----|------|----------|
| T1 | Observado 34 → mother_code 34 → candidatos = group_T1(34) | Lista = catálogo oficial (p. ej. incluye 1,17,33,49,76) |
| T2 | Candidato C; vecinos T2; hits {V1,V2,V3} | score(C)=3; tres matches; **no** score(V) salvo V∈candidatos |
| T3 | N=26, Quiniela Leidsa, K=10 | compañeros directos 27,38 (regresión motor actual) |
| T4 | N=45, Leidsa+Loteka, K=10 | 2 lottery_ids; ranking con scores |
| T5 | Posterior: tras ancla draw_id D, candidato C | windows 1/2/3/5/10 correctas vs secuencia real |
| T6 | Patrón (N=35,C=4,V=7) si existe en datos | counts, tasas, ciclos; si n&lt;10 → warning |
| T7 | Cross-lottery: N en Leidsa, V en Loteka same_date | confirmer_draw_id ≠ observed_draw_id; follow en Leidsa |
| T8 | No fusionar por fecha | dos draws misma fecha → dos identidades |
| T9 | IA tool: pregunta de ciclo | respuesta solo con payload tool; sin números inventados |
| T10 | Fórmulas intactas | Table1 N=1 → `1 ÷ 1220` code 34; Table2 N=1 → `1220 ÷ 1` code 5 |

---

## 11. Qué parte ya existe

1. Catálogo T1/T2 + grupos (`table1.py`, `table2.py`, `catalog.py`).
2. Motor de análisis actual: ancla → compañeros → vecinos → matches → ranking (`analysis.py`, `scoring.py`).
3. Regla R7: fortalece candidato, no confirmador.
4. Múltiples confirmadores (+1 cada uno).
5. Trazas con `draw_id`, lotería, posición, neighbor, companion.
6. API `/analyze` + UI Relaciones + Predicción run.
7. Tool chat `lottery_analyze_numeric_relations`.
8. Control Center pantallas A/B/C (parcial) + auditoría guía.
9. Histórico tipado `lottery_draws` / `lottery_draw_numbers`.
10. ADR metodológico (`ADR_LOTTERY_NUMERIC_RELATIONS_MOTOR.md`).

---

## 12. Qué parte falta

1. **Análisis posterior** (próx. 1/2/3/5/10 sorteos del candidato).
2. **Ciclos** (min/max/promedio/mediana/distribución/racha).
3. **Tasas / frecuencia / soporte** con terminología correcta y warning de muestra.
4. **Modelo de evento** persistido o materializado + detalle de patrón.
5. **Matriz y top combinaciones** (pares y sets de confirmadores).
6. **Separación lotería principal vs confirmadoras** + modos de relación temporal.
7. **UI D/E/F** (histórico, matriz, detalle patrón).
8. **Tools IA** para H1/H3/H4/H6.
9. **Tendencias** por año y por lotería.
10. Extensión de `/analyze` opcional (v2) sin romper v1.

---

## 13. Plan de implementación (solo tras aprobación)

### Principios

- No tocar Producción hasta GO por fase.
- No nuevas fórmulas / no nuevo motor predictivo.
- No mutar histórico.
- LLM no calcula.
- Cambios mínimos y testeados en DEV primero.

### Fases propuestas

| Fase | Nombre | Entregables | Criterio GO |
|------|--------|-------------|-------------|
| **J-0** | Aprobación diseño | Este documento firmado | Stakeholders OK |
| **J-1** | Posterior + eventos | `posterior.py`, `conditions.py`, tests T5/T8; API H1/H2/H3 (read-only compute) | Tests verdes; draws intactos |
| **J-2** | Combinaciones | H4/H5/H6 + agregados; warning muestra | Casos T6 |
| **J-3** | UI D/E/F | Pantallas histórico / matriz / patrón | UAT visual |
| **J-4** | Tools IA | 3–4 tools + prompts *solo bloques de interpretación* (sin cambiar matemáticas) | Preguntas §9 responden vía tools |
| **J-5** | Analyze v2 opcional | primary/confirming + posterior_windows en Relaciones | Compatibilidad v1 |
| **J-6** | DEV E2E → Prod | Smoke + evidencia; despliegue controlado | GO producción |

### Estimación relativa (orden)

J-1 (núcleo) → J-2 → J-3 → J-4 → J-5 → J-6.

### No hacer

- Winning Engine / dashboard ejecutivo / motores de consenso.
- Motor “cycles” genérico del registry como producto aparte.
- Estadísticas de frecuencia bruta de números sin paso T1→T2.
- Cualquier cambio a sync o fórmulas.

---

## Decisión solicitada

Aprobar o corregir:

1. mother_code = N (como ADR actual).  
2. Default `event_per_confirmer` para estadísticas de patrón.  
3. Ciclo medido en **sorteos** de la lotería de seguimiento.  
4. Plan J-1…J-6 y APIs H1–H7.  
5. Umbral de muestra insuficiente (propuesta: 10).

**Producción no se modifica hasta GO de J-0.**
