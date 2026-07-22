# Lottery 2.0 — Stage B + Closure Report

**Date:** 2026-07-22  
**Branch:** `feature/lottery-2.0`  
**Production:** https://jaios.justech.do

## 1. Delivery report commit

- `31aa9cd` — docs(lottery): add Lottery 2.0 production delivery report

## Follow-up commits (IA + sync allowlist for Stage B)

- `1f5ec96` — fix(lottery): harden IA intent routing and sync write allowlist
- `921ef9a` — fix(lottery): correct draw_count resolver and number-compare windows
- `f5f2818` — fix(lottery): allow observe dry-run on docker postgres allowlist
- `9d12b48` — fix(lottery): allow guarded_write confirmation on configured allowlist DB

## 2–5. Authenticated Lottery IA UAT

Evidence: `/var/jaios/lottery-bake/lottery-2.0-ai-uat-20260722c/`

| # | Question | Tools | Result |
|---|----------|-------|--------|
| 1 | Quiniela Real 15 mar 2022 | `lottery_get_result_by_date` | **PASS** → 01, 19, 07 |
| 2 | cinco sorteos siguientes | `lottery_get_following_draws` | **PASS** (5 fechas) |
| 3 | siete días siguientes | `lottery_get_following_days` | **PASS** (calendar ≠ draws) |
| 4 | cuántas veces el 01 | `lottery_get_number_occurrences` | **PASS** |
| 5 | última vez el 19 | `lottery_get_last_occurrence` | **PASS** |
| 6 | compara 01 Real vs Nacional Noche | `lottery_compare_lotteries` | **PASS** |
| 7 | repeticiones últimos 30 sorteos | `lottery_find_repetitions` | **PASS** |
| 8 | más cobertura histórica | `lottery_get_coverage` | **PASS** |
| 9 | hasta qué fecha actualizada Real | `lottery_get_draw_count` | **PASS** |
| 10 | compara últimos 30 de tres | `lottery_compare_lotteries` | **PASS** |

- P0: 0 · P1: 0 (after intent fixes)
- Synthesis fallback activo (“redacción no disponible”) — datos estructurados reales; no predicción/apuestas/SQL libre
- Defects fixed before Stage B: wrong tools for occurrences/last/compare/freshness; `30` misread as ball number; `require_resolved` → `resolve_or_raise`

## 6–7. Stage B lottery selection

| source_id | Name | Why |
|-----------|------|-----|
| 5 | Quiniela Leidsa | Adapter `elboletoganador.historial.v1`, external_id=5, TZ America/Santo_Domingo, 7 draws/7d, last 2026-07-21, health healthy |
| 6 | Quiniela Loteka | Same source contract, external_id=6, recent daily coverage |
| 4 | Loteria Nacional | Same contract, external_id=4, recent coverage (Noche line; **not** Nacional Día) |

**Excluded:** Quiniela Real (`last_draw_date` metadata 2099 — anomalous), Nacional Día / source 20–21 (ambiguous), other 47 lotteries.

## 8. Observe mode

9/9 runs (3×3), source=api, window last 3 days:

- HTTP 200, `wrote_to_database=false`
- fetched=9 / new=0 / unchanged=9 / conflicts=0 each
- Counts unchanged: 91931 / 388788

## 9. Backup pre-write

- `/var/jaios/backups/pre_lottery_2_0_stageb_write_20260722_225509.dump` (36M)
- Alembic: `057_lottery_admin_controls`
- Rollback images: `pre-lottery-2.0-20260722`

## 10–16. Manual write + idempotent second pass

Per lottery (5,6,4), two passes:

| Metric | Pass 1 | Pass 2 |
|--------|--------|--------|
| fetched | 9 | 9 |
| new / inserted | 0 / 0 | 0 / 0 |
| updated | 0 | 0 |
| unchanged | 9 | 9 |
| conflicted | 0 | 0 |
| errors | 0 | 0 |

Counts before/after: **91931 / 388788** (no change — API already aligned).

## 17–20. Scheduler

- Mode: `guarded_write`, enabled=true
- Confirmation: `ENABLE GUARDED WRITE ON jaios`
- run-now: `guarded_write_ok`, circuit **closed**, inserted=0, draws_after=91931
- Redis lock acquired per tick; no concurrent conflicts observed
- Interval: 60 minutes; next_run set after tick
- 6h monitor started on VPS: `/var/jaios/lottery-bake/lottery-2.0-stageb-20260722/monitor/`

## 21. Per-lottery sync state (final)

| Lottery | SYNC | AUTO_WRITE |
|---------|------|------------|
| Leidsa (5) | true | true |
| Loteka (6) | true | true |
| Loteria Nacional (4) | true | true |
| All others (47) | false | false |
| Quiniela Real (13) | false | false |
| La Primera Tarde / La Suerte MD (20/21) | false | false |

## Global flags (final)

```
LOTTERY_MODULE_ENABLED=true
LOTTERY_SCHEDULER_ENABLED=true
LOTTERY_SCHEDULER_MODE=guarded_write
LOTTERY_SYNC_ENABLED=true
LOTTERY_SYNC_WRITE_ENABLED=true
LOTTERY_SYNC_AUTOMATIC_WRITE_ENABLED=true
```

## 22–27. Counts / modules / Nacional Día

- Before & after Stage B writes: 50 / 91931 / 388788
- Nacional Día **not** modified (20/21 remain sync/auto false)
- Login, lottery, dashboard, prices, oportunidades → 200
- Rollback available via dump + `pre-lottery-2.0-20260722` images

## Residual risks

1. Quiniela Real `last_draw_date=2099-07-01` metadata anomaly (excluded from Stage B).
2. Scheduler dry-run still **fetches** broader API window; **writes** gated by `is_auto_write_enabled` (only 3).
3. Synthesis LLM unavailable — structured tool answers only.
4. 6h soak continues via VPS monitor; review `monitor_6h.log` after window.

## Stop

Stage B complete. **Do not start Stage C** without new authorization.
