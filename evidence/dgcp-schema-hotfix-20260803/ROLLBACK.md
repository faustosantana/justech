# Rollback — DGCP schema hotfix DEV

**Backup:** `evidence/dgcp-schema-hotfix-20260803/backup/jaios_lottery_dev_20260803T030544Z.dump`

```bash
# Restore full DEV DB (destructive to current DEV only)
docker exec -i jaios-lottery-pg-dev pg_restore -U jaios -d jaios_lottery_dev --clean --if-exists \
  < evidence/dgcp-schema-hotfix-20260803/backup/jaios_lottery_dev_20260803T030544Z.dump
```

Alembic version at backup: see `alembic_version_20260803T030544Z.txt` (`066_reconcile_dgcp_opp`).

Downgrade of 066 is intentionally a no-op — restore dump instead of dropping columns.
