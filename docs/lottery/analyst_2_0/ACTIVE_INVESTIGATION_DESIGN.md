# ACTIVE_INVESTIGATION_DESIGN

## Modelo

`ActiveInvestigationSession` (Pydantic), persistido en `conversation_v4.active_investigation`:

- `investigation_id`, `conversation_id`, `topic`
- `subjects`, `relation`, `event_type`, `metric`
- `lotteries`, `positions`, `date_anchor`, `time_window`, `limit`
- `results`, `evidence`, `last_event`, `tools_used`, `summary`
- `last_user_question`, `last_answer`, `last_intent`, `follow_up_kind`
- `created_at`, `updated_at`, `expires_at`, `status`

## TTL

- **600 segundos (10 minutos)** desde la última interacción válida.
- Cada turno activo llama `touch()` y renueva `expires_at`.
- Si expiró al cargar el turno: se limpia la investigación y el sticky `same_day` (no reutilizar en silencio).
- Tema nuevo explícito / cambio de sujeto único → nueva investigación.

## Ciclo de vida

1. `SessionExpirationManager.apply_on_turn_start`
2. `HermesDecisionEngine.decide`
3. `InvestigationStateManager.begin_or_continue`
4. Si `reuse_evidence` → `NaturalResponseGenerator` sin tools
5. Si no → Research/Tools
6. `update_after_research` escribe evidence + last_event + sticky pair
7. `ConversationTraceLogger` registra decisión segura (sin chain-of-thought)

## Evidencia reutilizable

Para atributos `lotteries` / `positions` / `date` / `explain` / `count`, si `last_event` ya tiene apariciones, **no** se reabre una consulta de un solo número.
