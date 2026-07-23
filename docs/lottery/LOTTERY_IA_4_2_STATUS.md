# Lottery IA 4.2 — P0 memory + domain (partial delivery)

## Causa exacta de pérdida de memoria
1. `GET_LAST_OCCURRENCE` no guardaba la fecha encontrada en `summary_for_context` → `date_context` quedaba `None`.
2. El follow-up solo reconocía «siguientes», no «después».
3. No existía resolución de «esas loterías» ni `last_occurrences` por lotería.

## Persistencia
Sigue siendo PostgreSQL JSONB en `lottery_chat_sessions.context.conversation_v4` (por tenant/usuario/session_id). No es solo RAM del worker.

## Schema ampliado
`last_occurrences`, `last_tool_results`, `last_analysis`, `calendar_window`, `analysis_scope`, `analysis_depth`, `primary_lottery`, `last_user_reference`.

## Entregado en este corte
- Reference Resolver
- Fechas derivadas por lotería + `ANALYZE_POST_OCCURRENCE_WINDOW` (executor)
- Domain classifier (out_of_domain / restricted / prediction)
- Prompt v3 en **draft** (activo sigue v2 hasta benchmark)
- JSON crudo oculto en parámetros del chat (lista legible)
- Tests unitarios `test_lottery_ia_4_2_memory.py`

## Pendiente (siguiente bake)
- Preferencias default_analysis_lottery_ids (UI + API)
- Insight Engine tipado completo
- Benchmark 4.2 ≥250 casos + UAT autenticado Conversación A/B
- Activar v3 solo si supera v2
- Modos de profundidad quick/standard/deep en UI
- Streaming de fases del planner

## No tocado
- Sync (Leidsa, Loteka, Nacional)
- Nacional Día
- Etapa C
- Hermes orquestador
