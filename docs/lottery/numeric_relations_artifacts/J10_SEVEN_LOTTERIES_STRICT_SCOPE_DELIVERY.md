# J-10L — Delivery: universo cerrado de siete loterías + limpieza Tabla 1/2

## 1–4. Base

| Campo | Valor |
|-------|--------|
| Rama base | `origin/feature/nr-control-center-final-ux-j10` |
| Commit base | `3ccfff3` |
| Worktree | `/Users/faustosantana/Projects/justech-j10-seven-lotteries` |
| Rama paralela | `feature/nr-j10-seven-lotteries-strict-scope` |

## 5–8. Universo activo vs archivado

**Regla central:** `eligible_for_active_analysis = is_featured == true`  
Implementación: `get_active_analysis_lotteries()` / `resolve_active_scope_ids()`.

### Discrepancia de nombres (sin cambio de datos)

Producto esperado: Nacional, Quiniela Leidsa/Loteka/Real, Gana Más, **New York 2:30**, **New York 10:30**.

Seed DEV histórico: incluye **Loto Leidsa** y **Loto Real** en lugar de NY.

**No se alteró la DB.** El código aplica solo `is_featured`. Alinear nombres requiere acción admin deliberada.

Las loterías no destacadas (Anguila, Haití, Miami, etc.) **no se borran**; quedan en `scope=archived`.

## 9–16. Cobertura

| Área | Estado |
|------|--------|
| Política central | `active_scope_policy.py` + `active_scope.py` |
| NR `/lotteries` | default `scope=active` |
| Analyze + history + next-draws + compare | filtran IDs no featured; metadata `analysis_scope_meta` |
| Filtros FE | API default active (historial y motor heredan) |
| IA | `ai_active_scope.active_lottery_context_for_llm` (aditivo) |
| Caché | `scope_set_hash` en metadata (no hay Redis NR hoy) |
| Tabla 1/2 | columnas técnicas fuera de la grilla; “Ver cálculo técnico” |
| Archivo histórico | `/lottery/admin/lotteries/archivo-historico` |

## 17–23. Pruebas / conflictos

- `backend/tests/test_lottery_nr_j10l_active_scope.py` — **10 passed**
- Fórmulas internas intactas (`build_catalog`)
- **Evitar conflicto J-10S:** no se reescribió `historial-numero/page.tsx`; el alcance llega por API
- Riesgo medio: `lottery_nr_historical.py`, `api.ts`, `motor-table.tsx`, `admin/lotteries/page.tsx`

## 24–26. Confirmaciones

- DEV compartido: **no remontado**, sin seeds, sin migraciones
- Producción: **intacta**
- Sin merge / cherry-pick hacia J-10S

## Tabla de commits

| Commit | SHA | Funcionalidad | Archivos clave | Dependencias | Riesgo |
|--------|-----|---------------|----------------|--------------|--------|
| J-10L.0 | `efafcb8` | Auditoría | SCOPE_AUDIT.md | — | Bajo |
| J-10L.1 | `6e96db2` | Política backend | active_scope*.py | — | Bajo |
| J-10L.2 | `ef40467` | Cálculos/señales | lottery_nr_historical, analyze | L.1 | Medio |
| J-10L.3 | `8b259d3` | UX filtros/API | api.ts, active-lotteries | L.1 | Medio |
| J-10L.4 | `ab22e29` | Tabla 1/2 | motor-table | — | Bajo |
| J-10L.5 | `ae2e1cc` | Archivo admin | archivo-historico | L.3 | Bajo |
| J-10L.6 | `b03c1b3` | IA + tests | ai_active_scope, tests | L.1 | Bajo |
| J-10L.7 | `c62d088` | Delivery | DELIVERY.md | — | Bajo |

## Integración manual post J-10S

```bash
git fetch origin
git cherry-pick <shas J-10L.0..L.7>   # selectivo
# Si lottery_nr_historical.py choca: reaplicar solo _clamp_scope_ids + _prepare*
```
