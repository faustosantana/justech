# Lottery 2.0 — Phase 1 audit findings

## Backup

- Path: `/var/jaios/backups/pre_lottery_2_0_20260722_222139.dump`
- Evidence: `/var/jaios/lottery-bake/lottery-2.0-phase1-20260722_222047/`

## Counts (pre-change)

- Lotteries: 50
- Draws: 91,931
- Numbers: 388,788
- Alembic: `056_lottery_scheduler_operations`
- Usable (active ∧ ¬aggregate): 49
- Aggregate inactive: 1

## Why the UI showed fewer than 50

1. Search page used `lotteries.slice(0, 40)` — hard cap of 40.
2. Catalog defaulted to `activeOnly=true` and relied on `/lotteries` without visibility flags.
3. API default `limit=50` and no `is_visible` / `is_searchable` / `is_ai_enabled` separation.
4. Aggregate lottery (source_id 30) is inactive by design.

## Decision

Introduce independent flags in migration `057_lottery_admin_controls` and admin UI at `/lottery/admin/lotteries`.
