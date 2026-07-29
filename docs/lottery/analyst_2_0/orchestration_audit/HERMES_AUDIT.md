# HERMES_AUDIT.md

**Componente:** `HermesDecisionEngine`  
**Archivo:** `backend/app/lottery/ai/active_investigation/hermes_decision_engine.py`  
**No confundir con:** Huawei ModelArts (`_synthesize_via_hermes`)

---

## 1. Qué es Hermes aquí

Orquestador **determinista** del turno conversacional (Analyst 2.0).  
No llama a ModelArts. No calcula coincidencias. No escribe la respuesta final salvo vía decisión de *reutilizar evidencia*.

Docstring del módulo (líneas 1–4): deja explícito que es decisión local estructurada, no el LLM de Huawei.

---

## 2. Responsabilidades reales

| Pregunta | Respuesta con evidencia |
|----------|-------------------------|
| ¿Planifica tools? | **No directamente.** Marca `requires_research` / `reuse_evidence`; el plan lo arma `ResearchPlanner` / `DynamicResearchPlanner`. |
| ¿Solo enruta? | **Sí, enrutado de turno:** `new_investigation` \| `contextual_follow_up` \| `attribute_of_last_event` \| `filter_refine` \| `meta`. |
| ¿Construye contexto? | **Sí, parcial:** hereda `subjects`, `relation`, `requested_attribute`, `refers_to`. |
| ¿Decide herramientas? | **Indirecto:** al forzar research vs reuse. La tool concreta la elige classifier/planner/intent. |

---

## 3. Decisiones que toma (`decide`)

Orden de evaluación (código):

1. `nueva conversación` → `new_investigation` / `explicit_reset`
2. Meta/corrección → `meta` / sin research
3. Pareja explícita en el mensaje (≥2 números) → `new_investigation` / `explicit_pair_or_topic`
4. `ContextualFollowUpResolver` → attribute / filter; puede setear `reuse_evidence`
5. `follow_up_kind` sticky same_day → attribute + posible reuse
6. Follow-up corto deíctico → `contextual_follow_up` + research
7. Default → research

### Evidencia de runtime

Único `hermes_decision` completo persistido en evidencia de producción beta:

| Campo | Valor (smoke T2) |
|-------|------------------|
| `turn_type` | `attribute_of_last_event` |
| `requested_attribute` | `lotteries` |
| `inherited_subjects` | `["78","02"]` |
| `reuse_evidence` | `true` |
| `reason_code` | `attr:lotteries:reuse` |
| `requires_research` | `false` |

Fuente: `evidence/lottery-analyst-certification-200/prod-beta20-20260728/SMOKE_RESULTS.json`.

Agent50 (50 casos offline) ejercita HermesDecision + classifier **sin** Huawei; resultado 50/0 — valida el orquestador local, no ModelArts.

---

## 4. Qué deja de funcionar si Hermes OFF (simulación)

Ver también ablation en `INTELLIGENCE_REPORT.md`.

- Se pierde el short-circuit de **evidence reuse** (`send_message` ~436–493).
- Follow-ups de atributo («¿en cuáles loterías?») dependen otra vez de IntentResolver + sticky state solo — más frágil (bugs pre-2.0: «No pude completar…»).
- TTL/investigation structured still exists vía SessionExpirationManager, pero **sin** `HermesDecision` el binding de `inherited_relation` / `requested_attribute` se debilita.

---

## 5. Valor real

| Criterio | Evidencia |
|----------|-----------|
| Aporta valor | **Sí** — estabiliza continuidad 2.0 (Agent50, Manual30, smoke reuse). |
| Es “inteligencia LLM” | **No** — reglas + estado. |
| Es cuello de botella | No; latencia despreciable vs Huawei (~10–15 s). |
| Riesgo de naming | Alto: equipo puede creer que “Hermes” = Huawei. |

---

## 6. Veredicto Hermes

**Hermes (DecisionEngine) aporta orquestación determinista de turno y reuso de evidencia.**  
No es el cerebro generativo. Sin él, el producto vuelve al modo pre-2.0 más propenso a romper follow-ups; el SQL y el intent seguirían respondiendo preguntas nuevas.
