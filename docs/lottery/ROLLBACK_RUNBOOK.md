# Rollback Runbook — Lottery Official Bake

## Artifacts

- DB backup: `/var/jaios/backups/pre_lottery_official_bake_20260722_220216.dump`
- Image tags: `pre-lottery-official-20260722` (backend + frontend)
- Evidence: `/var/jaios/lottery-bake/20260722/rollback/`

## Immediate rollback (images only — preferred)

```bash
cd /opt/jaios-app
docker tag jaios-app-backend:pre-lottery-official-20260722 jaios-app-backend:latest
docker tag jaios-app-frontend:pre-lottery-official-20260722 jaios-app-frontend:latest
docker compose up -d --force-recreate --no-deps backend frontend
curl -sf https://jaios.justech.do/api/v1/health
curl -s -o /dev/null -w "%{http_code}\n" https://jaios.justech.do/login
curl -s -o /dev/null -w "%{http_code}\n" https://jaios.justech.do/dashboard
curl -s -o /dev/null -w "%{http_code}\n" https://jaios.justech.do/dgcp
curl -s -o /dev/null -w "%{http_code}\n" https://jaios.justech.do/prices
```

Note: rolling backend to pre-lottery image removes Lottery from the API until re-baked. DB lottery tables remain (harmless).

## Re-enable Lottery after image rollback

Rebuild/redeploy `lottery-official-20260722` as `latest` and recreate.

## Database restore (only if data corruption)

```bash
cd /opt/jaios-app
# STOP writes / confirm maintenance window first
docker compose exec -T postgres pg_restore -U jaios -d jaios --clean --if-exists \
  /path/copied/into/container/pre_lottery_official_bake_20260722_220216.dump
```

Prefer image rollback first; restore DB only if counts/schema are wrong.

## Validation after rollback

1. Login / dashboard
2. DGCP + Prices
3. API health
4. If Lottery expected: `/lottery` + dashboard draws count
