# C5 — History Sync Validation (DEV only)

## Sync

| Field | Value |
|-------|--------|
| Target | `jaios_lottery_dev` @ host `127.0.0.1:5433` |
| Script | `backend/scripts/dev_incremental_sync_c5.py` |
| Range | 2026-07-22 .. 2026-07-23 |
| Source | `api.elboletoganador.com` (read) |
| Production | **not touched** |
| Draws before | **91,927** |
| Draws after | **91,941** |
| Rows added | **14** (7 lotteries × 2 days) |
| Duplicates | 0 skipped_existing |
| FEATURED_SEVEN UUIDs | validated unchanged |
| Evidence | `evidence/c5_dev_sync_report.json` |
| Rollback | delete draw_ids listed in `rollback_delete_draw_ids` |

Official sync writer blocks DEV writes by design; this script is a **validation-only DEV incremental loader** with hard DSN guards.

## Case reconstruction

### 22-Jul-2026 observations

| Lottery | UUID | Source ref | Numbers | Match manual |
|---------|------|------------|----------|--------------|
| New York 2:30 | `1c488641-adb6-4790-89e7-879d361da7cc` | 226039 | **35**, 61, 45 | NY Día=35 ✓ |
| Loteria Nacional | `0118037f-8f8b-4a82-899c-42cd50b6e194` | 226060 | **14**, 7, 16 | Nacional=14 ✓ |

### Structural prediction

```
35 → T1 companions include 54
54 → T2 neighbors include 14
→ FUERTE OFICIAL = 54
```

Lab coincidence after sync: **SI_FUERTE_OFICIAL**

### 23-Jul-2026 — Gana Más appearance of 54

| Field | Value |
|-------|--------|
| Lottery | **Gana Mas** |
| UUID | `43250709-ee65-476f-91f6-cb8438f49d65` |
| Draw date | 2026-07-23 |
| Draw id | `f18eb0a7-eadb-4979-9352-e2b547dd388c` |
| Source reference | `226103` |
| Numbers | **54**, 19, 77 |
| Position of 54 | **1** (1ro) |
| Source API hora | `14:43:56` (payload) |
| Invented? | **NO** — present in upstream API and inserted verbatim |

## Conclusion

C5 is **fully closed**: structural fuerte oficial 54 **and** historical confirmation that 54 appeared in Gana Más the next day.
