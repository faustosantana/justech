# ARCHITECTURE_DECISION_FLOW.md

**Auditoría:** Orquestación Lottery Analyst (Hermes + Huawei + Motor + Agente)  
**Consulta de referencia:** «¿Cuándo fue la última vez que coincidieron el 78 y el 02?»  
**Fecha:** 2026-07-28  
**Modo:** solo lectura — sin cambios de código ni despliegue

---

## 1. Diagrama exacto del recorrido (sesión fresca)

```
Usuario
  ↓
API send_chat_message
  lottery.py :: send_chat_message
  ↓
LotteryChatService.send_message
  lottery_chat_service.py
  ↓
understand() → resolve_intent()
  understanding.py → lottery_intent.py
  (same_day + want_last_only + numbers 78,02)
  ↓
IntentResolver.resolve + ConversationBrain.apply_resolution
  intent_resolver.py · conversation_brain.py
  ↓
SessionExpirationManager.apply_on_turn_start
  session_expiration.py
  ↓
HermesDecisionEngine.decide          ← Hermes LOCAL (no HTTP Huawei)
  hermes_decision_engine.py
  turn_type=new_investigation
  ↓
InvestigationStateManager.begin_or_continue
  state_manager.py
  ↓
ResearchPlanner.plan → ResearchEngine.build_plan
  → QuestionClassifier.classify → coincidences_only
  → DynamicResearchPlanner.build
  research_planner.py · research_engine.py
  question_classifier.py · dynamic_planner.py
  ↓
ToolOrchestrator.run
  → LotteryToolExecutor.execute(GET_NUMBER_OCCURRENCES)
  → LotteryQueryService.same_day_number_coincidences
  → LotteryRepository.same_day_number_coincidences (SQL)
  tool_orchestrator.py · lottery_tools.py
  lottery_query_service.py · lottery_repository.py
  ↓
format_coincidence_narrative          ← hechos / fechas / total
  same_day_coincidence.py
  ↓
EvidenceAggregator + update_after_research
  evidence_aggregator.py · state_manager.py
  ↓
_synthesize (opcional)                ← Huawei ModelArts / DeepSeek-V3.2
  lottery_chat_service._synthesize → _synthesize_via_hermes
  (reescribe plantilla; no elige tool)
  ↓
format_analyst_response + replace_global_lottery_phrasing
  response_formatter.py · official_lottery_scope.py
  ↓
NaturalResponseGenerator.enhance_factual_template
  natural_response.py
  ↓
Persist conversation_v4 + ActiveInvestigationSession
  ↓
Usuario
```

**Motor matemático (`run_complete_analysis`):** **NO** está en este camino.

---

## 2. Etapas — archivo / clase / función / I-O

| # | Etapa | Archivo | Clase / función | Responsabilidad | Entrada | Salida |
|---|--------|---------|-----------------|-----------------|---------|--------|
| 1 | HTTP | `api/v1/lottery.py` | `send_chat_message` | Entrada REST | `session_id`, `content` | `ChatSendResponse` |
| 2 | Orquestador | `services/lottery_chat_service.py` | `LotteryChatService.send_message` | Coordina el turno completo | texto, sesión | mensaje + context + suggestions |
| 3 | Comprensión | `lottery/ai/understanding.py` | `understand` | Domain gate + resolve_intent | texto, `ConversationState` | `UnderstandingResult` |
| 4 | Intent reglas | `services/lottery_intent.py` | `resolve_intent` | Elige tool/params por regex/NLP | texto, ctx | `ResolvedIntent` (`GET_NUMBER_OCCURRENCES`, `same_day`, `want_last_only`) |
| 5 | Continuidad slots | `analyst/intent_resolver.py` | `IntentResolver.resolve` | Filtros, deícticos, sticky | texto, state | `resolution` dict |
| 6 | Memoria sticky | `analyst/conversation_brain.py` | `ConversationBrain.apply_resolution` | Aplica números/relación al state | understanding + resolution | `ConversationState` |
| 7 | TTL investigación | `active_investigation/session_expiration.py` | `SessionExpirationManager.apply_on_turn_start` | Expira / invalida evidencia fuera de scope | state | state, inv\|None, meta |
| 8 | Decisión de turno | `active_investigation/hermes_decision_engine.py` | `HermesDecisionEngine.decide` | ¿Nueva investigación / follow-up / reuse? | message, state, inv, resolution | `HermesDecision` |
| 9 | Sesión activa | `active_investigation/state_manager.py` | `InvestigationStateManager.begin_or_continue` | Crea/continúa investigation TTL 10 min | state, decision | `ActiveInvestigationSession` |
| 10 | Plan | `analyst/research_planner.py` + `research_engine.py` | `ResearchPlanner.plan` / `ResearchEngine.build_plan` | Arma pasos de tools | state, understanding | `ResearchPlan` |
| 11 | Clasificación research | `analyst/question_classifier.py` | `QuestionClassifier.classify` | kind=`coincidences_only` | texto, state | `ResearchQuestion` |
| 12 | Steps | `analyst/dynamic_planner.py` | `DynamicResearchPlanner.build` | 1 step: occurrences + same_day + OFFICIAL_SCOPE | question, state | `list[PlanStep]` |
| 13 | Ejecución | `analyst/tool_orchestrator.py` | `ToolOrchestrator.run` | Corre tools del plan | plan | resultados + narrative |
| 14 | Tool | `services/lottery_tools.py` | `LotteryToolExecutor.execute` | Branch same_day → query service | params | data, total, summary |
| 15 | Query | `services/lottery_query_service.py` | `same_day_number_coincidences` | Resuelve 7 loterías; agrega por fecha | numbers, lotteries | `{total, items, last…}` |
| 16 | SQL | `services/lottery_repository.py` | `same_day_number_coincidences` | Fechas donde aparecen ambos números | lottery_ids, numbers | rows |
| 17 | Narrative | `lottery/ai/same_day_coincidence.py` | `format_coincidence_narrative` | Texto factual | summary | string |
| 18 | Evidence | `active_investigation/evidence_aggregator.py` | `from_same_day_summary` | Normaliza last_event | summary | evidence dict |
| 19 | Síntesis LLM | `lottery_chat_service.py` | `_synthesize` / `_synthesize_via_hermes` | Reescribe plantilla (opcional) | question, template, facts | texto, provider |
| 20 | Formato final | `analyst/response_formatter.py` | `format_analyst_response` | Estructura respuesta analista | texto + meta | texto final |

---

## 3. Quién decide vs quién transforma vs quién consulta

| Componente | Decide (branch) | Transforma | Consulta datos |
|------------|-----------------|------------|----------------|
| `resolve_intent` / classifier | **Sí** — tool y kind | | |
| `HermesDecisionEngine` | **Sí** — research vs reuse vs meta | | |
| `DynamicResearchPlanner` | Parcial — qué steps | **Sí** — arma params | |
| `LotteryQueryService` / repo | Scope oficial | Agrega | **Sí** — SQL |
| Motor matemático | No en este query | | No llamado |
| Huawei ModelArts | **No** | **Sí** — NL rewrite | No |
| EvidenceAggregator | No | **Sí** | No |
| Conversation Session | Sticky subjects | Persist | Lee state |

---

## 4. Nota de naming (crítica)

| Nombre en código | Qué es realmente |
|------------------|------------------|
| `HermesDecisionEngine` | Orquestador **determinista local** (Python) |
| `_synthesize_via_hermes` / `huawei_modelarts` | Llamada HTTP a **Huawei ModelArts** (DeepSeek-V3.2) |
| Motor / `run_complete_analysis` | Motor numérico T1×T2 — **otro producto** dentro del mismo backend |

---

## 5. Follow-up del mismo diálogo (evidencia prod smoke)

Tras la pregunta 78+02, «¿En cuáles loterías?»:

```
Usuario → send_message → Hermes (attribute_of_last_event, reuse_evidence=true)
  → NaturalResponseGenerator.answer_attribute_from_evidence
  → Usuario
```

**Sin** planner, **sin** SQL nuevo, **sin** Huawei (provider=`evidence_reuse`).  
Fuente: `evidence/.../prod-beta20-20260728/SMOKE_RESULTS.json`.
