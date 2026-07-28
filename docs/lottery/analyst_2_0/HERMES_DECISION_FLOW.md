# HERMES_DECISION_FLOW

## Aclaración de nombres

En este producto coexisten dos “Hermes”:

1. **HermesDecisionEngine (2.0)** — orquestador **determinístico** por turno (Python).  
2. **Hermes ModelArts HTTP** — sintetizador LLM opcional (`_synthesize_via_hermes`), etiquetado `provider_used=huawei_modelarts`.

El Decision Engine **no** sustituye tools ni el motor matemático.

## Decisión por turno (`HermesDecision`)

Campos seguros (trazables):

- `hermes_decision_id`
- `turn_type`: `new_investigation` | `contextual_follow_up` | `attribute_of_last_event` | `filter_refine` | `topic_switch` | `clarify` | `meta` | `reuse_evidence`
- `refers_to`, `requested_attribute`
- `inherited_subjects`, `inherited_metric`, `inherited_relation`
- `requires_research`, `reuse_evidence`, `confidence`, `reason_code`

## Ejemplo

```text
user: ¿En cuáles loterías?
HermesDecision:
  turn_type: attribute_of_last_event
  refers_to: active_investigation.last_event
  requested_attribute: lotteries
  inherited_subjects: [78, 02]
  inherited_metric: same_day
  requires_research: false   # si evidence ya tiene apariciones
  reuse_evidence: true
  confidence: high
```

## Orden en `send_message`

IntentResolver → Brain → **HermesDecisionEngine** → StateManager → (reuse | ResearchPlanner) → Tools → NaturalResponse → Trace.
