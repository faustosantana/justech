# Production Deployment Report — Lottery Official Bake

**Date (UTC):** 2026-07-22  
**Environment:** https://jaios.justech.do  
**Operator evidence dir:** `/var/jaios/lottery-bake/20260722/`

## Pre-deploy

- API health OK before bake
- PostgreSQL backup: `/var/jaios/backups/pre_lottery_official_bake_20260722_220216.dump` (~36MB)
- Rollback tags registered (see IMAGE_TAGGING_POLICY.md)
- Lottery flags confirmed disabled for scheduler/sync write

## Deploy steps

1. Sync validated wiring from running container → host bake context
2. Tag rollback images
3. `pg_dump` backup
4. `docker build` backend bake → `lottery-official-20260722` + `latest`
5. `docker compose build frontend` → tag `lottery-official-20260722`
6. `docker compose up -d --force-recreate --no-deps backend frontend`

## Post-recreate results

| Check | Result |
|-------|--------|
| API health | 200 |
| Lottery baked in image layers | Yes (`docker history` shows COPY lottery layers) |
| Hot-patch dependency | Eliminated (recreate from image) |
| Alembic current | `056_lottery_scheduler_operations` |
| Draws / lotteries / numbers | 91931 / 50 / 388788 |
| Flags module/sched/sync/write/auto | true / false / false / false / false |
| Quiniela Real 2022-03-15 | 01, 19, 07 |

## Compose

Unchanged service definitions; images resolved via `jaios-app-backend:latest` and `jaios-app-frontend:latest`.
