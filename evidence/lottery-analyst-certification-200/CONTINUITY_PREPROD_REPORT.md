# Continuidad referencial + claridad de posiciones (preprod)

**Veredicto:** LISTO PARA BETA  
**Imagen runtime:** `jaios-app-backend:lottery-ia-ux-v2.4.5.5-cont` (`sha256:156e3cf7a802…`)  
**Cert200:** `cert200-20260728T174031Z-d0cb56bb` — 200 PASS / 0 FAIL (banco/semilla/evaluador sin cambios; SHA `6d056978…`)  
**Manual30:** 30 PASS / 0 FAIL  

## Causas raíz

### Caso 1 — sujeto compuesto 35+14 colapsado
1. `IntentResolver` heredaba `numbers=['35','14']` correctamente.
2. `build_same_day_follow_up_params` no trataba follow-ups demostrativos de listado (`esas veces`, `cuáles fueron`, etc.).
3. El branch `last_n` de `QuestionClassifier` forzaba `numbers[:1]` → apariciones individuales del 35.

### Caso 2 — «todas las posiciones» como posición de fila
1. `canonicalize_position_scope` / `position_label_es` no parseaban ordinales `1ro/1ra/2da/3ra`.
2. Filas con posición desconocida se etiquetaban con el alcance del filtro («todas las posiciones»).

### Extra (LONG_30.T09 / M10) — refinamiento de filtro perdía el límite
1. Tras un `last_n`, `lottery_chat_service` sobrescribía `last_intent` con `understanding.intent` (p. ej. `compare_lotteries`).
2. `ConversationBrain.apply_resolution` borraba `last_analysis` (limit/items) en refinamientos solo-filtro porque `inherit_active_number` default era `False` y `understand()` reinyectaba el sujeto activo.

## Archivos modificados
- `backend/app/lottery/ai/same_day_coincidence.py`
- `backend/app/lottery/ai/turn_policy.py`
- `backend/app/lottery/ai/analyst/question_classifier.py`
- `backend/app/lottery/ai/analyst/dynamic_planner.py`
- `backend/app/lottery/ai/analyst/tool_orchestrator.py`
- `backend/app/lottery/ai/analyst/conversation_brain.py`
- `backend/app/lottery/ai/analyst/intent_resolver.py`
- `backend/app/services/lottery_chat_service.py`
- `backend/app/services/lottery_tools.py`
- `backend/tests/test_analyst_compound_event_continuity.py` (nuevo)
- `backend/tests/test_analyst_cert200_root_causes.py`
- `backend/tests/test_analyst_v243_context_last_n.py`
- `evidence/lottery-analyst-certification-200/scripts/run_manual30_continuity.py`

## Antes / después

| Caso | Antes | Después |
|------|-------|---------|
| «¿Cuáles fueron esas últimas 3 veces?» tras 35+14 | Últimas 3 del **35** | 3 **coincidencias** 35+14 con fecha/lotería/posiciones |
| Fila de resultado | `2026-07-21 — Real — todas las posiciones` | `… — 1ra posición` / `35 en 1ra y 14 en 3ra` |
| «Ahora en todas las posiciones» tras últimas 3 | Colapsaba a 1 aparición + ruido | Rehace **últimas 3** en alcance all-positions |

## Criterios de cierre
- Casos nuevos / suite rápida: PASS (33 unitarios en contenedor)
- Cert200: **200 PASS / 0 FAIL**
- Manual30: **30 PASS / 0 FAIL**
- Sin «todas las posiciones» como sustituto de posición real en filas
- Sin colapso de sujeto compuesto en follow-ups demostrativos
