# PRODUCCIÓN BETA 2.0 — Deploy controlado

**Veredicto: PRODUCCIÓN BETA ACTIVA**

## Versión desplegada

| Campo | Valor |
|-------|-------|
| Commit | `7ccb262d375169ec606d7789328f5d1f00e05514` |
| Tag | `lottery-analyst-2.0.0-beta` |
| Imagen | `jaios-app-backend:lottery-analyst-2.0.0-beta` |
| Digest | `sha256:138dd1c41f82eeec3faa4f6051a7274ad1936c63b6135692e5e85725efe110b3` |
| Origen certificado | `jaios-app-backend:lottery-analyst-2.0.0-dev` (mismo digest) |

## Backup / rollback

| Artefacto | Ruta |
|-----------|------|
| Backup completo | `/opt/jaios/backups/lottery-analyst-2.0-beta-20260728T204448Z/` |
| Imagen rollback | `jaios-app-backend:pre-beta20-rollback-20260728T204448Z` (`sha256:69ca7057a9be…`) |
| Compose backup | `/opt/jaios-app/docker-compose.harden.yml.bak-pre-beta20-20260728T204448Z` |
| Chat tables dump | `…/db/lottery_chat_tables.sql` |

### Rollback command

```bash
cd /opt/jaios-app && \
cp /opt/jaios-app/docker-compose.harden.yml.bak-pre-beta20-20260728T204448Z /opt/jaios-app/docker-compose.harden.yml && \
docker compose -f docker-compose.harden.yml up -d --no-deps --force-recreate backend lottery-sync-worker && \
docker network connect jaios-app_jaios-net jaios-app-backend-1 || true
docker network connect jaios-app_jaios-net jaios-app-lottery-sync-worker-1 || true
```

## Smoke (producción)

14/14 PASS · HTTP 500 = 0 · fallback genérico = 0

- 78+02 mismo día ✅
- ¿En cuáles loterías? ✅ (pair conservado, `reuse_evidence=true`)
- ¿Y en qué posiciones? ✅
- Follow-up «Dame más detalles» ✅
- TTL expiración 10 min ✅
- Consulta individual 35 ✅
- Comparación 22 vs 38 ✅

Providers observados: `huawei_modelarts`, `evidence_reuse`

## Servicios

- backend: healthy · imagen beta 2.0
- lottery-sync-worker: healthy
- frontend / gateway / postgres / redis / hermes: up

## Nota operativa

Tras `force-recreate`, el backend quedó un momento en `jaios-app_default` sin DNS a Postgres; se reconectó a `jaios-app_jaios-net` (fix aplicado y documentado en el backup).
