# Fases C+D — Motor de Relaciones Numéricas

Fecha: 2026-07-23  
Rama: `feature/lottery-numeric-relations-motor`  
Rollback vigente: tag `restore/lottery-pre-numeric-relations-motor-20260723` → `5136606`

## Resumen

Se expuso el motor ya validado (Fases A+B) como:

1. **Pantalla de auditoría** `/lottery/admin/numeric-relations`
2. **API admin** `/api/v1/lottery/admin/numeric-relations/*`
3. **Tool pública** `lottery_analyze_numeric_relations`
4. **Integración chat** intent → planner → tool → narrativa

Sin duplicar fórmulas ni scoring. Sync y Producción **no** fueron modificados.

## Archivos creados / modificados

### Creados
- `backend/app/lottery/numeric_relations/db_history.py`
- `backend/app/lottery/numeric_relations/api_schemas.py`
- `backend/app/lottery/numeric_relations/chat_narrative.py`
- `backend/app/api/v1/lottery_numeric_relations.py`
- `frontend/src/app/(platform)/lottery/admin/numeric-relations/page.tsx`
- `backend/tests/test_lottery_numeric_relations_phase_cd.py`
- `docs/lottery/numeric_relations_artifacts/PHASE_CD_DELIVERABLES.md` (este archivo)
- `docs/lottery/numeric_relations_artifacts/PHASE_CD_CONVERSATIONAL_EXAMPLES.md`

### Modificados
- `backend/app/api/v1/router.py`
- `backend/app/services/lottery_ai_contracts.py`
- `backend/app/services/lottery_tools.py`
- `backend/app/services/lottery_intent.py`
- `backend/app/services/lottery_chat_service.py`
- `backend/app/lottery/ai/understanding.py`
- `backend/app/lottery/ai/planner.py`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/modules/registry.ts`
- `frontend/src/app/(platform)/lottery/admin/ai/layout.tsx`
- `frontend/src/app/(platform)/apps/[appId]/[section]/page.tsx`

## Rutas

| Método | Ruta | Uso |
|--------|------|-----|
| GET | `/lottery/admin/numeric-relations/tables` | Tabla 1 + Tabla 2 (separadas) |
| GET | `/lottery/admin/numeric-relations/groups` | Agrupaciones T1 / T2 |
| GET | `/lottery/admin/numeric-relations/comparative` | Vista comparativa (motor) |
| POST | `/lottery/admin/numeric-relations/analyze` | Análisis histórico |
| UI | `/lottery/admin/numeric-relations` | Auditoría visual |

## Tool pública

`lottery_analyze_numeric_relations`

Entrada:
- `observed_number` (1..100)
- `lotteries` / `lottery`
- `occurrence_mode`: `last_k` | `all`
- `occurrence_k` (obligatorio si `last_k`; sin default oculto)

Salida tipada del motor + `matches`, `companions_score_zero`, `metadata`.

## Evidencia de centralización

- API y tool llaman `analyze_from_db` → `analyze_observed_number`
- Chat usa `format_numeric_relations_reply(data)` solo con hechos del motor
- No hay `1220` / `calculate_table1_value` en API ni en narrativa del chat

## Evidencia Huawei no inventa

- Si `occurrences_used=0`: respuesta dice explícitamente que no inventa compañeros/códigos/vecinos/scores
- Síntesis LLM instruida a no completar ranking vacío
- Ejemplo controlado 26→27 score 3 / 38 score 0 se reproduce en tests

## UI / permisos

- Tabs separados: Tabla 1, Tabla 2, Agrupaciones T1, Agrupaciones T2, Análisis
- Límite de ocurrencias visible: 5 / 10 / 20 / todas
- JSON solo tras toggle “auditoría avanzada”
- Gate: `canAccessLotteryAdmin` / permisos `lottery_admin_ai` | `lottery.admin` | `lottery.statistics`

## Pruebas

```text
39 passed — test_lottery_numeric_relations_{phase_cd,analysis,table1,table2,groups,exclusions}
```

## Confirmaciones

| Ítem | Estado |
|------|--------|
| Sync no modificado | Sí |
| Producción no modificada | Sí (solo rama feature) |
| Fórmulas / rango 1–100 intactos | Sí |
| Despliegue prod | **No autorizado** — detenido |

## Rollback

```bash
git checkout restore/lottery-pre-numeric-relations-motor-20260723
# o
git reset --hard 5136606
```

## Siguiente paso (requiere autorización)

Validación integral + despliegue.
