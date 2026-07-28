# ARCHITECTURE_AUDIT — Lottery Analyst 2.0

**Base:** `65da5c7` / `lottery-analyst-continuity-beta-2026.1.1`  
**Alcance:** capa conversacional únicamente (sin Motor Matemático / Prompt Maestro / Huawei credentials / cert200 bank).

## Flujo actual (antes de 2.0)

```
send_message
  → understand()
  → IntentResolver.resolve()
  → ConversationBrain.apply_resolution()
  → ResearchPlanner / QuestionClassifier / DynamicResearchPlanner
  → ToolOrchestrator → LotteryToolExecutor
  → format_* templates
  → _synthesize() [LLMRouter → Hermes ModelArts HTTP]  # solo reescritura
  → persist conversation_v4
```

**Hallazgo clave:** Hermes/Huawei **no orquestaban**. Solo sintetizaban texto sobre un template factual ya construido. La orquestación era 100% determinística en Python.

## Por qué fallaba «¿En cuáles loterías?»

Tras «última coincidencia 78 y 02»:

1. El par podía quedar en `active_pair` / `active_relation=same_day`.
2. El follow-up «¿En cuáles loterías?» resolvía `follow_up_kind=lotteries`.
3. `build_same_day_follow_up_params` **no** reconocía esa frase → `None`.
4. `QuestionClassifier` caía en `filtered_follow_up` (un solo número) o plan vacío.
5. `ToolOrchestrator` respondía: *«No pude completar la consulta en este momento.»*

Causa raíz: no existía una **Active Investigation Session** que tratara el follow-up como atributo del **evento** de coincidencia.

## Persistencia previa

- `ConversationState` en `session.context["conversation_v4"]`
- Sin TTL de investigación (solo config admin 72h no aplicada al chat)
- `remember_occurrence()` podía colapsar el par a un solo número

## Inserción 2.0 (implementada)

| Componente | Módulo |
|------------|--------|
| ActiveInvestigationSession | `ai/active_investigation/session.py` |
| SessionExpirationManager (10 min) | `session_expiration.py` |
| HermesDecisionEngine | `hermes_decision_engine.py` |
| ContextualFollowUpResolver | `contextual_follow_up.py` |
| EvidenceAggregator | `evidence_aggregator.py` |
| NaturalResponseGenerator | `natural_response.py` |
| InvestigationStateManager | `state_manager.py` |
| ConversationTraceLogger | `trace_logger.py` |

Hook principal: `LotteryChatService.send_message` (tras Brain, antes de ResearchPlanner; reuso de evidencia; persistencia post-tools).

## No tocado

Motor Matemático, Prompt Maestro, Tabla 1/2, Ranking, histórico, credenciales Huawei, banco/semilla/evaluador cert200.
