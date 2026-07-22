# Lottery — Official Integration into JAIOS

## Canonical repository

- **Repo:** `jaios-platform` (local path `/Users/faustosantana/Projects/jaios-platform`)
- **Branch:** `feature/lottery-official-module`
- **Production host app dir:** `/opt/jaios-app` (rsync/deploy layout, no git on VPS)

## Commits

| Role | SHA |
|------|-----|
| Consolidation commit (lottery code landed) | `1321dfe` |
| Config completion for official bake | `3a0779a` |

## What was integrated

- Backend models (`app/models/lottery.py`)
- Alembic `051`–`056` (+ stub `050_process_requirements`)
- API `app/api/v1/lottery.py` + router include
- Schemas, services, LLM tools (`lottery_tools.py`)
- `AssistantSource.LOTTERY`
- RBAC lottery permissions + `lottery_client`
- Frontend `/lottery/*`, registry, middleware, `apiClient`
- Exports, shares, favorites, saved queries, admin sync/scheduler UI
- Full lottery settings block (scheduler/sync write defaults **false**)

## Production status

- URL: https://jaios.justech.do
- Module key: `lottery` / label **Resultados de Loterías**
- Data: 50 lotteries, 91,931 draws, 388,788 numbers
- Alembic head: `056_lottery_scheduler_operations`

## Independent repo

`jaios-lottery` is no longer the primary reference for ongoing development.
