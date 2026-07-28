# HUAWEI_USAGE_AUDIT

## ¿Se llama Huawei?

Sí, **opcionalmente**, en la fase de **síntesis de texto** — no en el planning ni en el motor factual.

### Call path

`LotteryChatService._synthesize`:

1. Si `assistant_synthesis_enabled` es false → `local_template`
2. `LLMRouter.complete` (provider configurado, a menudo `huawei_modelarts`)
3. Si falla → `_synthesize_via_hermes` (HTTP ModelArts con `HERMES_MODEL_API_URL` / `HERMES_MODEL_API_KEY`)
4. Si falla → `local_template` + `fallback_reason`

### Cuándo se descarta la salida LLM

- `ConversationPolicy.should_force_local_template` (meta-continuidad, all-positions/lotteries refine, etc.)
- Texto interno / demasiado corto
- Guardrail A.7: fechas de `last_n` presentes en template y ausentes en LLM

### Trazabilidad 2.0 (`runtime_trace` / `agent_trace`)

- `provider_used`
- `model_used`
- `prompt_version`
- `latency_ms` / `llm_latency_ms`
- `fallback_reason`
- `hermes_decision_id` + `hermes_decision` (resumen seguro)
- `evidence_reused`
- `investigation_id`

### Qué NO hace Huawei aquí

- No decide tools
- No calcula coincidencias
- No altera histórico / Tabla 1-2 / Ranking
- Credenciales: sin cambios (reuso de settings existentes)

### Participación real de Hermes-orquestador

A partir de Analyst 2.0, **antes** de generar respuesta, `HermesDecisionEngine` produce una decisión estructurada. El HTTP Huawei sigue siendo solo polish de lenguaje cuando no hay `force_local_template` ni reuso de evidencia.
