# Real metadata 2099 — Audit (read-only)

**Date:** 2026-07-22  
**Lottery:** Quiniela Real (`source_id=13`)  
**Action:** Audit only — **no metadata write**, sync remains disabled.

## Findings

| Field | Value |
|-------|-------|
| Table | `lottery_lotteries` |
| Row id | `205c58d2-cfcf-44e6-894d-97358b3d540b` |
| `last_draw_date` (metadata) | **2099-07-01** |
| `draw_count` (metadata) | **4152** |
| `first_draw_date` | 2015-01-02 |
| `is_sync_enabled` / `is_auto_write_enabled` | **false / false** |

### Actual draws table (`lottery_draws`)

| Metric | Value |
|--------|------:|
| MIN(draw_date) | 2015-01-02 |
| MAX(draw_date) | **2026-07-21** |
| COUNT(*) | **4118** |
| Rows with draw_date = 2099-07-01 | **0** |
| Future draws (> today) | **0** |

## Origin

- The anomalous date lives in **lottery metadata** (`lottery_lotteries.last_draw_date`), not in historical draw rows.
- No evidence of a real 2099 draw in `lottery_draws`.
- Likely caused by a bad refresh of denormalized counters/dates (importer/sync metadata update) rather than an adapter returning 2099 results.
- `draw_count` metadata (4152) also **diverges** from live count (4118).

## Impact

| Surface | Impact |
|---------|--------|
| Dashboard / catalog “last result” | Can show **2099-07-01** as last date (misleading) |
| Lottery IA `get_draw_count` / freshness | Can report coverage until 2099 (seen in UAT Q9/Q12) |
| Sync Stage B | **None** — Real remains SYNC/AUTO_WRITE false |
| Historical numbers integrity | **Unaffected** — 4118 draws through 2026-07-21 intact |

## Recommended correction (not applied)

```sql
-- Proposed only after explicit authorization
UPDATE lottery_lotteries l
SET
  draw_count = s.cnt,
  first_draw_date = s.min_d,
  last_draw_date = s.max_d,
  updated_at = now()
FROM (
  SELECT lottery_id, COUNT(*)::int AS cnt, MIN(draw_date) AS min_d, MAX(draw_date) AS max_d
  FROM lottery_draws
  WHERE lottery_id = '205c58d2-cfcf-44e6-894d-97358b3d540b'
  GROUP BY lottery_id
) s
WHERE l.id = s.lottery_id;
```

Expected after fix: `last_draw_date = 2026-07-21`, `draw_count = 4118`.

## Controls kept

- `SYNC_ENABLED=false`
- `AUTO_WRITE_ENABLED=false`
- Nacional Día untouched

## Repair status (Lottery 3.0)

Alembic revision `058_lottery_3_0_platform` recomputes all lottery metadata from `lottery_draws` on upgrade.
Admin API: `POST /api/v1/lottery/admin/metadata/recompute` (optional targeted or full).
Deploy requires migration bake — not applied by this documentation alone.
