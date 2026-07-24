# Phase H — Change Plan (Gate 4)

**Fecha:** 2026-07-24  
**Entorno objetivo:** https://jaios.justech.do (`/opt/jaios-app`)  
**Autorización:** Fase H — desplegar solo si Gates 0–4 PASS  

---

## Gates previos

| Gate | Resultado | Notas |
|------|-----------|-------|
| 0 Producción audit | PASS | Entrypoint real: `uvicorn app.main:app`. No slim. |
| 1 Paridad stack | PASS | Overlay bake sobre `lottery-position-multi-20260723b` + FE build host. Sin stub admin-nav. |
| 2 RC final + smoke | PASS | 47 tests locales; smoke parity API/chat sobre BD prod (contenedor temporal). |
| 3 Backup/rollback | PASS | Dump Fc 36MB SHA256 OK; tags `rollback-pre-numeric-relations-20260724`. Snapshot proveedor: no automatizado (equivalente documentado). |
| 4 Este plan | PASS | |

---

## Archivos / artefactos que cambian en Producción

1. `/opt/jaios-app/docker-compose.harden.yml` — pins de imagen backend/frontend/worker → `numeric-relations-20260724`
2. Contenedores recreados: `backend`, `frontend`, `lottery-sync-worker`
3. Host FE source: página `frontend/.../numeric-relations/page.tsx` (ya copiada para bake; no hot-patch runtime)

**No se modifican:** sincronizador (código), flags `LOTTERY_SYNC_*` en `.env`, registros históricos, fórmulas 1..100.

---

## Servicios reiniciados

- `jaios-app-backend-1`
- `jaios-app-frontend-1`
- `jaios-app-lottery-sync-worker-1` (misma imagen backend; sin cambio de lógica sync)

No reiniciar postgres/redis/gateway salvo fallo.

---

## Migraciones

Ninguna nueva. Alembic permanece en `060_lottery_ai_alerting_closeout`.

---

## Impacto estimado

- Bajo: feature admin + tool chat NR.
- Lectura histórica adicional en analyze.
- Sin escritura de draws.

## Ventana / tiempo

- Ventana: inmediata controlada  
- Estimado: 15–25 min (up -d + smoke)

---

## Orden exacto de comandos

```bash
cd /opt/jaios-app
cp docker-compose.harden.yml docker-compose.harden.yml.bak-pre-numeric-relations-20260724
# set images to numeric-relations-20260724 for backend, frontend, lottery-sync-worker
docker compose -f docker-compose.yml -f docker-compose.harden.yml up -d backend frontend lottery-sync-worker
curl -sf https://jaios.justech.do/api/v1/health
# smoke Gate 6
```

---

## Criterios de éxito

- Health 200; openapi incluye `/lottery/admin/numeric-relations/*`
- Panel NR 200 (auth)
- Casos 26/34/45 OK; 403 usuario; chat multi 1 tool; clarify bare
- `LOTTERY_SYNC_WRITE_ENABLED` sigue `true` (sin cambio)
- Conteos draws no disminuyen

## Criterios de rollback

Cualquier fallo de la sección ROLLBACK AUTOMÁTICO de la autorización Fase H → restaurar tags `rollback-pre-numeric-relations-20260724` y recreate.

---

## Confirmaciones

- Sync intacto (sin overlay de `lottery_sync*`)
- `LOTTERY_SYNC_WRITE_ENABLED` no cambia
- Histórico no alterado / no merge de draws
- Metodología 1..100 intacta
