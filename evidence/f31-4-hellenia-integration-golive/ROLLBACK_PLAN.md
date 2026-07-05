# Rollback Plan — Hellenia PROD Promotion

## Before deploy

1. `./scripts/backup-hellenia-prod.sh` (or equivalent PROD backup)
2. Verify backup with verify script
3. Record backup path in deploy log

## Deploy sequence (when approved)

```bash
# TEST already validated — same commit on PROD
git checkout feature/f31-1-justech-modules
rsync custom/ to PROD VPS
docker compose run odoo -d hellenia_prod -u justech_modules,hellenia_governance,justech_admin --stop-after-init
```

## Rollback

1. Stop odoo container
2. Restore PostgreSQL from backup
3. Restore filestore if needed
4. Restore custom/ from backup tarball
5. Restart stack
6. Verify healthcheck PROD

## Partial rollback

- Uninstall justech_admin / hellenia_governance only if needed (last resort)
- Prefer full DB restore for fiscal safety
