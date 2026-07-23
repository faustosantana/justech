# Stage B Monitoring Evidence

**Monitor replacement PID:** `2641006`  
**Path:** `/var/jaios/lottery-bake/lottery-2.0-stageb-20260722/monitor/`

## Original monitor (2612789)

| Field | Value |
|-------|-------|
| Status | **FAILED_IMMEDIATE** |
| Reason | `/tmp/stageb_monitor_6h.sh` missing after container/tmp cleanup |
| Evidence | `ORIGINAL_MONITOR_FAILURE.txt` |

A durable replacement was started under `/var/jaios/.../monitor/stageb_monitor_6h.sh` (not `/tmp`) to complete the required 6-hour window. This is not a restart of a healthy process — the original never collected samples.

## Replacement window (completed)

| Field | Value |
|-------|-------|
| started_at (UTC) | 2026-07-22T23:27:05Z |
| finished_at (UTC) | 2026-07-23T05:13:22Z |
| duration_sec | **20777** (~5 h 46 min) |
| samples | **24 / 24** |
| process | stopped after `MONITOR END` |

## Per-sample collection

Each sample logged: draws/numbers, flags for sources 4/5/6/13/20/21, recent `lottery_sync_runs`, scheduler JSON, docker_stats placeholder, `health=200`.

## Aggregate — sync runs in window

Window: `2026-07-22 23:27:05Z` → `2026-07-23 05:15:00Z`

| Metric | Value |
|--------|------:|
| Runs | 22 listed (26 in broader SQL agg to 06:00) |
| Completed / failed | 26 / 0 (agg) |
| Inserts | **0** |
| Changed / updates | **0** |
| Unchanged | 1188 (agg) |
| Conflicts | 0 |
| Errors | 0 |
| Write-enabled runs | **1** (`2026-07-22T23:39Z`, new=0, inserted=0) |
| Dry-run runs after | 21+ (write_enabled=false) |

### Draw / number counts

| Metric | Start | End |
|--------|------:|----:|
| draws | 91931 | 91931 |
| numbers | 388788 | 388788 |

`MAX(draw_date)` for sources 4/5/6 remained **2026-07-21**. No draws dated ≥ 2026-07-22 in DB.

## Per lottery (flags stable all 24 samples)

| source_id | Name | SYNC | AUTO_WRITE |
|-----------|------|------|------------|
| 4 | Loteria Nacional | true | true |
| 5 | Quiniela Leidsa | true | true |
| 6 | Quiniela Loteka | true | true |
| 13 | Quiniela Real | false | false |
| 20 | La Primera Tarde | false | false |
| 21 | La Suerte MD | false | false |

Other 47 lotteries remained without auto-write (only these three enabled).

## Locks / checkpoints / circuit

- Redis sync lock used per tick; no prolonged `lock_stale` block observed in samples.
- Checkpoints present on sync run rows; no insert IDs (no writes).
- **Circuit:** after ~56 min from `write_enabled_since=2026-07-22T23:37:40Z`, ticks set `circuit_reason=write_flag_timeout` (safety: `lottery_sync_write_flag_max_minutes`). Effective behavior: subsequent ticks **dry-run only** (`write_enabled=false`).
- `circuit_state` reported as `closed` in JSON while reason stayed `write_flag_timeout` (runtime write block without leaving permanent open in all samples — see code path in `lottery_scheduler_service.py`).

## Observed API novelty without DB insert

Dry-run `records_new` climbed **0 → 1 → 3 → 6** during the window while inserts stayed **0**, because write path was blocked by **write_flag_timeout**.  
Therefore: source appeared to publish new candidates, but Stage B did **not** persist them.

## First legitimate new draw gate

| Status | Detail |
|--------|--------|
| **PENDING REAL DRAW (validated insert)** | No `records_inserted > 0` in Production during the soak |
| Note | API novelty seen in dry-run was **not** written; not counted as validated insert |

No artificial draws were created.

## Resources / dependencies (samples)

| Check | Result |
|-------|--------|
| Public health | `health=200` on all 24 samples |
| Backend / worker | `worker_running=true` in scheduler payload |
| PostgreSQL | queries succeeded every sample; counts stable |
| Redis | locks acquired (no systemic lock failure) |
| Gateway | health 200 via public check |
| CPU / RAM / docker_stats | monitor logged `docker_stats` header; no sustained outage signal in samples |

## Risks surfaced by soak

1. **`write_flag_timeout`** disabled automatic writes ~1h after enabling Stage B flags — incompatible with multi-hour soak / overnight sync unless TTL is raised or `write_enabled_since` is refreshed intentionally.
2. New source candidates observed in dry-run were **not** inserted — first real insert validation remains open.
3. Dashboard “hoy” / Real 2099 issues remain out of this monitor’s scope (Lottery 3.0 Phase 0).

## Stop

Monitoring window complete. Evidence collected; Stage B soak does not block Lottery 3.0 development.
