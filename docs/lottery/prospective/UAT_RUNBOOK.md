# UAT Runbook — Prospective Pilot

1. Confirm APP_ENV is development/uat (not production).
2. Apply Alembic `062_lottery_prospective_pilot` **only** on DEV/UAT DB.
3. POST `/api/v1/pilot/configurations` then `/activate`.
4. Sync/load input results for the day.
5. POST `/prospective-validation/run-daily` with complete numbers.
6. Review primary / multi-fuerte on `/lottery/prospective-pilot`.
7. prepare-lock → lock before draw; verify `/integrity`.
8. After draws, evaluate (or `/evaluate-pending`).
9. Review metrics, comparison, audit-log.
10. Confirm locked prediction cannot be edited.
11. Repeat daily.

## Rollback
Pause pilot, disable scheduler, do not delete locked rows; CANCELLED/EXPIRED if needed. Downgrade migration only on empty DEV DB.
