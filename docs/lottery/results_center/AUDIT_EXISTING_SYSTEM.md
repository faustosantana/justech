# Auditoría — sistema de resultados existente

## Base de datos
- PostgreSQL schema `jaios`
- Tablas oficiales: `lottery_lotteries`, `lottery_draws`, `lottery_draw_numbers`
- Sync ledger: `lottery_sync_runs`, `lottery_scheduler_state`

## Posiciones
- `lottery_draw_numbers.position`: 1=primera, 2=segunda, 3=tercera

## FEATURED_SEVEN
- `lottery_lotteries.is_featured = true` (7 loterías producto)

## Actualización diaria (reutilizada)
- Adapter: `ElBoletoApiAdapter` (`lottery_sync_service.py`)
- Writer: `LotterySyncWriter` → tablas oficiales
- Scheduler: `LotterySchedulerService` + APScheduler (`lottery_scheduler.py`)
- Worker opcional: `python -m app.lottery.sync.worker`
- Flags (default OFF): `lottery_sync_enabled`, `lottery_sync_write_enabled`, `lottery_sync_automatic_write_enabled`, `lottery_scheduler_enabled`, `lottery_scheduler_mode`

## APIs ya existentes
- `GET /api/v1/lottery/results/by-date|range|...`
- Admin sync/scheduler

## Motor
- Complete Analysis Engine **no** consulta draws en DB hoy.
- Acceso oficial nuevo: `LotteryResultService` / `analysis_engine.results_access`.

## Conclusión
No se crea segundo scraper ni segunda base. Solo falta facade + UI Resultados + visibilidad.
