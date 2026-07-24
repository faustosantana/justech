# ADR: Motor de Relaciones Numéricas para Loterías

- **Estado:** Aprobado para Fase A+B — implementado en rama de trabajo (sin UI/deploy)
- **Fecha:** 2026-07-23
- **Rama de trabajo:** `feature/lottery-numeric-relations-motor`
- **Punto de restauración:** `restore/lottery-pre-numeric-relations-motor-20260723`
- **Fuente de verdad metodológica:** `Prompt_Maestro_Motor_Loterias_Cursor.txt` + aclaraciones funcionales confirmadas (evento = `drawn_number = N`)
- **Alcance explícitamente excluido:** predicciones, probabilidades, metodologías adicionales, ampliación de sync, Etapa C, cambio de Nacional Día, Hermes como orquestador

---

## 1. Contexto

Lottery IA ya dispone de:

- histórico tipado (`lottery_draws` / `lottery_draw_numbers`);
- chat tipado (domain → understand → planner → tools → síntesis);
- Admin Center IA.

**No** existe hoy el cálculo de Tabla 1 / Tabla 2, agrupaciones por código, ni el análisis de fortalecimiento por vecinos anclado a ocurrencias reales de un número observado.

Este ADR define la arquitectura del **Motor de Relaciones Numéricas** como módulo nuevo, separable, verificable con pruebas unitarias antes de cualquier integración conversacional o de predicción (esta última no forma parte del alcance).

---

## 2. Decisión

Implementar un paquete de dominio puro **`lottery.numeric_relations`** con capas estrictamente separadas:

1. Cálculo matemático (Decimal, ROUND_HALF_UP, T1/T2, agrupaciones).
2. Consulta histórica (ocurrencias reales de `N`).
3. Análisis de relaciones (compañeros → vecinos → matches).
4. Puntuación.
5. Trazabilidad.
6. Integración delgada con Lottery IA (API / tool / UI de auditoría), sin que el LLM calcule ni invente códigos.

### 2.1 Reglas invariantes (metodología confirmada)

| # | Regla |
|---|--------|
| R1 | Universo fijo **`{1..100}`**. Sin rangos configurables ni 1–999. |
| R2 | Evento histórico = sorteo donde **`drawn_number = N`** (número observado real). |
| R3 | La aparición de compañeros **no** activa el evento histórico. |
| R4 | Tras anclar historial, el mismo **`N`** se usa como **código madre** en Tabla 1. |
| R5 | Candidatos fortalecibles = **todos** los compañeros de Tabla 1 (`table1_code_to_numbers[N]`). No se analiza un solo compañero: el motor procesa el **conjunto completo**. |
| R6 | En cada sorteo ancla, comparar **resto de números del sorteo** (1..100) vs **vecinos** T2 de cada compañero. |
| R7 | Si aparece un vecino → fortalecer al **compañero**; **nunca** al vecino. |
| R7b | Dentro de **un mismo sorteo**, si coinciden **varios** vecinos del mismo compañero, **todos** se contabilizan (+1 por cada vecino distinto coincidente). No detenerse en la primera coincidencia. |
| R8 | Excluir **`N`** de las coincidencias del mismo sorteo (solo ancla). |
| R9 | `exclude_self=True` en vecinos del compañero. |
| R10 | No mezclar grupos Tabla 1 con Tabla 2. |
| R11 | Sin float en cálculo principal; Decimal + ROUND_HALF_UP. |
| R12 | Sin predicciones / probabilidades / metodologías extra. |
| R13 | `K` (últimas N ocurrencias o “todas”) es parámetro operativo; **default UI pendiente** de mapear interfaz actual (no inventar en ADR de implementación temprana). |
| R14 | **Resultado principal** = ranking **completo** de todos los compañeros ordenados por puntuación descendente (cada uno con vecinos, coincidencias, score y traza). |

---

## 3. Estructura de carpetas

```
backend/app/lottery/numeric_relations/
  __init__.py
  constants.py              # N_MIN=1, N_MAX=100, DIVISOR=1220, digit lengths
  decimal_math.py           # helpers Decimal / ROUND_HALF_UP / digit sum
  table1.py                 # calculate / format / generate / group T1
  table2.py                 # calculate / format / generate / group T2
  catalog.py                # TableCatalog: number↔code maps (in-memory, built once)
  models.py                 # dataclasses / Pydantic domain models (sin ORM)
  history.py                # protocol + adapter: fetch occurrences of N
  analysis.py               # analyze_observed_number → ranking
  scoring.py                # score accumulation + dedupe keys
  trace.py                  # build human/machine traces
  service.py                # fachada de aplicación (orquesta capas 1–5)

backend/app/api/v1/
  lottery_numeric_relations.py   # (Fase C/D) endpoints admin/auditoría — no en Fase A

backend/tests/
  test_lottery_numeric_relations_table1.py
  test_lottery_numeric_relations_table2.py
  test_lottery_numeric_relations_groups.py
  test_lottery_numeric_relations_analysis.py   # con draws sintéticos (Fase B)
  test_lottery_numeric_relations_exclusions.py

docs/lottery/
  ADR_LOTTERY_NUMERIC_RELATIONS_MOTOR.md      # este documento
  LOTTERY_NUMERIC_RELATIONS_AUDIT_UI.md       # (Fase C)
```

Frontend (Fases C+):

```
frontend/src/app/(platform)/lottery/admin/numeric-relations/
  page.tsx                  # auditoría tablas + agrupaciones
  analysis/page.tsx         # (opcional) ranking + traza
```

**No** colocar el cálculo dentro de `lottery_chat_service.py` ni dentro del planner LLM.

---

## 4. Componentes y responsabilidades

| Componente | Responsabilidad | No hace |
|------------|-----------------|---------|
| `decimal_math` | Redondeo, formateo, suma literal de dígitos | SQL, scoring |
| `table1` / `table2` | Fórmulas `n÷1220` y `1220÷n`, longitudes 11/12 | Histórico |
| `catalog` | Construye y cachea mapas 1..100 | I/O |
| `history` | Localiza últimas K (o todas) ocurrencias de `drawn_number=N` en loterías dadas | Matemáticas T1/T2 |
| `analysis` | Compañeros, vecinos, cruce con números del sorteo | Persistencia, LLM |
| `scoring` | +1 por match válido, dedupe | Definir vecinos |
| `trace` | Serializa ruta auditable | Cambiar scores |
| `service` | Caso de uso: `analyze(observed_number, lottery_ids, occurrence_limit)` | Sync, prompts |
| Integración Lottery IA | Tool tipada / API admin / UI auditoría; síntesis solo narra hechos | Recalcular con float/LLM |

---

## 5. Modelos de dominio

Tipos conceptuales (implementación: dataclasses o Pydantic; **sin** tablas nuevas en Fase A).

```text
ObservedNumber          = int  # N ∈ [1,100]

MotherCode              = int  # mismo valor N usado como clave en Tabla 1

TableKind               = "table_1" | "table_2"

FormattedComputation:
  number: int
  table: TableKind
  formula: str
  visible_value: str          # p.ej. "0.0008196721"
  digits_without_point: str   # p.ej. "00008196721"
  digit_count: int            # 11 o 12
  digit_list: list[int]
  code: int                   # suma literal

TableCatalog:
  table1_number_to_code: dict[int, int]
  table1_code_to_numbers: dict[int, list[int]]
  table2_number_to_code: dict[int, int]
  table2_code_to_numbers: dict[int, list[int]]
  table1_rows: list[FormattedComputation]
  table2_rows: list[FormattedComputation]

HistoricalOccurrence:
  lottery_id: UUID
  lottery_name: str
  draw_id: UUID
  draw_date: date
  draw_time: time | None
  observed_number: int        # N ancla (= drawn)
  draw_numbers: list[DrawNumberRef]  # todas las posiciones del sorteo

DrawNumberRef:
  position: int | str
  position_label: str | None
  drawn_number: int           # ya normalizado 1..100 o filtrado fuera

Companion:
  number: int                 # c ∈ compañeros(N)
  table1_code: int            # == N (mother code)
  table2_code: int
  table2_group: list[int]
  neighbors: list[int]        # group \ {c}

Match:
  companion: int
  neighbor: int
  occurrence: HistoricalOccurrence  # ref / id
  lottery_name: str
  draw_date: date
  position: str | int
  dedupe_key: str

StrengthenedCandidate:
  number: int                 # compañero
  table1_code: int
  table2_code: int
  table2_group: list[int]
  neighbors: list[int]
  matched_neighbors: list[int]
  score: int
  matches: list[Match]
  trace: str

AnalysisResult:
  observed_number: int
  mother_code: int            # == observed_number
  primary_table: "table_1"
  lottery_ids: list[UUID]
  occurrence_limit: OccurrenceLimit
  occurrences_used: int
  direct_companions: list[int]
  candidates: list[StrengthenedCandidate]  # ordenados por score desc
```

`OccurrenceLimit`:

```text
OccurrenceLimit =
  | { mode: "last_k", k: int }      # k >= 1
  | { mode: "all" }
```

Default concreto de UI: **diferido** hasta inventario de controles existentes (playground / admin). El motor acepta el parámetro de forma explícita siempre.

---

## 6. Interfaces públicas

### 6.1 Cálculo (Fase A — sin I/O)

```text
calculate_table1_value(n) -> Decimal
calculate_table2_value(n) -> Decimal
format_table1_digits(n) -> FormattedComputation
format_table2_digits(n) -> FormattedComputation
sum_literal_digits(formatted_visible: str) -> int
generate_table1() -> list[FormattedComputation]
generate_table2() -> list[FormattedComputation]
group_table1_by_code() -> dict[int, list[int]]
group_table2_by_code() -> dict[int, list[int]]
build_catalog() -> TableCatalog
get_table1_companions(mother_code: int) -> list[int]
get_table2_code_for_number(number: int) -> int
get_table2_neighbors(number: int, exclude_self: bool = True) -> list[int]
```

### 6.2 Histórico (Fase B)

```text
protocol DrawHistoryPort:
  find_occurrences(
    observed_number: int,
    lottery_ids: list[UUID],
    limit: OccurrenceLimit,
  ) -> list[HistoricalOccurrence]
```

Implementación: adaptador sobre `LotteryRepository` / query service existente (solo lectura).

### 6.3 Análisis (Fase B)

```text
match_neighbors_against_draw_numbers(
  neighbors: list[int],
  draw_numbers: list[int],
  exclude_numbers: set[int],  # siempre incluye N
) -> list[int]

score_candidate(matches: list[Match]) -> int

analyze_observed_number(
  observed_number: int,
  lottery_ids: list[UUID],
  limit: OccurrenceLimit,
  catalog: TableCatalog | None = None,
  history: DrawHistoryPort,
) -> AnalysisResult
```

Nota: el nombre de la fachada usa **`observed_number`**, no “mother_code occurrence by companions”. Internamente `mother_code = observed_number` para Tabla 1.

### 6.4 Integración (Fases C/D — post evidencia matemática)

```text
GET  /lottery/admin/numeric-relations/tables
GET  /lottery/admin/numeric-relations/groups
POST /lottery/admin/numeric-relations/analyze
  body: { observed_number, lottery_ids, occurrence_limit }
```

Tool tipada opcional (misma firma de entrada/salida que el service), invocable desde chat **solo** devolviendo hechos del motor.

---

## 7. Separación de capas

```
┌─────────────────────────────────────────────────────────┐
│ Integración Lottery IA (API / Admin UI / Tool / Chat)   │
│  — no calcula; presenta AnalysisResult / tablas         │
└──────────────────────────▲──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│ service.py — orquestación del caso de uso               │
└──────────────┬─────────────────┬────────────────────────┘
               │                 │
     ┌─────────▼────────┐  ┌─────▼──────────────┐
     │ analysis+scoring │  │ history (port/SQL) │
     │ + trace          │  │ solo drawn=N       │
     └─────────▲────────┘  └────────────────────┘
               │
     ┌─────────▼────────┐
     │ catalog T1 / T2  │  ← decimal_math (sin I/O)
     └──────────────────┘
```

- **Cálculo matemático:** puro, determinista, testeable offline.
- **Consulta histórica:** solo localiza sorteos con `drawn_number = N` en loterías pedidas.
- **Análisis:** compañeros T1 + vecinos T2 + cruce con `D(H)\{N}`.
- **Puntuación:** agrega matches deduplicados.
- **Trazabilidad:** no altera scores.
- **Integración:** permisos admin, sin ampliar sync.

---

## 8. Flujo exacto: `observed_number` → ranking

Entrada: `N`, `lottery_ids[]`, `occurrence_limit`.

1. Validar `N ∈ [1,100]`; validar `lottery_ids` no vacío si el producto lo exige.
2. `catalog = build_catalog()` (1..100).
3. `occurrences = history.find_occurrences(N, lottery_ids, limit)`  
   — cada ítem: sorteo donde **salió realmente N**.
4. `companions = catalog.table1_code_to_numbers.get(N, [])`  
   — si vacío, resultado con candidatos vacíos (código madre sin grupo).
5. Para **cada** compañero `c` en `companions` (conjunto completo; ninguno se omite):
   - `t2 = table2_number_to_code[c]`
   - `group = table2_code_to_numbers[t2]`
   - `neighbors = group \ {c}`
   - `matches = []`
   - Para cada ocurrencia `H`:
     - `peers = { d ∈ D(H) | d ∈ [1,100] } \ {N}`
     - `hit = neighbors ∩ peers`  — **todos** los vecinos coincidentes en ese sorteo
     - Por **cada** `v` en `hit`, crear `Match` si `dedupe_key` nuevo (+1 cada uno)
   - `score =` suma de matches válidos (regla inicial +1 por vecino/aparición válida)
   - Incluir siempre al compañero en la salida aunque `score == 0` (ranking completo)
   - Construir `trace` y `StrengthenedCandidate`
6. Ordenar **todos** los compañeros por `score` desc; desempate: `number` asc.
7. Devolver `AnalysisResult` cuyo producto principal es ese ranking completo.

**Ejemplo definitivo (metodología):**

- Salió realmente el 34 → ocurrencias históricas `drawn_number=34`.
- Código madre 34 → **todos** sus compañeros (p.ej. 1,2,3,4,5); cada uno se analiza.
- Compañero 1 → vecinos T2: 6,7,8,9,10,11,12.
- En un sorteo ancla del 34 también salieron **7, 9 y 12** → **score +3** para el compañero **1** (no +1; no se fortalece 7/9/12).
- Cuantos más vecinos de un compañero aparecen (en ese sorteo y en el resto de ocurrencias K), mayor su fortaleza en el ranking para el próximo sorteo.

---

## 9. Representación de conceptos

| Concepto | Representación |
|----------|----------------|
| Ocurrencia histórica | `HistoricalOccurrence` con `observed_number=N` y lista de números del sorteo |
| Sorteo | `draw_id` + fecha/hora + `lottery_id/name` |
| Compañeros | `direct_companions: list[int]` + por candidato `number` |
| Vecinos | `neighbors: list[int]` por candidato |
| Coincidencias | `matches: list[Match]` |
| Candidato fortalecido | `StrengthenedCandidate` |
| Puntuación | `score: int` — +1 por cada vecino coincidente válido; varios vecinos en el mismo sorteo suman varios puntos |
| Trazabilidad | `trace: str` + `matches[]` estructurados (una entrada por vecino/sorteo/posición deduplicada) |
| Ranking completo | `candidates` incluye **todos** los compañeros del código madre, ordenados por score desc |

Formato de traza canónico:

```text
salió {N}
→ ocurrencia histórica real del {N} ({lottery}, {date})
→ código madre {N}
→ compañero {c}
→ código Tabla 2 {t2}
→ vecinos {[...]}
→ salió el vecino {v} en ese mismo sorteo (posición {p})
→ se fortalece {c} para el próximo sorteo
```

---

## 10. Estrategia de pruebas

### Fase A (obligatoria antes de histórico)

- Ejemplos documentales:
  - T1: `1 → 0.0008196721 → 34`; `5 → 0.0040983607 → 37`
  - T2: `1 → 1220.00000000 → 5`; `5 → 244.000000000 → 10`; `3 → 406.666666667 → 65`
- Para todo `n` en 1..100: `len(digits_t1)==11`, `len(digits_t2)==12`
- Unicidad de cada `n` en cada tabla; código = suma literal de dígitos
- Grupos: pertenencia bidireccional number↔code
- Prohibición: no usar `float` en rutas de cálculo (revisión + tests de tipo Decimal)

### Fase B

- Fixtures: ancla `N=34`; compañero `1` con vecinos `{6..12}`; en un sorteo peers `{7,9,12}` → **score(1)=3**; vecinos no reciben score
- Se emiten candidatos para **todos** los compañeros del grupo (incl. score 0)
- Ranking ordenado por score desc
- `N` presente en el sorteo no genera match por sí mismo
- `exclude_self`: compañero no se confirma solo
- Dedupe: mismo draw/posición/vecino una sola vez (no contar dos veces el mismo 7 en la misma posición)
- Alcance lotería: con una sola `lottery_id` no aparecen draws de otra
- `occurrence_limit`: `last_k` vs `all`

### No pruebas de

- Predicción de acierto futuro
- Probabilidades
- “Mejora” de tablas para forzar ejemplos

---

## 11. Manejo de duplicados

`dedupe_key` sugerido (estable):

```text
{lottery_id}|{draw_id}|{position}|{companion}|{neighbor}
```

- Mismo vecino en **otro** sorteo → cuenta aparte.
- Mismo vecino en **otra** lotería → cuenta aparte.
- Mismo evento exacto reprocesado → no duplica.
- Números fuera de 1..100 en el sorteo → ignorados (no error de metodología).

---

## 12. Reglas de exclusión (checklist de implementación)

| Regla | Implementación |
|-------|----------------|
| Excluir N como confirmación | `peers = D(H) \ {N}` siempre |
| Excluir compañero de sus vecinos | `exclude_self=True` |
| No fortalecer al vecino | solo `candidate.number = companion` recibe score |
| No mezclar T1 y T2 | compañeros solo de `table1_code_to_numbers`; vecinos solo de `table2_*` |
| No evento por compañeros | `history` filtra únicamente `drawn_number = N` |
| No float | Decimal + ROUND_HALF_UP |

---

## 13. Parámetros de entrada

| Parámetro | Tipo | Notas |
|-----------|------|-------|
| `observed_number` | int 1..100 | Ancla histórica **y** código madre T1 |
| `lottery_ids` | list[UUID] | Una o varias; no expandir a “todas” si el usuario no lo pidió |
| `occurrence_limit` | `last_k(k)` \| `all` | Sin default inventado en motor; la UI decidirá valores ofrecidos (5/10/20/all) |

---

## 14. Salida esperada

### API / service

JSON alineado al documento maestro, extendido con ancla histórica:

```json
{
  "observed_number": 34,
  "mother_code": 34,
  "primary_table": "table_1",
  "lottery_ids": ["..."],
  "occurrence_limit": {"mode": "last_k", "k": 10},
  "occurrences_used": 10,
  "direct_companions": [1, 2, 3, 4, 5],
  "candidates": [
    {
      "number": 1,
      "table1_code": 34,
      "table2_code": 5,
      "table2_group": [1, 7, "..."],
      "neighbors": [6, 7, 8, 9, 10, 11, 12],
      "matched_neighbors": [7, 9, 12],
      "score": 3,
      "matches": [
        {
          "neighbor": 7,
          "lottery_name": "Quiniela Leidsa",
          "draw_date": "2026-07-10",
          "position": "Segunda"
        },
        {
          "neighbor": 9,
          "lottery_name": "Quiniela Leidsa",
          "draw_date": "2026-07-10",
          "position": "Tercera"
        },
        {
          "neighbor": 12,
          "lottery_name": "Quiniela Leidsa",
          "draw_date": "2026-07-10",
          "position": "Cuarta"
        }
      ],
      "trace": "salió 34 → ocurrencia histórica real del 34 → código madre 34 → compañero 1 → vecinos coincidentes 7,9,12 en el mismo sorteo → score +3 → se fortalece 1"
    }
  ]
}
```

Los demás compañeros del código madre aparecen también en `candidates` (con su propio score, matches y traza), formando el **ranking completo**.

### Interfaz

- **Resultado principal:** ranking **completo** de todos los compañeros del código madre, ordenados por mayor puntuación (señal de fortalecimiento histórico para el próximo sorteo, **sin** lenguaje de predicción/probabilidad).
- Cada fila: compañero, score, vecinos coincidentes, detalle de matches y traza expandible.
- No presentar “un único compañero fuerte” como única salida del motor.

### Auditoría

Tabla por número:

`Número | Tabla | Fórmula | Resultado visible | Dígitos | Cantidad | Código`

Agrupaciones **separadas** T1 y T2.

Vista de ocurrencias usadas (sorteos donde salió N) para un análisis dado.

---

## 15. Plan por fases (recordatorio; sin ejecutar)

| Fase | Entrega | Gate |
|------|---------|------|
| **A** | Motor matemático + tests documentales + tabla 100 números | Tests verdes; sin histórico |
| **B** | History port + analysis + scoring + trace + tests sintéticos | Ejemplo 34→1 vía vecino 7 |
| **C** | UI auditoría tablas/grupos | Paridad visual con ejemplos del prompt |
| **D** | API/tool integración Lottery IA | Sin predicción; permisos admin |

---

## 16. Consecuencias

**Positivas**

- Metodología auditable y testeable de forma aislada.
- Reutiliza histórico existente sin alterar sync.
- Evita que el LLM invente códigos o fortalezca vecinos.

**Negativas / costos**

- Doble semántica de `N` (balón histórico + código madre) debe documentarse en UI para no confundir al usuario.
- Números de lotería >100 quedan fuera de este motor por diseño.

**Rechazado explícitamente**

- Evento = aparición de cualquier compañero del código.
- Ventanas de fechas libres como ancla primaria.
- Float, predicción, ampliar rango, Stage C, tocar Nacional Día.

---

## 17. Autorización

- Fase A+B: **autorizada e implementada** en `feature/lottery-numeric-relations-motor` (2026-07-23).
- Fase C+ (UI, chat, planner, Huawei, sync, producción, predicción): **no autorizada**.

Artefactos: `docs/lottery/numeric_relations_artifacts/`.
