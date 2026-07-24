# Lottery IA Control Center — Diseño funcional (Fase I)

**Versión documento:** 1.0-draft  
**Fecha:** 2026-07-24  
**Estado:** PROPUESTA PARA APROBACIÓN — **sin implementación**  
**Alcance:** Diseño de plataforma administrativa (Motor Matemático + Predicciones + Prompt Studio)  
**Fuera de alcance:** código, Producción, sync, metodología matemática, alteración de tablas calculadas o histórico  

**Base actual (AS-IS):** Centro IA en `/lottery/admin/ai/*` + panel NR en `/lottery/admin/numeric-relations`.  
**Objetivo (TO-BE):** Lottery IA como Control Center administrable: conocimiento, reglas, fórmulas (solo lectura/auditoría del motor) y motores visibles, auditables y configurables desde UI.

---

## 0. Principios de diseño

1. **Huawei interpreta; el motor calcula.** Ninguna pantalla del Control Center recalcula Tabla 1/2 ni altera scores.
2. **Tablas 1 y 2 siempre separadas.** Nunca vistas mezcladas.
3. **Identidad de sorteo = `draw_id`.** Auditoría siempre ancla en draw_id.
4. **Motores desactivados no se ejecutan** (chat, consenso, jobs).
5. **Prompts versionados:** draft → gates → publish → rollback; sin cajas vacías sin ayuda.
6. **Sin Producción / sync / metodología en esta fase.** Solo diseño.

---

## 1. Arquitectura del Control Center

```
┌─────────────────────────────────────────────────────────────────┐
│  Lottery IA Control Center (Admin UI)                           │
│  /lottery/admin/control-center  (hub)                           │
├──────────────┬──────────────────┬───────────────────────────────┤
│ Motor        │ Predicciones     │ Prompt Studio 2.0             │
│ Matemático   │ (orquestación)   │ (conocimiento + publicación)  │
└──────┬───────┴────────┬─────────┴─────────────┬─────────────────┘
       │                │                       │
       ▼                ▼                       ▼
┌──────────────┐ ┌──────────────┐ ┌─────────────────────────────┐
│ NR Service   │ │ Motor        │ │ Prompt/Agent/Tool Registry  │
│ (read-only   │ │ Registry +   │ │ Versions · Gates · Diff     │
│  catalog +   │ │ Orchestrator │ │ Benchmark hooks             │
│  analyze)    │ │ (flags)      │ │                             │
└──────┬───────┘ └──────┬───────┘ └──────────────┬──────────────┘
       │                │                        │
       └────────────────┴──────────┬─────────────┘
                                   ▼
                    PostgreSQL (config + audit)
                    Lottery history (read-only)
```

### Capas

| Capa | Responsabilidad |
|------|-----------------|
| **Presentación** | Menús, pantallas, mock flows, ayuda contextual |
| **Aplicación admin** | CRUD de config, toggles de motores/tools, versionado, publish gates |
| **Dominio Lottery IA** | Intent → planner → tools; motor NR inmutable |
| **Datos** | Config versionada + histórico de draws (solo lectura desde UI motor) |

### Separación crítica

| Qué | Editable en UI | Qué implica |
|-----|----------------|-------------|
| Catálogo Tabla 1/2 (valores) | **No** (solo visualización/auditoría) | Generado por motor; no “editar fórmula” |
| Análisis histórico | Parámetros de consulta sí; scores no | Llama al mismo `analyze` |
| Motores de predicción | On/off, peso, prioridad | Orquestación; motores stub pueden existir sin lógica |
| Prompt / tools / agent | Sí, versionado | No cambia matemáticas NR |

---

## 2. Flujo de navegación (IA)

### Menú raíz propuesto

```
Lottery IA
├── Resumen (dashboard unificado)
├── Motor Matemático          ← MÓDULO 1 (nuevo hub)
│   ├── Tabla 1
│   ├── Tabla 2
│   ├── Agrupaciones T1
│   ├── Agrupaciones T2
│   ├── Relaciones (análisis)
│   └── Auditoría de traza
├── Predicciones              ← MÓDULO 2
│   ├── Motores
│   ├── Prioridades / pesos
│   └── Historial de ejecuciones
├── Prompt Studio             ← MÓDULO 3 (rediseño)
│   ├── Identidad
│   ├── Dominio
│   ├── Memoria
│   ├── Aclaraciones
│   ├── Análisis (razonamiento)
│   ├── Herramientas
│   ├── Respuesta (formato)
│   ├── Prompt interno
│   ├── Versiones
│   └── Publicación
├── Operación (existente, reubicado)
│   ├── Playground
│   ├── Benchmarks
│   ├── Memoria / sesiones
│   ├── Modelos
│   ├── Seguridad
│   └── Auditoría admin
└── Enlaces: Sync · Scheduler · Lotterías  (solo lectura / fuera de este diseño)
```

### Navegación clave

1. **Motor Matemático → Tabla 1** → clic fila → **Detalle número** → “Ver grupo” → Agrupaciones T1.  
2. **Relaciones** → Analizar → Ranking → expandir fila → **Auditoría de traza**.  
3. **Predicciones → Motores** → desactivar “Relaciones Numéricas” → chat/consenso no invocan tool NR.  
4. **Prompt Studio → Análisis** → editar pasos → guardar draft → **Publicación** (gates + benchmark) → publicar.  
5. **Versiones** → Comparar A/B → Restaurar / Publicar / Archivar.

---

## 3. Mockups de pantallas

> Convenciones de mockup: `[ ]` control, `(···)` acción, `──` layout. Textos en español.  
> Todos los mockups son **wireframes de aprobación**, no UI final pixel-perfect.

### 3.1 Hub — Lottery IA / Resumen

```
┌─ Lottery IA · Control Center ─────────────────────────────────────┐
│  Salud runtime · Prompt activo · Motores ON · Último benchmark     │
│  [Alertas: 2]  [Gates publicación: OK/BLOQUEADO]                   │
│                                                                    │
│  Accesos rápidos:                                                  │
│  (Motor Matemático) (Predicciones) (Prompt Studio) (Playground)    │
└────────────────────────────────────────────────────────────────────┘
```

### 3.2 Motor Matemático — Tabla 1

```
┌─ Motor Matemático › Tabla 1 ────────────── [Tabla 2] [Grupos] [Analizar] ─┐
│  Universo 1..100 · Fuente: NumericRelationsService (solo lectura)           │
│  Buscar número [____]                                                       │
│                                                                             │
│  # │ Fórmula      │ Decimal        │ Dígitos      │ n │ Código │ Grupo     │
│  1 │ 1 ÷ 1220     │ 0.0008196…     │ 0008196…     │ … │  …     │ [1,…]     │
│  … │ …            │ …              │ …            │ … │  …     │ …         │
│ 34 │ 34 ÷ 1220    │ …              │ …            │ … │  34    │ 1,17,33…  │
│                                                                             │
│  Clic fila → Detalle                                                        │
│  ⚠ Tabla 2 no visible aquí                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Detalle de número (Tabla 1 o 2)

```
┌─ Detalle · Número 34 · Tabla 1 ─────────────────────────────────────────────┐
│  Fórmula: 34 ÷ 1220                                                         │
│  Proceso: división → cadena dígitos → suma hasta código                     │
│  Resultado decimal: …                                                       │
│  Código madre: 34                                                           │
│  Grupo completo: [1, 17, 33, 49, 76]                                        │
│  (Ver agrupación T1)  (Analizar este número)                                │
│  ⚠ Valores calculados por motor; no editables                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Tabla 2

Misma grilla que Tabla 1 con fórmula `1220 ÷ n`, códigos/grupos **independientes**.  
Banner: “Tabla de confirmación — no mezclar con Tabla 1”.

### 3.5 Agrupaciones T1 / T2 (pantallas separadas)

```
┌─ Agrupaciones · Tabla 1 ────────────────────────────────────────────────────┐
│  Buscar código [ 34 ] (Buscar)                                              │
│                                                                             │
│  Código 34                                                                  │
│  Integrantes: 1 · 17 · 33 · 49 · 76                                         │
│  Cada chip → Detalle número                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

Réplica idéntica para **Agrupaciones Tabla 2** (ruta distinta, store distinto).

### 3.6 Relaciones — ejecución manual

```
┌─ Relaciones · Análisis histórico ───────────────────────────────────────────┐
│  Número observado [ 26 ]                                                    │
│  Loterías     [☑ Quiniela Leidsa] [☐ Loteka] [☐ Nacional] … (multi)       │
│  Ocurrencias  (● 5) (○ 10) (○ 20) (○ Todas)   ← sin default oculto si empty │
│  (Analizar)                                                                 │
│                                                                             │
│  Resultado                                                                  │
│  Compañeros T1: 27, 38                                                      │
│  Ranking:                                                                   │
│    27  score 0   [Expandir traza]                                           │
│    38  score 0   [Expandir traza]                                           │
│  Metadata: draw_ids_analyzed · dedupe · llm_calculates=false                │
│  Disclaimer: señal histórica, no garantía                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.7 Auditoría de traza (expandible por punto de ranking)

```
┌─ Traza · compañero 27 · score 0 ────────────────────────────────────────────┐
│  Observado: 26 │ Madre: 26 │ Compañero: 27                                  │
│  Por cada coincidencia / no-match:                                          │
│  · draw_id · fecha · lotería · código T2 · grupo T2 · vecino · puntos       │
│  Score 0 visible con razón (“sin vecinos coincidentes”)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.8 Predicciones — catálogo de motores

```
┌─ Predicciones › Motores ────────────────────────────────────────────────────┐
│  ☑ Relaciones Numéricas   peso 1.0  prio 10  ON   última: 2026-07-24  OK   │
│  ☐ Frecuencias            peso 0.5  prio 20  OFF  —                        │
│  ☐ Ausencias              …                                                 │
│  ☐ Vecinos                …                                                 │
│  ☐ Tendencias / Ciclos / IA Conversacional / Consenso / Benchmark / Simul.  │
│                                                                             │
│  Cada fila → panel: Nombre · Descripción · Estado · Prioridad · Peso ·      │
│  Última ejecución · Resultado · (Editar) (Activar/Desactivar)               │
│  Regla: motores OFF no se invocan desde chat ni jobs                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Nota de diseño:** motores sin implementación real aparecen como **“Planificado / stub”** (OFF por defecto). Solo Relaciones Numéricas arranca ON (vinculado al motor v1.0.0).

### 3.9 Prompt Studio — sección con ayuda (reemplaza cajas vacías)

Plantilla de **toda** sección (Identidad, Dominio, Memoria, Aclaraciones, Análisis, Herramientas, Respuesta):

```
┌─ Prompt Studio › Identidad ─────────────────────────────────────────────────┐
│  Título: Identidad                                                          │
│  ¿Qué es?     Texto fijo de ayuda (no vacío)                                │
│  ¿Para qué?   …                                                             │
│  Impacto:     Cómo cambia el tono/comportamiento del asistente              │
│  Ejemplo:     “Eres Lottery IA de Justech…”                                 │
│  Validaciones: longitud min/max · placeholders prohibidos · …               │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Contenido editable (draft):                                                │
│  [________________________ textarea ________________________]               │
│  (Guardar draft) (Vista previa tono) (Ver en Prompt interno)                │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Identidad / Dominio / Memoria / Aclaraciones

Cada una con bloque de ayuda fijo + editor. Memoria documenta **qué se persiste** (sesión, compared_lotteries, etc.) y **qué no** (no inventar lotería/K).

#### Análisis (razonamiento visual)

```
┌─ Análisis · Pasos de razonamiento ──────────────────────────────────────────┐
│  1 Interpretar intención          [↑][↓] [Editar] [Desactivar]              │
│  2 Detectar lotería(s)            …                                         │
│  3 Detectar número observado      …                                         │
│  4 Detectar cantidad / K          …  (aclarar si falta)                     │
│  5 Ejecutar motor(es) activos     …  (respeta Predicciones)                 │
│  6 Organizar respuesta            …                                         │
│  (Añadir paso) — con validación de orden y dependencias                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Herramientas (dentro de Prompt Studio + enlace a registry)

```
┌─ Herramientas del prompt ───────────────────────────────────────────────────┐
│  ☑ lottery_analyze_numeric_relations   prio · docs · (Desactivar)           │
│  ☑ history / statistics / …                                                 │
│  ☐ frequency (si motor OFF → tool también gated)                            │
│  Documentación inline + link a Predicciones                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Respuesta (formato final)

```
┌─ Formato de respuesta ──────────────────────────────────────────────────────┐
│  ☑ Resumen  ☑ Ranking  ☑ Explicación  ☑ Advertencias  ☑ Traza (colapsable) │
│  Plantilla + preview                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Prompt interno (ya no oculto)

```
┌─ Prompt interno ────────────────────────────────────────────────────────────┐
│  [Buscar en prompt ______]  (Exportar) (Importar) (Diff vs activo)          │
│  Editor monolítico + anclas a secciones                                     │
│  Versiones del prompt: lista humana (no solo UUID)                          │
│  (Comparar) (Restaurar) (Guardar draft)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.10 Versiones (rediseño)

```
┌─ Versiones ─────────────────────────────────────────────────────────────────┐
│  Nombre          │ #  │ Estado    │ Modelo │ Fecha │ Autor │ Motivo │ Bench │
│  NR + multi-lot  │ 12 │ Publicada │ gpt-…  │ …     │ …     │ Fix K  │ PASS  │
│  Draft análisis  │ 13 │ Borrador  │ …      │ …     │ …     │ …      │ —     │
│                                                                             │
│  Selección → Notas · Historial · Resultado benchmark                        │
│  (Comparar) (Duplicar) (Restaurar) (Publicar) (Archivar)                    │
│  UUID solo en “Modo desarrollador” / pie técnico                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.11 Publicación (asistente, no un botón solo)

```
┌─ Publicar versión 13 ───────────────────────────────────────────────────────┐
│  1. Diff de cambios (bloques tocados)                                       │
│  2. Gates: Huawei · tools críticas · benchmark P0/P1 · agent publicado      │
│  3. Benchmark vinculado / último run                                        │
│  4. Impacto: motores/tools afectados · prompts · chat                       │
│  5. Rollback: versión N-1 lista                                             │
│  (Cancelar)  (Publicar — habilitado solo si gates PASS)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Modelo de datos (propuesto)

> Extiende tablas AI admin existentes; **no** escribe en `lottery_draws` / números.

### 4.1 Motor Matemático (solo lectura)

Sin nuevas tablas de fórmulas: se proyecta desde `NumericRelationsService` (catálogo en memoria + analyze).  
Opcional (fase posterior): `lottery_nr_analyze_runs` (auditoría de ejecuciones admin) — **no** en MVP si analyze ya deja audit genérico.

### 4.2 Predicciones — registry

```
lottery_prediction_motors
  id, key, name, description,
  enabled bool, priority int, weight numeric,
  status enum(active|disabled|stub|error),
  implementation_ref nullable,   -- null = stub
  last_run_at, last_run_result jsonb,
  updated_at, updated_by

lottery_prediction_motor_runs
  id, motor_id, started_at, finished_at,
  trigger (chat|admin|job), input jsonb, output jsonb, ok bool
```

### 4.3 Prompt Studio

Reutilizar / extender:

- `lottery_ai_prompt_versions` (+ campos: display_name, change_reason, author_id, benchmark_ref, notes)
- Bloques tipados: `identidad|dominio|memoria|aclaraciones|analisis|herramientas|respuesta|seguridad|tono`
- `lottery_ai_prompt_steps` (pasos de Análisis ordenados)
- `lottery_ai_tool_bindings` (tool ↔ enabled/priority en contexto prompt)
- Version metadata: model_id, published_at, archived_at

### 4.4 Publicación / gates

- Snapshot de gates en `publish_events`
- Link a benchmark run id

---

## 5. APIs necesarias

### 5.1 Motor Matemático (existentes + endurecer contrato UX)

| Método | Path | Uso UI |
|--------|------|--------|
| GET | `/lottery/admin/numeric-relations/tables` | Tabla 1/2 |
| GET | `/lottery/admin/numeric-relations/groups` | Agrupaciones |
| GET | `/lottery/admin/numeric-relations/lotteries` | Multi-select |
| POST | `/lottery/admin/numeric-relations/analyze` | Relaciones |
| GET | `/lottery/admin/numeric-relations/numbers/{n}?table=1\|2` | **Nuevo** detalle |

Respuesta analyze ya trae ranking/trace/metadata — la UI de Auditoría solo presenta.

### 5.2 Predicciones (nuevas)

| Método | Path |
|--------|------|
| GET/PATCH | `/lottery/admin/predictions/motors` |
| GET/PATCH | `/lottery/admin/predictions/motors/{key}` |
| GET | `/lottery/admin/predictions/motors/{key}/runs` |

Orchestrator (chat): filtra tools/motors por `enabled`.

### 5.3 Prompt Studio (extender existentes)

| Área | APIs |
|------|------|
| Bloques con schema de ayuda | `GET /prompts/schema` (catálogo título/ayuda/ejemplos/validaciones) |
| CRUD draft / publish / rollback | existentes + campos display |
| Pasos análisis | `GET/PUT /prompts/{id}/analysis-steps` |
| Prompt interno full text | `GET/PUT /prompts/{id}/compiled` + search query param |
| Diff / compare | `GET /prompts/compare?a=&b=` |
| Import/export | `POST /prompts/export`, `POST /prompts/import` |
| Versiones enriquecidas | `GET /versions` con nombre, autor, motivo, bench |
| Publicación guiada | `GET /publish-preview/{id}` → gates, diff, impacto, rollback target |

---

## 6. Componentes reutilizables

| Componente | Uso |
|------------|-----|
| `AdminPageHeader` | Título + breadcrumbs + acciones |
| `HelpPanel` | Qué es / para qué / impacto / ejemplo |
| `ValidationHints` | Reglas del bloque |
| `DataTable` + row click | Tablas 1/2, versiones, motores |
| `CodeGroupChips` | Integrantes de agrupación |
| `LotteryMultiSelect` | Relaciones + chat defaults |
| `OccurrenceLimitPicker` | 5/10/20/todas sin default oculto |
| `RankingTable` + `TraceDrawer` | Relaciones / auditoría |
| `MotorToggleRow` | Predicciones + tools |
| `StepEditor` | Análisis visual |
| `VersionMetaCard` | Nombre, #, estado, modelo, autor… |
| `DiffViewer` | Prompt / versiones |
| `PublishWizard` | Gates → bench → impacto → confirmar |
| `DisclaimerBanner` | Señal histórica NR |
| `DevOnlyId` | UUID solo en modo desarrollador |

---

## 7. Plan de implementación por fases (post-aprobación)

| Fase | Nombre | Entrega | Dependencias |
|------|--------|---------|--------------|
| **I-0** | Aprobación de este diseño | Sign-off | — |
| **I-1** | Motor Matemático hub | Rutas T1/T2/Grupos/Detalle/Relaciones/Traza sobre APIs NR existentes (+ detalle number) | I-0 |
| **I-2** | Predicciones registry | CRUD motores + gating en planner/tools (NR real; resto stub OFF) | I-0 |
| **I-3** | Prompt Studio help + secciones | Schema de ayuda; sin cajas vacías; Identidad…Respuesta | I-0 |
| **I-4** | Análisis steps + Tools binding | StepEditor + tool priorities | I-3 |
| **I-5** | Prompt interno + versiones UX | Full text, search, diff, meta humana | I-3 |
| **I-6** | Publish wizard | Preview gates/bench/impacto/rollback | I-5 |
| **I-7** | Docs funcionales in-app + manual | Documentación pedida | I-6 |
| **I-8** | UAT admin (no prod hasta GO) | Matriz UAT | I-1…I-7 |

**Producción:** solo tras GO explícito (igual que NR). Esta Fase I diseño **no despliega**.

---

## 8. Riesgos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Confundir UI de fórmulas con edición de metodología | Alta | Solo lectura + copy fijo “calculado por motor” |
| Activar motores stub y romper chat | Alta | Stub OFF; orchestrator ignora disabled; critical tools protected |
| Publish sin gates | Alta | Wizard bloqueante (reusar publish-gates) |
| Scope creep (10 motores + studio completo) | Media | Stubs + fases I-1…I-6 |
| Duplicar panel NR actual vs hub nuevo | Media | Migrar rutas; redirect desde `/numeric-relations` |
| Prompt interno editable rompe seguridad | Media | Validaciones + diff review + rollback |
| Estimación insuficiente en versionado | Media | I-5 acotado a metadatos + compare 2 versiones |

---

## 9. Estimación de desarrollo (tras aprobación)

Estimación en **días-persona** (1 dev full-stack familiarizado con Lottery IA):

| Fase | Estimación | Notas |
|------|------------|-------|
| I-1 Motor Matemático UI | 5–7 d | Reusa APIs; detalle + traza pulida |
| I-2 Predicciones | 4–6 d | Registry + gating |
| I-3 Prompt help sections | 5–7 d | Schema + 7 secciones |
| I-4 Steps + tools | 4–5 d | |
| I-5 Prompt interno / versions UX | 6–8 d | Diff/search/export |
| I-6 Publish wizard | 3–4 d | |
| I-7 Documentación | 2–3 d | |
| I-8 UAT / fixes | 3–5 d | |
| **Total** | **~32–45 d** | ~7–9 semanas calendario 1 dev |

Paralelizable: I-1 ∥ I-2; I-3 antes de I-4/I-5.

---

## 10. Documentación funcional (compromiso I-7)

Manual que explicará **cada pantalla, botón, sección, flujo, versión y motor** del Control Center.  
En esta Fase I (diseño) el índice propuesto es:

1. Introducción y principios  
2. Navegación  
3. Motor Matemático (T1, T2, grupos, relaciones, auditoría)  
4. Predicciones  
5. Prompt Studio (todas las secciones)  
6. Versiones y publicación  
7. Operación (playground, benchmarks)  
8. Permisos  
9. Rollback de config  
10. Glosario (`draw_id`, score 0, gates, stub)

---

## 11. Criterios de aceptación del diseño (para tu aprobación)

- [ ] Menú **Lottery IA → Motor Matemático** con T1/T2/grupos/relaciones/auditoría separados  
- [ ] Predicciones con motors on/off y regla “disabled = no execute”  
- [ ] Prompt Studio sin cajas vacías; cada bloque con ayuda  
- [ ] Prompt interno visible/versionable  
- [ ] Versiones con metadatos humanos + compare/restore/publish/archive  
- [ ] Publicación como wizard (gates, bench, impacto, rollback)  
- [ ] Sin cambio a metodología / sync / prod / histórico en la fase de diseño  

---

## 12. Qué **no** haremos al implementar (recordatorio)

- No modificar fórmulas ni rango 1..100  
- No editar celdas del catálogo como si fueran CMS  
- No modificar sync ni fusionar draws  
- No desplegar a Producción sin GO  
- No calcular en el LLM  

---

**Fin de la propuesta Fase I.**  
Esperando tu revisión y aprobación explícita antes de cualquier implementación de pantallas.
