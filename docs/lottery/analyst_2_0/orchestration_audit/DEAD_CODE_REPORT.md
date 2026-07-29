# DEAD_CODE_REPORT.md

Clasificación: **Eliminar** | **Simplificar** | **Mantener**  
Criterio: llamadas desde `LotteryChatService.send_message` y suites activas; no se eliminó nada en esta auditoría.

---

## 1. Hallazgos

| Ítem | Evidencia | Clasificación | Notas |
|------|-----------|---------------|-------|
| Dual same_day en `resolve_intent` (early ~377 vs late ~1116) | Segunda rama raramente alcanzada si early return | **Simplificar** | Redundancia defensiva; no muerta del todo |
| `app/lottery/ai/planner.py` `build_plan` | Aún llamado en `send_message:565` pero research plan suele ganar | **Simplificar** | Legacy path; mantener hasta unificar |
| `ResearchPlanner._build_deep_steps` same_day vs `DynamicResearchPlanner.coincidences_only` | Mismo tool outcome; ResearchEngine preferred | **Simplificar** | Duplicación de intención |
| Naming Hermes DecisionEngine vs `_synthesize_via_hermes` | Colisión cognitiva | **Simplificar** (rename docs/code futuro) | No tocar en prod ahora |
| `want_last_only` drop en DynamicResearchPlanner | Intent lo setea; planner no lo propaga | **Simplificar** / bug latente | Comportamiento: narrativa full+last vs last-only |
| J11A stack (`numeric_relations/j11a/*`) | No referenciado desde `lottery_chat_service` | **Mantener** (módulo paralelo) o **Eliminar** si producto abandonó J11A UI | Fuera del Analyst chat path |
| `KnowledgeEngine` / `PROMPT_MAESTRO_VERSION=v5` | Active prompt es v6 vía `get_active_prompt` | **Simplificar** | Constante desalineada |
| Prompts v1–v5 files | `get_active_prompt` apunta v6 | **Mantener** histórico / **Eliminar** si no hay feature-flag | Verificar flags antes de borrar |
| `ContextualFollowUpResolver` | Usado por Hermes en follow-ups | **Mantener** | Vivo |
| Evidence reuse early-return | Vivo en 2.0 | **Mantener** | |
| Complete analysis / Motor path | Vivo para analyze; bloqueado en same_day | **Mantener** | No dead |
| Fallbacks `local_template` | 8/44 v2452 | **Mantener** | Activos y necesarios |
| Fallback clarify_number_slot_locked | 1/44 | **Mantener** | |
| Routers LLMRouter + Hermes HTTP | Ambos en `_synthesize` | **Mantener** con **Simplificar** docs | Orden claro en código |
| LOTTERY_HINTS New York legacy names | Actualizado en hotfix scope | **Mantener** | |
| Pre-scope evidence con Anguila en smoke antiguo | Datos históricos de evidencia | N/A | No código |

---

## 2. Decisiones duplicadas (sobreingeniería leve)

Capas que clasifican “qué quiere el usuario”:

1. `resolve_intent` / NLP stability  
2. `understand` follow-up detectors  
3. `IntentResolver`  
4. `QuestionClassifier`  
5. `HermesDecisionEngine`  
6. `ContextualFollowUpResolver`

**Todas viven.** Solapan en same_day/follow-up.  
Clasificación global: **Simplificar** (consolidar en 2 capas: Understanding + TurnDecision) en una generación futura — **no ahora**.

---

## 3. Planners

| Planner | Estado |
|---------|--------|
| `DynamicResearchPlanner` | **Activo** — path principal research |
| `ResearchPlanner` (+ deep/quick fallback) | **Activo** — envelope |
| `planner.build_plan` (legacy) | **Secundario** — Simplificar |
| J11A `planner_engine` | **Fuera** del Analyst chat |

---

## 4. Fallbacks muertos

Ningún fallback principal está muerto:

- synthesis disabled → local_template  
- meta continuity → force local_template  
- date drift → revert template  
- evidence dirty scope → invalidate session  

---

## 5. Resumen de acción (futuro — no ejecutar aquí)

| Acción | Ítems |
|--------|-------|
| Eliminar (candidato) | Prompts no referenciados tras inventario de flags; J11A si producto cerrado |
| Simplificar | Dual intent same_day; legacy `build_plan`; rename Hermes HTTP; propagar `want_last_only` |
| Mantener | HermesDecision, Evidence, Official Scope, Motor, Prompt v6, Huawei synthesis, SQL path |
