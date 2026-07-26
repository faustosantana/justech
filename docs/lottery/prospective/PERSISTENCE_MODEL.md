# Persistence Model

## Postgres (Alembic 062)
Schema `jaios`: lottery_pilot_configurations, lottery_prospective_runs, lottery_prospective_audit_logs, lottery_pilot_daily_snapshots.

Models: `app/models/lottery_prospective.py`

## DEV/UAT SQLite mirror
`artifacts/prospective/pilot_dev_uat.sqlite` (or `LOTTERY_PROSPECTIVE_DB`) for local/tests.

## Gate
`assert_not_production()` — APP_ENV production raises.
