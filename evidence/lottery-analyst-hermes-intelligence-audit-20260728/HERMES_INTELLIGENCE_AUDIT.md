# HERMES INTELLIGENCE AUDIT — evidencia viva

**Fecha:** 2026-07-28/29  
**Entorno:** Producción Beta 2.1 (`lottery-analyst-2.1.0-beta`)  
**Sesión:** `f478b6ef-c46f-42bc-bc22-2a1dff44f285`  
**Artefactos:** `evidence/lottery-analyst-hermes-intelligence-audit-20260728/`  
**Modo:** solo observación — sin cambios de código

## Aclaración de nombres

| Nombre | Qué es |
|--------|--------|
| **HermesDecisionEngine** | Orquestador local determinista (no LLM) |
| **Huawei / ModelArts** | DeepSeek vía `_synthesize_via_hermes` / Analyst Reasoning Layer |

No existe el label `generic_followup` en el código. El más cercano observado aquí es:

`turn_type = contextual_follow_up` + `reason_code = default_research`

---

## Timeline completo (5 turnos)

### T1 — «¿Cuántas veces coincidieron el 35 y el 14?»

| # | Campo | Evidencia |
|---|--------|-----------|
| 1 | Qué recibió Hermes | Mensaje de usuario. Investigation asset BEFORE = `null` (sesión nueva). |
| 2 | Qué entendió | `turn_type=new_investigation`, `reason_code=explicit_pair_or_topic`, `inherited_subjects=["35","14"]`, `requires_research=true`, `reuse_evidence=false`, `reasoning_mode=interpret_pattern`, confidence=high |
| 3 | Investigation Asset | AFTER id=`0d6043585c704a56`, relation=`same_day`, `results_total=120`, evidence.items len=20 (head truncado), tools=`lottery_get_number_occurrences` |
| 4 | Intent | NLP `compare_numbers` · research `coincidences_only` / mode `deep` |
| 5 | Acción | Research obligatorio; tool SQL same-day; luego Analyst Reasoning |
| 6 | Al planner | plan=`["same_day_coincidence"]`, steps_completed=`same_day_coincidence`, evidence_count=1 |
| 7 | Qué recibió Huawei | AnalystReasoningLayer mode=`interpret_pattern`, prompt=`analyst-reasoning-v1.1`, evidence_hash=`65860e62d7770b25`. **No** recibe el ActiveInvestigationSession completo; solo EvidencePackage (no logueado en API, solo hash). |
| 8 | Qué respondió Huawei | Guard **rechazó** (`count_mismatch:20!=120`); fallback interpretativo local con **120** + misma fecha ≠ misma lotería. Provider final efectivo: fallback tras Huawei. |

---

### T2 — «Muéstrame esos resultados.»

| # | Campo | Evidencia |
|---|--------|-----------|
| 1 | Qué recibió Hermes | Mensaje + asset BEFORE id=`0d6043585c704a56` subjects 35/14 total **120** |
| 2 | Qué entendió | `turn_type=contextual_follow_up`, `reason_code=default_research` (**no** `previous_list`, **no** attribute). Subjects heredados 35/14, relation=`same_day`. `reuse_evidence=false`, `requires_research=true` |
| 3 | Asset | Mismo investigation_id; total sigue 120; `follow_up_kind=contextual_follow_up`; items head sigue siendo sample de 20 |
| 4 | Intent | NLP `compare_lotteries` · research otra vez `coincidences_only` |
| 5 | Acción | **No** reutilizó la tabla del asset. Volvió a investigar same-day (`default_research`). |
| 6 | Al planner | Otra vez solo `same_day_coincidence` — **no** llegó un “list results table” |
| 7 | Huawei | Reasoning otra vez (`interpret_pattern`); hash distinto; **no** recibe asset table completa |
| 8 | Respuesta | Otra vez narrativa del total 120 (fallback por `count_mismatch:20!=120`). **No listó las filas** que el usuario pidió. |

**Por qué `default_research` / no listado:**  
`ContextualFollowUpResolver` no matchea «Muéstrame esos resultados» a `previous_list` (patrones: «anteriores», «esas fechas/veces», «cuáles fueron»…). Sin attribute → cae al default del DecisionEngine (`reason_code=default_research`).

---

### T3 — «Filtra solo Loteka.»

| # | Campo | Evidencia |
|---|--------|-----------|
| 1 | Recibió | Mensaje + asset total 120 |
| 2 | Entendió Hermes | Otra vez `contextual_follow_up` + `default_research`. **`requested_attribute=null`** — **no** `filter_refine` |
| 3 | Asset AFTER | total pasa a **3**; sticky `active_lotteries=["Loteka"]`; items head = 3 filas Loteka |
| 4 | Intent | NLP `clarification_response` · research sigue `coincidences_only` |
| 5 | Acción | Research + SQL con filtro Loteka (efecto lateral del IntentResolver / lotteries), **pero Hermes no etiquetó filter_refine** |
| 6 | Planner | De nuevo solo `same_day_coincidence` (ahora scoped) |
| 7 | Huawei | **NONE** — `reasoning_mode=skip`, `local_template` |
| 8 | Respuesta | Plantilla: «coincidieron … 3 ocasión(es)» + hallazgos; **no** dice “export/filter applied” de forma explícita de producto |

**Por qué no `filter_refine`:**  
`detect_attribute` para lottery exige patrones tipo «(solo) en Loteka / en nacional…». «Filtra solo Loteka.» **no** entra en ese regex → Hermes no ve `filter_lottery`. El filtro sí aparece en sticky/SQL por otra capa.

---

### T4 — «Ordénalos por fecha.»

| # | Campo | Evidencia |
|---|--------|-----------|
| 1 | Recibió | Mensaje + asset total **3** (ya Loteka) |
| 2 | Entendió | `contextual_follow_up` + `default_research`; attr=null (**no** hay sort-by-date en Hermes) |
| 3 | Asset | Sigue total 3, Loteka |
| 4 | Intent | `clarification_response` / `coincidences_only` |
| 5 | Acción | Re-research same-day (no operación “ORDER BY” dedicada) |
| 6 | Planner | `same_day_coincidence` otra vez |
| 7 | Huawei | Reasoning `interpret_pattern`, **guard_passed=true** |
| 8 | Respuesta | Huawei listó las **3** fechas de más reciente a más antigua (2026-03-07, 2020-10-22, 2018-08-21). Útil **por coincidencia** (n=3 en evidence), no porque Hermes haya decidido un intent “sort”. |

---

### T5 — «Exporta a Excel.»

| # | Campo | Evidencia |
|---|--------|-----------|
| 1 | Recibió | Mensaje + asset total 3 Loteka |
| 2 | Entendió | `contextual_follow_up` + `default_research`; sin intent export |
| 3 | Asset | Sin cambio material (total 3) |
| 4 | Intent | `clarification_response` / `coincidences_only` |
| 5 | Acción | Re-ejecuta coincidencia; **no** export |
| 6 | Planner | `same_day_coincidence` |
| 7 | Huawei | **NONE** (`reasoning_mode=skip`) |
| 8 | Respuesta | Misma plantilla factual de 3 coincidencias — **cero Excel / cero archivo** |

---

## Preguntas explícitas del brief

### Si Hermes responde algo tipo follow-up genérico — ¿POR QUÉ?

En este caso concreto no salió `generic_followup` (no existe). Salió:

`contextual_follow_up` + `reason_code=default_research`

**Por qué (código observado):**

1. Hay investigation activa + no hay números nuevos en el mensaje.  
2. `ContextualFollowUpResolver.detect_attribute()` no reconoce el utterance.  
3. No es `short_deictic` fuerte lo bastante para otro branch (o cae igual a research).  
4. Default del DecisionEngine: `requires_research=true`, `reuse_evidence=false`.

### ¿Por qué Huawei nunca recibe el asset table?

Evidencia de esta corrida:

- Huawei **solo** entra por Analyst Reasoning Layer (o skip).  
- El payload es EvidencePackage (`evidence_hash` en traza), **no** `active_investigation` completo.  
- En T3 y T5: `channel=NONE` → Huawei no recibe nada.  
- En T1/T2/T4: recibe package resumido (counts/occurrences ≤20), no “tabla de investigación” ni órdenes export/sort.

**Por qué:** diseño actual — LLM analiza evidencia verificada compacta; no es un agente con el asset como spreadsheet.

---

## ¿Podría GPT responder correctamente con exactamente la información que Hermes le entregó?

### Veredicto: **NO**

Justificación por turno, con la información **efectivamente entregada** al camino LLM (o la ausencia de ella):

| Turno | ¿GPT podría cumplir la intención del usuario? | Por qué |
|-------|-----------------------------------------------|---------|
| T1 contar | **Parcial / Sí descriptivo** | Con EvidencePackage (total 120) un GPT podría explicar el conteo. Aquí Huawei inventó 20 y el Guard lo botó; el usuario igual vio 120 por fallback **no-LLM**. |
| T2 mostrar resultados | **NO** | Hermes no entregó intent “listar filas del asset” ni reuso de tabla; re-entregó el mismo plan de coincidencia. Sin instrucción + filas completas, GPT no puede “mostrar esos resultados” como listado. |
| T3 filtrar Loteka | **NO vía Hermes→Huawei** | Huawei no fue llamado. El filtro ocurrió en SQL/sticky, no como decisión semántica clara hacia el LLM. |
| T4 ordenar | **NO como capacidad general** | No hubo intent sort. GPT en T4 ordenó 3 fechas porque el package ya traía esas 3 filas; no porque Hermes le pidiera “ordenar”. Con 120 filas truncadas a 20, no podría ordenar el universo real. |
| T5 export Excel | **NO** | Cero herramienta/export en lo entregado; Huawei ni siquiera fue invocado. Ningún GPT puede inventar un `.xlsx` real solo con el template factual. |

**Conclusión de inteligencia conversacional:**  
Hermes **conserva sujetos (35/14) y relation same_day**, y el SQL puede estrechar a Loteka, pero **no demuestra comprensión de los actos de habla** “muéstrame / filtra / ordena / exporta” como operaciones distintas sobre el Investigation Asset. Los follow-ups T2–T5 colapsan a `default_research` + `coincidences_only`.

---

## Evidencia cruda

- `evidence/lottery-analyst-hermes-intelligence-audit-20260728/raw_timeline.json`
- `evidence/lottery-analyst-hermes-intelligence-audit-20260728/compact_timeline.json`
