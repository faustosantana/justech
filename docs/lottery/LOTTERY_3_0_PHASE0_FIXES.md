# Lottery 3.0 — Phase 0 Fixes

**Branch:** `feature/lottery-3.0`  
**Date:** 2026-07-23

## Corrections delivered

| Issue | Fix |
|-------|-----|
| Resultados Hoy = 0 | `dashboard_v2` / `v3` use `America/Santo_Domingo` local date via `settings.lottery_sync_timezone` |
| Última actualización vacía | Derived from `MAX(draw.updated_at/created_at)`, last sync run `completed_at`, and metadata |
| Quiniela Real 2099 | Alembic `058` recomputes all lottery metadata from `lottery_draws`; API `POST /lottery/admin/metadata/recompute` |
| Latest results polluted by 2099 | Latest cards use live `MAX(draw_date)` per lottery, not metadata alone |
| Inventario / horarios | Stage B trio seeded with `draw_times=20:55`, window intervals; `GET /lottery/sync/windows` |

## Controls unchanged

- Auto-write only Leidsa / Loteka / Lotería Nacional
- Real sync/auto-write remain **false**
- Nacional Día not modified

## Related

- `LOTTERY_3_0_ARCHITECTURE.md`
- `REAL_METADATA_2099_AUDIT.md` (pre-repair evidence)
