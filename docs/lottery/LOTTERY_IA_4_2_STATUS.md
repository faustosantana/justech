# Lottery IA 4.2 — P0 memory + domain (partial delivery)

## Causa exacta de pérdida de memoria
1. `GET_LAST_OCCURRENCE` no guardaba la fecha encontrada en `summary_for_context` → `date_context` quedaba `None`.
2. El follow-up solo reconocía «siguientes», no «después».
3. No existía resolución de «esas loterías» ni `last_occurrences` por lotería.
4. **Bug adicional (UAT turn 2):** tras ejecutar multi-last-occurrence, un `_execute_plan` duplicado sobrescribía `structured`/`tool_trace` y colapsaba la respuesta a una sola lotería (la memoria sí se guardaba, por eso el turno «7 días después» funcionaba).

## Persistencia
PostgreSQL JSONB en `lottery_chat_sessions.context.conversation_v4` (tenant/usuario/session_id). No es solo RAM del worker.

## Schema ampliado
`last_occurrences`, `last_tool_results`, `last_analysis`, `calendar_window`, `analysis_scope`, `analysis_depth`, `primary_lottery`, `last_user_reference`.

## Entregado en este corte
- Reference Resolver
- Fechas derivadas por lotería + `ANALYZE_POST_OCCURRENCE_WINDOW`
- Domain classifier (out_of_domain / restricted / prediction)
- Prompt v3 en **draft** (activo sigue **v2** hasta benchmark)
- JSON crudo oculto en parámetros del chat
- Fix overwrite multi-last-occurrence
- Follow-up «¿en cuál se repitió?» + «hazlo con N» encadena post-ventana
- Tests `test_lottery_ia_4_2_memory.py`

## UAT autenticado (prod bake ia42)
- Turno «7 días después en esas loterías» → `post_occurrence_window` sin pedir fecha/lotería ✅
- Fuera de dominio / restringido técnico → rechazo ✅
- Turno fill multi-lotería + reaparición: corregidos en hotfix post-UAT (redeploy)

## Pendiente (no declarar 4.2 completo)
- Preferencias `default_analysis_lottery_ids` (UI + API)
- Insight Engine tipado completo + packs
- Benchmark ≥250 + activar v3 solo si supera v2
- Modos quick/standard/deep en UI
- Streaming de fases del planner / cancel / idempotencia

## No tocado
- Sync (Leidsa, Loteka, Nacional)
- Nacional Día
- Etapa C
- Hermes orquestador
