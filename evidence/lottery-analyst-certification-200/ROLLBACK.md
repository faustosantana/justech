# Rollback — LOTTERY_ANALYST_CERTIFIED_2026_1

## Exact restore path

```bash
# 1) Fetch certified tag
cd /opt/jaios-app
git fetch origin refs/tags/lottery-analyst-certified-2026.1:refs/tags/lottery-analyst-certified-2026.1

# 2) Selective bake from frozen UX tag (same commit as certified)
git archive lottery-ia-ux-v2.4.5.3 scripts/deploy_lottery_ia_selective.sh | tar -x -C /tmp
BASE_IMAGE=jaios-app-backend:lottery-ia-ux-v2.4.5.3 \
  bash /tmp/scripts/deploy_lottery_ia_selective.sh lottery-ia-ux-v2.4.5.3

# 3) Optional DB restore (only if data corrupted)
# WARNING: destructive to current DB contents
# docker exec -i jaios-app-postgres-1 pg_restore -U jaios -d jaios --clean --if-exists \
#   < /var/jaios/backups/LOTTERY_ANALYST_CERTIFIED_2026_1_20260728_031519.dump
```

## Verify after rollback

- `docker ps` shows `jaios-app-backend:lottery-ia-ux-v2.4.5.3` healthy
- Hermes `/health` → 200
- Motor: 35+14→54 and 39+58→94
- Chat smoke: last 22 → 2026-07-20 Gana Más
