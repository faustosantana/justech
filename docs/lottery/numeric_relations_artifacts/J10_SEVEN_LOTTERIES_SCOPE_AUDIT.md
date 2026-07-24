# J-10L.0 — Auditoría: universo de loterías (alcance cerrado)

**Worktree:** `/Users/faustosantana/Projects/justech-j10-seven-lotteries`  
**Rama:** `feature/nr-j10-seven-lotteries-strict-scope`  
**Base:** `origin/feature/nr-control-center-final-ux-j10` @ `3ccfff3`  
**Aislamiento:** no tocar J-10S · no remount · no seeds · no migraciones · no Producción

## Decisión de producto

Fuente de verdad operativa:

`eligible_for_active_analysis = lottery.is_featured == true`

Universo esperado (nombres de producto):

1. Lotería Nacional  
2. Quiniela Leidsa  
3. Quiniela Loteka  
4. Gana Más  
5. Quiniela Real  
6. New York 2:30  
7. New York 10:30  

## Discrepancia documentada (sin cambio de datos)

El seed DEV `scripts/j10_seed_featured_dev.py` marca actualmente:

| Seed (is_featured) | En lista de producto J-10L |
|--------------------|----------------------------|
| Quiniela Leidsa | sí |
| Quiniela Loteka | sí |
| Loteria Nacional | sí (sin tilde) |
| Gana Mas | sí (sin tilde) |
| Quiniela Real | sí |
| Loto Leidsa | **no** (producto pide New York 2:30) |
| Loto Real | **no** (producto pide New York 10:30) |

**Acción:** no se alteran registros en esta sesión. El código aplica solo `is_featured`. La alineación de nombres (NY vs Loto) queda para un cambio administrativo deliberado fuera de J-10L / J-10S.

## Matriz de alcance

| área | archivo | comportamiento actual | aplica is_featured | riesgo | cambio requerido | prueba |
|------|---------|----------------------|--------------------|--------|------------------|--------|
| Modelo | `models/lottery.py` | columna `is_featured` | storage | bajo | ninguna | ORM |
| Catálogo público | `lottery_admin_service.list_catalog` | `featured_only` opcional | sí | medio | hub ya lo usa | count=7 |
| NR lotteries | `lottery_numeric_relations.numeric_relations_lotteries` | todas no agregadas | **no** | **alto** | default ACTIVE featured | Anguila ausente |
| Analyze v1 | `numeric_relations_analyze` | cualquier UUID | **no** | alto | filtrar a featured | IDs archivados ignorados |
| History API | `lottery_nr_historical._prepare*` | cualquier UUID | **no** | alto | política central | scope metadata |
| Number explorer | `number_explorer.py` | usa LotteryScope | no (pasivo) | medio | vía API | — |
| Hub CC | `control-center/page.tsx` | catalog featured | sí | bajo | ninguna | 7 tarjetas |
| Historial | `historial-numero/page.tsx` | NR lotteries + boot featured | parcial | **evitar editar** | endpoint default active | filtros=7 |
| Motor forms | `historical-form`, `relations-form` | NR lotteries all | no | alto | consumir active | — |
| Tabla 1/2 UI | `motor-table.tsx` | fórmula/resultado/dígitos | N/A | medio | columnas producto | sin fórmula en grid |
| Admin lotteries | `admin/lotteries/page.tsx` | inventario completo | write | bajo | zona archivo | archived visible solo admin |
| IA defaults | `lottery/ai/ui_catalog.py` | set distinto | no | alto | resolver featured | active_lottery_ids |
| Caché NR | — | no hay Redis NR | n/a | bajo | hash de alcance en metadata | metadata.scope_hash |
| Seed | `j10_seed_featured_dev.py` | 7 Loto* | sí | — | **no ejecutar** | doc only |

## Archivos de alto conflicto con J-10S (evitar)

- `historial-numero/page.tsx`
- `phase_j10_stabilization/**`
- nav móvil / layout CC si J-10S lo toca

Preferir helpers aditivos + default de API.
