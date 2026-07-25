# Pre-J11A — SQLite Configuration Fix (TD-001)

## Problem

Hardcoded laptop path:

`/Users/faustosantana/Projects/lottery-history-scraper/data/lottery.db`

appeared in:

- `backend/app/api/v1/lottery.py` (sync dry-run)
- `backend/app/services/lottery_sync_service.py`
- `backend/app/services/lottery_sync_writer.py`

## Solution

Central resolver: `backend/app/lottery/sync_sqlite_config.py`

| Priority | Source |
|----------|--------|
| 1 | Explicit `sqlite_path` argument |
| 2 | `settings.lottery_sync_sqlite_path` / `LOTTERY_SYNC_SQLITE_PATH` |
| 3 | `LotterySyncSqliteConfigError` — **no silent fallback** |

Validations: exists, is file, readable (configurable).

## Environment

```bash
export LOTTERY_SYNC_SQLITE_PATH=/path/to/snapshot.db
```

DEV/TEST/PROD must set distinct values. CI/tests use temp files.

## Exceptions (documented)

| Path pattern | Status |
|--------------|--------|
| Docs under `docs/lottery/**` mentioning historical laptop paths | Evidence only — not runtime |
| `lottery_sync_gate_backup_dir` default `/var/jaios/backups/...` | Server path default for prod gates — not a laptop SQLite snapshot; overridable via env |
| Optional test env `LOTTERY_STAGING_BACKUP_DIR` | Local staging dumps; skip if unset |

## Tests

`backend/tests/test_pre_j11a_sqlite_config.py`
