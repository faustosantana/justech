# UAT Report — Lottery Official Bake (2026-07-22)

## Scope

Post `force-recreate` validation on https://jaios.justech.do after baking `jaios-app-backend:lottery-official-20260722` and frontend release tag.

## Results summary

| Area | Result |
|------|--------|
| Login / Dashboard / Prices / DGCP UI | PASS (HTTP 200) |
| Lottery UI routes | PASS |
| API health / dashboard | PASS |
| Counts 50 / 91931 / 388788 | PASS |
| Quiniela Real 2022-03-15 → 01,19,07 | PASS |
| Compare / statistics / chat / favorites / saved | PASS |
| Export CSV / XLSX / PDF | PASS |
| Shares | PASS |
| AssistantSource.LOTTERY | PASS |
| RBAC role_has_permission matrix | PASS |
| lottery_client admin blocked (non-superadmin) | PASS (403) |
| Scheduler / sync write flags | PASS (all false) |
| Alembic `056` | PASS |
| Image bake (no hot-patch) | PASS |

### Note on one automated check

An initial check used a **superadmin** user with JWT role `lottery_client`; superadmin bypass returned 200 on admin sync. Retest with a non-superadmin user + `lottery_client` role returned **403** as required.

## Flags observed

```
LOTTERY_MODULE_ENABLED=true
LOTTERY_SCHEDULER_ENABLED=false
LOTTERY_SYNC_ENABLED=false
LOTTERY_SYNC_WRITE_ENABLED=false
LOTTERY_SYNC_AUTOMATIC_WRITE_ENABLED=false
```

## Evidence files

- `/var/jaios/lottery-bake/20260722/validation/uat_console.txt`
- `/var/jaios/lottery-bake/20260722/validation/uat_report.json`
- `/var/jaios/lottery-bake/20260722/validation/alembic_after.txt`
